import asyncio
import glob
import os
import random
import re
import logging
from typing import Union
from itertools import cycle

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from yt_dlp import YoutubeDL

import config
from ZeMusic import app
from ZeMusic.utils.database import is_on_off
from ZeMusic.utils.formatters import time_to_seconds, seconds_to_min
from ZeMusic.utils.decorators import asyncify

# إعدادات التدوير
YT_API_KEYS = getattr(config, "YT_API_KEYS", [])[:]
API_KEYS_CYCLE = cycle(YT_API_KEYS) if YT_API_KEYS else None
INVIDIOUS_SERVERS = getattr(config, "INVIDIOUS_SERVERS", [])
INVIDIOUS_CYCLE = cycle(INVIDIOUS_SERVERS) if INVIDIOUS_SERVERS else None

# إعداد السيمفور للتحكم في التزامن
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(10)

# تكوين السجل (Logging)
logger = logging.getLogger(__name__)

def cookies():
    """إرجاع مسار ملف كوكيز عشوائي مع إنشاء المجلد إذا لم يكن موجوداً"""
    try:
        folder_path = os.path.join(os.getcwd(), "cookies")
        os.makedirs(folder_path, exist_ok=True)
        txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
        
        if not txt_files:
            logger.warning("لم يتم العثور على ملفات كوكيز في المجلد المحدد")
            return None
            
        cookie_txt_file = random.choice(txt_files)
        return cookie_txt_file
    except Exception as e:
        logger.error(f"خطأ في دالة الكوكيز: {str(e)}")
        return None

async def shell_cmd(cmd):
    """تنفيذ أمر shell مع معالجة الأخطاء"""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, errorz = await proc.communicate()
        if errorz:
            error_msg = errorz.decode("utf-8")
            if "unavailable videos are hidden" in error_msg.lower():
                return out.decode("utf-8")
            return error_msg
        return out.decode("utf-8")
    except Exception as e:
        logger.error(f"خطأ في shell_cmd: {str(e)}")
        return str(e)

def convert_duration(duration: str) -> int:
    """تحويل مدة YouTube (ISO 8601) إلى ثواني"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        """التحقق من وجود رابط YouTube"""
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    @asyncify
    def url(self, message_1: Message) -> Union[str, None]:
        """استخراج رابط من الرسالة"""
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        
        for message in messages:
            # معالجة كيانات النص
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset : entity.offset + entity.length]
            # معالجة كيانات التسمية التوضيحية
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على تفاصيل الفيديو"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = 0 if str(duration_min) == "None" else int(time_to_seconds(duration_min))
            
            return title, duration_min, duration_sec, thumbnail, vidid
        return None, None, None, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على عنوان الفيديو"""
        title, _, _, _, _ = await self.details(link, videoid)
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على مدة الفيديو"""
        _, duration_min, _, _, _ = await self.details(link, videoid)
        return duration_min

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على الصورة المصغرة"""
        _, _, _, thumbnail, _ = await self.details(link, videoid)
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على رابط الفيديو المباشر"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        cookie_file = cookies()
        cmd = [
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            link
        ]
        
        if cookie_file:
            cmd.extend(["--cookies", cookie_file])
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if stdout:
                return 1, stdout.decode().split("\n")[0]
            return 0, stderr.decode()
        except Exception as e:
            logger.error(f"خطأ في video: {str(e)}")
            return 0, str(e)

    async def playlist(self, link, limit, videoid: Union[bool, str] = None):
        """الحصول على قائمة التشغيل"""
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]

        cookie_file = cookies()
        cmd = (
            f"yt-dlp -i --compat-options no-youtube-unavailable-videos "
            f'--get-id --flat-playlist --playlist-end {limit} --skip-download "{link}"'
        )
        
        if cookie_file:
            cmd += f" --cookies {cookie_file}"
        
        playlist = await shell_cmd(cmd)
        return [key for key in playlist.split("\n") if key] if playlist else []

    async def track(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على تفاصيل المسار"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        if link.startswith(("http://", "https://")):
            return await self._track(link)
        
        try:
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                track_details = {
                    "title": result["title"],
                    "link": result["link"],
                    "vidid": result["id"],
                    "duration_min": result["duration"],
                    "thumb": result["thumbnails"][0]["url"].split("?")[0],
                }
                return track_details, result["id"]
        except Exception:
            pass
        
        return await self._track(link)

    @asyncify
    def _track(self, q):
        """الداخلية للحصول على تفاصيل المسار"""
        try:
            options = {
                "format": "best",
                "noplaylist": True,
                "quiet": True,
                "extract_flat": "in_playlist",
                "cookiefile": cookies() or "",
            }
            with YoutubeDL(options) as ydl:
                info_dict = ydl.extract_info(f"ytsearch: {q}", download=False)
                details = info_dict.get("entries")[0]
                return {
                    "title": details["title"],
                    "link": details["url"],
                    "vidid": details["id"],
                    "duration_min": seconds_to_min(details["duration"]) if details.get("duration") else None,
                    "thumb": details.get("thumbnails", [{}])[0].get("url", "")
                }, details["id"]
        except Exception as e:
            logger.error(f"خطأ في _track: {str(e)}")
            return {}, None

    @asyncify
    def formats(self, link: str, videoid: Union[bool, str] = None):
        """الحصول على التنسيقات المتاحة"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        ytdl_opts = {
            "quiet": True,
            "cookiefile": cookies() or "",
        }

        try:
            with YoutubeDL(ytdl_opts) as ydl:
                r = ydl.extract_info(link, download=False)
                formats_available = []
                for format in r.get("formats", []):
                    try:
                        if "dash" in str(format.get("format", "")).lower():
                            continue
                            
                        formats_available.append({
                            "format": format.get("format", ""),
                            "filesize": format.get("filesize", 0),
                            "format_id": format.get("format_id", ""),
                            "ext": format.get("ext", ""),
                            "format_note": format.get("format_note", ""),
                            "yturl": link,
                        })
                    except Exception:
                        continue
                return formats_available, link
        except Exception as e:
            logger.error(f"خطأ في formats: {str(e)}")
            return [], link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        """الحصول على شريط التمرير"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        try:
            a = VideosSearch(link, limit=10)
            result = (await a.next()).get("result", [])
            if result and len(result) > query_type:
                item = result[query_type]
                return (
                    item.get("title", ""),
                    item.get("duration", ""),
                    item.get("thumbnails", [{}])[0].get("url", "").split("?")[0],
                    item.get("id", "")
                )
        except Exception as e:
            logger.error(f"خطأ في slider: {str(e)}")
        
        return "", "", "", ""

    async def download(self, link: str, mystic, video=False, videoid=None, 
                      songaudio=False, songvideo=False, format_id=None, title=None):
        """تنزيل المحتوى مع التحكم في التزامن"""
        async with DOWNLOAD_SEMAPHORE:
            return await self._download(link, mystic, video, videoid, songaudio, songvideo, format_id, title)
    
    async def _download(self, link: str, mystic, video=False, videoid=None, 
                       songaudio=False, songvideo=False, format_id=None, title=None):
        """التنزيل الفعلي للمحتوى"""
        if videoid:
            link = self.base + link
        
        loop = asyncio.get_running_loop()
        cookie_file = cookies()
        
        def audio_dl():
            """تنزيل الصوت"""
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join("downloads", "%(id)s.%(ext)s"),
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            if cookie_file:
                ydl_opts["cookiefile"] = cookie_file
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                
                if not os.path.exists(file_path):
                    ydl.download([link])
                
                return file_path

        def video_dl():
            """تنزيل الفيديو"""
            ydl_opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": os.path.join("downloads", "%(id)s.%(ext)s"),
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            if cookie_file:
                ydl_opts["cookiefile"] = cookie_file
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                
                if not os.path.exists(file_path):
                    ydl.download([link])
                
                return file_path

        def song_video_dl():
            """تنزيل فيديو الأغنية"""
            ydl_opts = {
                "format": f"{format_id}+140",
                "outtmpl": os.path.join("downloads", f"{title}.%(ext)s"),
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
            return os.path.join("downloads", f"{title}.mp4")

        def song_audio_dl():
            """تنزيل صوت الأغنية"""
            ydl_opts = {
                "format": format_id,
                "outtmpl": os.path.join("downloads", f"{title}.%(ext)s"),
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
            return os.path.join("downloads", f"{title}.mp3")

        try:
            if songvideo:
                return await loop.run_in_executor(None, song_video_dl), None
            elif songaudio:
                return await loop.run_in_executor(None, song_audio_dl), None
            elif video:
                if await is_on_off(config.YTDOWNLOADER):
                    return await loop.run_in_executor(None, video_dl), True
                else:
                    result = await self.video(link, videoid)
                    return result[1], None if result[0] == 1 else None
            else:
                return await loop.run_in_executor(None, audio_dl), True
        except Exception as e:
            logger.error(f"خطأ في التنزيل: {str(e)}")
            return None, None
