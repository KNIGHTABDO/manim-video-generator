import os
import asyncio
import logging
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
import nest_asyncio

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Allow nested event loops (needed for Flask integration)
nest_asyncio.apply()

class TelegramNotifier:
    """Handle Telegram bot notifications for video generation events"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = None
        
        if self.bot_token:
            self.bot = Bot(token=self.bot_token)
            logger.info("Telegram bot initialized successfully")
        else:
            logger.warning("Telegram bot token not found in environment variables")
    
    def is_configured(self):
        """Check if Telegram bot is properly configured"""
        return self.bot_token and self.chat_id and self.bot
    
    async def send_message(self, message):
        """Send a message to the configured chat"""
        if not self.is_configured():
            logger.warning("Telegram bot not configured, skipping notification")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Telegram message sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {str(e)}")
            return False
    
    async def send_video_generation_start(self, concept, user_ip=None):
        """Send notification when video generation starts"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_info = f" from {user_ip}" if user_ip else ""
        
        message = f"""
🎬 <b>Video Generation Started</b>

📝 <b>Concept:</b> {concept}
🕒 <b>Time:</b> {timestamp}
👤 <b>User:</b> {user_info if user_info else "Unknown"}
🚀 <b>Status:</b> Processing...

<i>I'll notify you when it's complete!</i>
        """.strip()
        
        return await self.send_message(message)
    
    async def send_video_generation_success(self, concept, duration=None, file_size=None, user_ip=None):
        """Send notification when video generation succeeds"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_info = f" from {user_ip}" if user_ip else ""
        
        message = f"""
✅ <b>Video Generation Successful!</b>

📝 <b>Concept:</b> {concept}
🕒 <b>Completed:</b> {timestamp}
👤 <b>User:</b> {user_info if user_info else "Unknown"}
⚡ <b>Status:</b> Ready for download
        """.strip()
        
        if duration:
            message += f"\n⏱️ <b>Generation Time:</b> {duration:.1f} seconds"
        
        if file_size:
            message += f"\n📊 <b>File Size:</b> {file_size:.1f} MB"
        
        message += "\n\n🎉 <i>Video is now available!</i>"
        
        return await self.send_message(message)
    
    async def send_video_generation_error(self, concept, error_details=None, user_ip=None):
        """Send notification when video generation fails"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_info = f" from {user_ip}" if user_ip else ""
        
        message = f"""
❌ <b>Video Generation Failed</b>

📝 <b>Concept:</b> {concept}
🕒 <b>Failed at:</b> {timestamp}
👤 <b>User:</b> {user_info if user_info else "Unknown"}
💥 <b>Status:</b> Error occurred
        """.strip()
        
        if error_details:
            # Truncate error details if too long
            if len(error_details) > 200:
                error_details = error_details[:200] + "..."
            message += f"\n🐛 <b>Error:</b> {error_details}"
        
        message += "\n\n🔧 <i>Please check the logs for more details.</i>"
        
        return await self.send_message(message)
    
    async def send_daily_stats(self, total_videos, successful_videos, failed_videos):
        """Send daily statistics"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        success_rate = (successful_videos / total_videos * 100) if total_videos > 0 else 0
        
        message = f"""
📊 <b>Daily Statistics - {timestamp}</b>

🎬 <b>Total Videos:</b> {total_videos}
✅ <b>Successful:</b> {successful_videos}
❌ <b>Failed:</b> {failed_videos}
📈 <b>Success Rate:</b> {success_rate:.1f}%

<i>Keep up the great work!</i>
        """.strip()
        
        return await self.send_message(message)
    
    async def send_system_alert(self, alert_type, message):
        """Send system alerts"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        emoji_map = {
            'warning': '⚠️',
            'error': '🚨',
            'info': 'ℹ️',
            'success': '✅'
        }
        
        emoji = emoji_map.get(alert_type, '📢')
        
        alert_message = f"""
{emoji} <b>System Alert</b>

🏷️ <b>Type:</b> {alert_type.upper()}
🕒 <b>Time:</b> {timestamp}
📝 <b>Message:</b> {message}
        """.strip()
        
        return await self.send_message(alert_message)

# Global notifier instance
telegram_notifier = TelegramNotifier()

def send_telegram_notification(coro):
    """Helper function to run async notification in sync context"""
    try:
        # Create new event loop for this thread if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the coroutine
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {str(e)}")
        return False

# Convenience functions for easy use
def notify_generation_start(concept, user_ip=None):
    """Notify that video generation has started"""
    return send_telegram_notification(
        telegram_notifier.send_video_generation_start(concept, user_ip)
    )

def notify_generation_success(concept, duration=None, file_size=None, user_ip=None):
    """Notify that video generation was successful"""
    return send_telegram_notification(
        telegram_notifier.send_video_generation_success(concept, duration, file_size, user_ip)
    )

def notify_generation_error(concept, error_details=None, user_ip=None):
    """Notify that video generation failed"""
    return send_telegram_notification(
        telegram_notifier.send_video_generation_error(concept, error_details, user_ip)
    )

def notify_daily_stats(total_videos, successful_videos, failed_videos):
    """Send daily statistics"""
    return send_telegram_notification(
        telegram_notifier.send_daily_stats(total_videos, successful_videos, failed_videos)
    )

def notify_system_alert(alert_type, message):
    """Send system alert"""
    return send_telegram_notification(
        telegram_notifier.send_system_alert(alert_type, message)
    )
