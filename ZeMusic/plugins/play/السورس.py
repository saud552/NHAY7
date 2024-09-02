import asyncio
import os
import time
import requests
from config import START_IMG_URL, OWNER_ID
from pyrogram import Client, filters, emoji
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ZeMusic import app
import config

lnk = "https://t.me/" + config.CHANNEL_LINK

@app.on_message(filters.regex(r"^(السورس|سورس)$"))
async def huhh(client: Client, message: Message):
    dev = await client.get_users(OWNER_ID)
    name = dev.first_name

    await message.reply(
        text=f"""<b>Dev ↠ <a href='tg://user?id={OWNER_ID}'>{name}</b></a>""",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                   InlineKeyboardButton(
                        text=config.CHANNEL_NAME, url=lnk),
                ],
            ]
        ),
        reply_to_message_id=message.id  # This ensures the bot replies to the user s message
    )
