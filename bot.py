#!/usr/bin/env python3
"""
Telegram Bot for Weekly File Sending with Huami-Token Integration
Sends a file every Sunday using the huami-token project
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiohttp
import python_telegram_bot
from python_telegram_bot import Bot, Update
from python_telegram_bot.ext import Application, CommandHandler, ContextTypes
from python_telegram_bot.error import TelegramError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WeeklyFileBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.huami_email = os.getenv('HUAMI_EMAIL')
        self.huami_password = os.getenv('HUAMI_PASSWORD')
        self.output_dir = Path('/app/output')
        self.huami_token_dir = Path('/app/huami-token')
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        await update.message.reply_text(
            "🤖 Weekly File Bot is active!\n\n"
            "I send files every Friday automatically.\n"
            "Commands:\n"
            "/status - Check bot status\n"
            "/send_now - Send file immediately\n"
            "/next_send - Show next scheduled send time"
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        next_send = self.get_next_friday()
        await update.message.reply_text(
            f"✅ Bot is running\n"
            f"📅 Next scheduled send: {next_send.strftime('%Y-%m-%d %H:%M')}\n"
            f"📁 Output directory: {self.output_dir}"
        )
    
    async def send_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /send_now command"""
        await update.message.reply_text("🔄 Generating file now...")
        
        try:
            file_path = await self.generate_file()
            if file_path:
                await self.send_file(update.effective_chat.id, file_path)
                await update.message.reply_text("✅ File sent successfully!")
            else:
                await update.message.reply_text("❌ Failed to generate file")
        except Exception as e:
            logger.error(f"Error in send_now: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def next_send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /next_send command"""
        next_send = self.get_next_friday()
        await update.message.reply_text(
            f"📅 Next automatic send: {next_send.strftime('%Y-%m-%d %H:%M')}\n"
            f"⏰ Time remaining: {self.get_time_until_next_friday()}"
        )
    
    def get_next_friday(self) -> datetime:
        """Calculate next Friday at 10:00 AM"""
        now = datetime.now()
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 10:
            days_until_friday = 7
        
        next_friday = now + timedelta(days=days_until_friday)
        return next_friday.replace(hour=10, minute=0, second=0, microsecond=0)
    
    def get_time_until_next_friday(self) -> str:
        """Get human readable time until next Friday"""
        next_friday = self.get_next_friday()
        now = datetime.now()
        delta = next_friday - now
        
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    async def generate_file(self) -> Optional[Path]:
        """Generate file using huami-token script"""
        try:
            logger.info("Running huami-token script...")
            
            # Change to huami-token directory
            os.chdir(self.huami_token_dir)
            
            # Run huami-token command
            cmd = [
                'python', 'main.py',
                '--method', 'amazfit',
                '--email', self.huami_email,
                '--password', self.huami_password,
                '--bt_keys'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"huami-token failed: {result.stderr}")
                return None
            
            # Parse output to extract key and create file
            output_lines = result.stdout.split('\n')
            key_info = self.parse_huami_output(output_lines)
            
            if key_info:
                return self.create_output_file(key_info)
            else:
                logger.error("Could not extract key information from output")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("huami-token script timed out")
            return None
        except Exception as e:
            logger.error(f"Error running huami-token: {e}")
            return None
    
    def parse_huami_output(self, output_lines: list) -> Optional[dict]:
        """Parse huami-token output to extract device information"""
        key_info = None
        
        for line in output_lines:
            if 'Device' in line and 'MAC:' in line and 'Key:' in line:
                # Extract MAC address
                mac_start = line.find('MAC:') + 4
                mac_end = line.find(',', mac_start)
                mac = line[mac_start:mac_end].strip()
                
                # Extract key
                key_start = line.find('Key:') + 4
                key = line[key_start:].strip()
                
                # Extract active status
                active_start = line.find('Active:') + 7
                active_end = line.find(',', active_start)
                active = line[active_start:active_end].strip()
                
                key_info = {
                    'mac': mac,
                    'key': key,
                    'active': active,
                    'timestamp': datetime.now().isoformat()
                }
                break
        
        return key_info
    
    def create_output_file(self, key_info: dict) -> Path:
        """Create output file with key information"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"huami_token_{timestamp}.txt"
        file_path = self.output_dir / filename
        
        content = f"""Huami Token Information
Generated: {key_info['timestamp']}
Device MAC: {key_info['mac']}
Active: {key_info['active']}
Bluetooth Key: {key_info['key']}

This file was automatically generated by the Weekly File Bot.
"""
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Created output file: {file_path}")
        return file_path
    
    async def send_file(self, chat_id: int, file_path: Path) -> bool:
        """Send file to Telegram chat"""
        try:
            bot = Bot(token=self.token)
            
            with open(file_path, 'rb') as file:
                await bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=f"📄 Weekly Huami Token File\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            logger.info(f"File sent successfully to chat {chat_id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return False
    
    async def weekly_scheduler(self) -> None:
        """Background task for weekly file sending"""
        while True:
            try:
                now = datetime.now()
                next_friday = self.get_next_friday()
                
                # Sleep until next Friday
                sleep_seconds = (next_friday - now).total_seconds()
                logger.info(f"Sleeping {sleep_seconds/3600:.1f} hours until next Friday")
                
                await asyncio.sleep(sleep_seconds)
                
                # Generate and send file
                logger.info("Starting weekly file generation...")
                file_path = await self.generate_file()
                
                if file_path and self.chat_id:
                    success = await self.send_file(int(self.chat_id), file_path)
                    if success:
                        logger.info("Weekly file sent successfully")
                    else:
                        logger.error("Failed to send weekly file")
                else:
                    logger.error("Failed to generate file or no chat_id configured")
                    
            except Exception as e:
                logger.error(f"Error in weekly scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
    
    def run(self) -> None:
        """Start the bot"""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return
        
        if not self.chat_id:
            logger.error("TELEGRAM_CHAT_ID not set")
            return
        
        if not self.huami_email or not self.huami_password:
            logger.error("HUAMI_EMAIL or HUAMI_PASSWORD not set")
            return
        
        # Create application
        application = Application.builder().token(self.token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("send_now", self.send_now_command))
        application.add_handler(CommandHandler("next_send", self.next_send_command))
        
        # Start weekly scheduler in background
        asyncio.create_task(self.weekly_scheduler())
        
        # Start bot
        logger.info("Starting Weekly File Bot...")
        application.run_polling()

if __name__ == '__main__':
    bot = WeeklyFileBot()
    bot.run()
