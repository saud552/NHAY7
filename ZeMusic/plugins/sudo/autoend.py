from ZeMusic.pyrogram_compatibility import filters
from ZeMusic.pyrogram_compatibility.types import Message
from ZeMusic import app
import config
from ZeMusic.misc import SUDOERS
from config import BANNED_USERS
from ZeMusic.utils.database import autoend_off, autoend_on
from ZeMusic.utils.decorators import AdminRightsCheck
from ZeMusic.core.userbot import assistants  # استدعاء المعطيات المتعلقة بـ assistant
from ZeMusic.utils.functions import get_assistant  # استيراد وظيفة الحصول على الحساب المساعد

# أمر المغادرة التلقائية
@app.on_message(filters.command("مغادرة") & SUDOERS)
async def auto_end_stream(_, message: Message):
    usage = "<b>example :</b>\n\n/مغادرة [تفعيل | تعطيل]"
    if len(message.command) != 2:
        return await message.reply_text(usage)

    state = message.text.split(None, 1)[1].strip().lower()
    if state == "تفعيل":
        await autoend_on()
        await message.reply_text(
            "تم تفعيل المغادرة التلقائية بنجاح.\n\nسيقوم الحساب المساعد بمغادرة الدردشة تلقائياً عندما لا يوجد أعضاء في المكالمة."
        )
    elif state == "تعطيل":
        await autoend_off()
        await message.reply_text("تم تعطيل المغادرة التلقائية بنجاح.")
    else:
        await message.reply_text(usage)

# أمر مغادرة الحساب المساعد
@app.on_message(filters.command("المساعد غادر") & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def leave_chat(_, message: Message, chat_id):
    try:
        # استدعاء الحساب المساعد المناسب للمجموعة
        assistant = await get_assistant(chat_id)
        user_mention = message.from_user.mention if message.from_user else "المشرف"
        await assistant.leave_chat(chat_id)
        await message.reply_text(f"تم مغادرة المجموعة بنجاح بواسطة {user_mention} ✅")
    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء المغادرة: {str(e)}")

# أمر انضمام الحساب المساعد
@app.on_message(filters.command("المساعد انضم") & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def join_chat(_, message: Message, chat_id):
    try:
        # استدعاء الحساب المساعد المناسب للمجموعة
        assistant = await get_assistant(chat_id)
        user_mention = message.from_user.mention if message.from_user else "المشرف"
        await assistant.join_chat(chat_id)
        await message.reply_text(f"تم الانضمام للمجموعة بنجاح بواسطة {user_mention} ✅")
    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء الانضمام: {str(e)}")
