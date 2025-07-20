import re
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# ============================================
# إعدادات Telegram API الأساسية
# ============================================
API_ID = int(getenv("API_ID", "20036317"))
API_HASH = getenv("API_HASH", "986cb4ba434870a62fe96da3b5f6d411")

# Get your token from @BotFather on Telegram
BOT_TOKEN = getenv("BOT_TOKEN", "7686060382:AAH3wBx0cwW0X7rRVg14XlOhourcG3WgTt0")
BOT_NAME = getenv("BOT_NAME", "لارين")
BOT_USERNAME = getenv("BOT_USERNAME", "")
BOT_ID = getenv("BOT_ID", "7686060382")  # معرف البوت الرقمي

# ============================================
# إعدادات قاعدة البيانات - SQLite
# ============================================
DATABASE_PATH = getenv("DATABASE_PATH", "zemusic.db")
DATABASE_TYPE = getenv("DATABASE_TYPE", "sqlite")
ENABLE_DATABASE_CACHE = getenv("ENABLE_DATABASE_CACHE", "True").lower() == "true"

# ============================================
# إعدادات TDLib
# ============================================
# مسار ملفات TDLib
TDLIB_FILES_PATH = getenv("TDLIB_FILES_PATH", "tdlib_files")

# إعدادات الأمان والتخفي
DEVICE_MODEL = getenv("DEVICE_MODEL", "ZeMusic Bot")
SYSTEM_VERSION = getenv("SYSTEM_VERSION", "Ubuntu 20.04")
APPLICATION_VERSION = getenv("APPLICATION_VERSION", "2.0.0")

# ============================================
# إعدادات الحسابات المساعدة
# ============================================
# ملاحظة: سيتم إدارة الحسابات المساعدة من خلال قاعدة البيانات
# بدلاً من متغيرات البيئة الثابتة
ASSISTANT_MANAGEMENT_ENABLED = True
MAX_ASSISTANTS = int(getenv("MAX_ASSISTANTS", "10"))
MIN_ASSISTANTS = int(getenv("MIN_ASSISTANTS", "0"))  # 0 = اختياري
ENABLE_ASSISTANT_AUTO_MANAGEMENT = getenv("ENABLE_ASSISTANT_AUTO_MANAGEMENT", "True").lower() == "true"

# للتوافق مع الكود القديم (اختياري)
STRING1 = getenv("STRING_SESSION", None)
STRING2 = getenv("STRING_SESSION2", None)
STRING3 = getenv("STRING_SESSION3", None)
STRING4 = getenv("STRING_SESSION4", None)
STRING5 = getenv("STRING_SESSION5", None)

# ============================================
# إعدادات النظام الذكي الجديد
# ============================================

# قناة التخزين الذكي (للتخزين في قناة تيليجرام)
CACHE_CHANNEL_USERNAME = getenv("CACHE_CHANNEL_USERNAME", None)

# تحويل يوزر القناة إلى الشكل المناسب
CACHE_CHANNEL_ID = None
if CACHE_CHANNEL_USERNAME:
    # إذا كان ID رقمي، نحوله للصيغة الصحيحة
    if CACHE_CHANNEL_USERNAME.isdigit() or (CACHE_CHANNEL_USERNAME.startswith('-') and CACHE_CHANNEL_USERNAME[1:].isdigit()):
        try:
            channel_id = int(CACHE_CHANNEL_USERNAME)
            if not str(channel_id).startswith('-100') and channel_id > 0:
                CACHE_CHANNEL_ID = f"-100{channel_id}"
            else:
                CACHE_CHANNEL_ID = str(channel_id)
        except ValueError:
            CACHE_CHANNEL_ID = None
    # إذا كان يوزر، نتركه كما هو
    elif CACHE_CHANNEL_USERNAME.startswith('@') or not CACHE_CHANNEL_USERNAME.startswith('-'):
        # إزالة @ إن وجدت
        username = CACHE_CHANNEL_USERNAME.replace('@', '')
        CACHE_CHANNEL_ID = f"@{username}"
    else:
        # صيغة ID مباشرة
        CACHE_CHANNEL_ID = CACHE_CHANNEL_USERNAME

# ============================================
# YouTube Data API Keys (متعددة للتدوير)
# ============================================
YT_API_KEYS_ENV = getenv("YT_API_KEYS", "[]")
try:
    import json
    YT_API_KEYS = json.loads(YT_API_KEYS_ENV) if YT_API_KEYS_ENV != "[]" else []
except:
    YT_API_KEYS = []

# مفاتيح افتراضية (تحديث مطلوب)
if not YT_API_KEYS:
    YT_API_KEYS = [
        "EQD5mxRgCuRNLxKxeOjG6r14iSroLF5FtomPnet-sgP5xNJb",
        # أضف مفاتيحك هنا
    ]

# ============================================
# خوادم Invidious الأفضل (محدثة 2025)
# ============================================
INVIDIOUS_SERVERS_ENV = getenv("INVIDIOUS_SERVERS", "[]")
try:
    import json
    INVIDIOUS_SERVERS = json.loads(INVIDIOUS_SERVERS_ENV) if INVIDIOUS_SERVERS_ENV != "[]" else []
except:
    INVIDIOUS_SERVERS = []

# خوادم افتراضية محدثة (مجربة ديسمبر 2024 - يناير 2025)
if not INVIDIOUS_SERVERS:
    INVIDIOUS_SERVERS = [
        "https://inv.nadeko.net",           # 🥇 الأفضل - 99.666% uptime
        "https://invidious.nerdvpn.de",     # 🥈 ممتاز - 100% uptime  
        "https://yewtu.be",                 # 🥉 جيد - 89.625% uptime
        "https://invidious.f5.si",          # ⚡ سريع - Cloudflare
        "https://invidious.materialio.us",  # 🌟 موثوق
        "https://invidious.reallyaweso.me", # 🚀 سريع
        "https://iteroni.com",              # ⚡ جيد
        "https://iv.catgirl.cloud",         # 😸 ممتاز
        "https://youtube.alt.tyil.nl",      # 🇳🇱 هولندا
    ]

# ============================================
# إعدادات ملفات الكوكيز المتعددة
# ============================================
COOKIES_FILES_ENV = getenv("COOKIES_FILES", "[]")
try:
    import json
    COOKIES_FILES = json.loads(COOKIES_FILES_ENV) if COOKIES_FILES_ENV != "[]" else []
except:
    COOKIES_FILES = []

# مسارات افتراضية لملفات الكوكيز
if not COOKIES_FILES:
    import os
    cookies_dir = "cookies"
    if os.path.exists(cookies_dir):
        COOKIES_FILES = [
            f"{cookies_dir}/cookies1.txt",
            f"{cookies_dir}/cookies2.txt", 
            f"{cookies_dir}/cookies3.txt",
            f"{cookies_dir}/cookies4.txt",
            f"{cookies_dir}/cookies5.txt"
        ]
        # فلترة الملفات الموجودة فقط
        COOKIES_FILES = [f for f in COOKIES_FILES if os.path.exists(f)]
    else:
        # ملف واحد افتراضي للتوافق
        COOKIES_FILES = ["cookies.txt"] if os.path.exists("cookies.txt") else []

# ============================================
# إعدادات الكوكيز (التوافق مع الكود القديم)
# ============================================
COOKIE_METHOD = "browser"
COOKIE_FILE = COOKIES_FILES[0] if COOKIES_FILES else "cookies.txt"

# ============================================
# إعدادات القنوات والدعم
# ============================================
Muntazer = getenv("muntazer", "CHANNEL_ASHTRAK")
CHANNEL_ASHTRAK = getenv("CHANNEL_ASHTRAK", "K55DD")
CHANNEL_NAME = getenv("CHANNEL_NAME", "السورس")
CHANNEL_LINK = getenv("CHANNEL_LINK", "K55DD")
STORE_NAME = getenv("STORE_NAME", "المتجر")
STORE_LINK = getenv("STORE_LINK", "https://t.me/YMMYN")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/K55DD")

# ============================================
# إعدادات المشروع العامة
# ============================================
DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", 480))
LOGGER_ID = int(getenv("LOGGER_ID", "-1001993781277"))
LANGUAGE = "ar"
LANGS = "ar"

# Get this value from @FallenxBot on Telegram by /id
OWNER_ID = int(getenv("OWNER_ID", 5901732027))

# ============================================
# إعدادات Heroku (اختياري)
# ============================================
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

# ============================================
# إعدادات Git
# ============================================
UPSTREAM_REPO = getenv("UPSTREAM_REPO", "https://github.com/saud552/NHAY7")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "master")
GIT_TOKEN = getenv("GIT_TOKEN", None)

# ============================================
# إعدادات الخدمات الخارجية
# ============================================
# Spotify API
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", None)
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", None)

# ============================================
# إعدادات الملفات والحدود
# ============================================
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", 25))
TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", 104857600))
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", 1073741824))

# ============================================
# إعدادات المساعد التلقائي
# ============================================
AUTO_LEAVING_ASSISTANT = getenv("AUTO_LEAVING_ASSISTANT", "True")

# ============================================
# متغيرات داخلية
# ============================================
APK = 5140000000
AMK = APK + 5600000
ANK = AMK + 9515
DAV = ANK

# ============================================
# URLs للصور
# ============================================
START_IMG_URL = getenv("START_IMG_URL", "https://te.legra.ph/file/e8bdc13568a49de93b071.jpg")
PING_IMG_URL = "https://te.legra.ph/file/b8a0c1a00db3e57522b53.jpg"
PLAYLIST_IMG_URL = "https://te.legra.ph/file/4ec5ae4381dffb039b4ef.jpg"
STATS_IMG_URL = "https://te.legra.ph/file/e906c2def5afe8a9b9120.jpg"
TELEGRAM_AUDIO_URL = "https://te.legra.ph/file/6298d377ad3eb46711644.jpg"
TELEGRAM_VIDEO_URL = "https://te.legra.ph/file/6298d377ad3eb46711644.jpg"
STREAM_IMG_URL = "https://te.legra.ph/file/bd995b032b6bd263e2cc9.jpg"
SOUNCLOUD_IMG_URL = "https://te.legra.ph/file/bb0ff85f2dd44070ea519.jpg"
YOUTUBE_IMG_URL = "https://telegra.ph/file/f995c36145125aa44bd37.jpg"
SPOTIFY_ARTIST_IMG_URL = "https://te.legra.ph/file/37d163a2f75e0d3b403d6.jpg"
SPOTIFY_ALBUM_IMG_URL = "https://te.legra.ph/file/b35fd1dfca73b950b1b05.jpg"
SPOTIFY_PLAYLIST_IMG_URL = "https://te.legra.ph/file/95b3ca7993bbfaf993dcb.jpg"

# ============================================
# متغيرات إضافية للتوافق
# ============================================
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}

def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(stringt.split(":"))))

DURATION_LIMIT = int(time_to_seconds(f"{DURATION_LIMIT_MIN}:00"))

# ============================================
# التحقق من صحة الإعدادات
# ============================================
if SUPPORT_CHAT:
    if not re.match("(?:http|https)://", SUPPORT_CHAT):
        raise SystemExit(
            "[ERROR] - Your SUPPORT_CHAT url is wrong. Please ensure that it starts with https://"
        )

# رسائل النظام
ASSISTANT_NOT_FOUND_MESSAGE = """
⚠️ **عذراً، لا يمكن تشغيل الموسيقى حالياً**

🚫 **المشكلة:** لا يوجد حساب مساعد متاح لتشغيل الموسيقى

📱 **ملاحظة:** يحتاج البوت لحسابات مساعدة لتشغيل الموسيقى في المكالمات الصوتية

📞 **للحصول على المساعدة:**
🔗 مجموعة الدعم: {SUPPORT_CHAT}
👤 مطور البوت: [المطور](tg://user?id={OWNER_ID})

⏰ **باقي وظائف البوت متاحة:** البحث، الأوامر، إدارة المجموعات

🔧 سيتم حل المشكلة في أقرب وقت ممكن
"""

# ============================================
# إعدادات إضافية للإحصائيات والإذاعة
# ============================================
ENABLE_DATABASE_CACHE = getenv("ENABLE_DATABASE_CACHE", "True").lower() == "true"
APPLICATION_VERSION = "2.0.0 TDLib Edition"
