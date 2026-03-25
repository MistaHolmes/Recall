"""
cogs/voice.py — Voice channel join/leave, PCM capture, and Whisper transcription

Uses discord-ext-voice-recv (VoiceRecvClient + BasicSink) for discord.py 2.7+.
Audio is buffered per-user in memory and flushed to Whisper every 30 s.
"""

import asyncio
import io
import logging
import wave
import tempfile
import os
from functools import lru_cache
import discord
from discord import app_commands
from discord.ext import commands, voice_recv
from utils import embeds
from config import config

log = logging.getLogger("cog.voice")

# PCM format delivered by discord: 16-bit signed little-endian, stereo, 48 kHz
_PCM_CHANNELS    = 2
_PCM_SAMPLE_WIDTH = 2       # bytes — 16-bit
_PCM_FRAME_RATE  = 48_000   # Hz
# Minimum buffered bytes before we bother transcribing (~0.5 s of stereo audio)
_MIN_PCM_BYTES   = _PCM_FRAME_RATE * _PCM_CHANNELS * _PCM_SAMPLE_WIDTH // 2


@lru_cache(maxsize=1)
def _get_whisper_model():
    """Load and cache the Whisper model once for the process lifetime."""
    try:
        import whisper
        model_name = config.WHISPER_MODEL   # default: "base"
        log.info(f"Loading Whisper model: {model_name} (first call only)")
        return whisper.load_model(model_name)
    except ImportError:
        log.warning("openai-whisper not installed — transcription disabled")
        return None


class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._voice_tasks: dict[int, asyncio.Task] = {}
        # guild_id → {user_id: bytearray of accumulated PCM}
        self._pcm_buffers: dict[int, dict[int, bytearray]] = {}

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _make_audio_callback(self, guild_id: int):
        """Return a BasicSink callback that appends PCM per user."""
        loop = asyncio.get_event_loop()

        def on_audio(user, data: voice_recv.VoiceData):
            """Called by voice_recv for every received audio packet (~20 ms)."""
            if user is None or data.pcm is None:
                return
            buffers = self._pcm_buffers.setdefault(guild_id, {})
            if user.id not in buffers:
                buffers[user.id] = bytearray()
            buffers[user.id].extend(data.pcm)

        return on_audio

    async def _flush_buffers(self, guild_id: int) -> None:
        """Transcribe and clear all buffered PCM for the guild."""
        buffers = self._pcm_buffers.pop(guild_id, {})
        if not buffers:
            return
        session = self.bot.active_sessions.get(guild_id)
        if not session:
            return
        guild = self.bot.get_guild(guild_id)

        for user_id, pcm_data in buffers.items():
            if len(pcm_data) < _MIN_PCM_BYTES:
                continue
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wf:
                wf.setnchannels(_PCM_CHANNELS)
                wf.setsampwidth(_PCM_SAMPLE_WIDTH)
                wf.setframerate(_PCM_FRAME_RATE)
                wf.writeframes(bytes(pcm_data))
            wav_buf.seek(0)
            text = await self._transcribe_wav(wav_buf, user_id, guild)
            if text:
                session["voice_transcript"] += f"\n{text}"

    async def join_voice(self, guild_id: int, voice_channel: discord.VoiceChannel):
        """Join a voice channel and start capturing audio."""
        # Cancel any stale flush loop
        old_task = self._voice_tasks.pop(guild_id, None)
        if old_task and not old_task.done():
            old_task.cancel()

        # Disconnect any existing voice client (prevents Already-connected error)
        existing_vc = voice_channel.guild.voice_client
        if existing_vc and existing_vc.is_connected():
            try:
                if hasattr(existing_vc, "stop_listening"):
                    existing_vc.stop_listening()
            except Exception:
                pass
            await existing_vc.disconnect(force=True)

        # Connect using VoiceRecvClient so we can receive audio
        self._pcm_buffers[guild_id] = {}
        vc = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)

        session = self.bot.active_sessions.get(guild_id)
        if session:
            session["voice_client"] = vc

        # Attach a BasicSink that accumulates PCM data per user
        vc.listen(voice_recv.BasicSink(self._make_audio_callback(guild_id)))

        task = asyncio.create_task(self._chunk_flush_loop(guild_id, vc))
        self._voice_tasks[guild_id] = task
        log.info(f"Joined voice channel in guild {guild_id}: {voice_channel.name}")

    async def leave_voice(self, guild_id: int):
        """Leave voice and flush any remaining audio."""
        task = self._voice_tasks.pop(guild_id, None)
        if task:
            task.cancel()

        # Flush whatever PCM is still buffered
        await self._flush_buffers(guild_id)

        session = self.bot.active_sessions.get(guild_id)
        vc = session.get("voice_client") if session else None
        if not vc:
            g = self.bot.get_guild(guild_id)
            vc = g.voice_client if g else None
        if vc and vc.is_connected():
            if hasattr(vc, "stop_listening"):
                vc.stop_listening()
            await vc.disconnect()

    async def _chunk_flush_loop(self, guild_id: int, vc):
        """Flush buffered PCM to Whisper every 30 s while session is active."""
        try:
            while guild_id in self.bot.active_sessions:
                await asyncio.sleep(30)
                if not vc.is_connected():
                    break
                await self._flush_buffers(guild_id)
        except asyncio.CancelledError:
            log.info(f"Voice chunk loop cancelled for guild {guild_id}")
        except Exception as e:
            log.error(f"Voice capture error: {e}")

    async def _transcribe_wav(self, wav_file, user_id: int, guild) -> str:
        """Transcribe a WAV file using the cached local Whisper model."""
        model = _get_whisper_model()
        if model is None:
            return ""

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
                wav_file.seek(0)
                f.write(wav_file.read())

            # Run blocking transcription on a thread-pool executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: model.transcribe(tmp_path, fp16=False)
            )

            member = guild.get_member(user_id) if guild else None
            name = member.display_name if member else f"User{user_id}"
            text = result.get("text", "").strip()
            if not text:
                return ""
            log.info(f"Transcribed {len(text)} chars from {name}")
            return f"[{name}]: {text}"
        except Exception as e:
            log.error(f"Transcription error for user {user_id}: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)   # always clean up temp file

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="voicejoin", description="Make the bot join your voice channel")
    async def voice_join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message(
                embed=embeds.error("You must be in a voice channel first."), ephemeral=True
            )

        # Always defer first so Discord doesn't time out the interaction.
        try:
            await interaction.response.defer(thinking=True)
        except discord.NotFound:
            log.warning("voicejoin: interaction already expired before defer")

        # Wrap join_voice so any exception still resolves the "thinking..." bubble.
        channel_name = interaction.user.voice.channel.name
        try:
            await self.join_voice(interaction.guild_id, interaction.user.voice.channel)
            msg = (
                f"🎙️ Joined **{channel_name}**\n"
                "⚠️ Recording voice for transcription. Audio is deleted immediately after processing."
            )
            reply_embed = embeds.info(msg)
        except Exception as e:
            log.error(f"voicejoin error: {e}", exc_info=True)
            reply_embed = embeds.error(f"Failed to join voice channel: {e}")

        try:
            await interaction.followup.send(embed=reply_embed)
        except (discord.NotFound, discord.HTTPException):
            await interaction.channel.send(embed=reply_embed)

    @app_commands.command(name="voiceleave", description="Make the bot leave the voice channel")
    async def voice_leave(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            await self.leave_voice(interaction.guild_id)
            reply_embed = embeds.info("👋 Left the voice channel.")
        except Exception as e:
            log.error(f"voiceleave error: {e}", exc_info=True)
            reply_embed = embeds.error(f"Failed to leave voice channel: {e}")
        await interaction.followup.send(embed=reply_embed)

    # ── Auto-join when study session starts ───────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Auto-reconnect if disconnected while session is active
        guild_id = member.guild.id
        if guild_id not in self.bot.active_sessions:
            return

        vc: discord.VoiceClient = member.guild.voice_client
        if vc is None and guild_id in self._voice_tasks:
            log.warning(f"Voice client dropped in guild {guild_id}, attempting reconnect")
            self._voice_tasks.pop(guild_id, None)


async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
