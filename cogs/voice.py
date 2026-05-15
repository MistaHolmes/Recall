"""
cogs/voice.py — Voice capture, PCM buffering, Whisper transcription

Architecture (clean rewrite):
  ┌──────────────┐   RTP frames   ┌─────────────────────────────────┐
  │ Discord voice│ ─────────────► │ BasicSink._audio_cb()           │
  │  gateway     │                │  appends raw PCM per user       │
  └──────────────┘                └────────────┬────────────────────┘
                                               │ every 30 s
                                               ▼
                                  ┌─────────────────────────────────┐
                                  │ _flush_loop() task              │
                                  │  pop PCM → WAV → _transcribe()  │
                                  │  → append to session transcript │
                                  └─────────────────────────────────┘

Transcription backend (priority order):
  1. Groq  whisper-large-v3-turbo  (requires GROQ_API_KEY)
  2. Local openai-whisper          (requires: pip install openai-whisper)

Public API used by other cogs:
  • cog.join_voice(guild_id, channel, text_channel=None)
  • cog.leave_voice(guild_id)
"""

import asyncio
import io
import logging
import os
import tempfile
import wave
from functools import lru_cache

import discord
from discord import app_commands
from discord.ext import commands, voice_recv

from ai.summarizer import generate_voice_summary
from utils import embeds
from config import config

log = logging.getLogger("cog.voice")

# ── Discord PCM format ────────────────────────────────────────────────────────
_CHANNELS     = 2        # stereo
_SAMPLE_WIDTH = 2        # bytes per sample (16-bit)
_FRAME_RATE   = 48_000   # Hz
# Minimum bytes to bother transcribing (≈ 0.5 s of stereo audio)
_MIN_BYTES    = _FRAME_RATE * _CHANNELS * _SAMPLE_WIDTH // 2
# Seconds between periodic PCM flushes
_FLUSH_INTERVAL = 30

# ── Local Whisper model (loaded lazily, cached) ───────────────────────────────

@lru_cache(maxsize=1)
def _local_whisper():
    try:
        import whisper
        name = config.WHISPER_MODEL
        log.info(f"Loading local Whisper model '{name}' …")
        return whisper.load_model(name)
    except ImportError:
        log.warning("openai-whisper not installed; local transcription unavailable")
        return None


# ── VoiceCog ──────────────────────────────────────────────────────────────────

class VoiceCog(commands.Cog):
    """Per-guild voice recording, transcription, and summary delivery."""

    _CONNECT_RETRIES = 3    # total attempts before giving up
    _CONNECT_TIMEOUT = 30   # seconds Discord has to complete the handshake

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id → { user_id → bytearray of raw PCM }
        self._pcm: dict[int, dict[int, bytearray]] = {}
        # guild_id → running flush-loop Task
        self._flush_tasks: dict[int, asyncio.Task] = {}
        # guild_id → accumulated transcript (standalone / no study session)
        self._standalone_tx: dict[int, str] = {}
        # guild_id → text channel supplied at /voicejoin time
        self._text_channels: dict[int, discord.TextChannel] = {}

    # =========================================================================
    # Audio sink callback
    # =========================================================================

    def _audio_cb(self, guild_id: int):
        """Return the callable voice_recv.BasicSink will invoke per RTP frame.

        Intentionally minimal: just append bytes.  No timestamps, no silence
        detection, no reconnect logic — that complexity lives elsewhere.
        """
        store = self._pcm.setdefault(guild_id, {})

        def _on_audio(user: discord.Member, data: voice_recv.VoiceData):
            if user is None or data.pcm is None:
                return
            buf = store.setdefault(user.id, bytearray())
            buf.extend(data.pcm)

        return _on_audio

    # =========================================================================
    # PCM → WAV → transcription
    # =========================================================================

    @staticmethod
    def _to_wav(pcm: bytes) -> io.BytesIO:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(_SAMPLE_WIDTH)
            wf.setframerate(_FRAME_RATE)
            wf.writeframes(pcm)
        buf.seek(0)
        return buf

    async def _transcribe(self, wav: io.BytesIO, user_id: int, guild_id: int) -> str:
        """Transcribe a WAV buffer → "[DisplayName]: text" or "".

        Never raises; returns "" on any failure so the caller can safely ignore.
        """
        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        name   = member.display_name if member else f"User{user_id}"

        # ── 1. Groq API ───────────────────────────────────────────────────────
        if config.GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=config.GROQ_API_KEY)
                wav.seek(0)
                raw = wav.read()
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: client.audio.transcriptions.create(
                        file=("audio.wav", raw, "audio/wav"),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    ),
                )
                text = (result if isinstance(result, str) else result.text).strip()
                if text:
                    log.info(f"Groq: {len(text)} chars from {name}")
                    return f"[{name}]: {text}"
                return ""
            except Exception as exc:
                log.warning(f"Groq transcription failed for {name}: {exc}")
                # fall through to local Whisper

        # ── 2. Local Whisper ──────────────────────────────────────────────────
        model = _local_whisper()
        if model is None:
            log.warning(f"No transcription backend available for {name}")
            return ""

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav.seek(0)
                f.write(wav.read())
                tmp_path = f.name
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: model.transcribe(tmp_path, fp16=False)
            )
            text = result.get("text", "").strip()
            if text:
                log.info(f"Local Whisper: {len(text)} chars from {name}")
                return f"[{name}]: {text}"
            return ""
        except Exception as exc:
            log.error(f"Local Whisper error for {name}: {exc}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def _flush(self, guild_id: int) -> None:
        """Pop all buffered PCM → transcribe → store in session or standalone."""
        buffers = self._pcm.pop(guild_id, {})
        if not buffers:
            return

        session = self.bot.active_sessions.get(guild_id)

        for user_id, raw in buffers.items():
            if len(raw) < _MIN_BYTES:
                continue
            wav  = self._to_wav(bytes(raw))
            text = await self._transcribe(wav, user_id, guild_id)
            if not text:
                continue
            if session:
                session["voice_transcript"] += f"\n{text}"
                log.debug(f"Appended {len(text)} chars to session transcript (guild {guild_id})")
            else:
                self._standalone_tx[guild_id] = (
                    self._standalone_tx.get(guild_id, "") + f"\n{text}"
                )
                log.debug(f"Appended {len(text)} chars to standalone transcript (guild {guild_id})")

    async def _flush_loop(self, guild_id: int, vc: voice_recv.VoiceRecvClient) -> None:
        """Flush PCM every _FLUSH_INTERVAL seconds until cancelled.

        CancelledError is swallowed — leave_voice() always calls _flush() once
        more after cancelling this task, so no audio is ever lost.
        """
        try:
            while True:
                await asyncio.sleep(_FLUSH_INTERVAL)
                if not vc.is_connected():
                    log.info(f"Flush loop: vc disconnected for guild {guild_id}, stopping")
                    break
                await self._flush(guild_id)
        except asyncio.CancelledError:
            pass   # leave_voice() will do a final _flush() after we return

    # =========================================================================
    # Connect / disconnect helpers
    # =========================================================================

    async def _connect(self, channel: discord.VoiceChannel) -> voice_recv.VoiceRecvClient:
        """Connect with retry, always clearing stale clients first.

        Raises ConnectionError after _CONNECT_RETRIES failures.
        """
        guild_id = channel.guild.id

        # Always force-disconnect any lingering vc.  A vc from a previous
        # timed-out handshake still holds a guild.voice_client reference and
        # will cause the next connect() to fail immediately.
        existing = channel.guild.voice_client
        if existing:
            log.debug(f"Clearing stale vc for guild {guild_id}")
            try:
                if hasattr(existing, "stop_listening"):
                    existing.stop_listening()
            except Exception:
                pass
            try:
                await existing.disconnect(force=True)
            except Exception:
                pass
            await asyncio.sleep(0.5)   # let Discord's gateway process the disconnect

        last_exc: Exception | None = None
        for attempt in range(1, self._CONNECT_RETRIES + 1):
            try:
                vc = await channel.connect(
                    cls=voice_recv.VoiceRecvClient,
                    timeout=self._CONNECT_TIMEOUT,
                    self_deaf=False,
                    self_mute=False,
                )
                log.info(
                    f"Voice connected: guild={guild_id} "
                    f"channel=#{channel.name} (attempt {attempt})"
                )
                return vc
            except Exception as exc:
                last_exc = exc
                log.warning(
                    f"Voice connect attempt {attempt}/{self._CONNECT_RETRIES} "
                    f"guild={guild_id}: {exc}"
                )
                half_open = channel.guild.voice_client
                if half_open:
                    try:
                        await half_open.disconnect(force=True)
                    except Exception:
                        pass
                if attempt < self._CONNECT_RETRIES:
                    await asyncio.sleep(2 * attempt)   # 2 s, 4 s

        raise ConnectionError(
            f"Voice connect failed after {self._CONNECT_RETRIES} attempts "
            f"(guild {guild_id}, channel #{channel.name})"
        ) from last_exc

    # =========================================================================
    # Public API (called by other cogs)
    # =========================================================================

    async def join_voice(
        self,
        guild_id: int,
        channel: discord.VoiceChannel,
        *,
        text_channel: discord.TextChannel | None = None,
    ) -> None:
        """Join *channel* and start buffering audio for *guild_id*.

        Safe to call when already connected — cancels the old flush-loop
        and reconnects cleanly.
        """
        # Stop and await any existing flush task so there is never more than one
        old = self._flush_tasks.pop(guild_id, None)
        if old and not old.done():
            old.cancel()
            try:
                await old
            except (asyncio.CancelledError, Exception):
                pass

        # Reset PCM store; preserve standalone transcript if partially collected
        self._pcm[guild_id] = {}
        if text_channel:
            self._text_channels[guild_id] = text_channel

        vc = await self._connect(channel)

        vc.listen(voice_recv.BasicSink(self._audio_cb(guild_id)))

        session = self.bot.active_sessions.get(guild_id)
        if session:
            session["voice_client"] = vc

        task = asyncio.create_task(
            self._flush_loop(guild_id, vc),
            name=f"voice-flush-{guild_id}",
        )
        self._flush_tasks[guild_id] = task
        log.info(f"join_voice complete: guild={guild_id} channel=#{channel.name}")

    async def leave_voice(self, guild_id: int) -> None:
        """Stop recording, transcribe remaining audio, and disconnect."""
        # 1. Stop flush loop
        task = self._flush_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        # 2. Final flush of remaining PCM
        await self._flush(guild_id)

        # 3. Disconnect
        guild = self.bot.get_guild(guild_id)
        vc    = guild.voice_client if guild else None
        if vc is None:
            session = self.bot.active_sessions.get(guild_id)
            if session:
                vc = session.get("voice_client")
        if vc:
            if hasattr(vc, "stop_listening"):
                try:
                    vc.stop_listening()
                except Exception:
                    pass
            try:
                await vc.disconnect(force=True)
                log.info(f"leave_voice complete: guild={guild_id}")
            except Exception as exc:
                log.warning(f"leave_voice disconnect error guild={guild_id}: {exc}")

    # =========================================================================
    # Slash commands
    # =========================================================================

    @app_commands.command(name="voicejoin", description="Make the bot join your voice channel")
    async def voice_join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                embed=embeds.error("You must be in a voice channel first."),
                ephemeral=True,
            )

        try:
            await interaction.response.defer(thinking=True)
        except (discord.NotFound, discord.HTTPException):
            log.warning("voicejoin: interaction expired before defer")

        channel_name = interaction.user.voice.channel.name
        try:
            await self.join_voice(
                interaction.guild_id,
                interaction.user.voice.channel,
                text_channel=interaction.channel,
            )
            embed = embeds.info(
                f"🎙️ Joined **{channel_name}**\n"
                "⚠️ Recording audio for transcription. "
                "Audio is processed and discarded immediately after each 30-second window."
            )
        except Exception as exc:
            log.error(f"voicejoin error: {exc}", exc_info=True)
            embed = embeds.error(f"Failed to join **{channel_name}**: {exc}")

        try:
            await interaction.followup.send(embed=embed)
        except (discord.NotFound, discord.HTTPException):
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="voiceleave", description="Make the bot leave the voice channel")
    async def voice_leave(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id

        try:
            await interaction.response.defer(thinking=True)
        except (discord.NotFound, discord.HTTPException):
            log.warning("voiceleave: interaction expired before defer")

        try:
            await self.leave_voice(guild_id)
            reply = embeds.info("👋 Left the voice channel.")
        except Exception as exc:
            log.error(f"voiceleave error: {exc}", exc_info=True)
            reply = embeds.error(f"Failed to leave voice channel: {exc}")

        try:
            await interaction.followup.send(embed=reply)
        except (discord.NotFound, discord.HTTPException):
            await interaction.channel.send(embed=reply)

        # ── Standalone summary (no active study session) ──────────────────────
        if guild_id not in self.bot.active_sessions:
            transcript = self._standalone_tx.pop(guild_id, "").strip()
            channel    = self._text_channels.pop(guild_id, None) or interaction.channel
            if transcript:
                await channel.send(embed=embeds.info("🔄 Generating voice meeting summary…"))
                try:
                    summary = await generate_voice_summary(transcript)
                    await channel.send(embed=embeds.session_summary("Voice Meeting", summary))
                except Exception as exc:
                    log.error(f"Voice summary error: {exc}", exc_info=True)
                    await channel.send(embed=embeds.error(f"Could not generate summary: {exc}"))
            else:
                await channel.send(
                    embed=embeds.info(
                        "ℹ️ No speech was captured during this session.\n"
                        "Make sure you are speaking **while the bot is in the channel**."
                    )
                )

    # =========================================================================
    # Auto-reconnect on unexpected disconnect
    # =========================================================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Re-join if the bot itself is kicked or disconnected unexpectedly.

        Fires only when:
          • the event belongs to the bot itself
          • the bot had a channel before and has none after  (= disconnected)
          • there is an active study session or an in-progress standalone recording
        """
        if member.id != self.bot.user.id:
            return

        guild_id = member.guild.id

        # Ignore connect / channel-move events
        if before.channel is None or after.channel is not None:
            return

        # Nothing worth reconnecting for
        if (
            guild_id not in self.bot.active_sessions
            and guild_id not in self._text_channels
        ):
            return

        log.warning(
            f"Bot unexpectedly disconnected from voice in guild {guild_id} "
            f"(was in #{before.channel.name}). Scheduling reconnect."
        )

        # Cancel the now-orphaned flush task
        task = self._flush_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

        # Reconnect as an independent task — immune to self-cancellation
        asyncio.create_task(
            self._auto_reconnect(guild_id, before.channel),
            name=f"voice-auto-reconnect-{guild_id}",
        )

    async def _auto_reconnect(
        self, guild_id: int, channel: discord.VoiceChannel
    ) -> None:
        """Re-join *channel* after an unexpected disconnect."""
        await asyncio.sleep(2)   # let Discord's gateway settle after the disconnect

        if (
            guild_id not in self.bot.active_sessions
            and guild_id not in self._text_channels
        ):
            log.info(f"Auto-reconnect for guild {guild_id} aborted (session ended)")
            return

        log.info(f"Auto-reconnecting to #{channel.name} in guild {guild_id}")
        try:
            await self.join_voice(
                guild_id,
                channel,
                text_channel=self._text_channels.get(guild_id),
            )
            log.info(f"Auto-reconnect successful for guild {guild_id}")
        except Exception as exc:
            log.error(f"Auto-reconnect failed for guild {guild_id}: {exc}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
