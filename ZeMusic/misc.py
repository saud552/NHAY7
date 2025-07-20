import socket
import time

import heroku3
from pyrogram import filters

import config
from .logging import LOGGER

# قائمة السُوبر يوزرز (SUDOERS) تعتمد على فلتر المستخدم من Pyrogram
SUDOERS = filters.user()

HAPP = None
_boot_ = time.time()


def is_heroku():
    return "heroku" in socket.getfqdn()


XCB = [
    "/",
    "@",
    ".",
    "com",
    ":",
    "",
    "git",
    "heroku",
    "push",
    str(config.HEROKU_API_KEY),
    "https",
    str(config.HEROKU_APP_NAME),
    "HEAD",
    "master",
]


def dbb():
    """
    تهيئة قاعدة بيانات محلية (في الذاكرة) للمسارات المؤقتة.
    تم استبدالها بنظام SQLite الجديد.
    """
    global db
    db = {}
    LOGGER(__name__).info("Local Database Initialized.")


async def sudo():
    """
    تحميل قائمة sudoers من قاعدة البيانات الجديدة.
    """
    global SUDOERS
    # نظّف أي مكونات سابقة
    SUDOERS = filters.user()
    
    # أضف المعرفات الثابتة من config
    SUDOERS.add(config.OWNER_ID)
    SUDOERS.add(config.DAV)
    
    # تحميل المديرين من قاعدة البيانات
    try:
        from ZeMusic.core.database import db
        sudoers_list = await db.get_sudoers()
        for user_id in sudoers_list:
            SUDOERS.add(user_id)
        LOGGER(__name__).info(f"✅ تم تحميل {len(sudoers_list)} مدير من قاعدة البيانات SQLite")
    except Exception as e:
        LOGGER(__name__).error(f"خطأ في تحميل المديرين: {e}")
    
    LOGGER(__name__).info("✅ تم تحميل sudo(): استخدام قاعدة البيانات SQLite الجديدة")


def heroku():
    """
    تكوين تطبيق Heroku إذا كنا على بيئة Heroku.
    """
    global HAPP
    if is_heroku():
        if config.HEROKU_API_KEY and config.HEROKU_APP_NAME:
            try:
                Heroku = heroku3.from_key(config.HEROKU_API_KEY)
                HAPP = Heroku.app(config.HEROKU_APP_NAME)
                LOGGER(__name__).info("تم تكوين تطبيق Heroku.")
            except BaseException:
                LOGGER(__name__).warning(
                    "Please make sure your Heroku API Key and App name are configured correctly."
                )
