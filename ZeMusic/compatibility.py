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

class TDLibFilter:
    """فلتر أساسي لـ TDLib"""
    def __init__(self, filter_type: str):
        self.filter_type = filter_type
    
    def __and__(self, other):
        return CombinedFilter([self, other], "and")
    
    def __or__(self, other):
        return CombinedFilter([self, other], "or")
    
    def __invert__(self):
        return InvertedFilter(self)

class CombinedFilter(TDLibFilter):
    """فلتر مركب"""
    def __init__(self, filters: list, operator: str):
        super().__init__("combined")
        self.filters = filters
        self.operator = operator

class InvertedFilter(TDLibFilter):
    """فلتر معكوس"""
    def __init__(self, filter_obj):
        super().__init__("inverted")
        self.filter = filter_obj

class TDLibFilters:
    """محاكاة filters من pyrogram"""
    
    def __init__(self):
        self.group = TDLibFilter("group")
        self.private = TDLibFilter("private")
        self.channel = TDLibFilter("channel")
        self.via_bot = TDLibFilter("via_bot")
        self.forwarded = TDLibFilter("forwarded")
        self.text = TDLibFilter("text")
        self.photo = TDLibFilter("photo")
        self.video = TDLibFilter("video")
        self.audio = TDLibFilter("audio")
        self.document = TDLibFilter("document")
    
    def command(self, commands, prefixes=""):
        """محاكاة filters.command"""
        return CommandFilter(commands, prefixes)

class CommandFilter(TDLibFilter):
    """فلتر الأوامر"""
    def __init__(self, commands, prefixes):
        super().__init__("command")
        self.commands = commands if isinstance(commands, list) else [commands]
        self.prefixes = prefixes

    # محاكاة أنواع الرسائل والردود
    class MessageType:
        def __init__(self, type_name: str, **kwargs):
            self.type = type_name
            self.kwargs = kwargs
    
    class CallbackQuery:
        def __init__(self, **kwargs):
            self.data = kwargs.get('data', '')
            self.from_user = kwargs.get('from_user')
            self.message = kwargs.get('message')
    
    class InlineQuery:
        def __init__(self, **kwargs):
            self.query = kwargs.get('query', '')
            self.from_user = kwargs.get('from_user')
    
    class Message:
        def __init__(self, **kwargs):
            self.text = kwargs.get('text', '')
            self.chat = kwargs.get('chat')
            self.from_user = kwargs.get('from_user')
            self.message_id = kwargs.get('message_id')
    
    # محاكاة أنواع لوحة المفاتيح
    class InlineKeyboardMarkup:
        def __init__(self, buttons):
            self.buttons = buttons
    
    class InlineKeyboardButton:
        def __init__(self, text, **kwargs):
            self.text = text
            self.kwargs = kwargs

# إنشاء مثيل عام للتوافق
app = CompatibilityClient("ZeMusic")

# إضافة aliases للتوافق الكامل
Client = CompatibilityClient

# إضافة types وهمية للتوافق
class enums:
    class ChatType:
        PRIVATE = "private"
        GROUP = "group"
        SUPERGROUP = "supergroup"
        CHANNEL = "channel"
    
    class ChatMemberStatus:
        OWNER = "creator"
        ADMINISTRATOR = "administrator"
        MEMBER = "member"
        RESTRICTED = "restricted"
        LEFT = "left"
        BANNED = "kicked"
    
    class ParseMode:
        HTML = "HTML"
        MARKDOWN = "Markdown"
    
    class MessageEntityType:
        URL = "url"
        TEXT_LINK = "text_link"
        BOT_COMMAND = "bot_command"
    
    class ChatMembersFilter:
        ALL = "all"
        BANNED = "banned"
        RESTRICTED = "restricted"

class errors:
    class FloodWait(Exception):
        def __init__(self, value: int):
            self.value = value
    
    class MessageNotModified(Exception):
        pass
    
    class MessageIdInvalid(Exception):
        pass

# متغيرات إضافية للتوافق
__version__ = "2.0.0-TDLib"

LOGGER(__name__).info("🔄 تم تحميل طبقة التوافق - الملفات القديمة ستعمل مع TDLib")