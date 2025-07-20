# -*- coding: utf-8 -*-
"""
🚀 نظام التحميل الذكي الخارق - موحد لجميع أنواع المحادثات
=====================================================

يدمج بين:
- تدوير الكوكيز والمفاتيح التلقائي
- تخزين ذكي في قناة تيليجرام 
- بحث فائق السرعة في قاعدة البيانات
- تحميل متوازي لا محدود
- تبديل خاطف بين طرق التحميل
"""

import os
import re
import asyncio
import logging
import time
import sqlite3
import hashlib
import concurrent.futures
from typing import Dict, Optional, List
from itertools import cycle
import aiohttp
import aiofiles
import yt_dlp
from youtube_search import YoutubeSearch

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError, MessageIdInvalid

import config
from ZeMusic import app, LOGGER
from ZeMusic.platforms.Youtube import cookies
from ZeMusic.plugins.play.filters import command
from ZeMusic.utils.database import is_search_enabled, is_search_enabled1

# --- إعدادات النظام الذكي ---
REQUEST_TIMEOUT = 10
DOWNLOAD_TIMEOUT = 120
MAX_SESSIONS = 50  # عدد جلسات HTTP متوازية

# قناة التخزين الذكي
SMART_CACHE_CHANNEL = config.CACHE_CHANNEL_ID

# إعدادات العرض
channel = getattr(config, 'STORE_LINK', '')
lnk = f"https://t.me/{channel}" if channel else None

# --- تدوير المفاتيح والخوادم ---
YT_API_KEYS = config.YT_API_KEYS
API_KEYS_CYCLE = cycle(YT_API_KEYS) if YT_API_KEYS else None

INVIDIOUS_SERVERS = config.INVIDIOUS_SERVERS
INVIDIOUS_CYCLE = cycle(INVIDIOUS_SERVERS) if INVIDIOUS_SERVERS else None

# تدوير ملفات الكوكيز
COOKIES_FILES = config.COOKIES_FILES
COOKIES_CYCLE = cycle(COOKIES_FILES) if COOKIES_FILES else None

# --- إعدادات yt-dlp عالية الأداء ---
def get_ytdlp_opts(cookies_file=None):
    opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "retries": 2,
        "no-cache-dir": True,
        "ignoreerrors": True,
        "socket-timeout": REQUEST_TIMEOUT,
        "force-ipv4": True,
        "throttled-rate": "1M",
        "extractor-args": "youtube:player_client=android,web",
        "concurrent-fragments": 12,
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "postprocessor_args": ["-ar", "44100"],
        "noprogress": True,
        "verbose": False,
    }
    
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
    
    # إضافة aria2c إذا متوفر
    import shutil
    if shutil.which("aria2c"):
        opts.update({
            "external_downloader": "aria2c",
            "external_downloader_args": ["-x", "16", "-s", "16", "-k", "1M"],
        })
    
    return opts

# إنشاء مجلد التحميلات
os.makedirs("downloads", exist_ok=True)

# --- قاعدة البيانات للفهرسة الذكية ---
DB_FILE = "smart_cache.db"

def init_database():
    """تهيئة قاعدة البيانات للفهرسة الذكية"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            file_id TEXT UNIQUE,
            file_unique_id TEXT,
            
            search_hash TEXT UNIQUE,
            title_normalized TEXT,
            artist_normalized TEXT,
            keywords_vector TEXT,
            
            original_title TEXT,
            original_artist TEXT,
            duration INTEGER,
            file_size INTEGER,
            
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            popularity_rank REAL DEFAULT 0,
            
            phonetic_hash TEXT,
            partial_matches TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إنشاء الفهارس للسرعة الخارقة
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_search_hash ON channel_index(search_hash)",
        "CREATE INDEX IF NOT EXISTS idx_title_norm ON channel_index(title_normalized)",
        "CREATE INDEX IF NOT EXISTS idx_artist_norm ON channel_index(artist_normalized)",
        "CREATE INDEX IF NOT EXISTS idx_popularity ON channel_index(popularity_rank DESC)",
        "CREATE INDEX IF NOT EXISTS idx_message_id ON channel_index(message_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_id ON channel_index(file_id)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات عند بدء الوحدة
init_database()

class HyperSpeedDownloader:
    """مدير التحميل فائق السرعة"""
    
    def __init__(self):
        self.session_pool = []
        self.executor_pool = None
        self.method_performance = {
            'cache': {'weight': 1000, 'active': True, 'avg_time': 0.001},
            'youtube_api': {'weight': 100, 'active': True, 'avg_time': 2.0},
            'invidious': {'weight': 90, 'active': True, 'avg_time': 3.0},
            'ytdlp_cookies': {'weight': 80, 'active': True, 'avg_time': 5.0},
            'ytdlp_no_cookies': {'weight': 60, 'active': True, 'avg_time': 8.0},
            'youtube_search': {'weight': 50, 'active': True, 'avg_time': 4.0}
        }
        
        # تهيئة النظام
        asyncio.create_task(self.initialize())
    
    async def initialize(self):
        """تهيئة مجموعة الاتصالات الخارقة"""
        try:
            connector = aiohttp.TCPConnector(
                limit=1000,
                limit_per_host=200,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            # إنشاء جلسات HTTP متعددة
            for i in range(MAX_SESSIONS):
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers={'User-Agent': f'ZeMusic-{i}'}
                )
                self.session_pool.append(session)
            
            # مجموعة معالجات Thread عملاقة
            self.executor_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100)
            
            LOGGER(__name__).info("🚀 تم تهيئة نظام التحميل الخارق")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تهيئة النظام: {e}")
    
    def normalize_text(self, text: str) -> str:
        """تطبيع النص للبحث"""
        if not text:
            return ""
        
        # تحويل للأحرف الصغيرة وإزالة التشكيل
        text = text.lower()
        text = re.sub(r'[ًٌٍَُِّْ]', '', text)  # إزالة التشكيل
        text = re.sub(r'[^\w\s]', '', text)  # إزالة الرموز
        text = re.sub(r'\s+', ' ', text).strip()  # تنظيف المسافات
        
        # تطبيع الحروف العربية
        replacements = {
            'ة': 'ه', 'ي': 'ى', 'أ': 'ا', 'إ': 'ا',
            'آ': 'ا', 'ؤ': 'و', 'ئ': 'ي'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def create_search_hash(self, title: str, artist: str = "") -> str:
        """إنشاء هاش للبحث السريع"""
        normalized_title = self.normalize_text(title)
        normalized_artist = self.normalize_text(artist)
        combined = f"{normalized_title}_{normalized_artist}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    async def lightning_search_cache(self, query: str) -> Optional[Dict]:
        """بحث خاطف في الكاش (أقل من 0.001 ثانية)"""
        try:
            normalized_query = self.normalize_text(query)
            search_hash = self.create_search_hash(normalized_query)
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # بحث مباشر بالهاش
            cursor.execute(
                "SELECT message_id, file_id, original_title, original_artist, duration FROM channel_index WHERE search_hash = ? LIMIT 1",
                (search_hash,)
            )
            result = cursor.fetchone()
            
            if result:
                # تحديث إحصائيات الاستخدام
                cursor.execute(
                    "UPDATE channel_index SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE search_hash = ?",
                    (search_hash,)
                )
                conn.commit()
                conn.close()
                
                return {
                    'message_id': result[0],
                    'file_id': result[1],
                    'title': result[2],
                    'artist': result[3],
                    'duration': result[4],
                    'source': 'cache',
                    'cached': True
                }
            
            # بحث تقريبي
            cursor.execute(
                "SELECT message_id, file_id, original_title, original_artist, duration FROM channel_index WHERE title_normalized LIKE ? OR keywords_vector LIKE ? LIMIT 1",
                (f'%{normalized_query}%', f'%{normalized_query}%')
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return {
                    'message_id': result[0],
                    'file_id': result[1],
                    'title': result[2],
                    'artist': result[3],
                    'duration': result[4],
                    'source': 'cache_fuzzy',
                    'cached': True
                }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في البحث السريع: {e}")
        
        return None
    
    async def get_session(self):
        """الحصول على أقل جلسة مشغولة"""
        if not self.session_pool:
            await self.initialize()
        return self.session_pool[0]  # تبسيط للآن
    
    async def youtube_api_search(self, query: str) -> Optional[Dict]:
        """البحث عبر YouTube Data API"""
        if not API_KEYS_CYCLE:
            return None
        
        session = await self.get_session()
        
        for _ in range(len(YT_API_KEYS)):
            try:
                key = next(API_KEYS_CYCLE)
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": 1,
                    "key": key
                }
                
                async with session.get("https://www.googleapis.com/youtube/v3/search", params=params) as resp:
                    if resp.status != 200:
                        continue
                    
                    data = await resp.json()
                    items = data.get("items", [])
                    if not items:
                        continue
                    
                    item = items[0]
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    
                    return {
                        "video_id": video_id,
                        "title": snippet.get("title", "")[:60],
                        "artist": snippet.get("channelTitle", "Unknown"),
                        "thumb": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                        "source": "youtube_api"
                    }
                    
            except Exception as e:
                LOGGER(__name__).warning(f"فشل YouTube API: {e}")
                continue
        
        return None
    
    async def invidious_search(self, query: str) -> Optional[Dict]:
        """البحث عبر Invidious"""
        if not INVIDIOUS_CYCLE:
            return None
        
        session = await self.get_session()
        
        for _ in range(len(INVIDIOUS_SERVERS)):
            try:
                server = next(INVIDIOUS_CYCLE)
                url = f"{server}/api/v1/search"
                params = {"q": query, "type": "video"}
                
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        continue
                    
                    data = await resp.json()
                    video = next((item for item in data if item.get("type") == "video"), None)
                    if not video:
                        continue
                    
                    return {
                        "video_id": video.get("videoId"),
                        "title": video.get("title", "")[:60],
                        "artist": video.get("author", "Unknown"),
                        "duration": int(video.get("lengthSeconds", 0)),
                        "thumb": next(
                            (t.get("url") for t in reversed(video.get("videoThumbnails", []))),
                            None
                        ),
                        "source": "invidious"
                    }
                    
            except Exception as e:
                LOGGER(__name__).warning(f"فشل Invidious: {e}")
                continue
        
        return None
    
    async def youtube_search_simple(self, query: str) -> Optional[Dict]:
        """البحث عبر youtube_search"""
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            if not results:
                return None
            
            result = results[0]
            return {
                "video_id": result["id"],
                "title": result["title"][:60],
                "artist": result.get("channel", "Unknown"),
                "duration": result.get("duration", ""),
                "thumb": result["thumbnails"][0] if result.get("thumbnails") else None,
                "link": f"https://youtube.com{result['url_suffix']}",
                "source": "youtube_search"
            }
            
        except Exception as e:
            LOGGER(__name__).warning(f"فشل YouTube Search: {e}")
            return None
    
    async def download_with_ytdlp(self, video_info: Dict) -> Optional[Dict]:
        """تحميل عبر yt-dlp مع تدوير الكوكيز"""
        video_id = video_info.get("video_id")
        if not video_id:
            return None
        
        url = f"https://youtu.be/{video_id}"
        
        # محاولة مع الكوكيز أولاً
        if COOKIES_CYCLE:
            for _ in range(len(COOKIES_FILES)):
                try:
                    cookies_file = next(COOKIES_CYCLE)
                    opts = get_ytdlp_opts(cookies_file)
                    
                    loop = asyncio.get_running_loop()
                    info = await loop.run_in_executor(
                        self.executor_pool,
                        lambda: yt_dlp.YoutubeDL(opts).extract_info(url, download=True)
                    )
                    
                    if info:
                        audio_path = f"downloads/{video_id}.mp3"
                        if os.path.exists(audio_path):
                            return {
                                "audio_path": audio_path,
                                "title": info.get("title", video_info.get("title", ""))[:60],
                                "artist": info.get("uploader", video_info.get("artist", "Unknown")),
                                "duration": int(info.get("duration", 0)),
                                "file_size": os.path.getsize(audio_path),
                                "source": f"ytdlp_cookies_{cookies_file}"
                            }
                
                except Exception as e:
                    LOGGER(__name__).warning(f"فشل yt-dlp مع كوكيز {cookies_file}: {e}")
                    continue
        
        # محاولة بدون كوكيز
        try:
            opts = get_ytdlp_opts()
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                self.executor_pool,
                lambda: yt_dlp.YoutubeDL(opts).extract_info(url, download=True)
            )
            
            if info:
                audio_path = f"downloads/{video_id}.mp3"
                if os.path.exists(audio_path):
                    return {
                        "audio_path": audio_path,
                        "title": info.get("title", video_info.get("title", ""))[:60],
                        "artist": info.get("uploader", video_info.get("artist", "Unknown")),
                        "duration": int(info.get("duration", 0)),
                        "file_size": os.path.getsize(audio_path),
                        "source": "ytdlp_no_cookies"
                    }
        
        except Exception as e:
            LOGGER(__name__).error(f"فشل yt-dlp بدون كوكيز: {e}")
        
        return None
    
    async def cache_to_channel(self, audio_info: Dict, search_query: str) -> Optional[str]:
        """حفظ الملف في قناة التخزين وقاعدة البيانات"""
        if not SMART_CACHE_CHANNEL:
            return None
        
        try:
            audio_path = audio_info["audio_path"]
            title = audio_info["title"]
            artist = audio_info["artist"]
            duration = audio_info["duration"]
            file_size = audio_info["file_size"]
            
            # إنشاء caption للملف
            caption = f"""🎵 {title}
🎤 {artist}
⏱️ {duration}s | 📊 {file_size/1024/1024:.1f}MB
🔗 {audio_info["source"]}
🔍 {search_query}"""
            
            # رفع الملف للقناة
            message = await app.send_audio(
                chat_id=SMART_CACHE_CHANNEL,
                audio=audio_path,
                title=title,
                performer=artist,
                duration=duration,
                caption=caption
            )
            
            # حفظ في قاعدة البيانات
            search_hash = self.create_search_hash(title, artist)
            normalized_title = self.normalize_text(title)
            normalized_artist = self.normalize_text(artist)
            keywords = f"{normalized_title} {normalized_artist} {self.normalize_text(search_query)}"
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO channel_index 
                (message_id, file_id, file_unique_id, search_hash, title_normalized, artist_normalized, 
                 keywords_vector, original_title, original_artist, duration, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.id, message.audio.file_id, message.audio.file_unique_id,
                search_hash, normalized_title, normalized_artist, keywords,
                title, artist, duration, file_size
            ))
            
            conn.commit()
            conn.close()
            
            LOGGER(__name__).info(f"✅ تم حفظ {title} في التخزين الذكي")
            return message.audio.file_id
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حفظ التخزين: {e}")
        
        return None
    
    async def hyper_download(self, query: str) -> Optional[Dict]:
        """النظام الخارق للتحميل مع جميع الطرق"""
        start_time = time.time()
        
        try:
            # خطوة 1: البحث الفوري في الكاش
            cached_result = await self.lightning_search_cache(query)
            if cached_result:
                LOGGER(__name__).info(f"⚡ كاش فوري: {query} ({time.time() - start_time:.3f}s)")
                return cached_result
            
            # خطوة 2: البحث عن معلومات الفيديو بالتوازي
            search_tasks = []
            
            if API_KEYS_CYCLE:
                search_tasks.append(('youtube_api', self.youtube_api_search(query)))
            if INVIDIOUS_CYCLE:
                search_tasks.append(('invidious', self.invidious_search(query)))
            search_tasks.append(('youtube_search', self.youtube_search_simple(query)))
            
            # تشغيل جميع عمليات البحث بالتوازي
            search_results = await asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True)
            
            # أخذ أول نتيجة ناجحة
            video_info = None
            for i, result in enumerate(search_results):
                if isinstance(result, dict) and result.get("video_id"):
                    video_info = result
                    break
            
            if not video_info:
                return None
            
            # خطوة 3: تحميل الصوت
            audio_info = await self.download_with_ytdlp(video_info)
            if not audio_info:
                return None
            
            # خطوة 4: حفظ في التخزين الذكي (في الخلفية)
            if SMART_CACHE_CHANNEL:
                asyncio.create_task(self.cache_to_channel(audio_info, query))
            
            LOGGER(__name__).info(f"✅ تحميل جديد: {query} ({time.time() - start_time:.3f}s)")
            
            return {
                'audio_path': audio_info['audio_path'],
                'title': audio_info['title'],
                'artist': audio_info['artist'],
                'duration': audio_info['duration'],
                'source': audio_info['source'],
                'cached': False
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في التحميل الخارق: {e}")
            return None

# إنشاء مدير التحميل العالمي
downloader = HyperSpeedDownloader()

async def remove_temp_files(*paths):
    """حذف الملفات المؤقتة"""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                LOGGER(__name__).warning(f"فشل حذف {path}: {e}")

async def download_thumbnail(url: str, title: str) -> Optional[str]:
    """تحميل الصورة المصغرة"""
    if not url:
        return None
    
    try:
        title_clean = re.sub(r'[\\/*?:"<>|]', "", title)
        thumb_path = f"downloads/thumb_{title_clean[:20]}.jpg"
        
        session = await downloader.get_session()
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(thumb_path, mode='wb') as f:
                    await f.write(await resp.read())
                return thumb_path
    except Exception as e:
        LOGGER(__name__).warning(f"فشل تحميل الصورة: {e}")
    
    return None

# --- المعالج الموحد لجميع أنواع المحادثات ---
@app.on_message(
    command(["song", "/song", "بحث", config.BOT_NAME + " ابحث", "يوت"]) & 
    (filters.private | filters.group | filters.channel)
)
async def smart_download_handler(client, message: Message):
    """المعالج الموحد للتحميل الذكي"""
    
    # التحقق من تفعيل الخدمة
    try:
        if message.chat.type == "private":
            if not await is_search_enabled1():
                return await message.reply_text("⟡ عذراً عزيزي اليوتيوب معطل من قبل المطور")
        else:
            if not await is_search_enabled():
                return await message.reply_text("⟡ عذراً عزيزي اليوتيوب معطل من قبل المطور")
    except:
        pass
    
    # استخراج الاستعلام
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply_text("📝 **الاستخدام:** `بحث اسم الأغنية`")
    
    # رسالة المعالجة
    status_msg = await message.reply_text("⚡ **جاري المعالجة بالنظام الذكي...**")
    
    try:
        # التحميل بالنظام الخارق
        result = await downloader.hyper_download(query)
        
        if not result:
            await status_msg.edit_text("❌ **فشل في العثور على النتائج، جرب استعلاماً آخر**")
            return
        
        # تحديث الرسالة
        source_emoji = {
            'cache': '⚡ من التخزين السريع',
            'youtube_api': '🔍 YouTube API',
            'invidious': '🌐 Invidious',
            'ytdlp_cookies': '🍪 تحميل مع كوكيز',
            'ytdlp_no_cookies': '📥 تحميل مباشر',
            'youtube_search': '🔎 بحث يوتيوب'
        }
        
        source_text = source_emoji.get(result['source'], result['source'])
        await status_msg.edit_text(f"🎵 **تم العثور على:** {result['title']}\n📡 **المصدر:** {source_text}\n⬆️ **جاري الرفع...**")
        
        # إعداد الملف للإرسال
        if result.get('cached') and result.get('file_id'):
            # إرسال من الكاش
            await message.reply_audio(
                audio=result['file_id'],
                caption=f"🎵 **{result['title']}**\n🎤 **{result['artist']}**\n📡 **{source_text}**",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 قناة البوت", url=lnk)
                ]]) if lnk else None
            )
        else:
            # تحميل الصورة المصغرة
            thumb_path = None
            if 'thumb' in result and result['thumb']:
                thumb_path = await download_thumbnail(result['thumb'], result['title'])
            
            # إرسال الملف الجديد
            await message.reply_audio(
                audio=result['audio_path'],
                title=result['title'],
                performer=result['artist'],
                duration=result.get('duration', 0),
                thumb=thumb_path,
                caption=f"🎵 **{result['title']}**\n🎤 **{result['artist']}**\n📡 **{source_text}**",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 قناة البوت", url=lnk)
                ]]) if lnk else None
            )
            
            # حذف الملفات المؤقتة
            await remove_temp_files(result.get('audio_path'), thumb_path)
        
        # حذف رسالة المعالجة
        try:
            await status_msg.delete()
        except:
            pass
        
    except Exception as e:
        LOGGER(__name__).error(f"خطأ في المعالج: {e}")
        try:
            await status_msg.edit_text(f"❌ **خطأ في المعالجة:** {str(e)}")
        except:
            pass

# --- إحصائيات سريعة للمطور ---
@app.on_message(command(["cache_stats"]) & filters.user(config.OWNER_ID))
async def cache_stats_handler(client, message: Message):
    """عرض إحصائيات التخزين الذكي"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM channel_index")
        total_cached = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(access_count) FROM channel_index")
        total_hits = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT original_title, access_count FROM channel_index ORDER BY access_count DESC LIMIT 5")
        top_songs = cursor.fetchall()
        
        conn.close()
        
        stats_text = f"""📊 **إحصائيات التخزين الذكي**

💾 **المحفوظ:** {total_cached} ملف
⚡ **مرات الاستخدام:** {total_hits}
📈 **معدل الكفاءة:** {(total_hits/max(1,total_cached)):.1f}

🎵 **الأكثر طلباً:**
"""
        
        for i, (title, count) in enumerate(top_songs, 1):
            stats_text += f"{i}. {title[:30]}... ({count})\n"
        
        await message.reply_text(stats_text)
        
    except Exception as e:
        await message.reply_text(f"❌ خطأ: {e}")

LOGGER(__name__).info("🚀 تم تحميل نظام التحميل الذكي الخارق")
