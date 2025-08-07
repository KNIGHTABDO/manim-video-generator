#!/usr/bin/env python3
"""
Test script for Telegram bot functionality.
Run this script to test if your Telegram bot is configured correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from telegram_bot import telegram_notifier, notify_system_alert, notify_generation_start, notify_generation_success
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_configuration():
    """Test if Telegram bot is properly configured"""
    print("🔍 Testing Telegram Bot Configuration...")
    print(f"Bot Token exists: {'✅' if telegram_notifier.bot_token else '❌'}")
    print(f"Chat ID exists: {'✅' if telegram_notifier.chat_id else '❌'}")
    print(f"Bot instance created: {'✅' if telegram_notifier.bot else '❌'}")
    print(f"Fully configured: {'✅' if telegram_notifier.is_configured() else '❌'}")
    print()
    
    if not telegram_notifier.is_configured():
        print("❌ Telegram bot is not configured correctly!")
        print()
        print("To configure the bot:")
        print("1. Copy .env.example to .env")
        print("2. Set TELEGRAM_BOT_TOKEN (get from @BotFather)")
        print("3. Set TELEGRAM_CHAT_ID (your user ID)")
        print("4. Run this test again")
        return False
    
    return True

def test_notifications():
    """Test sending different types of notifications"""
    if not test_configuration():
        return
    
    print("📤 Testing notifications...")
    
    # Test system alert
    print("Sending test system alert...")
    result1 = notify_system_alert('info', 'Test notification from setup script! 🧪')
    print(f"System alert: {'✅ Sent' if result1 else '❌ Failed'}")
    
    # Test generation start notification
    print("Sending test generation start notification...")
    result2 = notify_generation_start('Test concept', '127.0.0.1')
    print(f"Generation start: {'✅ Sent' if result2 else '❌ Failed'}")
    
    # Test generation success notification
    print("Sending test generation success notification...")
    result3 = notify_generation_success('Test concept', duration=45.2, file_size=8.7, user_ip='127.0.0.1')
    print(f"Generation success: {'✅ Sent' if result3 else '❌ Failed'}")
    
    print()
    if all([result1, result2, result3]):
        print("🎉 All tests passed! Check your Telegram for the messages.")
    else:
        print("⚠️  Some tests failed. Check your configuration and try again.")

if __name__ == "__main__":
    print("🤖 Telegram Bot Test Script")
    print("=" * 40)
    test_notifications()
