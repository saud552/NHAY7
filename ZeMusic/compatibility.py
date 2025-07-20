"""
ملف التوافق للانتقال من Pyrogram إلى TDLib
يوفر classes ودوال أساسية للملفات القديمة التي تستخدم pyrogram
"""

import asyncio
from typing import Optional, Dict, Any
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.logging import LOGGER
import config

class CompatibilityClient:
    """عميل توافق لمحاكاة pyrogram Client"""
    
    def __init__(self, name: str = "ZeMusic", **kwargs):
        self.name = name
        self.id = None
        self.username = None
        self.mention = None
        self.me = None
        
        # محاكاة خصائص pyrogram
        self.api_id = config.API_ID
        self.api_hash = config.API_HASH
        self.bot_token = config.BOT_TOKEN
        
        LOGGER(__name__).info(f"🔄 تهيئة عميل التوافق: {name}")
    
    async def start(self):
        """بدء العميل - يستخدم TDLib في الخلفية"""
        try:
            # التأكد من تشغيل TDLib
            if not tdlib_manager.bot_client:
                await tdlib_manager.initialize_bot()
            
            if tdlib_manager.bot_client:
                # الحصول على معلومات البوت
                bot_info = await tdlib_manager.bot_client.get_me()
                self.id = bot_info.get('id')
                self.username = bot_info.get('username', '')
                self.me = bot_info
                self.mention = f"@{self.username}" if self.username else f"البوت {self.id}"
                
                LOGGER(__name__).info(f"✅ تم تشغيل عميل التوافق: {self.mention}")
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في تشغيل عميل التوافق: {e}")
            raise
    
    async def stop(self):
        """إيقاف العميل"""
        LOGGER(__name__).info("🛑 إيقاف عميل التوافق")
        # TDLib manager سيتولى الإيقاف
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """إرسال رسالة"""
        try:
            if tdlib_manager.bot_client:
                return await tdlib_manager.bot_client.send_message(chat_id, text)
            else:
                LOGGER(__name__).error("TDLib bot client غير متاح")
                return None
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال رسالة: {e}")
            return None
    
    async def get_chat_member(self, chat_id: int, user_id: int):
        """الحصول على معلومات عضو في مجموعة"""
        try:
            if tdlib_manager.bot_client:
                return await tdlib_manager.bot_client.get_chat_member(chat_id, user_id)
            else:
                LOGGER(__name__).error("TDLib bot client غير متاح")
                return None
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على معلومات العضو: {e}")
            return None
    
    async def get_chat(self, chat_id: int):
        """الحصول على معلومات المحادثة"""
        try:
            if tdlib_manager.bot_client:
                return await tdlib_manager.bot_client.get_chat(chat_id)
            else:
                LOGGER(__name__).error("TDLib bot client غير متاح")
                return None
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على معلومات المحادثة: {e}")
            return None

class CompatibilityAssistant:
    """عميل مساعد للتوافق"""
    
    def __init__(self, session_string: str, **kwargs):
        self.session_string = session_string
        self.is_connected = False
        
    async def start(self):
        """بدء الحساب المساعد"""
        # TDLib manager سيتولى إدارة الحسابات المساعدة
        LOGGER(__name__).info("🔄 محاولة تشغيل حساب مساعد عبر TDLib")
        
    async def stop(self):
        """إيقاف الحساب المساعد"""
        LOGGER(__name__).info("🛑 إيقاف حساب مساعد")

# توفير aliases للاستيراد
Client = CompatibilityClient

# توفير فلاتر وهمية للتوافق
class filters:
    @staticmethod
    def command(commands):
        """فلتر أوامر وهمي"""
        def decorator(func):
            LOGGER(__name__).info(f"🔄 تسجيل أمر للتوافق: {commands}")
            return func
        return decorator
    
    @staticmethod
    def private():
        """فلتر رسائل خاصة وهمي"""
        def decorator(func):
            return func
        return decorator
    
    incoming = None
    private = None

# توفير types وهمية
class types:
    class Message:
        def __init__(self):
            self.from_user = None
            self.chat = None
            self.text = ""
    
    class InlineKeyboardMarkup:
        def __init__(self, buttons):
            self.buttons = buttons
    
    class InlineKeyboardButton:
        def __init__(self, text, **kwargs):
            self.text = text
            self.kwargs = kwargs

# إنشاء مثيل عام للتوافق
app = CompatibilityClient("ZeMusic")

LOGGER(__name__).info("🔄 تم تحميل طبقة التوافق - الملفات القديمة ستعمل مع TDLib")