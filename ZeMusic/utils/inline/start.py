from pyrogram.types import InlineKeyboardButton
import config
from ZeMusic import app

lnk = f"https://t.me/{config.CHANNEL_LINK}"
lnk2 = f"https://t.me/{config.STORE_LINK}"

def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text="أضفني إلى مجموعتك",
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [InlineKeyboardButton(text="الأوامر", callback_data="zzzback")],
        [
            InlineKeyboardButton(text=config.STORE_NAME, url2=config.STORE_LINK),
            InlineKeyboardButton(text=config.CHANNEL_NAME, url=config.CHANNEL_LINK)
        ],
        [InlineKeyboardButton(text="𝐃𝐞𝐯", user_id=config.OWNER_ID),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text="أضفني إلى مجموعتك",
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [InlineKeyboardButton(text="الأوامر", callback_data="zzzback")],
        [
            InlineKeyboardButton(text=config.STORE_NAME, url2=config.STORE_LINK),
            InlineKeyboardButton(text=config.CHANNEL_NAME, url=config.CHANNEL_LINK)
        ],
        [InlineKeyboardButton(text="𝐃𝐞𝐯", user_id=config.OWNER_ID),
        ],
    ]
    return buttons
