import socket
import time

import heroku3
from pyrogram import filters

import config
# لم يعد هناك استخدام لموديول mongo هنا
# from ZeMusic.core.mongo import mongodb

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
    """
    global db
    db = {}
    LOGGER(__name__).info("Local Database Initialized.")


async def sudo():
    """
    تجاوز خطوة تحميل قائمة sudoers من MongoDB.
    الآن يقرأ فقط OWNER_ID و DAV من config.
    """
    global SUDOERS
    # نظّف أي مكونات سابقة
    SUDOERS = filters.user()
    # أضف المعرفات الثابتة من config
    SUDOERS.add(config.OWNER_ID)
    SUDOERS.add(config.DAV)
    LOGGER(__name__).info("✅ تجاوز sudo(): استخدام OWNER_ID و DAV بدون MongoDB")


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
