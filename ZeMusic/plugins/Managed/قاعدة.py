import requests
import random
import os
import re
import asyncio
import time
import asyncio
from ZeMusic.pyrogram_compatibility import Client, filters
from ZeMusic.pyrogram_compatibility.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from ZeMusic.pyrogram_compatibility.errors import UserAlreadyParticipant
import asyncio
import random
from ZeMusic.utils.database import add_served_chat
from ZeMusic import app

@app.on_message(filters.command(["ا", "هلا", "سلام", "المالك", "بخير", "وانت", "بوت"],"") & filters.group)
async def bot_check(_, message):
    chat_id = message.chat.id
    await add_served_chat(chat_id)
