import asyncio
import time
from pyrogram import Client
from .logging import LOGGER

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
