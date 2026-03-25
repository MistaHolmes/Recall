#!/usr/bin/env python3
"""
Setup Test Script for Discord AI Study Bot
Run this to verify all your API keys and dependencies are working correctly.
"""

import os
import sys
from dotenv import load_dotenv

def test_setup():
    """Test all components of the setup"""
    print("🔍 Testing Discord AI Study Bot Setup...")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    all_tests_passed = True

    # Test 1: Environment Variables
    print("\n1️⃣ Testing Environment Variables...")

    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    gemini_key = os.getenv('GEMINI_API_KEY')

    if discord_token and len(discord_token) > 50:
        print("   ✅ Discord Bot Token: Present and valid length")
    else:
        print("   ❌ Discord Bot Token: Missing or invalid")
        all_tests_passed = False

    if gemini_key and len(gemini_key) > 20:
        print("   ✅ Gemini API Key: Present and valid length")
    else:
        print("   ❌ Gemini API Key: Missing or invalid")
        all_tests_passed = False

    # Test 2: Python Dependencies
    print("\n2️⃣ Testing Python Dependencies...")

    dependencies = [
        ('discord.py', 'discord'),
        ('google-generativeai', 'google.generativeai'),
        ('sentence-transformers', 'sentence_transformers'),
        ('chromadb', 'chromadb'),
        ('whisper', 'whisper'),
        ('PyPDF2', 'PyPDF2'),
        ('python-dotenv', 'dotenv'),
    ]

    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"   ✅ {package_name}: Imported successfully")
        except ImportError:
            print(f"   ❌ {package_name}: Not installed (run: pip install {package_name})")
            all_tests_passed = False

    # Test 3: Gemini API Connection
    if gemini_key:
        print("\n3️⃣ Testing Gemini AI API...")
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)

            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                "Respond with exactly: 'Gemini API is working perfectly!'"
            )

            if "working perfectly" in response.text.lower():
                print("   ✅ Gemini API: Connection successful")
                print(f"   📝 Response: {response.text}")
            else:
                print("   ⚠️ Gemini API: Connected but unexpected response")
                print(f"   📝 Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Gemini API: Connection failed - {str(e)}")
            all_tests_passed = False

    # Test 4: Local AI Models
    print("\n4️⃣ Testing Local AI Models...")

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_embedding = model.encode("This is a test sentence.")
        print(f"   ✅ Sentence Transformers: Working (dimension: {len(test_embedding)})")
    except Exception as e:
        print(f"   ❌ Sentence Transformers: Failed - {str(e)}")
        all_tests_passed = False

    try:
        import chromadb
        client = chromadb.Client()
        print("   ✅ ChromaDB: Initialized successfully")
    except Exception as e:
        print(f"   ❌ ChromaDB: Failed - {str(e)}")
        all_tests_passed = False

    # Test 5: Discord.py Basic Setup
    print("\n5️⃣ Testing Discord.py Setup...")

    try:
        import discord
        from discord.ext import commands

        # Test bot initialization (without connecting)
        bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
        print("   ✅ Discord Bot: Initialization successful")
        print(f"   📦 Discord.py version: {discord.__version__}")
    except Exception as e:
        print(f"   ❌ Discord Bot: Failed - {str(e)}")
        all_tests_passed = False

    # Final Results
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! You're ready to build the Discord bot!")
        print("\n📋 Next Steps:")
        print("   1. Invite your bot to a Discord server")
        print("   2. Start with Phase 1 implementation")
        print("   3. Run: python bot.py")
        print("\n💡 Pro tip: Create a test Discord server for development")
    else:
        print("❌ Some tests failed. Please fix the issues above before continuing.")
        print("\n🔧 Common fixes:")
        print("   • Missing API keys → Copy them to .env file")
        print("   • Missing packages → Run: pip install -r requirements.txt")
        print("   • Wrong API key format → Check you copied the full key")

    return all_tests_passed

if __name__ == "__main__":
    success = test_setup()
    sys.exit(0 if success else 1)