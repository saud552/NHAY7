import asyncio
import os
import sys
import signal
from contextlib import suppress

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db
from ZeMusic.core.music_manager import music_manager
from ZeMusic.core.command_handler import tdlib_command_handler
from ZeMusic.plugins.owner.owner_panel import owner_panel

class ZeMusicBot:
    """البوت الرئيسي لـ ZeMusic مع دعم TDLib"""
    
    def __init__(self):
        self.is_running = False
        self.startup_time = None
        
    async def initialize(self):
        """تهيئة النظام"""
        try:
            LOGGER(__name__).info("🚀 بدء تهيئة ZeMusic Bot...")
            
            # تهيئة قاعدة البيانات
            LOGGER(__name__).info("📊 تهيئة قاعدة البيانات...")
            await self._ensure_database_ready()
            
            # تهيئة البوت الرئيسي - استخدام البوت البسيط
            LOGGER(__name__).info("🤖 تشغيل البوت الرئيسي...")
            try:
                from ZeMusic.core.simple_bot import simple_bot
                bot_success = await simple_bot.start()
                if not bot_success:
                    LOGGER(__name__).error("❌ فشل في تشغيل البوت الرئيسي")
                    return False
                LOGGER(__name__).info("✅ تم تشغيل البوت البسيط بنجاح")
            except Exception as e:
                LOGGER(__name__).error(f"❌ خطأ في تشغيل البوت: {e}")
                return False
            
            # تحميل الحسابات المساعدة من قاعدة البيانات
            LOGGER(__name__).info("📱 تحميل الحسابات المساعدة...")
            try:
                # محاولة تحميل حسابات TDLib إذا كانت متاحة
                assistants_count = tdlib_manager.get_assistants_count()
                connected_count = tdlib_manager.get_connected_assistants_count()
                LOGGER(__name__).info(f"📊 حالة الحسابات المساعدة: {assistants_count} إجمالي، {connected_count} متصل")
            except Exception as e:
                LOGGER(__name__).warning(f"⚠️ خطأ في تحميل الحسابات المساعدة: {e}")
                assistants_count = 0
                connected_count = 0
            
            if assistants_count == 0:
                LOGGER(__name__).warning("⚠️ لا توجد حسابات مساعدة - البوت سيعمل بوظائف محدودة")
                self._show_no_assistants_warning()
            else:
                LOGGER(__name__).info(f"✅ تم تحميل {assistants_count} حساب مساعد ({connected_count} متصل)")
            
            # تحميل المديرين من قاعدة البيانات
            await self._load_sudoers()
            
            # إعداد معالج الأوامر مع TDLib
            try:
                await self._setup_command_handler()
            except Exception as e:
                LOGGER(__name__).warning(f"⚠️ خطأ في إعداد معالج الأوامر: {e}")
            
            # بدء المهام الدورية
            try:
                await self._start_periodic_tasks()
            except Exception as e:
                LOGGER(__name__).warning(f"⚠️ خطأ في المهام الدورية: {e}")
            
            # بدء مهمة تنظيف music_manager
            try:
                from ZeMusic.core.music_manager import start_cleanup_task
                start_cleanup_task()
            except Exception as e:
                LOGGER(__name__).warning(f"⚠️ خطأ في مهمة التنظيف: {e}")
            
            # بدء مهام assistants_handler
            try:
                from ZeMusic.plugins.owner.assistants_handler import assistants_handler
                await assistants_handler.start_auto_leave_task()
            except Exception as e:
                LOGGER(__name__).warning(f"⚠️ خطأ في مهام المساعدين: {e}")
            
            self.startup_time = asyncio.get_event_loop().time()
            self.is_running = True
            
            LOGGER(__name__).info("🎵 تم تشغيل ZeMusic Bot بنجاح!")
            self._show_startup_message()
            
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في تهيئة البوت: {e}")
            return False
    
    async def _ensure_database_ready(self):
        """التأكد من جاهزية قاعدة البيانات"""
        try:
            # التحقق من إمكانية الوصول لقاعدة البيانات
            stats = await db.get_stats()
            LOGGER(__name__).info(f"📊 قاعدة البيانات جاهزة - {stats['users']} مستخدم، {stats['chats']} مجموعة")
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في قاعدة البيانات: {e}")
            raise
    
    async def _load_sudoers(self):
        """تحميل قائمة المديرين"""
        try:
            sudoers = await db.get_sudoers()
            LOGGER(__name__).info(f"👨‍💼 تم تحميل {len(sudoers)} مدير")
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تحميل المديرين: {e}")
    
    async def _setup_command_handler(self):
        """إعداد معالج الأوامر"""
        try:
            # التحقق من نوع البوت مع حماية آمنة
            if hasattr(tdlib_manager, 'bot_client') and tdlib_manager.bot_client and hasattr(tdlib_manager.bot_client, 'add_update_handler'):
                # البوت يستخدم TDLib
                def message_handler(update):
                    asyncio.create_task(tdlib_command_handler.handle_message(update))
                
                def callback_handler(update):
                    if update.get('@type') == 'updateNewCallbackQuery':
                        asyncio.create_task(tdlib_command_handler.handle_callback_query(update))
                
                tdlib_manager.bot_client.add_update_handler('updateNewMessage', message_handler)
                tdlib_manager.bot_client.add_update_handler('updateNewCallbackQuery', callback_handler)
                
                LOGGER(__name__).info("🎛️ تم إعداد معالج الأوامر مع TDLib")
            else:
                # البوت يستخدم python-telegram-bot - المعالجات مسجلة مسبقاً
                LOGGER(__name__).info("🎛️ معالجات الأوامر جاهزة مع python-telegram-bot")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إعداد معالج الأوامر: {e}")
    
    async def _start_periodic_tasks(self):
        """بدء المهام الدورية"""
        try:
            # مهمة تنظيف الجلسات والحسابات الخاملة
            asyncio.create_task(self._cleanup_task())
            
            # مهمة مراقبة صحة النظام
            asyncio.create_task(self._health_check_task())
            
            # مهمة إحصائيات دورية
            asyncio.create_task(self._stats_task())
            
            LOGGER(__name__).info("⏰ تم بدء المهام الدورية")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في بدء المهام الدورية: {e}")
    
    def _show_no_assistants_warning(self):
        """عرض تحذير عدم وجود حسابات مساعدة"""
        warning_message = f"""
╔══════════════════════════════════════╗
║           ⚠️  تحذير مهم  ⚠️              ║
╠══════════════════════════════════════╣
║                                      ║
║  🚫 لا توجد حسابات مساعدة مضافة        ║
║                                      ║
║  📝 البوت سيعمل بوظائف محدودة:          ║
║     ✅ الأوامر العادية                 ║
║     ✅ البحث والمعلومات               ║
║     ❌ تشغيل الموسيقى                 ║
║                                      ║
║  📱 لإضافة حساب مساعد:                ║
║     /owner ← إدارة الحسابات المساعدة    ║
║                                      ║
║  📞 للدعم: @{config.SUPPORT_CHAT or 'YourSupport'}               ║
║                                      ║
╚══════════════════════════════════════╝
        """
        print(warning_message)
    
    def _show_startup_message(self):
        """عرض رسالة بدء التشغيل"""
        assistants_count = tdlib_manager.get_assistants_count()
        connected_count = tdlib_manager.get_connected_assistants_count()
        
        startup_message = f"""
╔══════════════════════════════════════╗
║          🎵 ZeMusic Bot 🎵            ║
╠══════════════════════════════════════╣
║                                      ║
║  ✅ البوت جاهز للعمل                  ║
║                                      ║
║  📊 الحالة:                          ║
║     🤖 البوت الرئيسي: متصل            ║
║     📱 الحسابات المساعدة: {assistants_count} ({connected_count} متصل)     ║
║     💾 قاعدة البيانات: جاهزة          ║
║                                      ║
║  🎯 الوضائف المتاحة:                 ║
║     {'✅ تشغيل الموسيقى' if assistants_count > 0 else '❌ تشغيل الموسيقى (يحتاج حسابات مساعدة)'}               ║
║     ✅ إدارة المجموعات                ║
║     ✅ الأوامر الإدارية               ║
║                                      ║
║  📞 الدعم: @{config.SUPPORT_CHAT or 'YourSupport'}               ║
║                                      ║
╚══════════════════════════════════════╝
        """
        print(startup_message)
    
    async def _cleanup_task(self):
        """مهمة تنظيف دورية"""
        while self.is_running:
            try:
                await asyncio.sleep(1800)  # كل 30 دقيقة
                
                # تنظيف الجلسات المنتهية
                await music_manager.cleanup_sessions()
                
                # تنظيف الحسابات الخاملة
                await tdlib_manager.cleanup_idle_assistants()
                
                # تنظيف كاش قاعدة البيانات
                await db.clear_cache()
                
                LOGGER(__name__).info("🧹 تم تنظيف النظام")
                
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في مهمة التنظيف: {e}")
    
    async def _health_check_task(self):
        """مهمة فحص صحة النظام"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # كل 5 دقائق
                
                # فحص البوت الرئيسي
                if not tdlib_manager.bot_client or not tdlib_manager.bot_client.is_connected:
                    LOGGER(__name__).warning("⚠️ البوت الرئيسي غير متصل - محاولة إعادة الاتصال...")
                    await tdlib_manager.initialize_bot()
                
                # فحص الحسابات المساعدة
                connected_count = tdlib_manager.get_connected_assistants_count()
                total_count = tdlib_manager.get_assistants_count()
                
                if total_count > 0 and connected_count < total_count * 0.5:  # أقل من 50% متصل
                    LOGGER(__name__).warning(f"⚠️ عدد الحسابات المتصلة منخفض: {connected_count}/{total_count}")
                
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في فحص صحة النظام: {e}")
    
    async def _stats_task(self):
        """مهمة إحصائيات دورية"""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # كل ساعة
                
                stats = await db.get_stats()
                assistants_count = tdlib_manager.get_assistants_count()
                connected_count = tdlib_manager.get_connected_assistants_count()
                active_sessions = len(music_manager.active_sessions)
                
                LOGGER(__name__).info(
                    f"📊 إحصائيات: {stats['users']} مستخدم، "
                    f"{stats['chats']} مجموعة، "
                    f"{connected_count}/{assistants_count} مساعد، "
                    f"{active_sessions} جلسة نشطة"
                )
                
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في مهمة الإحصائيات: {e}")
    
    async def handle_no_assistant_request(self, chat_id: int, user_id: int) -> str:
        """التعامل مع طلبات التشغيل عند عدم وجود حسابات مساعدة"""
        try:
            # إضافة المستخدم والمجموعة لقاعدة البيانات
            await db.add_user(user_id)
            await db.add_chat(chat_id)
            
            # رسالة الإشعار
            return config.ASSISTANT_NOT_FOUND_MESSAGE.format(
                SUPPORT_CHAT=config.SUPPORT_CHAT or "@YourSupport",
                OWNER_ID=config.OWNER_ID
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالجة طلب بدون مساعد: {e}")
            return "❌ عذراً، حدث خطأ في النظام"
    
    async def shutdown(self):
        """إيقاف البوت بأمان"""
        try:
            LOGGER(__name__).info("🛑 بدء إيقاف البوت...")
            
            self.is_running = False
            
            # إيقاف جميع الجلسات النشطة
            LOGGER(__name__).info("🎵 إيقاف الجلسات النشطة...")
            for chat_id in list(music_manager.active_sessions.keys()):
                await music_manager.stop_music(chat_id)
            
            # إيقاف جميع العملاء
            LOGGER(__name__).info("📱 إيقاف العملاء...")
            await tdlib_manager.stop_all()
            
            LOGGER(__name__).info("✅ تم إيقاف البوت بنجاح")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إيقاف البوت: {e}")
    
    def setup_signal_handlers(self):
        """إعداد معالجات الإشارات"""
        def signal_handler(signum, frame):
            LOGGER(__name__).info(f"🔔 تم استلام إشارة {signum}")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """الدالة الرئيسية"""
    try:
        # التحقق من المتطلبات
        if not config.API_ID or not config.API_HASH or not config.BOT_TOKEN:
            print("❌ خطأ: المتغيرات المطلوبة غير مكتملة")
            print("تأكد من ضبط: API_ID, API_HASH, BOT_TOKEN")
            sys.exit(1)
        
        # إنشاء البوت
        bot = ZeMusicBot()
        
        # إعداد معالجات الإشارات
        bot.setup_signal_handlers()
        
        # تهيئة وبدء البوت
        success = await bot.initialize()
        if not success:
            print("❌ فشل في تهيئة البوت")
            sys.exit(1)
        
        # تشغيل البوت
        try:
            # البقاء في حالة تشغيل
            while bot.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            LOGGER(__name__).info("⌨️ تم استلام إشارة إيقاف من المستخدم")
        finally:
            await bot.shutdown()
    
    except Exception as e:
        LOGGER(__name__).error(f"❌ خطأ مهم في البوت: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # إعداد حدود asyncio
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # تشغيل البوت
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ فادح: {e}")
        sys.exit(1)
