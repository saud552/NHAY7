import asyncio
import importlib
import sys
from pyrogram import idle
from pyrogram.enums import ParseMode

import config
from ZeMusic import LOGGER, init_database
from ZeMusic.core.bot import Mody
from ZeMusic.core.dir import dirr
from ZeMusic.core.git import git
from ZeMusic.core.userbot import Userbot
from ZeMusic.misc import dbb, heroku, sudo
from ZeMusic.plugins import ALL_MODULES
from ZeMusic.utils.database import get_banned_users, get_gbanned_users

async def init():
    """تهيئة البوت والخدمات"""
    # تهيئة الدلائل والملفات
    dirr()
    git()
    dbb()
    heroku()
    
    # تهيئة قاعدة البيانات الجديدة
    db_init = await init_database()
    if not db_init:
        LOGGER(__name__).error("❌ فشل في تهيئة قاعدة البيانات - إيقاف البوت")
        sys.exit(1)
    
    # تهيئة البوت والمساعدين
    await sudo()
    
    try:
        LOGGER(__name__).info("🔄 بدء تشغيل ZeMusic Bot...")
        
        # إنشاء عميل البوت
        app = Mody()
        
        # إنشاء عميل المساعد
        userbot = Userbot()
        
        # بدء البوت
        await app.start()
        LOGGER(__name__).info("✅ تم تشغيل البوت بنجاح")
        
        # بدء المساعدين
        await userbot.start()
        LOGGER(__name__).info("✅ تم تشغيل المساعدين بنجاح")
        
        # تحميل الوحدات
        for module in ALL_MODULES:
            importlib.import_module(f"ZeMusic.plugins.{module}")
        LOGGER(__name__).info(f"✅ تم تحميل {len(ALL_MODULES)} وحدة")
        
        # رسالة البدء
        try:
            await app.send_message(
                config.LOGGER_ID,
                f"🎵 **ZeMusic Bot Started Successfully!**\n\n"
                f"🗄️ **Database:** SQLite (محسّن)\n"
                f"📊 **Modules:** {len(ALL_MODULES)}\n"
                f"🤖 **Bot:** @{app.username}\n"
                f"👥 **Assistants:** تم تفعيلهم\n\n"
                f"✅ **Status:** Ready to serve music!",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            LOGGER(__name__).warning(f"تعذر إرسال رسالة البدء: {e}")
        
        # إبقاء البوت يعمل
        LOGGER(__name__).info("🎵 ZeMusic Bot is now running...")
        await idle()
        
    except Exception as e:
        LOGGER(__name__).error(f"❌ خطأ في تشغيل البوت: {e}")
        sys.exit(1)
    finally:
        # إيقاف الخدمات
        try:
            await app.stop()
            await userbot.stop()
            LOGGER(__name__).info("🛑 تم إيقاف البوت")
        except:
            pass

if __name__ == "__main__":
    # تشغيل البوت
    try:
        asyncio.get_event_loop().run_until_complete(init())
    except KeyboardInterrupt:
        LOGGER(__name__).info("🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        LOGGER(__name__).error(f"❌ خطأ فادح: {e}")
        sys.exit(1)
