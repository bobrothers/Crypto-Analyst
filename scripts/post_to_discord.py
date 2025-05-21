#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_to_discord.py
-----------------
Posts the generated daily brief to a Discord channel using either
the Discord.py library or a webhook, based on configuration.

This script is called as the final step in the daily_swarm_workflow defined in swarm.yaml.
"""

import os
import logging
import argparse
import json
import requests
from typing import Optional, Dict, Any, Union
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_poster')

# Default Discord configuration
DEFAULT_CHANNEL_ID = os.getenv('DISCORD_MARKET_PULSE_CHANNEL_ID')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')


def post_message_webhook(
    message: str,
    webhook_url: str,
    username: str = "Crypto Analyst Swarm",
    avatar_url: Optional[str] = None
) -> requests.Response:
    """
    Post a message to Discord using a webhook.
    
    Args:
        message: The message to post
        webhook_url: The Discord webhook URL
        username: The username to display for the bot
        avatar_url: Optional URL for the bot's avatar
    
    Returns:
        Response from the webhook request
    """
    payload = {
        "content": message,
        "username": username
    }
    
    if avatar_url:
        payload["avatar_url"] = avatar_url
    
    logger.info(f"Posting to Discord webhook as {username}")
    
    response = requests.post(
        webhook_url,
        json=payload
    )
    
    if response.status_code == 204:
        logger.info("Successfully posted to Discord webhook")
    else:
        logger.error(f"Failed to post to Discord webhook: {response.status_code} - {response.text}")
    
    return response


def post_message_bot(
    message: str,
    channel_id: str,
    token: str
) -> bool:
    """
    Post a message to Discord using a bot with discord.py library.
    
    Args:
        message: The message to post
        channel_id: The Discord channel ID to post to
        token: The Discord bot token for authentication
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Only import discord.py if we're using the bot method
        # to avoid unnecessary dependencies
        import discord
        from discord.ext import commands
        
        # Set up the bot client
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix='!', intents=intents)
        
        @bot.event
        async def on_ready():
            logger.info(f"Bot connected as {bot.user}")
            try:
                channel = bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(message)
                    logger.info(f"Posted message to channel {channel.name}")
                else:
                    logger.error(f"Channel with ID {channel_id} not found")
                await bot.close()
            except Exception as e:
                logger.error(f"Error posting message: {str(e)}")
                await bot.close()
        
        logger.info("Starting Discord bot to post message")
        bot.run(token)
        return True
    
    except ImportError:
        logger.error("discord.py library not installed. "
                     "Install with: pip install discord.py")
        return False
    except Exception as e:
        logger.error(f"Error with Discord bot: {str(e)}")
        return False


def post_file(
    file_path: str,
    channel_id: str,
    use_webhook: bool = False,
    webhook_url: Optional[str] = None
) -> bool:
    """
    Post a file to Discord channel.
    
    Args:
        file_path: Path to the file to post
        channel_id: The Discord channel ID to post to
        use_webhook: Whether to use a webhook instead of bot
        webhook_url: The webhook URL (required if use_webhook=True)
    
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if content is too long for a single Discord message
        if len(content) > 2000:
            logger.warning("Content exceeds Discord's 2000 character limit. Splitting into chunks.")
            chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
            
            success = True
            for i, chunk in enumerate(chunks):
                chunk_content = f"**Part {i+1}/{len(chunks)}**\n{chunk}"
                
                if use_webhook and webhook_url:
                    response = post_message_webhook(chunk_content, webhook_url)
                    success = success and (response.status_code == 204)
                else:
                    success = success and post_message_bot(chunk_content, channel_id, DISCORD_BOT_TOKEN)
            
            return success
        else:
            # Content fits in a single message
            if use_webhook and webhook_url:
                response = post_message_webhook(content, webhook_url)
                return response.status_code == 204
            else:
                return post_message_bot(content, channel_id, DISCORD_BOT_TOKEN)
    
    except Exception as e:
        logger.error(f"Error posting file to Discord: {str(e)}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Post content to Discord channel')
    parser.add_argument('--channel_id', default=DEFAULT_CHANNEL_ID,
                       help='Discord channel ID to post to')
    parser.add_argument('--file', required=True,
                       help='Path to the file to post')
    parser.add_argument('--method', choices=['bot', 'webhook'], default='bot',
                       help='Method to use for posting (default: bot)')
    parser.add_argument('--webhook_url',
                       help='Discord webhook URL (required if method=webhook)')
    args = parser.parse_args()
    
    try:
        # Validate arguments
        if args.method == 'webhook' and not args.webhook_url:
            logger.error("Webhook URL is required when using webhook method")
            return 1
        
        if not args.channel_id:
            logger.error("Discord channel ID is required")
            return 1
        
        # Resolve file path
        file_path = args.file
        if not os.path.isabs(file_path):
            # Try to resolve relative to data/briefs folder
            data_dir = os.getenv('DATA_STORAGE_PATH', 'data')
            briefs_dir = os.path.join(data_dir, 'briefs')
            candidate_path = os.path.join(briefs_dir, file_path)
            if os.path.exists(candidate_path):
                file_path = candidate_path
        
        # Post file to Discord
        success = post_file(
            file_path=file_path,
            channel_id=args.channel_id,
            use_webhook=(args.method == 'webhook'),
            webhook_url=args.webhook_url
        )
        
        if success:
            logger.info("Successfully posted to Discord")
            return 0
        else:
            logger.error("Failed to post to Discord")
            return 1
    
    except Exception as e:
        logger.error(f"Error during Discord posting: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
