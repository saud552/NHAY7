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
            # معالج الأوامر الأساسية
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("owner", self._handle_owner))
            self.application.add_handler(CommandHandler("ping", self._handle_ping))
            
            # معالج الرسائل
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # معالج callback queries
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تسجيل المعالجات: {e}")
    
    async def _handle_start(self, update: Update, context):
        """معالج أمر /start"""
        try:
            user = update.effective_user
            
            # إضافة المستخدم لقاعدة البيانات
            from ZeMusic.core.database import db
            await db.add_user(user.id)
            if update.effective_chat.type != 'private':
                await db.add_chat(update.effective_chat.id)
            
            welcome_text = f"""
🎵 أهلاً بك في {config.BOT_NAME}!

🤖 حالة البوت: جاهز للعمل
📱 الحسابات المساعدة: غير مضافة بعد

⚙️ للمالك: استخدم /owner لإضافة الحسابات المساعدة
📚 للمساعدة: استخدم /help

🎯 ملاحظة: إضافة الحسابات المساعدة مطلوبة لتشغيل الموسيقى
"""
            
            await update.message.reply_text(welcome_text)
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج start: {e}")
    
    async def _handle_help(self, update: Update, context):
        """معالج أمر /help"""
        help_text = f"""
📚 قائمة أوامر {config.BOT_NAME}:

👤 أوامر عامة:
/start - بدء البوت
/help - عرض المساعدة
/ping - فحص حالة البوت

⚙️ للمالك فقط:
/owner - لوحة إدارة البوت
/addassistant - إضافة حساب مساعد
/removeassistant - إزالة حساب مساعد

🎵 أوامر الموسيقى (تحتاج حسابات مساعدة):
/play - تشغيل موسيقى
/stop - إيقاف الموسيقى
/pause - إيقاف مؤقت
/resume - استكمال التشغيل

📞 للدعم: @{config.SUPPORT_CHAT or 'YourSupport'}
"""
        await update.message.reply_text(help_text)
    
    async def _handle_owner(self, update: Update, context):
        """معالج أمر /owner"""
        try:
            user_id = update.effective_user.id
            
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await update.message.reply_text("❌ هذا الأمر للمالك فقط!")
                return
            
            # استيراد لوحة المالك
            from ZeMusic.plugins.owner.owner_panel import owner_panel
            result = await owner_panel.show_main_panel(user_id)
            
            if result:
                await update.message.reply_text(
                    result.get('text', 'لوحة التحكم'),
                    reply_markup=result.get('reply_markup')
                )
            else:
                await update.message.reply_text("⚙️ لوحة التحكم الرئيسية")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج owner: {e}")
            await update.message.reply_text("❌ حدث خطأ في تحميل لوحة التحكم")
    
    async def _handle_ping(self, update: Update, context):
        """معالج أمر /ping"""
        await update.message.reply_text("🏓 البوت يعمل بشكل طبيعي!")
    
    async def _handle_message(self, update: Update, context):
        """معالج الرسائل العادية"""
        try:
            # يمكن إضافة معالجات للرسائل هنا
            pass
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج الرسائل: {e}")
    
    async def _handle_callback(self, update: Update, context):
        """معالج callback queries"""
        try:
            query = update.callback_query
            await query.answer()
            
            # استيراد معالج الأوامر
            from ZeMusic.core.command_handler import tdlib_command_handler
            
            # تحويل للمعالج المناسب
            callback_data = query.data
            
            if callback_data.startswith('owner_'):
                from ZeMusic.plugins.owner.owner_panel import owner_panel
                result = await owner_panel.handle_callback(query.from_user.id, callback_data)
                
                if result:
                    await query.edit_message_text(
                        result.get('text', 'لوحة التحكم'),
                        reply_markup=result.get('reply_markup')
                    )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج callback: {e}")
    
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