from pyrogram import filters
from pyrogram.types import Message
from ZeMusic import app
from config
from ZeMusic.misc import SUDOERS
from ZeMusic.utils.database import autoend_off, autoend_on, AdminRightsCheck

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
@app.on_message(filters.command("المساعد غادر") & filters.group)
@AdminRightsCheck
async def leave_chat(_, message: Message, _, chat_id):
    try:
        user_mention = message.from_user.mention if message.from_user else "المشرف"
        await config.STRING2.leave_chat(chat_id)
        await message.reply_text(f"تم مغادرة المجموعة بنجاح بواسطة {user_mention} ✅")
    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء المغادرة: {str(e)}")

# أمر انضمام الحساب المساعد
@app.on_message(filters.command("المساعد انضم") & filters.group)
@AdminRightsCheck
async def join_chat(_, message: Message, _, chat_id):
    try:
        user_mention = message.from_user.mention if message.from_user else "المشرف"
        await config.STRING2.join_chat(chat_id)
        await message.reply_text(f"تم الانضمام للمجموعة بنجاح بواسطة {user_mention} ✅")
    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء الانضمام: {str(e)}")
