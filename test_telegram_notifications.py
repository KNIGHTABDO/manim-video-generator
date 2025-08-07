#!/usr/bin/env python3
"""
Test script for Telegram notifications
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot import notify_generation_start, notify_generation_success, notify_generation_error

def test_telegram_notifications():
    """Test all Telegram notification functions"""
    
    # Load environment variables
    load_dotenv()
    
    print("🔍 Testing Telegram Bot Configuration...")
    print(f"Bot Token: {os.getenv('TELEGRAM_BOT_TOKEN')[:10]}...")
    print(f"Chat ID: {os.getenv('TELEGRAM_CHAT_ID')}")
    
    try:
        # Test 1: Generation start notification
        print("\n📤 Testing generation start notification...")
        prompt = "Create a sine wave animation"
        notify_generation_start(prompt)
        print("✅ Generation start notification sent!")
        
        # Test 2: Generation success notification
        print("\n📤 Testing generation success notification...")
        video_path = "/path/to/test/video.mp4"
        duration = 3.5
        file_size = 2.1
        notify_generation_success(prompt, duration, file_size)
        print("✅ Generation success notification sent!")
        
        # Test 3: Generation error notification
        print("\n📤 Testing generation error notification...")
        error_message = "Test error: This is just a test"
        notify_generation_error(prompt, error_message)
        print("✅ Generation error notification sent!")
        
        print("\n🎉 All Telegram notifications tested successfully!")
        print("Check your Telegram chat to see the messages!")
        
    except Exception as e:
        print(f"\n❌ Error testing notifications: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure your bot token is correct")
        print("2. Make sure your chat ID is correct")
        print("3. Make sure you've started a conversation with your bot")
        print("4. Check your internet connection")

if __name__ == "__main__":
    test_telegram_notifications()
