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
MIN_ASSISTANTS = int(getenv("MIN_ASSISTANTS", "1"))

# للتوافق مع الكود القديم (اختياري)
STRING1 = getenv("STRING_SESSION", None)
STRING2 = getenv("STRING_SESSION2", None)
STRING3 = getenv("STRING_SESSION3", None)
STRING4 = getenv("STRING_SESSION4", None)
STRING5 = getenv("STRING_SESSION5", None)

# ============================================
# YouTube Data API Keys
# ============================================
YT_API_KEYS = [
    "EQD5mxRgCuRNLxKxeOjG6r14iSroLF5FtomPnet-sgP5xNJb",
    # يمكن إضافة مفاتيح أخرى
]

# ============================================
# Invidious Servers
# ============================================
INVIDIOUS_SERVERS = [
    "https://yewtu.be",
    "https://vid.puffyan.us",
    "https://inv.riverside.rocks",
    "https://yewtu.eu.org",
    "https://yewtu.cafe",
    "https://yewtu.snopyta.org",
    "https://yewtu.shareyour.world",
    "https://yewtu.privacytools.io",
    "https://yewtu.kavin.rocks",
    "https://yewtu.nixnet.services",
    "https://yewtu.ossdv.cn",
    "https://yewtu.invidious.io",
    "https://yewtu.mooo.com",
    "https://yewtu.fdn.fr",
    "https://invidious.snopyta.org",
    "https://yewtu.ayaka.systems",
    "https://yewtu.offensive-security.dev"
]

# ============================================
# إعدادات الكوكيز
# ============================================
COOKIE_METHOD = "browser"
COOKIE_FILE = "cookies.txt"

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
ASSISTANT_NOT_FOUND_MESSAGE = (
    "❌ **خطأ في النظام**\n\n"
    "🔍 **المشكلة:** لم يتم العثور على حساب مساعد متاح\n"
    "⚠️ **الحل:** يرجى التواصل مع مطور البوت لإضافة حساب مساعد\n\n"
    "👨‍💻 **للتواصل:** {SUPPORT_CHAT}\n"
    "📱 **المطور:** @{OWNER_ID}"
)
