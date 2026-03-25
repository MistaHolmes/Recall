# Discord AI Study Bot - Getting Started Guide

## 🚀 Quick Setup Checklist

### **Step 1: Get Your API Keys (All Free!)**

#### 1.1 Discord Bot Token ⚡
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Give it a name → Create
3. Go to "Bot" tab → Click "Add Bot"
4. Copy the **Token** (keep this secret!)
5. Enable these **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent

#### 1.2 Google Gemini API Key 🧠 (FREE)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with Google account
3. Click "Create API Key" → Copy it
4. **Free Tier:** 15 requests/minute (plenty for our bot!)

#### 1.3 Hugging Face Token 🤗 (FREE - Optional)
1. Go to [Hugging Face](https://huggingface.co/settings/tokens)
2. Sign up/login → Create new token
3. **We'll use local embeddings first, this is backup**

### **Step 2: Invite Bot to Your Server**

1. In Discord Developer Portal → "OAuth2" → "URL Generator"
2. Select **Scopes:**
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select **Bot Permissions:**
   - ✅ Send Messages
   - ✅ Use Slash Commands
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Add Reactions
   - ✅ Connect (Voice)
   - ✅ Speak (Voice)
   - ✅ Mute Members
4. Copy generated URL → Open in browser → Select your server

### **Step 3: Environment Setup**

#### 3.1 Create .env file:
```bash
# Copy this into a file named .env in your project root

# Discord (REQUIRED)
DISCORD_BOT_TOKEN=paste_your_discord_token_here

# AI Models (FREE)
GEMINI_API_KEY=paste_your_gemini_key_here
HUGGINGFACE_API_TOKEN=optional_for_now

# Database (We'll use SQLite first, PostgreSQL later)
DATABASE_URL=sqlite:///study_bot.db

# Configuration
ENVIRONMENT=development
DEBUG=true
POMODORO_FOCUS_MINS=25
POMODORO_BREAK_MINS=5
QUIZ_TIMEOUT_SECS=60

# Voice & AI
WHISPER_MODEL=base
CHROMA_PERSIST_DIR=./chroma_data
```

#### 3.2 Install Python Dependencies:
```bash
pip install discord.py python-dotenv google-generativeai
pip install chromadb sentence-transformers
pip install openai-whisper PyPDF2 langchain
pip install asyncio-mqtt fastapi uvicorn
```

### **Step 4: Test Your Setup**

Create a simple test file to verify everything works:

```python
# test_setup.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Test Discord Token
discord_token = os.getenv('DISCORD_BOT_TOKEN')
print(f"Discord Token: {'✅ Set' if discord_token else '❌ Missing'}")

# Test Gemini API
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'Hello from Gemini!'")
        print(f"Gemini API: ✅ Working - {response.text}")
    except Exception as e:
        print(f"Gemini API: ❌ Error - {e}")
else:
    print("Gemini API: ❌ Missing key")

print("\n🚀 If you see checkmarks above, you're ready to build!")
```

Run: `python test_setup.py`

## 🎯 What's Next?

Once your setup test passes, you're ready to start **Phase 1** of the implementation!

The bot will be built in phases:
1. **Phase 1:** Basic Discord bot + commands *(~2 hours)*
2. **Phase 2:** PDF upload + AI Q&A *(~3 hours)*
3. **Phase 3:** Quiz generation + scoring *(~3 hours)*
4. **Phase 4:** Voice transcription + summaries *(~4 hours)*
5. **Phase 5:** Pomodoro automation + scheduling *(~3 hours)*
6. **Phase 6:** Polish + production setup *(~2 hours)*

**Total estimated time: ~17 hours** (can be done in 1-2 days with focus!)

## 🆘 Common Issues

**"Invalid Token" Error**
- Make sure you copied the Bot Token, not the Client Secret
- Check no extra spaces in .env file

**"Missing Permissions" Error**
- Re-invite bot with all permissions checked
- Make sure bot role is above other roles in server settings

**"Gemini API Error"**
- Check API key is correct
- Verify you're not exceeding free tier limits (15 req/min)

**Ready to build? Let's start with Phase 1! 🚀**