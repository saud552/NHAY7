from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.types import InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button
from pyrogram.enums import ChatType
from pyrogram.errors import UserNotParticipant
from ZeMusic import app
import config

channel = config.CHANNEL_LINK
async def subscription(_, __: Client, message: Message):
    if message.from_user:
        user_id = message.from_user.id
        try: 
            await app.get_chat_member(channel, user_id)
        except UserNotParticipant: 
            return False
        return True
    return True
    
subscribed = filters.create(subscription)

# تعريف دالة لمعالجة الأوامر
@app.on_message(filters.command(["تشغيل", "شغل"],"") & ~subscribed)
async def command_handler(_: Client, message: Message):
    if message.from_user:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            user_id = message.from_user.id
            user = message.from_user.first_name
            markup = Markup([
                [Button(config.CHANNEL_NAME, url=f"https://t.me/{channel}")]
            ])
            await message.reply(
                f"⟡ عذرًا عزيزي {user} \n⟡ عليك الاشتراك في قناة البوت أولاً",
                reply_markup=markup
            )
