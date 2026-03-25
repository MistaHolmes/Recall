# Updated Implementation Plan — AI Study Group Facilitator Bot
## Using Free Models & Modern Architecture

> **Goal:** Build a complete Discord AI study bot using free models in organized phases
> **Timeline:** Complete project in phases (originally 6-day plan condensed)
> **Key Change:** Replace OpenAI (paid) with Gemini + Hugging Face (free)

---

## 🏗️ System Architecture Overview

```
Discord Bot (discord.py)
    ↓
Phase 1: Basic Bot + Commands
    ↓
Phase 2: RAG Pipeline (Gemini + HuggingFace Embeddings)
    ↓
Phase 3: Quiz Engine (Gemini)
    ↓
Phase 4: Voice Transcription (Local Whisper)
    ↓
Phase 5: Gamification & Scheduling
    ↓
Phase 6: Polish & Testing
```

---

## 🔄 Technology Stack (Updated for Free Models)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Bot Framework** | Discord.py | Best Python Discord library |
| **LLM (Free)** | Google Gemini Pro | 15 req/min free tier, excellent quality |
| **Embeddings (Free)** | HuggingFace sentence-transformers | Free, runs locally or via API |
| **Voice Transcription** | OpenAI Whisper (Local) | Free, runs locally |
| **Vector Database** | ChromaDB | Free, local vector storage |
| **Database** | PostgreSQL | Free (local or ElephantSQL) |
| **Task Queue** | Celery + Redis | For background jobs |
| **Web Framework** | FastAPI | For internal API endpoints |

---

## 📦 Project Structure

```
study-bot/
├── bot.py                   # Main bot entry point
├── config.py               # Environment configuration
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Infrastructure setup
├── .env.example           # Environment template
│
├── cogs/                   # Discord command handlers
│   ├── __init__.py
│   ├── study.py           # /study start, /study end commands
│   ├── quiz.py            # /quiz command and reactions
│   ├── rag.py             # /ask command (Q&A)
│   ├── voice.py           # Voice channel management
│   └── admin.py           # /upload PDF, admin commands
│
├── ai/                     # AI pipeline (Free models)
│   ├── __init__.py
│   ├── gemini_client.py   # Google Gemini interface
│   ├── embeddings.py      # HuggingFace embeddings
│   ├── rag_pipeline.py    # Document processing & retrieval
│   ├── quiz_engine.py     # Quiz generation
│   └── summarizer.py      # Session summaries
│
├── db/                     # Database layer
│   ├── __init__.py
│   ├── database.py        # PostgreSQL connection & queries
│   ├── models.py          # Data models
│   └── schema.sql         # Database schema
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── embeds.py          # Discord embed builders
│   ├── audio.py           # Audio processing
│   └── logger.py          # Logging setup
│
└── tests/                  # Test files
    ├── test_gemini.py
    ├── test_rag.py
    └── test_quiz.py
```

---

## 🚀 Phase 1: Bot Foundation & Basic Commands (Day 1)

### Goals:
- ✅ Bot connects to Discord and stays online
- ✅ Basic slash commands work
- ✅ Database connection established
- ✅ Environment setup complete

### Tasks:
1. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install discord.py python-dotenv asyncpg
   ```

2. **Bot Registration & Permissions**
   - Create Discord application
   - Generate bot token
   - Set required permissions: `Send Messages`, `Use Slash Commands`, `Connect`, `Speak`, `Embed Links`
   - Enable intents: `MESSAGE_CONTENT`, `GUILD_VOICE_STATES`

3. **Basic Bot Structure**
   - `bot.py` - Main bot with cog loading
   - `config.py` - Environment variable management
   - Basic `/ping` and `/help` commands

4. **Database Setup**
   - PostgreSQL schema creation
   - Connection pool setup
   - Basic user registration

### Expected Output:
Bot responds to `/ping` with latency, connects to database successfully.

---

## 🧠 Phase 2: RAG Pipeline with Free Models (Day 2)

### Goals:
- ✅ PDF upload and processing works
- ✅ Gemini API integration functional
- ✅ `/ask` command returns relevant answers
- ✅ ChromaDB stores and retrieves documents

### Tasks:

1. **Gemini Pro Integration**
   ```python
   # ai/gemini_client.py
   import google.generativeai as genai

   class GeminiClient:
       def __init__(self, api_key):
           genai.configure(api_key=api_key)
           self.model = genai.GenerativeModel('gemini-pro')
   ```

2. **Free Embeddings Setup**
   ```python
   # ai/embeddings.py
   from sentence_transformers import SentenceTransformer

   class EmbeddingClient:
       def __init__(self):
           self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Free, local
   ```

3. **RAG Pipeline**
   - PDF text extraction (PyPDF2)
   - Document chunking (LangChain)
   - Embedding generation
   - ChromaDB storage
   - Similarity search implementation

4. **Commands Implementation**
   - `/upload` - Admin PDF upload
   - `/ask <question>` - RAG-powered Q&A

### Expected Output:
User uploads PDF, asks question via `/ask`, gets relevant answer with source citations.

---

## 🎯 Phase 3: Quiz Engine with Gemini (Day 3)

### Goals:
- ✅ Auto-generate MCQ quizzes from course material
- ✅ Interactive quiz with emoji reactions
- ✅ Score tracking and leaderboard
- ✅ Quiz timeout and answer reveal

### Tasks:

1. **Quiz Generation**
   ```python
   # ai/quiz_engine.py
   def generate_quiz(context: str) -> dict:
       prompt = f"""
       Based on this content, create a multiple choice quiz question:
       {context}

       Return JSON in this format:
       {{
           "question": "...",
           "options": ["A", "B", "C", "D"],
           "correct_answer": 0,
           "explanation": "..."
       }}
       """
   ```

2. **Interactive Quiz System**
   - Embed builder for quiz questions
   - Emoji reaction handling (🇦🇧🇨🇩)
   - Timer system (60 seconds default)
   - Score calculation and storage

3. **Leaderboard System**
   - PostgreSQL scoring tables
   - Streak tracking
   - Formatted leaderboard display

### Expected Output:
`/quiz` generates relevant MCQ, users answer via reactions, scores update leaderboard.

---

## 🎤 Phase 4: Voice Transcription & Summaries (Day 4)

### Goals:
- ✅ Bot joins voice channels during study sessions
- ✅ Real-time audio transcription with Whisper
- ✅ Session summaries using Gemini
- ✅ Privacy-compliant audio handling

### Tasks:

1. **Local Whisper Setup**
   ```bash
   pip install openai-whisper
   # or for better performance:
   pip install faster-whisper
   ```

2. **Voice Channel Integration**
   - Join/leave voice channels
   - PCM audio capture
   - 30-second audio chunking
   - Speaker identification

3. **Transcription Pipeline**
   - Background audio processing
   - Whisper model integration
   - Transcript accumulation
   - Privacy: auto-delete audio after transcription

4. **Session Summaries**
   - Combine voice transcript + chat messages + quiz scores
   - Gemini-powered summary generation
   - Structured output: Key Takeaways, Questions, Action Items

### Expected Output:
Complete study session with voice recording → transcription → AI summary.

---

## ⚡ Phase 5: Pomodoro & Scheduling (Day 5)

### Goals:
- ✅ Automated Pomodoro cycles (25min focus / 5min break)
- ✅ Voice channel mute/unmute control
- ✅ Session scheduling with reminders
- ✅ Streak tracking and gamification

### Tasks:

1. **Pomodoro Implementation**
   - AsyncIO timer system
   - Voice channel permission management
   - Break-time quiz triggering
   - Visual session status embeds

2. **Scheduling System**
   - `/schedule` command
   - APScheduler integration
   - Timezone support
   - Reminder notifications

3. **Gamification Features**
   - Daily streak tracking
   - XP/points system
   - Achievement badges
   - Leaderboard enhancements

### Expected Output:
Full study session automation with timing controls and engagement features.

---

## 🎨 Phase 6: Polish & Production (Day 6)

### Goals:
- ✅ Error handling and robustness
- ✅ Docker containerization
- ✅ Performance optimization
- ✅ Documentation and testing

### Tasks:

1. **Error Handling**
   - API rate limit handling
   - Connection retry logic
   - Graceful failure modes
   - User-friendly error messages

2. **Performance & Scalability**
   - Database connection pooling
   - Async optimization
   - Memory management
   - Background task optimization

3. **Production Setup**
   - Docker containerization
   - Environment configuration
   - Health checks
   - Monitoring setup

4. **Documentation**
   - Setup instructions
   - Command documentation
   - Admin guide
   - Troubleshooting guide

---

## 🔧 Environment Variables (.env)

```bash
# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# AI Models (Free)
GEMINI_API_KEY=your_gemini_api_key_here
HUGGINGFACE_API_TOKEN=your_huggingface_token_here

# Database
DATABASE_URL=postgresql://user:password@localhost/study_bot
REDIS_URL=redis://localhost:6379

# Configuration
ENVIRONMENT=development
DEBUG=true
POMODORO_FOCUS_MINS=25
POMODORO_BREAK_MINS=5
QUIZ_TIMEOUT_SECS=60

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db

# Whisper
WHISPER_MODEL=base
```

---

## 📊 Database Schema

```sql
-- db/schema.sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id BIGINT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guild_id BIGINT NOT NULL,
    topic TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    summary TEXT,
    creator_id UUID REFERENCES users(id)
);

CREATE TABLE quiz_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    user_id UUID REFERENCES users(id),
    question TEXT NOT NULL,
    correct BOOLEAN NOT NULL,
    points INTEGER DEFAULT 0,
    answered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    guild_id BIGINT NOT NULL,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_active DATE DEFAULT CURRENT_DATE,
    UNIQUE(user_id, guild_id)
);

-- Leaderboard view
CREATE VIEW leaderboard AS
SELECT
    u.discord_id,
    u.username,
    s.guild_id,
    SUM(q.points) as total_points,
    COUNT(q.id) as total_quizzes,
    AVG(CASE WHEN q.correct THEN 1.0 ELSE 0.0 END) as accuracy,
    st.current_streak,
    st.longest_streak
FROM users u
JOIN quiz_scores q ON u.id = q.user_id
JOIN sessions s ON q.session_id = s.id
LEFT JOIN streaks st ON u.id = st.user_id AND s.guild_id = st.guild_id
GROUP BY u.discord_id, u.username, s.guild_id, st.current_streak, st.longest_streak
ORDER BY total_points DESC;
```

---

## 🚀 Quick Start Commands

```bash
# 1. Clone and setup
git clone <your-repo>
cd study-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 4. Setup database
docker-compose up -d postgres redis
python -c "from db.database import setup_database; setup_database()"

# 5. Run bot
python bot.py
```

---

## ✅ Success Criteria

**Phase 1:** Bot online, basic commands work
**Phase 2:** PDF upload → ask questions → get AI answers
**Phase 3:** Generate quiz → react to answer → score updates
**Phase 4:** Voice recording → transcription → session summary
**Phase 5:** Full Pomodoro cycle with automation
**Phase 6:** Production ready with Docker deployment

---

## 🔍 Testing Strategy

Each phase includes:
- Unit tests for core functions
- Integration tests for API calls
- Discord bot testing in development server
- Performance testing for concurrent users
- Error handling validation

---

*This updated plan uses 100% free models while maintaining all the original functionality. Ready to start building!*