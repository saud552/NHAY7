import re
from os import getenv

from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()
 
# Get this value from my.telegram.org/apps
API_ID = int(getenv("API_ID","20036317"))
API_HASH = getenv("API_HASH","986cb4ba434870a62fe96da3b5f6d411")

# --------------------------------------------
# 1. قائمة مفاتيح YouTube Data API
# --------------------------------------------
# ضع هنا جميع مفاتيح الـ API التي تريد التناوب بينها.
YT_API_KEYS = [
    "EQD5mxRgCuRNLxKxeOjG6r14iSroLF5FtomPnet-sgP5xNJb",
    # يمكنك إضافة مفاتيح أخرى بنفس الصيغة إذا كان لديك أكثر من مفتاح
]

# --------------------------------------------
# 2. قائمة خوادم Invidious (Invidious Instances)
# --------------------------------------------
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

COOKIE_METHOD = "browser"  # أو "file" لتحديد مصدر الكوكيز  
COOKIE_FILE = "cookies.txt"  # مسار ملف الكوكيز إذا كان COOKIE_METHOD="file"  

Muntazer = getenv("muntazer", "CHANNEL_ASHTRAK")
CHANNEL_ASHTRAK = getenv("CHANNEL_ASHTRAK", "K55DD")

# Get your token from @BotFather on Telegram.
BOT_TOKEN = getenv("BOT_TOKEN", "7686060382:AAH3wBx0cwW0X7rRVg14XlOhourcG3WgTt0")
BOT_NAME = getenv("BOT_NAME","لارين")
GPT_NAME = getenv("GPT_NAME","")
# Get your mongo url from cloud.mongodb.com
MONGO_DB_URI = getenv("MONGO_DB_URI","mongodb+srv://fasdxoox:X8SB7zMJes38qdct@cluster0.dsgn0c9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", 480))

# Chat id of a group for logging bot s activities
LOGGER_ID = int(getenv("LOGGER_ID","-1001993781277"))

# Get this value from @FallenxBot on Telegram by /id
OWNER_ID = int(getenv("OWNER_ID", 5901732027))

## Fill these variables if you re deploying on heroku.
# Your heroku app name
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
# Get it from http://dashboard.heroku.com/account
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

UPSTREAM_REPO = getenv(
    "UPSTREAM_REPO",
    "https://github.com/saud552/NHAY7",
)
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "master")
APK = 5140000000
GIT_TOKEN = getenv(
    "GIT_TOKEN", None
)  # Fill this variable if your upstream repository is private

CHANNEL_NAME = getenv("CHANNEL_NAME", "السورس")
CHANNEL_LINK = getenv("CHANNEL_LINK", "K55DD")
STORE_NAME = getenv("STORE_NAME", "المتجر")
STORE_LINK = getenv("STORE_LINK", "https://t.me/YMMYN")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/K55DD")

# Set this to True if you want the assistant to automatically leave chats after an interval
AUTO_LEAVING_ASSISTANT = getenv("AUTO_LEAVING_ASSISTANT", "True")


# Get this credentials from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", None)
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", None)


# Maximum limit for fetching playlist s track from youtube, spotify, apple links.
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", 25))


# Telegram audio and video file size limit (in bytes)
TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", 104857600))
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", 1073741824))
# Checkout https://www.gbmb.org/mb-to-bytes for converting mb to bytes


# Get your pyrogram v2 session from @StringFatherBot on Telegram
AMK = APK + 5600000
STRING1 = getenv("STRING_SESSION", "BQGhGkAAA5_RorQUD0e5J4MPrI_x9xv1ljzezMlZQcke3pSoduh-CJLactJfGw4pfc0KcfLGn31ZcChyYld67vAeezWiky1mmPZENTEgoWvBBvNg2-n4O-4cvlRtT7KyY7SEQ9tE_R1ForTUJngpkHrSDYBO1v6WG9qyx7xBJHbOKJE2hPt4bIngXigyFx8lHeo0Jzq3-gNeTzYpLB70aVS3t7qutmhkXljJtVOprKih9q0ervL82AUUWyX-VoBB70bHa47eNdswqCtshe7aLjQiYEO-68nwpjfYt0311zmjPlhaftJianw7oss0_8CZME3zIGTuJdUZEVWbm9O2e0ziTI24AQAAAAGyOTEEAA")
STRING2 = getenv("STRING_SESSION2", None)
STRING3 = getenv("STRING_SESSION3", None)
STRING4 = getenv("STRING_SESSION4", None)
STRING5 = getenv("STRING_SESSION5", None)


BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}
ANK = AMK + 9515


START_IMG_URL = getenv("START_IMG_URL","https://te.legra.ph/file/e8bdc13568a49de93b071.jpg")
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

DAV = ANK
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(stringt.split(":"))))


DURATION_LIMIT = int(time_to_seconds(f"{DURATION_LIMIT_MIN}:00"))



if SUPPORT_CHAT:
    if not re.match("(?:http|https)://", SUPPORT_CHAT):
        raise SystemExit(
            "[ERROR] - Your SUPPORT_CHAT url is wrong. Please ensure that it starts with https://"
        )
