"""
Discord AI Study Bot
Configuration Module - Centralized settings management
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration class"""

    # Discord Settings
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_APPLICATION_ID = os.getenv('DISCORD_APPLICATION_ID')
    DISCORD_PUBLIC_KEY = os.getenv('DISCORD_PUBLIC_KEY')
    DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')

    # AI Model Settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')   # groq | gemini
    LLM_MODEL = os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile')

    # Database Settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///study_bot.db')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # Environment Settings
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Bot Configuration
    BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
    COMMAND_SYNC_GUILDS = os.getenv('COMMAND_SYNC_GUILDS')

    # Study Session Settings
    POMODORO_FOCUS_MINS = int(os.getenv('POMODORO_FOCUS_MINS', '25'))
    POMODORO_BREAK_MINS = int(os.getenv('POMODORO_BREAK_MINS', '5'))
    QUIZ_TIMEOUT_SECS = int(os.getenv('QUIZ_TIMEOUT_SECS', '60'))
    MAX_SESSION_HOURS = int(os.getenv('MAX_SESSION_HOURS', '4'))

    # Voice & Transcription
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
    VOICE_TIMEOUT_SECS = int(os.getenv('VOICE_TIMEOUT_SECS', '30'))
    AUTO_TRANSCRIBE = os.getenv('AUTO_TRANSCRIBE', 'true').lower() == 'true'

    # Vector Database
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './chroma_data')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

    # File Upload Limits
    MAX_PDF_SIZE_MB = int(os.getenv('MAX_PDF_SIZE_MB', '25'))
    MAX_PDFS_PER_GUILD = int(os.getenv('MAX_PDFS_PER_GUILD', '10'))

    # Rate Limiting
    GEMINI_RATE_LIMIT = int(os.getenv('GEMINI_RATE_LIMIT', '15'))
    QUIZ_COOLDOWN_SECS = int(os.getenv('QUIZ_COOLDOWN_SECS', '30'))

    # Features (Enable/Disable)
    ENABLE_VOICE_RECORDING = os.getenv('ENABLE_VOICE_RECORDING', 'true').lower() == 'true'
    ENABLE_AUTO_SUMMARIES = os.getenv('ENABLE_AUTO_SUMMARIES', 'true').lower() == 'true'
    ENABLE_GAMIFICATION = os.getenv('ENABLE_GAMIFICATION', 'true').lower() == 'true'
    ENABLE_SCHEDULING = os.getenv('ENABLE_SCHEDULING', 'true').lower() == 'true'

    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        errors = []

        if not cls.DISCORD_BOT_TOKEN or cls.DISCORD_BOT_TOKEN == 'MISSING_GET_FROM_DISCORD_DEVELOPER_PORTAL':
            errors.append("DISCORD_BOT_TOKEN is missing or not set properly")

        if not cls.GEMINI_API_KEY or cls.GEMINI_API_KEY.startswith('your_'):
            errors.append("GEMINI_API_KEY is missing or not set properly")

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

        return True

# Create global config instance
config = Config()