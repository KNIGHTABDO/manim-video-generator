# Telegram Bot Setup Guide

This guide will help you set up Telegram notifications for your Manim Video Generator.

## Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a conversation with BotFather
3. Send the command `/newbot`
4. Follow the prompts:
   - Choose a name for your bot (e.g., "Manim Video Generator")
   - Choose a username ending in 'bot' (e.g., "manim_video_gen_bot")
5. BotFather will give you a token. **Save this token securely!**

## Step 2: Get Your Chat ID

There are several ways to get your chat ID:

### Method 1: Using getUpdates API

1. Start a conversation with your newly created bot
2. Send any message to the bot (e.g., "Hello")
3. Open your browser and go to:
   ```
   https://api.telegram.org/bot<YourBOTToken>/getUpdates
   ```
   Replace `<YourBOTToken>` with the token from Step 1
4. Look for `"chat":{"id":` in the response - that number is your chat ID

### Method 2: Using @userinfobot

1. Search for `@userinfobot` on Telegram
2. Start a conversation and send any message
3. The bot will reply with your user information including your ID

## Step 3: Configure Environment Variables

1. Copy `.env.example` to `.env`:

   ```bash
   copy .env.example .env
   ```

2. Edit the `.env` file and add your bot credentials:
   ```bash
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   ```

## Step 4: Install Dependencies

Run the following command to install the required Telegram bot library:

```bash
pip install -r requirements.txt
```

## Step 5: Test Your Setup

1. Start your application:

   ```bash
   python app.py
   ```

2. Test the Telegram integration by making a POST request to `/test-telegram`:

   ```bash
   curl -X POST http://localhost:5001/test-telegram
   ```

3. Check your Telegram chat - you should receive a test message!

## What You'll Receive

Once configured, you'll receive Telegram notifications for:

- ✅ **Video Generation Started**: When someone requests a new video
- 🎉 **Video Generation Successful**: When a video is completed successfully
- ❌ **Video Generation Failed**: When there's an error during generation
- 📊 **Daily Statistics**: Summary of daily activity (if you implement the scheduling)
- 🚨 **System Alerts**: Important system notifications

## Example Notifications

### Generation Started

```
🎬 Video Generation Started

📝 Concept: Pythagorean theorem
🕒 Time: 2024-08-06 14:30:25
👤 User: from 192.168.1.100
🚀 Status: Processing...

I'll notify you when it's complete!
```

### Generation Successful

```
✅ Video Generation Successful!

📝 Concept: Pythagorean theorem
🕒 Completed: 2024-08-06 14:32:10
👤 User: from 192.168.1.100
⚡ Status: Ready for download
⏱️ Generation Time: 105.3 seconds
📊 File Size: 8.7 MB

🎉 Video is now available!
```

### Generation Failed

```
❌ Video Generation Failed

📝 Concept: Complex topic
🕒 Failed at: 2024-08-06 14:35:45
👤 User: from 192.168.1.100
💥 Status: Error occurred
🐛 Error: Manim rendering failed: Syntax error in generated code

🔧 Please check the logs for more details.
```

## Troubleshooting

### Bot Not Responding

- Check that your bot token is correct
- Make sure you've started a conversation with your bot
- Verify the bot hasn't been blocked

### Wrong Chat ID

- Double-check your chat ID is a number (not a string)
- Make sure you're using your personal chat ID, not a group ID
- Try the alternative methods to get your chat ID

### API Errors

- Ensure your bot token hasn't expired
- Check that you have internet connectivity
- Verify the token format is correct (should contain a colon)

### No Notifications Received

- Check the application logs for errors
- Test with the `/test-telegram` endpoint first
- Verify your `.env` file is in the correct location

## Security Notes

- Keep your bot token secret - never commit it to version control
- Consider using environment variables in production
- Regularly rotate your bot token if needed
- Monitor your bot's usage through BotFather

## Advanced Configuration

### Group Notifications

To send notifications to a group:

1. Add your bot to the group
2. Make the bot an administrator (optional)
3. Use the group chat ID instead of your personal chat ID

### Multiple Recipients

You can modify the code to send notifications to multiple chats by:

1. Setting multiple chat IDs in your environment
2. Modifying the `send_message` function to loop through them

### Custom Messages

You can customize the notification messages by editing the functions in `telegram_bot.py`:

- `send_video_generation_start()`
- `send_video_generation_success()`
- `send_video_generation_error()`

Enjoy your automated Telegram notifications! 🚀
