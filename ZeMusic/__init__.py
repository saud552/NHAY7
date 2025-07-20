import asyncio
import time
from .logging import LOGGER

# استخدام طبقة التوافق بدلاً من pyrogram مباشرة
try:
    # محاولة استيراد pyrogram إذا كان متاحاً
    from pyrogram import Client
    LOGGER(__name__).info("🔄 تم العثور على pyrogram - استخدام النظام المختلط")
except ImportError:
    # استخدام طبقة التوافق TDLib
    from .compatibility import Client, app
    LOGGER(__name__).info("🔄 استخدام طبقة التوافق TDLib")

# تهيئة قاعدة البيانات
async def init_database():
    """تهيئة قاعدة البيانات SQLite"""
    try:
        from .core.database import db
        LOGGER(__name__).info("✅ تم تهيئة قاعدة البيانات SQLite بنجاح")
        return True
    except Exception as e:
        LOGGER(__name__).error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False

# متغيرات عامة
SUDOERS = []
OWNER_ID = None
userbot = None

# تحديد وقت بدء التشغيل
StartTime = time.time()

LOGGER(__name__).info("🎵 تم تحميل ZeMusic Bot بنجاح")
