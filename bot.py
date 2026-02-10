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
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from telegram.error import TelegramError

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
        self.authorized_users = set()
        
        # Parse authorized users from environment variable
        authorized_users_str = os.getenv('AUTHORIZED_USERS', '')
        if authorized_users_str:
            self.authorized_users = set(int(user_id.strip()) for user_id in authorized_users_str.split(','))
        
        self.huami_token_dir = Path('/app/huami-token')
        
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot"""
        # If no authorized users are configured, allow everyone (backward compatibility)
        if not self.authorized_users:
            return True
        return user_id in self.authorized_users
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
            
        await update.message.reply_text(
            "🤖 GPS Data Bot is active!\n\n"
            "I send GPS data files every Friday automatically.\n"
            "Commands:\n"
            "/status - Check bot status\n"
            "/send_now - Send GPS files immediately\n"
            "/next_send - Show next scheduled send time"
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
            
        next_send = self.get_next_friday()
        await update.message.reply_text(
            f"✅ Bot is running\n"
            f"📅 Next scheduled send: {next_send.strftime('%Y-%m-%d %H:%M')}\n"
        )
    
    async def send_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /send_now command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
            
        await update.message.reply_text("🔄 Generating GPS files now...")
        
        try:
            file_paths = await self.generate_file()
            if file_paths:
                await self.send_file(update.effective_chat.id, file_paths)
                await update.message.reply_text(f"✅ {len(file_paths)} GPS files sent successfully!")
            else:
                await update.message.reply_text("❌ Failed to generate GPS files")
        except Exception as e:
            logger.error(f"Error in send_now: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def next_send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /next_send command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
            
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
    
    async def generate_file(self) -> Optional[list]:
        """Generate GPS files using huami-token script"""
        try:
            logger.info("Running huami-token script...")
            
            # Change to huami-token directory
            os.chdir(self.huami_token_dir)
            
            # Run huami-token command with correct syntax
            cmd = [
                'huami-token',
                '-e', self.huami_email,
                '-p', self.huami_password,
                '-m', 'amazfit',
                '--gps'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Log command output
            if result.stdout:
                logger.info(f"huami-token stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"huami-token stderr: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"huami-token failed with return code {result.returncode}")
                return None
            
            logger.info("GPS data download completed")
            
            # Find all .zip and .bin files in huami-token directory
            generated_files = []
            huami_dir = Path('/app/huami-token')
            
            # Look for all .zip and .bin files
            for file_path in huami_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.zip', '.bin']:
                    generated_files.append(file_path)
                    logger.info(f"Found generated file: {file_path}")
            
            if generated_files:
                return generated_files
            else:
                logger.error("No .zip or .bin files found")
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
        file_path = Path(filename)  # Create in current directory
        
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
    
    async def send_file(self, chat_id: int, file_paths: list) -> bool:
        """Send multiple GPS files to Telegram chat and delete them"""
        try:
            bot = Bot(token=self.token)
            
            for file_path in file_paths:
                with open(file_path, 'rb') as file:
                    await bot.send_document(
                        chat_id=chat_id,
                        document=file,
                        caption=f"📄 GPS Data File\nFile: {file_path.name}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                logger.info(f"Sent file: {file_path}")
                
                # Delete file after successful send
                try:
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
            
            logger.info(f"All {len(file_paths)} files sent and deleted successfully")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending files: {e}")
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
    
    async def weekly_job_callback(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Callback for weekly scheduled job"""
        logger.info("Starting weekly GPS data generation...")
        file_paths = await self.generate_file()
        
        if file_paths and self.chat_id:
            success = await self.send_file(int(self.chat_id), file_paths)
            if success:
                logger.info(f"Weekly GPS files ({len(file_paths)}) sent successfully")
            else:
                logger.error("Failed to send weekly GPS files")
        else:
            logger.error("Failed to generate GPS files or no chat_id configured")
    
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
        
        # Create application with job queue
        job_queue = JobQueue()
        application = Application.builder().token(self.token).job_queue(job_queue).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("send_now", self.send_now_command))
        application.add_handler(CommandHandler("next_send", self.next_send_command))
        
        # Schedule weekly job - every Friday at 10:00 AM
        job_queue.run_daily(
            callback=self.weekly_job_callback,
            time=datetime.now().replace(hour=10, minute=0, second=0, microsecond=0),
            days=(4,),  # Friday is day 4 (0=Monday)
            name="weekly_file_send"
        )
        
        # Start bot
        logger.info("Starting Weekly File Bot...")
        application.run_polling()

if __name__ == '__main__':
    bot = WeeklyFileBot()
    bot.run()
