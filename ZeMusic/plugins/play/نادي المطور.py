
import asyncio
from strings.filters import command
from ZeMusic.utils.decorators import AdminActual
from ZeMusic.pyrogram_compatibility.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaPhoto,
    Message,
)
from ZeMusic import (Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app)
from ZeMusic.pyrogram_compatibility import Client, filters
from ZeMusic.pyrogram_compatibility.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER_ID


@app.on_message(filters.command("نادي المطور", [".", ""]) & filters.group)
async def call_dev(client: Client, message: Message):

    usm = await client.get_users(OWNER_ID)
    mname = usm.first_name
    musrnam = usm.username
    
    chat = message.chat.id
    gti = message.chat.title
    chatusername = f"@{message.chat.username}"
    link = await app.export_chat_invite_link(chat)
    usr = await client.get_users(message.from_user.id)
    user_id = message.from_user.id
    user_ab = message.from_user.username
    user_name = message.from_user.first_name
    buttons = [[InlineKeyboardButton(gti, url=f"{link}")]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await app.send_message(OWNER_ID, f"<b>⌯ قام {message.from_user.mention}\n</b>"
                                     f"<b>⌯ بمناداتك عزيزي المطور\n</b>"
                                     f"<b>⌯ الأيدي {user_id}\n</b>"
                                     f"<b>⌯ اليوزر @{user_ab}\n</b>"
                                     f"<b>⌯ ايدي المجموعة {message.chat.id}\n</b>"
                                     f"<b>⌯ يوزر المجموعه {chatusername}</b>",
                                     reply_markup=reply_markup)
    
    await message.reply_text(f"⟡ تم إرسال طلبك للمطور سيتم الرد عليك قريباً .\n\n⟡ Dᥱꪜ -› @{musrnam} ")
