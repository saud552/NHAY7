import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import config
from ZeMusic.logging import LOGGER

class SimpleBotClient:
    """عميل بوت بسيط باستخدام python-telegram-bot كبديل لـ TDLib"""
    
    def __init__(self):
        self.bot = None
        self.application = None
        self.is_connected = False
        
    async def start(self) -> bool:
        """بدء البوت البسيط"""
        try:
            # إنشاء التطبيق
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            self.bot = self.application.bot
            
            # تسجيل المعالجات الأساسية
            self._register_handlers()
            
            # بدء البوت
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_connected = True
            LOGGER(__name__).info("✅ تم تشغيل البوت البسيط بنجاح")
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ فشل في تشغيل البوت البسيط: {e}")
            return False
    
    def _register_handlers(self):
        """تسجيل معالجات الأوامر الأساسية"""
        try:
            from ZeMusic.core.simple_handlers import simple_handlers
            from ZeMusic.core.assistant_manager import assistant_manager, PHONE_INPUT, CODE_INPUT, PASSWORD_INPUT
            from telegram.ext import ConversationHandler, filters
            
            # معالج المحادثة لإضافة الحسابات المساعدة
            assistant_conv_handler = ConversationHandler(
                entry_points=[],  # سيتم البدء من callback query
                states={
                    PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, assistant_manager.handle_phone_input)],
                    CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, assistant_manager.handle_code_input)],
                    PASSWORD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, assistant_manager.handle_password_input)],
                },
                fallbacks=[],
                allow_reentry=True
            )
            
            # معالج الأوامر الأساسية
            self.application.add_handler(CommandHandler("start", simple_handlers.handle_start))
            self.application.add_handler(CommandHandler("help", simple_handlers.handle_help))
            self.application.add_handler(CommandHandler("owner", simple_handlers.handle_owner))
            self.application.add_handler(CommandHandler("admin", simple_handlers.handle_admin))
            self.application.add_handler(CommandHandler("ping", simple_handlers.handle_ping))
            self.application.add_handler(CommandHandler("addassistant", simple_handlers.handle_addassistant))
            
            # معالج المحادثات
            self.application.add_handler(assistant_conv_handler)
            
            # معالج الرسائل النصية (للبحث)
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, simple_handlers.handle_search_message))
            
            # معالج callback queries
            self.application.add_handler(CallbackQueryHandler(simple_handlers.handle_callback_query))
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تسجيل المعالجات: {e}")
    

    
    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> Optional[Dict]:
        """إرسال رسالة"""
        try:
            if not self.is_connected or not self.bot:
                return None
            
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            return {
                'message_id': message.message_id,
                'chat': {'id': message.chat.id},
                'date': message.date.timestamp()
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال الرسالة: {e}")
            return None
    
    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup=None):
        """تعديل رسالة"""
        try:
            if not self.is_connected or not self.bot:
                return None
            
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تعديل الرسالة: {e}")
    
    async def stop(self):
        """إيقاف البوت"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            self.is_connected = False
            LOGGER(__name__).info("🛑 تم إيقاف البوت البسيط")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إيقاف البوت البسيط: {e}")


# مثيل البوت البسيط
simple_bot = SimpleBotClient()