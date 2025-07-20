"""
🎵 YouTube Platform Handler - Enhanced Edition
تطوير: ZeMusic Bot Team

الميزات الجديدة:
- نظام تحميل ذكي مع كاش متقدم
- تدوير تلقائي للكوكيز ومفاتيح API
- معالجة أخطاء شاملة ومتقدمة
- دعم خوادم Invidious المتعددة
- نظام إحصائيات ومراقبة الأداء
- تحسينات الأمان والاستقرار
"""

import asyncio
import glob
import os
import random
import re
import logging
import time
import hashlib
import json
from typing import Union, Dict, List, Optional, Tuple
from itertools import cycle
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from ZeMusic.pyrogram_compatibility.enums import MessageEntityType
from ZeMusic.pyrogram_compatibility.types import Message
from youtubesearchpython.__future__ import VideosSearch
from yt_dlp import YoutubeDL

import config
from ZeMusic import app
from ZeMusic.utils.database import is_on_off
from ZeMusic.utils.formatters import time_to_seconds, seconds_to_min
from ZeMusic.utils.decorators import asyncify

# =============================================================================
# إعدادات النظام المتقدم
# =============================================================================

# إعدادات التدوير المحسنة
YT_API_KEYS = getattr(config, "YT_API_KEYS", [])[:]
API_KEYS_CYCLE = cycle(YT_API_KEYS) if YT_API_KEYS else None
INVIDIOUS_SERVERS = getattr(config, "INVIDIOUS_SERVERS", [])
INVIDIOUS_CYCLE = cycle(INVIDIOUS_SERVERS) if INVIDIOUS_SERVERS else None

# إعدادات التحكم في التزامن والأداء
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(15)  # زيادة الحد المسموح
SEARCH_SEMAPHORE = asyncio.Semaphore(20)    # للبحث السريع
CONCURRENT_DOWNLOADS = 10

# إعدادات الكاش
CACHE_DIR = Path("cache/youtube")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DURATION = timedelta(hours=6)  # مدة صلاحية الكاش

# إعدادات التحميل
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# تكوين السجل المتقدم
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# إحصائيات الأداء
performance_stats = {
    'total_downloads': 0,
    'successful_downloads': 0,
    'failed_downloads': 0,
    'cache_hits': 0,
    'api_calls': 0,
    'last_reset': time.time()
}

@dataclass
class VideoInfo:
    """كلاس لمعلومات الفيديو"""
    title: str
    duration: str
    duration_sec: int
    thumbnail: str
    video_id: str
    link: str
    uploader: str = ""
    view_count: int = 0
    upload_date: str = ""
    quality_formats: List[Dict] = None

@dataclass
class DownloadResult:
    """نتيجة التحميل"""
    success: bool
    file_path: Optional[str]
    error_message: Optional[str]
    file_size: int = 0
    download_time: float = 0.0

# =============================================================================
# دوال مساعدة محسنة
# =============================================================================

def cookies():
    """إرجاع مسار ملف كوكيز عشوائي مع فلترة الملفات الصالحة"""
    try:
        folder_path = Path("cookies")
        folder_path.mkdir(exist_ok=True)
        
        txt_files = list(folder_path.glob("*.txt"))
        
        # فلترة الملفات الصالحة فقط
        valid_files = []
        for file_path in txt_files:
            if file_path.stat().st_size > 0:  # التأكد من أن الملف ليس فارغاً
                valid_files.append(str(file_path))
        
        if not valid_files:
            logger.warning("⚠️ لم يتم العثور على ملفات كوكيز صالحة")
            return None
            
        selected_file = random.choice(valid_files)
        logger.debug(f"🍪 تم اختيار ملف كوكيز: {selected_file}")
        return selected_file
        
    except Exception as e:
        logger.error(f"❌ خطأ في دالة الكوكيز: {str(e)}")
        return None

def get_cache_key(query: str, query_type: str = "search") -> str:
    """إنشاء مفتاح كاش فريد"""
    content = f"{query_type}:{query}:{time.strftime('%Y-%m-%d-%H')}"
    return hashlib.md5(content.encode()).hexdigest()

async def get_from_cache(cache_key: str) -> Optional[Dict]:
    """الحصول على البيانات من الكاش"""
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        # التحقق من صلاحية الكاش
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_time > CACHE_DURATION:
            cache_file.unlink()  # حذف الكاش المنتهي الصلاحية
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            performance_stats['cache_hits'] += 1
            logger.debug(f"📦 تم استخدام الكاش: {cache_key}")
            return data
            
    except Exception as e:
        logger.error(f"❌ خطأ في قراءة الكاش: {str(e)}")
        return None

async def save_to_cache(cache_key: str, data: Dict):
    """حفظ البيانات في الكاش"""
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.debug(f"💾 تم حفظ الكاش: {cache_key}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الكاش: {str(e)}")

async def shell_cmd(cmd: str, timeout: int = 300) -> str:
    """تنفيذ أمر shell مع معالجة متقدمة للأخطاء"""
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=timeout
        )
        
        out, errorz = await proc.communicate()
        
        if errorz:
            error_msg = errorz.decode("utf-8")
            # تجاهل بعض التحذيرات العادية
            ignored_warnings = [
                "unavailable videos are hidden",
                "requested format not available",
                "falling back to"
            ]
            
            if any(warning in error_msg.lower() for warning in ignored_warnings):
                return out.decode("utf-8")
            
            logger.warning(f"⚠️ تحذير shell: {error_msg}")
            return error_msg
            
        return out.decode("utf-8")
        
    except asyncio.TimeoutError:
        logger.error(f"⏰ انتهت مهلة تنفيذ الأمر: {cmd}")
        return "خطأ: انتهت مهلة التنفيذ"
    except Exception as e:
        logger.error(f"❌ خطأ في shell_cmd: {str(e)}")
        return str(e)

def convert_duration(duration: str) -> int:
    """تحويل مدة YouTube (ISO 8601) إلى ثواني مع دعم تنسيقات متعددة"""
    if not duration:
        return 0
        
    try:
        # تنسيق ISO 8601 (PT4M13S)
        iso_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if iso_match:
            hours = int(iso_match.group(1)) if iso_match.group(1) else 0
            minutes = int(iso_match.group(2)) if iso_match.group(2) else 0
            seconds = int(iso_match.group(3)) if iso_match.group(3) else 0
            return hours * 3600 + minutes * 60 + seconds
        
        # تنسيق عادي (4:13)
        time_parts = duration.split(':')
        if len(time_parts) == 2:  # MM:SS
            return int(time_parts[0]) * 60 + int(time_parts[1])
        elif len(time_parts) == 3:  # HH:MM:SS
            return int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
            
    except (ValueError, AttributeError) as e:
        logger.error(f"❌ خطأ في تحويل المدة '{duration}': {str(e)}")
    
    return 0

def get_next_api_key() -> Optional[str]:
    """الحصول على مفتاح API التالي"""
    if API_KEYS_CYCLE:
        return next(API_KEYS_CYCLE)
    return None

def get_next_invidious_server() -> Optional[str]:
    """الحصول على خادم Invidious التالي"""
    if INVIDIOUS_CYCLE:
        return next(INVIDIOUS_CYCLE)
    return None

def reset_performance_stats():
    """إعادة تعيين إحصائيات الأداء"""
    global performance_stats
    performance_stats = {
        'total_downloads': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'cache_hits': 0,
        'api_calls': 0,
        'last_reset': time.time()
    }

def get_performance_report() -> Dict:
    """الحصول على تقرير الأداء"""
    uptime = time.time() - performance_stats['last_reset']
    success_rate = 0
    if performance_stats['total_downloads'] > 0:
        success_rate = (performance_stats['successful_downloads'] / performance_stats['total_downloads']) * 100
    
    return {
        'uptime_hours': uptime / 3600,
        'total_downloads': performance_stats['total_downloads'],
        'success_rate': f"{success_rate:.1f}%",
        'cache_efficiency': f"{performance_stats['cache_hits']} hits",
        'api_calls': performance_stats['api_calls']
    }

# =============================================================================
# كلاس YouTube API المطور
# =============================================================================

class YouTubeAPI:
    """فئة YouTube API محسنة مع ميزات متقدمة"""
    
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        
        # إعدادات yt-dlp محسنة
        self.base_ytdl_opts = {
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "extract_flat": False,
            "writethumbnail": False,
            "writeinfojson": False,
        }

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        """التحقق من وجود رابط YouTube مع فحص محسن"""
        try:
            if videoid:
                link = self.base + link
            
            # فحص التنسيق أولاً
            if not re.search(self.regex, link):
                return False
            
            # فحص صلاحية الرابط
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.head(self.status + link, timeout=5) as response:
                        return response.status == 200
            except ImportError:
                # aiohttp غير متوفر، نفترض أن الرابط صالح
                logger.debug("aiohttp غير متوفر، تخطي فحص صلاحية الرابط")
                return True
            except:
                # إذا فشل الفحص، نفترض أنه صالح
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في فحص الرابط: {str(e)}")
            return False

    @asyncify
    def url(self, message_1: Message) -> Union[str, None]:
        """استخراج رابط من الرسالة مع معالجة محسنة"""
        try:
            messages = [message_1]
            if message_1.reply_to_message:
                messages.append(message_1.reply_to_message)
            
            for message in messages:
                # فحص الكيانات في النص
                if message.entities:
                    for entity in message.entities:
                        if entity.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK]:
                            if entity.type == MessageEntityType.URL:
                                text = message.text or message.caption
                                url = text[entity.offset : entity.offset + entity.length]
                            else:
                                url = entity.url
                            
                            # التحقق من أنه رابط YouTube
                            if re.search(self.regex, url):
                                return url
                
                # فحص الكيانات في التسمية التوضيحية
                if message.caption_entities:
                    for entity in message.caption_entities:
                        if entity.type == MessageEntityType.TEXT_LINK:
                            url = entity.url
                            if re.search(self.regex, url):
                                return url
                
                # البحث عن رابط في النص مباشرة
                text_content = message.text or message.caption or ""
                url_pattern = r'https?://(?:www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
                match = re.search(url_pattern, text_content)
                if match:
                    return match.group(0)
                    
        except Exception as e:
            logger.error(f"❌ خطأ في استخراج الرابط: {str(e)}")
        
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None) -> Tuple[str, str, int, str, str]:
        """الحصول على تفاصيل الفيديو مع كاش ذكي"""
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            
            # التحقق من الكاش أولاً
            cache_key = get_cache_key(link, "details")
            cached_data = await get_from_cache(cache_key)
            
            if cached_data:
                return (
                    cached_data['title'],
                    cached_data['duration_min'],
                    cached_data['duration_sec'],
                    cached_data['thumbnail'],
                    cached_data['vidid']
                )
            
            # البحث المتقدم
            async with SEARCH_SEMAPHORE:
                results = VideosSearch(link, limit=1)
                search_result = await results.next()
                
                for result in search_result.get("result", []):
                    title = result.get("title", "Unknown")
                    duration_min = result.get("duration", "0:00")
                    thumbnail = result.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
                    vidid = result.get("id", "")
                    
                    # تحويل المدة
                    duration_sec = 0 if str(duration_min) == "None" else convert_duration(duration_min)
                    if duration_sec == 0:
                        duration_sec = time_to_seconds(duration_min) if duration_min else 0
                    
                    # حفظ في الكاش
                    cache_data = {
                        'title': title,
                        'duration_min': duration_min,
                        'duration_sec': duration_sec,
                        'thumbnail': thumbnail,
                        'vidid': vidid
                    }
                    await save_to_cache(cache_key, cache_data)
                    
                    performance_stats['api_calls'] += 1
                    return title, duration_min, duration_sec, thumbnail, vidid
            
            return None, None, None, None, None
            
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على تفاصيل الفيديو: {str(e)}")
            return None, None, None, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        """الحصول على عنوان الفيديو"""
        title, _, _, _, _ = await self.details(link, videoid)
        return title or "عنوان غير معروف"

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        """الحصول على مدة الفيديو"""
        _, duration_min, _, _, _ = await self.details(link, videoid)
        return duration_min or "0:00"

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        """الحصول على الصورة المصغرة"""
        _, _, _, thumbnail, _ = await self.details(link, videoid)
        return thumbnail or ""

    async def video(self, link: str, videoid: Union[bool, str] = None) -> Tuple[int, str]:
        """الحصول على رابط الفيديو المباشر مع تحسينات"""
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            
            # التحقق من الكاش
            cache_key = get_cache_key(link, "video_url")
            cached_data = await get_from_cache(cache_key)
            
            if cached_data and cached_data.get('success'):
                return 1, cached_data['url']
            
            cookie_file = cookies()
            cmd = [
                "yt-dlp",
                "-g",
                "-f", "best[height<=?720][width<=?1280]/best",
                "--no-playlist",
                link
            ]
            
            if cookie_file:
                cmd.extend(["--cookies", cookie_file])
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if stdout:
                video_url = stdout.decode().strip().split("\n")[0]
                
                # حفظ في الكاش
                cache_data = {'success': True, 'url': video_url}
                await save_to_cache(cache_key, cache_data)
                
                return 1, video_url
            
            error_msg = stderr.decode() if stderr else "خطأ غير معروف"
            logger.error(f"❌ فشل في الحصول على رابط الفيديو: {error_msg}")
            return 0, error_msg
            
        except asyncio.TimeoutError:
            return 0, "انتهت مهلة الحصول على رابط الفيديو"
        except Exception as e:
            logger.error(f"❌ خطأ في video: {str(e)}")
            return 0, str(e)

    async def playlist(self, link: str, limit: int, videoid: Union[bool, str] = None) -> List[str]:
        """الحصول على قائمة التشغيل مع تحسينات"""
        try:
            if videoid:
                link = self.listbase + link
            if "&" in link:
                link = link.split("&")[0]
            
            # التحقق من الكاش
            cache_key = get_cache_key(f"{link}:{limit}", "playlist")
            cached_data = await get_from_cache(cache_key)
            
            if cached_data:
                return cached_data.get('videos', [])
            
            cookie_file = cookies()
            cmd = (
                f"yt-dlp -i --compat-options no-youtube-unavailable-videos "
                f"--get-id --flat-playlist --playlist-end {limit} --skip-download "
                f'--no-warnings "{link}"'
            )
            
            if cookie_file:
                cmd += f" --cookies {cookie_file}"
            
            playlist_output = await shell_cmd(cmd)
            video_ids = [vid_id.strip() for vid_id in playlist_output.split("\n") if vid_id.strip()]
            
            # حفظ في الكاش
            cache_data = {'videos': video_ids}
            await save_to_cache(cache_key, cache_data)
            
            return video_ids
            
        except Exception as e:
            logger.error(f"❌ خطأ في playlist: {str(e)}")
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None) -> Tuple[Dict, str]:
        """الحصول على تفاصيل المسار مع بحث محسن"""
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            
            # إذا كان رابطاً مباشراً
            if link.startswith(("http://", "https://")):
                return await self._track_from_url(link)
            
            # البحث بالنص
            return await self._track_from_search(link)
            
        except Exception as e:
            logger.error(f"❌ خطأ في track: {str(e)}")
            return {}, None

    async def _track_from_url(self, url: str) -> Tuple[Dict, str]:
        """الحصول على المسار من رابط مباشر"""
        try:
            title, duration_min, duration_sec, thumbnail, vidid = await self.details(url)
            
            if title:
                track_details = {
                    "title": title,
                    "link": url,
                    "vidid": vidid,
                    "duration_min": duration_min,
                    "duration_sec": duration_sec,
                    "thumb": thumbnail,
                }
                return track_details, vidid
                
        except Exception as e:
            logger.error(f"❌ خطأ في _track_from_url: {str(e)}")
        
        return await self._track_from_search(url)

    async def _track_from_search(self, query: str) -> Tuple[Dict, str]:
        """البحث عن المسار"""
        try:
            # التحقق من الكاش
            cache_key = get_cache_key(query, "track_search")
            cached_data = await get_from_cache(cache_key)
            
            if cached_data:
                return cached_data['track_details'], cached_data['video_id']
            
            async with SEARCH_SEMAPHORE:
                results = VideosSearch(query, limit=1)
                search_result = await results.next()
                
                for result in search_result.get("result", []):
                    track_details = {
                        "title": result.get("title", "Unknown"),
                        "link": result.get("link", ""),
                        "vidid": result.get("id", ""),
                        "duration_min": result.get("duration", "0:00"),
                        "duration_sec": convert_duration(result.get("duration", "0:00")),
                        "thumb": result.get("thumbnails", [{}])[0].get("url", "").split("?")[0],
                        "uploader": result.get("channel", {}).get("name", ""),
                        "view_count": result.get("viewCount", {}).get("text", "0"),
                    }
                    
                    # حفظ في الكاش
                    cache_data = {
                        'track_details': track_details,
                        'video_id': result.get("id", "")
                    }
                    await save_to_cache(cache_key, cache_data)
                    
                    return track_details, result.get("id", "")
                    
        except Exception as e:
            logger.error(f"❌ خطأ في البحث: {str(e)}")
        
        return {}, None

    @asyncify
    def formats(self, link: str, videoid: Union[bool, str] = None) -> Tuple[List[Dict], str]:
        """الحصول على التنسيقات المتاحة مع تفاصيل محسنة"""
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]

            ytdl_opts = self.base_ytdl_opts.copy()
            cookie_file = cookies()
            if cookie_file:
                ytdl_opts["cookiefile"] = cookie_file

            with YoutubeDL(ytdl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                formats_available = []
                
                for fmt in info.get("formats", []):
                    try:
                        # تخطي تنسيقات DASH
                        if "dash" in str(fmt.get("format", "")).lower():
                            continue
                        
                        # تنظيف وتنسيق البيانات
                        format_data = {
                            "format": fmt.get("format", "Unknown"),
                            "format_id": fmt.get("format_id", ""),
                            "ext": fmt.get("ext", ""),
                            "filesize": fmt.get("filesize") or 0,
                            "quality": fmt.get("quality") or fmt.get("height", "Unknown"),
                            "format_note": fmt.get("format_note", ""),
                            "acodec": fmt.get("acodec", ""),
                            "vcodec": fmt.get("vcodec", ""),
                            "fps": fmt.get("fps"),
                            "tbr": fmt.get("tbr"),  # Total bitrate
                            "yturl": link,
                        }
                        formats_available.append(format_data)
                        
                    except Exception as fmt_error:
                        logger.debug(f"تخطي تنسيق بسبب خطأ: {fmt_error}")
                        continue
                
                # ترتيب التنسيقات حسب الجودة
                formats_available.sort(
                    key=lambda x: (x.get("quality", 0) or 0, x.get("tbr", 0) or 0), 
                    reverse=True
                )
                
                return formats_available, link
                
        except Exception as e:
            logger.error(f"❌ خطأ في formats: {str(e)}")
            return [], link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None) -> Tuple[str, str, str, str]:
        """الحصول على شريط التمرير مع نتائج محسنة"""
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            
            # التحقق من الكاش
            cache_key = get_cache_key(f"{link}:{query_type}", "slider")
            cached_data = await get_from_cache(cache_key)
            
            if cached_data:
                return (
                    cached_data['title'],
                    cached_data['duration'],
                    cached_data['thumbnail'],
                    cached_data['video_id']
                )
            
            async with SEARCH_SEMAPHORE:
                search = VideosSearch(link, limit=max(15, query_type + 5))
                results = await search.next()
                
                result_list = results.get("result", [])
                if result_list and len(result_list) > query_type:
                    item = result_list[query_type]
                    
                    title = item.get("title", "")
                    duration = item.get("duration", "")
                    thumbnail = item.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
                    video_id = item.get("id", "")
                    
                    # حفظ في الكاش
                    cache_data = {
                        'title': title,
                        'duration': duration,
                        'thumbnail': thumbnail,
                        'video_id': video_id
                    }
                    await save_to_cache(cache_key, cache_data)
                    
                    return title, duration, thumbnail, video_id
                    
        except Exception as e:
            logger.error(f"❌ خطأ في slider: {str(e)}")
        
        return "", "", "", ""

    async def download(self, link: str, mystic=None, video: bool = False, videoid: Union[bool, str] = None,
                      songaudio: bool = False, songvideo: bool = False, format_id: str = None, 
                      title: str = None) -> DownloadResult:
        """تحميل محسن مع إدارة متقدمة للموارد"""
        
        download_start_time = time.time()
        performance_stats['total_downloads'] += 1
        
        async with DOWNLOAD_SEMAPHORE:
            try:
                result = await self._download_internal(
                    link, mystic, video, videoid, songaudio, songvideo, format_id, title
                )
                
                download_time = time.time() - download_start_time
                
                if result.success:
                    performance_stats['successful_downloads'] += 1
                    logger.info(f"✅ تم التحميل بنجاح في {download_time:.2f}ث: {result.file_path}")
                else:
                    performance_stats['failed_downloads'] += 1
                    logger.error(f"❌ فشل التحميل: {result.error_message}")
                
                result.download_time = download_time
                return result
                
            except Exception as e:
                performance_stats['failed_downloads'] += 1
                logger.error(f"❌ خطأ في التحميل: {str(e)}")
                return DownloadResult(
                    success=False,
                    file_path=None,
                    error_message=str(e),
                    download_time=time.time() - download_start_time
                )

    async def _download_internal(self, link: str, mystic, video: bool, videoid: Union[bool, str],
                                songaudio: bool, songvideo: bool, format_id: str, title: str) -> DownloadResult:
        """التحميل الداخلي مع معالجة متقدمة"""
        
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        loop = asyncio.get_running_loop()
        cookie_file = cookies()
        
        # تحديد نوع التحميل والإعدادات
        if songvideo:
            return await self._download_song_video(link, format_id, title, cookie_file, loop)
        elif songaudio:
            return await self._download_song_audio(link, format_id, title, cookie_file, loop)
        elif video:
            return await self._download_video(link, videoid, cookie_file, loop)
        else:
            return await self._download_audio(link, cookie_file, loop)

    async def _download_audio(self, link: str, cookie_file: str, loop) -> DownloadResult:
        """تحميل الصوت فقط"""
        def audio_dl():
            try:
                ydl_opts = {
                    "format": "bestaudio[ext=m4a]/bestaudio/best",
                    "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": False,
                    "writethumbnail": False,
                    "writeinfojson": False,
                }
                
                if cookie_file:
                    ydl_opts["cookiefile"] = cookie_file
                
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                    expected_filename = str(DOWNLOADS_DIR / f"{info['id']}.{info.get('ext', 'unknown')}")
                    
                    # التحقق من وجود الملف مسبقاً
                    if os.path.exists(expected_filename):
                        file_size = os.path.getsize(expected_filename)
                        return DownloadResult(True, expected_filename, None, file_size)
                    
                    # تحميل الملف
                    ydl.download([link])
                    
                    # العثور على الملف المحمل
                    downloaded_files = list(DOWNLOADS_DIR.glob(f"{info['id']}.*"))
                    if downloaded_files:
                        file_path = str(downloaded_files[0])
                        file_size = os.path.getsize(file_path)
                        return DownloadResult(True, file_path, None, file_size)
                    
                    return DownloadResult(False, None, "لم يتم العثور على الملف المحمل")
                    
            except Exception as e:
                return DownloadResult(False, None, f"خطأ في تحميل الصوت: {str(e)}")
        
        return await loop.run_in_executor(None, audio_dl)

    async def _download_video(self, link: str, videoid: Union[bool, str], cookie_file: str, loop) -> DownloadResult:
        """تحميل الفيديو"""
        
        # التحقق من إعدادات التحميل
        if await is_on_off(config.YTDOWNLOADER):
            return await self._download_video_file(link, cookie_file, loop)
        else:
            # الحصول على رابط مباشر فقط
            result_code, video_url = await self.video(link, videoid)
            if result_code == 1:
                return DownloadResult(True, video_url, None)
            else:
                return DownloadResult(False, None, video_url)

    async def _download_video_file(self, link: str, cookie_file: str, loop) -> DownloadResult:
        """تحميل ملف الفيديو الفعلي"""
        def video_dl():
            try:
                ydl_opts = {
                    "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])/best[height<=?720]",
                    "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "merge_output_format": "mp4",
                }
                
                if cookie_file:
                    ydl_opts["cookiefile"] = cookie_file
                
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                    expected_filename = str(DOWNLOADS_DIR / f"{info['id']}.mp4")
                    
                    if os.path.exists(expected_filename):
                        file_size = os.path.getsize(expected_filename)
                        return DownloadResult(True, expected_filename, None, file_size)
                    
                    ydl.download([link])
                    
                    if os.path.exists(expected_filename):
                        file_size = os.path.getsize(expected_filename)
                        return DownloadResult(True, expected_filename, None, file_size)
                    
                    return DownloadResult(False, None, "فشل في تحميل الفيديو")
                    
            except Exception as e:
                return DownloadResult(False, None, f"خطأ في تحميل الفيديو: {str(e)}")
        
        return await loop.run_in_executor(None, video_dl)

    async def _download_song_video(self, link: str, format_id: str, title: str, cookie_file: str, loop) -> DownloadResult:
        """تحميل فيديو الأغنية بجودة محددة"""
        def song_video_dl():
            try:
                safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
                
                ydl_opts = {
                    "format": f"{format_id}+bestaudio/best",
                    "outtmpl": str(DOWNLOADS_DIR / f"{safe_title}.%(ext)s"),
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "merge_output_format": "mp4",
                }
                
                if cookie_file:
                    ydl_opts["cookiefile"] = cookie_file
                
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                
                expected_path = DOWNLOADS_DIR / f"{safe_title}.mp4"
                if expected_path.exists():
                    file_size = expected_path.stat().st_size
                    return DownloadResult(True, str(expected_path), None, file_size)
                
                return DownloadResult(False, None, "لم يتم العثور على ملف الفيديو")
                
            except Exception as e:
                return DownloadResult(False, None, f"خطأ في تحميل فيديو الأغنية: {str(e)}")
        
        return await loop.run_in_executor(None, song_video_dl)

    async def _download_song_audio(self, link: str, format_id: str, title: str, cookie_file: str, loop) -> DownloadResult:
        """تحميل صوت الأغنية بجودة محددة"""
        def song_audio_dl():
            try:
                safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
                
                ydl_opts = {
                    "format": format_id,
                    "outtmpl": str(DOWNLOADS_DIR / f"{safe_title}.%(ext)s"),
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                }
                
                if cookie_file:
                    ydl_opts["cookiefile"] = cookie_file
                
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                
                expected_path = DOWNLOADS_DIR / f"{safe_title}.mp3"
                if expected_path.exists():
                    file_size = expected_path.stat().st_size
                    return DownloadResult(True, str(expected_path), None, file_size)
                
                return DownloadResult(False, None, "لم يتم العثور على ملف الصوت")
                
            except Exception as e:
                return DownloadResult(False, None, f"خطأ في تحميل صوت الأغنية: {str(e)}")
        
        return await loop.run_in_executor(None, song_audio_dl)

    async def get_performance_stats(self) -> Dict:
        """الحصول على إحصائيات الأداء"""
        return get_performance_report()

    async def cleanup_cache(self, max_age_hours: int = 24):
        """تنظيف الكاش القديم"""
        try:
            current_time = time.time()
            deleted_count = 0
            
            for cache_file in CACHE_DIR.glob("*.json"):
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > (max_age_hours * 3600):
                    cache_file.unlink()
                    deleted_count += 1
            
            logger.info(f"🧹 تم حذف {deleted_count} ملف كاش قديم")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف الكاش: {str(e)}")
            return 0

    async def cleanup_downloads(self, max_age_hours: int = 2):
        """تنظيف ملفات التحميل القديمة"""
        try:
            current_time = time.time()
            deleted_count = 0
            freed_space = 0
            
            for download_file in DOWNLOADS_DIR.iterdir():
                if download_file.is_file():
                    file_age = current_time - download_file.stat().st_mtime
                    if file_age > (max_age_hours * 3600):
                        file_size = download_file.stat().st_size
                        download_file.unlink()
                        deleted_count += 1
                        freed_space += file_size
            
            freed_mb = freed_space / (1024 * 1024)
            logger.info(f"🧹 تم حذف {deleted_count} ملف تحميل، توفير {freed_mb:.1f} MB")
            return deleted_count, freed_mb
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف التحميلات: {str(e)}")
            return 0, 0

# =============================================================================
# تهيئة المثيل العام
# =============================================================================

# إنشاء مثيل وحيد من API
youtube = YouTubeAPI()

# دوال للتوافق مع الكود القديم (deprecated - استخدم youtube مباشرة)
YoutubeAPI = YouTubeAPI  # للتوافق

# إعداد مهمة تنظيف دورية
async def periodic_cleanup():
    """مهمة تنظيف دورية"""
    while True:
        try:
            await asyncio.sleep(3600)  # كل ساعة
            await youtube.cleanup_cache(24)  # حذف الكاش أقدم من 24 ساعة
            await youtube.cleanup_downloads(2)  # حذف التحميلات أقدم من ساعتين
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف الدوري: {str(e)}")

# بدء مهمة التنظيف
try:
    asyncio.create_task(periodic_cleanup())
    logger.info("🚀 تم تشغيل نظام YouTube المحسن مع التنظيف التلقائي")
except Exception as e:
    logger.error(f"❌ خطأ في بدء النظام: {str(e)}")

# رسالة ترحيب
logger.info("🎵 YouTube Platform Handler - Enhanced Edition تم تحميله بنجاح!")
