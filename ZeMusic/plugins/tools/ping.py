from datetime import datetime

from ZeMusic.pyrogram_compatibility import filters
from ZeMusic.pyrogram_compatibility.types import Message

from ZeMusic import app
from ZeMusic.core.call import Mody
from ZeMusic.utils import bot_sys_stats
from ZeMusic.utils.decorators.language import language
from ZeMusic.utils.inline import supp_markup
from config import BANNED_USERS, PING_IMG_URL


@app.on_message(filters.command(["ping","بنج", "alive","البنج"],"") & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()
    response = await message.reply_photo(
        photo=PING_IMG_URL,
        caption=_["ping_1"].format(app.mention),
    )
    pytgping = await Mody.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000
    await response.edit_text(
        _["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping),
        reply_markup=supp_markup(_),
    )
