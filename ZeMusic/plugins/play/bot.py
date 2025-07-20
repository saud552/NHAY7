import asyncio
from ZeMusic import app
from config import OWNER_ID
import os
import requests
import ZeMusic.pyrogram_compatibility as pyrogram
from ZeMusic.pyrogram_compatibility import Client, filters, emoji
from ZeMusic.pyrogram_compatibility.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from ZeMusic.pyrogram_compatibility.errors import MessageNotModified
import config

@app.on_message(filters.regex(r"^(انا من|انا منو)$"))
async def BotMusic(client: Client, message: Message):
    
    italy = message.from_user.mention 
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if user_id == 5901732027:
            rank = f"""مطور السورس {italy}"""
        elif user_id == OWNER_ID:
            rank = f"""مطوري {italy}"""
        else:
            rank = italy
    except Exception as e:
        print(e)
    await message.reply_text(f"<b>⟡ انت </b>{rank}")
        


@app.on_message(filters.regex(r"^(ايديي|id)$"))
async def IdMusic(client: Client, message: Message):
    await message.reply_text(f"<b>⟡ ID :</b> <code>{message.from_user.id}</code>")




@app.on_message(filters.regex(r"^(اسمي)$"))
async def NameMusic(client: Client, message: Message):
    await message.reply_text(f"<b>⟡ اسمك :</b> {message.from_user.mention}")



@app.on_message(filters.regex(r"^(يوزري)$"))
async def UserMusic(client: Client, message: Message):
    await message.reply_text(f"<b>⟡ يوزرك :</b> @{message.from_user.username}")



@app.on_message(filters.regex(r"^(البايو|بايو)$"))
async def BioMusic(client: Client, message: Message):
    usr = await client.get_chat(message.from_user.id)
    bio = usr.bio
    await message.reply_text(f"""<b>⟡ البايو :</b> {bio}""")
    



@app.on_message(filters.regex(r"^(رابط الحذف|بوت الحذف)$"))
async def DeletMusic(client: Client, message: Message):
    await message.reply_text(f"""<b>⟡ بوت الحذف :</b> ( @LDDDLBOT )\n\n<b>""")

