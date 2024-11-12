import os
import re
import config
import aiohttp
import aiofiles
from ZeMusic.platforms.Youtube import cookie_txt_file
from config import OWNER_ID
import yt_dlp
from yt_dlp import YoutubeDL
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from youtube_search import YoutubeSearch

from ZeMusic import app
from ZeMusic.plugins.play.filters import command
from ZeMusic.utils.database import is_search_enabled1, enable_search1, disable_search1

def remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)
        
lnk = config.CHANNEL_LINK
Nem = config.BOT_NAME + " يوت"

@app.on_message(command(["song", "/song", "بحث", Nem,"يوت"]) & filters.private)
async def song_downloader1(client, message: Message):
    if not await is_search_enabled1():
        return await message.reply_text("<b>⟡ عذراً عزيزي اليوتيوب معطل من قبل المطور</b>")
        
    query = " ".join(message.command[1:])
    m = await message.reply_text("<b>⇜ جـارِ البحث ..</b>")
    
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if not results:
            await m.edit("- لم يتم العثـور على نتائج حاول مجددا")
            return

        link = f"https://youtube.com{results[0]['url_suffix']}"
        title = results[0]["title"][:40]
        title_clean = re.sub(r'[\\/*?:"<>|]', "", title)  # تنظيف اسم الملف
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f"{title_clean}.jpg"
        
        # تحميل الصورة المصغرة
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(thumb_name, mode='wb')
                    await f.write(await resp.read())
                    await f.close()

        duration = results[0]["duration"]

    except Exception as e:
        await m.edit("- لم يتم العثـور على نتائج حاول مجددا")
        print(str(e))
        return
    
    await m.edit("<b>جاري التحميل ♪</b>")
    
    ydl_opts = {
        "format": "bestaudio[ext=m4a]",  # تحديد صيغة M4A
        "keepvideo": False,
        "geo_bypass": True,
        "outtmpl": f"{title_clean}.%(ext)s",  # استخدام اسم نظيف للملف
        "quiet": True,
        "cookiefile": cookie_txt_file(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)  # التنزيل مباشرة
            audio_file = ydl.prepare_filename(info_dict)

        # حساب مدة الأغنية
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr) - 1, -1, -1):
            dur += int(float(dur_arr[i])) * secmul
            secmul *= 60

        # إرسال الصوت
        await message.reply_audio(
            audio=audio_file,
            caption=f"⟡ {app.mention}",
            title=title,
            performer=info_dict.get("uploader", "Unknown"),
            thumb=thumb_name,
            duration=dur,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=config.CHANNEL_NAME, url=lnk),
                    ],
                ]
            ),
        )
        try:
            await app.send_audio(
                chat_id="@vbbbbnnnm",  # معرف القناة التي تريد الإرسال إليها 
                audio=audio_file,
                caption=f"⟡ {app.mention}",
                title=title,
                performer=info_dict.get("uploader", "Unknown"),
                thumb=thumb_name,
                duration=dur,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text=config.CHANNEL_NAME, url=lnk),
                        ],
                    ]
                ),
            )
        except:
            pass
        await m.delete()

    except Exception as e:
        await m.edit(f"error, wait for bot owner to fix\n\nError: {str(e)}")
        print(e)

    # حذف الملفات المؤقتة
    try:
        remove_if_exists(audio_file)
        remove_if_exists(thumb_name)
    except Exception as e:
        print(e)


@app.on_message(command(["تعطيل اليوتيوب بالخاص"]) & filters.user(OWNER_ID))
async def disable_search_command1(client, message: Message):
    if not await is_search_enabled1():
        await message.reply_text("<b>⟡ اليوتيوب معطل من قبل يالطيب</b>")
        return
    await disable_search1()
    await message.reply_text("<b>⟡ تم تعطيل اليوتيوب بنجاح</b>")

@app.on_message(command(["تفعيل اليوتيوب بالخاص"]) & filters.user(OWNER_ID))
async def enable_search_command1(client, message: Message):
    if await is_search_enabled1():
        await message.reply_text("<b>⟡ اليوتيوب مفعل من قبل يالطيب</b>")
        return
    await enable_search1()
    await message.reply_text("<b>⟡ تم تفعيل اليوتيوب بنجاح</b>")
