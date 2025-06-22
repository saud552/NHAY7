# -*- coding: utf-8 -*-
import os
import re
import asyncio
import logging
import time

import aiohttp
import aiofiles
import yt_dlp

from itertools import cycle
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError

import config
from ZeMusic.platforms.Youtube import cookies
from ZeMusic import app
from ZeMusic.plugins.play.filters import command
from ZeMusic.utils.decorators import AdminActual
from ZeMusic.utils.database import is_search_enabled, enable_search, disable_search

# --- إعدادات الأداء والتدوير ---
MAX_CONCURRENT_DOWNLOADS = 50
REQUEST_TIMEOUT = 15

YT_API_KEYS = getattr(config, "YT_API_KEYS", [])[:]
API_KEYS_CYCLE = cycle(YT_API_KEYS) if YT_API_KEYS else None
INVIDIOUS_SERVERS = getattr(config, "INVIDIOUS_SERVERS", [])
INVIDIOUS_CYCLE = cycle(INVIDIOUS_SERVERS) if INVIDIOUS_SERVERS else None

# رابط القناة
channel = getattr(config, 'STORE_LINK', '')
lnk = f"https://t.me/{channel}" if channel else None

# إعدادات yt-dlp المتقدمة
YTDLP_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "retries": 3,
    "no-cache-dir": True,
    "ignoreerrors": True,
    "socket-timeout": REQUEST_TIMEOUT,
    "source-address": "0.0.0.0",
    "force-ipv4": True,
    "throttled-rate": "100K",
    "hls-use-mpegts": True,
    "extractor-args": "youtube:player_client=android",
    "postprocessor-args": "-ar 44100 -ac 2 -b:a 192k",
    "concurrent-fragments": 5,
}
# استخدام ملف الكوكيز من ZeMusic
try:
    cookie_file = cookies()
    if cookie_file:
        YTDLP_OPTS["cookiefile"] = cookie_file
except Exception as e:
    logging.error(f"فشل في استخدام ملف الكوكيز: {e}")

# مسار البحث في Invidious و ترويسة الطلبات
INVIDIOUS_SEARCH_PATH = "/api/v1/search"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ضبط السيمفور لتقييد التحميلات المتزامنة
semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

# ضبط الدليل لتنزيل الملفات
os.makedirs("downloads", exist_ok=True)

# تكوين السجل (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_performance.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- دالة حذف الملفات المؤقتة ---
async def remove_temp_files(*paths):
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"تم حذف الملف المؤقت: {path}")
            except Exception as e:
                logger.error(f"خطأ في حذف الملف {path}: {e}")

# --- البحث عبر Invidious API ---
async def search_invidious(query: str) -> dict:
    if not INVIDIOUS_SERVERS:
        return None
    async with semaphore:
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
            for _ in range(len(INVIDIOUS_SERVERS)):
                server = next(INVIDIOUS_CYCLE)
                try:
                    async with session.get(f"{server}{INVIDIOUS_SEARCH_PATH}", params={"q": query}) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                    video = next((item for item in data if item.get("type") == "video"), None)
                    if not video:
                        continue
                    result = {
                        "video_id": video.get("videoId"),
                        "title": video.get("title", "")[:60],
                        "author": video.get("author", "Unknown"),
                        "duration": int(video.get("lengthSeconds", 0)),
                        "thumb": next(
                            (t.get("url") for t in reversed(video.get("videoThumbnails", []))
                             if t.get("quality") == "medium"), None),
                        "source": "invidious"
                    }
                    return result
                except Exception as e:
                    logger.warning(f"فشل Invidious ({server}): {type(e).__name__}")
                    continue
    return None

# --- البحث عبر YouTube Data API ---
async def search_youtube_api(query: str) -> dict:
    if not YT_API_KEYS:
        return None
    async with semaphore:
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
            for _ in range(len(YT_API_KEYS)):
                key = next(API_KEYS_CYCLE)
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": 1,
                    "key": key
                }
                try:
                    async with session.get("https://www.googleapis.com/youtube/v3/search", params=params) as resp:
                        if resp.status != 200:
                            logger.warning(f"خطأ في YouTube API المفتاح {key[-5:]}: {resp.status}")
                            continue
                        result = await resp.json()
                    items = result.get("items", [])
                    if not items:
                        continue
                    item = items[0]
                    vid = item["id"]["videoId"]
                    snippet = item["snippet"]
                    detail_params = {
                        "part": "contentDetails",
                        "id": vid,
                        "key": key
                    }
                    async with session.get("https://www.googleapis.com/youtube/v3/videos", params=detail_params) as detail_resp:
                        if detail_resp.status != 200:
                            duration = 0
                        else:
                            detail_data = await detail_resp.json()
                            duration_iso = detail_data["items"][0]["contentDetails"]["duration"]
                            duration = convert_duration(duration_iso)
                    result = {
                        "video_id": vid,
                        "title": snippet.get("title", "")[:60],
                        "author": snippet.get("channelTitle", "Unknown"),
                        "duration": duration,
                        "thumb": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                        "source": "youtube_api"
                    }
                    return result
                except Exception as e:
                    logger.warning(f"فشل YouTube API: {type(e).__name__}")
                    continue
    return None

# --- تحويل مدة YouTube (ISO 8601) إلى ثواني ---
def convert_duration(duration: str) -> int:
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

# --- تنزيل الصوت عبر yt-dlp ---
async def download_with_ytdlp(video_id: str) -> dict:
    url = f"https://youtu.be/{video_id}"
    opts = YTDLP_OPTS.copy()
    opts["outtmpl"] = f"downloads/{video_id}.%(ext)s"
    try:
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(opts).extract_info(url, download=True))
        if not info:
            raise Exception("فشل استخراج معلومات الفيديو")
        ext = info.get("ext", "")
        audio_path = f"downloads/{video_id}.{ext}"
        if not os.path.exists(audio_path):
            files = [f for f in os.listdir("downloads") if f.startswith(video_id)]
            if files:
                audio_path = os.path.join("downloads", files[0])
            else:
                raise FileNotFoundError("لم يتم إنشاء ملف الصوت")
        result = {
            "audio": audio_path,
            "title": info.get("title", "")[:60],
            "author": info.get("uploader", "Unknown"),
            "duration": int(info.get("duration", 0)),
            "thumb": next(
                (t.get("url") for t in reversed(info.get("thumbnails", []))
                 if t.get("preference") == 1 or t.get("id") == "cover"),
                None
            ),
            "source": "yt-dlp"
        }
        return result
    except Exception as e:
        logger.error(f"خطأ في yt-dlp: {type(e).__name__} - {str(e)}")
        return None

# --- تحميل الصورة المصغرة ---
async def fetch_thumbnail(url: str, video_id: str) -> str:
    if not url or not video_id:
        return None
    path = f"downloads/thumb_{video_id}.jpg"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(path, mode='wb') as f:
                        await f.write(await resp.read())
                    return path
    except Exception as e:
        logger.warning(f"خطأ في تحميل الصورة: {e}")
    return None

# --- المعالج الرئيسي لأمر الأغنية ---
@app.on_message(command(["song", "/song", "بحث", config.BOT_NAME + " ابحث", "يوت"]) & filters.group)
async def song_downloader(client, message: Message):
    start_time = time.time()
    chat_id = message.chat.id

    # التحقق من حالة التفعيل
    if not await is_search_enabled(chat_id):
        await message.reply_text(
            "<b>⟡ عذراً، اليوتيوب معطل في هذه المجموعة. اكتب '</b>"
            "<code>تفعيل اليوتيوب</code>"
            "<b>' لتمكينه.</b>",
            parse_mode="HTML"
        )
        return

    # استخراج نص الأمر (اسم الأغنية أو الرابط)
    query = " ".join(message.command[1:])
    if not query:
        await message.reply_text("<b>⟡ يرجى إدخال اسم الأغنية أو الرابط</b>", parse_mode="HTML")
        return

    info = None
    thumb_path = None

    try:
        # التحقق إن كان الرابط أو آيدي مباشر
        yt_match = re.search(r"(?:youtu\.be/|youtube\.com/watch\?v=|youtube\.com/embed/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})", query)
        if yt_match:
            video_id = yt_match.group(1)
            info = await download_with_ytdlp(video_id)
            if not info:
                raise Exception("فشل تحميل المقطع من YouTube.")
        else:
            # إرسال رسالة البحث
            msg = await message.reply_text("<b>🔍 جاري البحث عن المقطع...</b>", parse_mode="HTML")
            # محاولة البحث بالطرق المتاحة
            info = None
            search_methods = [search_invidious, search_youtube_api]
            for method in search_methods:
                try:
                    info = await method(query)
                    if info:
                        break
                except Exception as e:
                    logger.warning(f"فشل البحث بالطريقة {method.__name__}: {e}")
                    continue
            # إذا فشلت طرق البحث
            if not info:
                raise Exception("لم يتم العثور على نتائج لبحثك.")
            # تنزيل الصوت إن لم يكن جاهزاً
            if "audio" not in info:
                audio_info = await download_with_ytdlp(info["video_id"])
                if audio_info:
                    info.update(audio_info)
                else:
                    raise Exception("فشل تحميل الصوت")
            await msg.edit_text("<b>📤 جاري رفع المقطع الصوتي...</b>", parse_mode="HTML")
            thumb_path = await fetch_thumbnail(info.get("thumb"), info.get("video_id", ""))
            await msg.delete()

        # تحميل الصورة المصغرة إذا لم تكن جاهزة
        if not thumb_path:
            thumb_path = await fetch_thumbnail(info.get("thumb"), info.get("video_id", ""))
        # إرسال الملف الصوتي مع البيانات
        await message.reply_audio(
            audio=info["audio"],
            title=info.get("title", "Unknown"),
            performer=info.get("author", "Unknown"),
            duration=info.get("duration", 0),
            thumb=thumb_path,
            caption=(
                f"🎵 {info.get('title', 'Unknown')}\n"
                f"👤 {info.get('author', 'Unknown')}\n"
                f"⏱️ {info.get('duration', 0)//60}:{info.get('duration', 0)%60:02d}\n"
                f"🔧 {info.get('source', '')}"
            ),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="sᴀᴜᴅ ♪", url=lnk)]]) if lnk else None
        )
        proc_time = time.time() - start_time
        logger.info(f"تم تنزيل '{query[:20]}' في {proc_time:.2f} ثانية")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await song_downloader(client, message)
    except RPCError as e:
        logger.error(f"خطأ في RPC: {e}")
        await message.reply_text("<b>⟡ حدث خطأ في الشبكة، يرجى المحاولة لاحقاً</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {type(e).__name__} - {str(e)}")
        await message.reply_text(f"<b>⟡ حدث خطأ جسيم: {str(e)[:100]}</b>", parse_mode="HTML")
    finally:
        if info:
            await remove_temp_files(info.get("audio"), thumb_path)

# --- أوامر تفعيل/تعطيل اليوتيوب ---
@app.on_message(command(["تعطيل اليوتيوب"]) & filters.group)
@AdminActual
async def disable_search_command(client, message: Message, _):
    chat_id = message.chat.id
    if not await is_search_enabled(chat_id):
        await message.reply_text("<b>⟡ اليوتيوب معطل مسبقاً في هذه المجموعة</b>", parse_mode="HTML")
        return
    await disable_search(chat_id)
    await message.reply_text("<b>⟡ تم تعطيل اليوتيوب بنجاح في هذه المجموعة</b>", parse_mode="HTML")

@app.on_message(command(["تفعيل اليوتيوب"]) & filters.group)
@AdminActual
async def enable_search_command(client, message: Message, _):
    chat_id = message.chat.id
    if await is_search_enabled(chat_id):
        await message.reply_text("<b>⟡ اليوتيوب مفعل مسبقاً في هذه المجموعة</b>", parse_mode="HTML")
        return
    await enable_search(chat_id)
    await message.reply_text("<b>⟡ تم تفعيل اليوتيوب بنجاح في هذه المجموعة</b>", parse_mode="HTML")
