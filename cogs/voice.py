"""
cogs/voice.py — Voice channel join/leave and PCM audio capture
"""

import asyncio
import logging
import wave
import tempfile
import os
import discord
from discord import app_commands
from discord.ext import commands
from utils import embeds

log = logging.getLogger("cog.voice")


class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._voice_tasks: dict[int, asyncio.Task] = {}

    async def join_voice(self, guild_id: int, voice_channel: discord.VoiceChannel):
        """Join a voice channel and start capturing audio."""
        if guild_id in self._voice_tasks:
            return  # Already recording

        vc = await voice_channel.connect()
        session = self.bot.active_sessions.get(guild_id)
        if session:
            session["voice_client"] = vc

        # Start recording using discord.py sinks
        sink = discord.sinks.WaveSink()
        vc.start_recording(sink, self._finished_recording, guild_id)

        task = asyncio.create_task(self._chunk_flush_loop(guild_id, vc))
        self._voice_tasks[guild_id] = task
        log.info(f"Joined voice channel in guild {guild_id}: {voice_channel.name}")

    async def leave_voice(self, guild_id: int):
        """Leave voice and cancel capture."""
        task = self._voice_tasks.pop(guild_id, None)
        if task:
            task.cancel()

        session = self.bot.active_sessions.get(guild_id)
        vc = session.get("voice_client") if session else None
        if not vc:
            vc = self.bot.get_guild(guild_id).voice_client if self.bot.get_guild(guild_id) else None
        if vc and vc.is_connected():
            vc.stop_recording()
            await vc.disconnect()

    async def _finished_recording(self, sink: discord.sinks.WaveSink, guild_id: int):
        """Called by discord.py when stop_recording() is invoked."""
        session = self.bot.active_sessions.get(guild_id)
        if not session:
            return
        guild = self.bot.get_guild(guild_id)
        for user_id, audio in sink.audio_data.items():
            text = await self._transcribe_wav(audio.file, user_id, guild)
            if text:
                session["voice_transcript"] += f"\n{text}"
        # Clear buffers from memory immediately
        sink.audio_data.clear()

    async def _chunk_flush_loop(self, guild_id: int, vc: discord.VoiceClient):
        """Restart recording every 30s to flush audio to transcription."""
        try:
            while guild_id in self.bot.active_sessions:
                await asyncio.sleep(30)
                if not vc.is_connected():
                    break
                vc.stop_recording()
                await asyncio.sleep(0.5)
                if guild_id in self.bot.active_sessions:
                    sink = discord.sinks.WaveSink()
                    vc.start_recording(sink, self._finished_recording, guild_id)
        except asyncio.CancelledError:
            log.info(f"Voice chunk loop cancelled for guild {guild_id}")
        except Exception as e:
            log.error(f"Voice capture error: {e}")

    async def _transcribe_wav(self, wav_file, user_id: int, guild) -> str:
        """Transcribe a WAV file using local Whisper."""
        try:
            import whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
                wav_file.seek(0)
                f.write(wav_file.read())

            loop = asyncio.get_event_loop()
            model = whisper.load_model("base")
            result = await loop.run_in_executor(None, lambda: model.transcribe(tmp_path))
            os.remove(tmp_path)

            member = guild.get_member(user_id) if guild else None
            name = member.display_name if member else f"User{user_id}"
            return f"[{name}]: {result['text'].strip()}"
        except ImportError:
            log.warning("whisper not installed — voice transcription disabled")
            return ""
        except Exception as e:
            log.error(f"Transcription error: {e}")
            return ""

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="voicejoin", description="Make the bot join your voice channel")
    async def voice_join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message(
                embed=embeds.error("You must be in a voice channel first."), ephemeral=True
            )
        await interaction.response.defer(thinking=True)
        await self.join_voice(interaction.guild_id, interaction.user.voice.channel)
        await interaction.followup.send(
            embed=embeds.info(f"🎙️ Joined **{interaction.user.voice.channel.name}**\n⚠️ This bot is recording voice audio for transcription. Audio is deleted immediately after processing.")
        )

    @app_commands.command(name="voiceleave", description="Make the bot leave the voice channel")
    async def voice_leave(self, interaction: discord.Interaction):
        await self.leave_voice(interaction.guild_id)
        await interaction.response.send_message(embed=embeds.info("👋 Left the voice channel."))

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
