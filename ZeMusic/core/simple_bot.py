# Simple Bot for ZeMusic
# Enhanced compatibility with python-telegram-bot

import logging
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from ZeMusic.core.simple_handlers import simple_handlers
import config

logger = logging.getLogger(__name__)

class SimpleBotManager:
    """إدارة بوت مبسط باستخدام python-telegram-bot"""
    
    def __init__(self):
        self.application = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    async def start(self) -> bool:
        """تشغيل البوت"""
        try:
            # إنشاء Application مع توكن البوت
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            
            # إضافة المعالجات
            self._add_handlers()
            
            # بدء البوت
            await self.application.initialize()
            await self.application.start()
            
            # بدء polling
            await self.application.updater.start_polling(
                poll_interval=1.0,
                timeout=10,
                bootstrap_retries=-1,
                drop_pending_updates=True,
            )
            
            self.is_running = True
            self.logger.info("✅ Simple Bot started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start simple bot: {e}")
            return False
    
    def _add_handlers(self):
        """إضافة المعالجات للبوت"""
        try:
            # معالجات الأوامر
            self.application.add_handler(CommandHandler("start", simple_handlers.handle_start))
            self.application.add_handler(CommandHandler("help", simple_handlers.handle_help))
            self.application.add_handler(CommandHandler("owner", simple_handlers.handle_owner))
            self.application.add_handler(CommandHandler("addassistant", simple_handlers.handle_addassistant))
            self.application.add_handler(CommandHandler("play", simple_handlers.handle_search_message))
            
            # معالج الأزرار (Callback Queries)
            self.application.add_handler(CallbackQueryHandler(simple_handlers.handle_callback_query))
            
            # معالج الرسائل النصية
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, simple_handlers.handle_message))
            
            self.logger.info("📝 Bot handlers added successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add handlers: {e}")
    
    async def stop(self):
        """إيقاف البوت"""
        try:
            if self.application and self.is_running:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.is_running = False
                self.logger.info("🛑 Simple bot stopped")
                
        except Exception as e:
            self.logger.error(f"❌ Error stopping simple bot: {e}")
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """إرسال رسالة"""
        try:
            if self.application and self.is_running:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    **kwargs
                )
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error sending message: {e}")
            return False

# Global instance
simple_bot = SimpleBotManager()