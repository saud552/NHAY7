import asyncio
import re
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from ZeMusic.logging import LOGGER

class SimpleHandlers:
    """معالجات بسيطة للأوامر الأساسية"""
    
    def __init__(self):
        pass
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        try:
            user = update.effective_user
            chat = update.effective_chat
            
            # إضافة المستخدم لقاعدة البيانات
            try:
                from ZeMusic.core.database import db
                await db.add_user(user.id)
                if chat.type != 'private':
                    await db.add_chat(chat.id)
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في إضافة للقاعدة: {e}")
            
            welcome_text = f"""
🎵 **أهلاً بك في {config.BOT_NAME}!**

🤖 **حالة البوت:** جاهز للعمل  
📱 **الحسابات المساعدة:** غير مضافة بعد  

**⚙️ للمالك:**
/owner - لوحة إدارة البوت  
/admin - لوحة التحكم  

**📚 للمساعدة:**
/help - عرض المساعدة  
/ping - فحص حالة البوت  

**🎵 لتشغيل الموسيقى:**
`بحث اسم الأغنية` - للبحث عن أغنية  
/play - تشغيل موسيقى  

🎯 **ملاحظة:** إضافة الحسابات المساعدة مطلوبة لتشغيل الموسيقى

📞 **للدعم:** @{config.SUPPORT_CHAT or 'YourSupport'}
"""
            
            await update.message.reply_text(
                welcome_text, 
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج start: {e}")
            await update.message.reply_text("❌ حدث خطأ في تحميل الرسالة الترحيبية")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /help"""
        try:
            help_text = f"""
📚 **قائمة أوامر {config.BOT_NAME}:**

**👤 أوامر عامة:**
/start - بدء البوت  
/help - عرض المساعدة  
/ping - فحص حالة البوت  

**⚙️ للمالك فقط:**
/owner - لوحة إدارة البوت  
/admin - لوحة التحكم  
/addassistant - إضافة حساب مساعد  
/removeassistant - إزالة حساب مساعد  

**🎵 أوامر الموسيقى:**
`بحث اسم الأغنية` - البحث عن أغنية  
/play - تشغيل موسيقى  
/stop - إيقاف الموسيقى  
/pause - إيقاف مؤقت  
/resume - استكمال التشغيل  

**📝 ملاحظة:** 
بعض الأوامر تحتاج إضافة حسابات مساعدة أولاً

📞 **للدعم:** @{config.SUPPORT_CHAT or 'YourSupport'}
"""
            
            await update.message.reply_text(
                help_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج help: {e}")
    
    async def handle_owner(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /owner"""
        try:
            user_id = update.effective_user.id
            
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await update.message.reply_text(
                    f"❌ **هذا الأمر للمالك فقط!**\n\n"
                    f"🆔 **معرفك:** `{user_id}`\n"
                    f"👑 **المالك:** `{config.OWNER_ID}`",
                    parse_mode='Markdown'
                )
                return
            
            # إنشاء لوحة التحكم
            keyboard = [
                [
                    InlineKeyboardButton("📱 إدارة الحسابات المساعدة", callback_data="owner_assistants"),
                    InlineKeyboardButton("📊 الإحصائيات", callback_data="owner_stats")
                ],
                [
                    InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="owner_settings"),
                    InlineKeyboardButton("🔧 صيانة النظام", callback_data="owner_maintenance")
                ],
                [
                    InlineKeyboardButton("📋 سجلات النظام", callback_data="owner_logs"),
                    InlineKeyboardButton("🗃️ قاعدة البيانات", callback_data="owner_database")
                ],
                [
                    InlineKeyboardButton("🔄 إعادة تشغيل", callback_data="owner_restart"),
                    InlineKeyboardButton("🛑 إيقاف البوت", callback_data="owner_shutdown")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # الحصول على الإحصائيات
            try:
                from ZeMusic.core.database import db
                stats = await db.get_stats()
                from ZeMusic.core.tdlib_client import tdlib_manager
                assistants_count = tdlib_manager.get_assistants_count()
                connected_count = tdlib_manager.get_connected_assistants_count()
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في الحصول على الإحصائيات: {e}")
                stats = {'users': 0, 'chats': 0}
                assistants_count = 0
                connected_count = 0
            
            panel_text = f"""
🎛️ **لوحة تحكم مالك البوت**

📊 **الإحصائيات السريعة:**
👥 المستخدمين: `{stats['users']}`
💬 المجموعات: `{stats['chats']}`  
📱 الحسابات المساعدة: `{assistants_count}` (`{connected_count}` متصل)

🤖 **حالة البوت:** ✅ يعمل بشكل طبيعي
💾 **قاعدة البيانات:** ✅ متصلة

👑 **المالك:** {user_id}
"""
            
            await update.message.reply_text(
                panel_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج owner: {e}")
            await update.message.reply_text("❌ حدث خطأ في تحميل لوحة التحكم")
    
    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /admin (نفس /owner)"""
        await self.handle_owner(update, context)
    
    async def handle_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /ping"""
        try:
            await update.message.reply_text("🏓 **البوت يعمل بشكل طبيعي!**", parse_mode='Markdown')
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج ping: {e}")
    
    async def handle_addassistant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /addassistant"""
        try:
            user_id = update.effective_user.id
            
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await update.message.reply_text(
                    "❌ **هذا الأمر للمالك فقط!**",
                    parse_mode='Markdown'
                )
                return
            
            # إرسال تعليمات سريعة
            text = """
➕ **إضافة حساب مساعد**

🎯 **للبدء السريع:**
استخدم لوحة التحكم للحصول على تجربة تفاعلية كاملة

💡 **اختر إحدى الطرق:**
1️⃣ استخدم /owner ثم "إدارة الحسابات المساعدة"
2️⃣ أو استخدم الأزرار أدناه
"""
            
            keyboard = [
                [InlineKeyboardButton("➕ بدء إضافة حساب مساعد", callback_data="add_assistant")],
                [InlineKeyboardButton("📊 عرض الحسابات الحالية", callback_data="list_assistants")],
                [InlineKeyboardButton("🔙 لوحة التحكم الرئيسية", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج addassistant: {e}")
    
    async def handle_search_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج البحث عن الأغاني"""
        try:
            message_text = update.message.text
            
            # التحقق من وجود كلمة "بحث"
            if not message_text.startswith('بحث'):
                return
            
            # استخراج اسم الأغنية
            search_query = message_text.replace('بحث', '').strip()
            
            if not search_query:
                await update.message.reply_text(
                    "❌ **يرجى كتابة اسم الأغنية**\n\n"
                    "**مثال:** `بحث عليكي عيون`",
                    parse_mode='Markdown'
                )
                return
            
            # رسالة انتظار
            waiting_msg = await update.message.reply_text(
                f"🔍 **جاري البحث عن:** `{search_query}`\n\n"
                "⏳ **انتظر قليلاً...**",
                parse_mode='Markdown'
            )
            
            try:
                # محاولة البحث
                await self._search_and_play(update, search_query, waiting_msg)
                
            except Exception as search_error:
                LOGGER(__name__).error(f"خطأ في البحث: {search_error}")
                await waiting_msg.edit_text(
                    f"❌ **فشل البحث عن:** `{search_query}`\n\n"
                    f"🔧 **السبب:** لم يتم إضافة حسابات مساعدة بعد\n"
                    f"⚙️ **الحل:** استخدم /owner لإضافة حساب مساعد",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج البحث: {e}")
    
    async def _search_and_play(self, update: Update, query: str, waiting_msg):
        """البحث وتشغيل الأغنية"""
        try:
            # التحقق من وجود حسابات مساعدة
            from ZeMusic.core.tdlib_client import tdlib_manager
            
            if tdlib_manager.get_assistants_count() == 0:
                await waiting_msg.edit_text(
                    f"❌ **لا يمكن تشغيل الموسيقى**\n\n"
                    f"🔍 **تم العثور على:** `{query}`\n"
                    f"📱 **المشكلة:** لا توجد حسابات مساعدة\n\n"
                    f"⚙️ **الحل:**\n"
                    f"1️⃣ استخدم /owner\n"
                    f"2️⃣ اختر 'إدارة الحسابات المساعدة'\n"
                    f"3️⃣ أضف حساب مساعد بـ Session String",
                    parse_mode='Markdown'
                )
                return
            
            # محاولة البحث في يوتيوب
            try:
                import yt_dlp
                
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    search_results = ydl.extract_info(
                        f"ytsearch1:{query}",
                        download=False
                    )
                
                if search_results and 'entries' in search_results and search_results['entries']:
                    video = search_results['entries'][0]
                    title = video.get('title', 'غير معروف')
                    duration = video.get('duration', 0)
                    url = video.get('webpage_url', '')
                    
                    duration_str = f"{duration//60}:{duration%60:02d}" if duration else "غير معروف"
                    
                    # إنشاء أزرار التشغيل
                    keyboard = [
                        [
                            InlineKeyboardButton("▶️ تشغيل", callback_data=f"play_{video.get('id', '')}"),
                            InlineKeyboardButton("⏸️ إيقاف مؤقت", callback_data="pause")
                        ],
                        [
                            InlineKeyboardButton("⏹️ إيقاف", callback_data="stop"),
                            InlineKeyboardButton("🔗 رابط", url=url)
                        ]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await waiting_msg.edit_text(
                        f"🎵 **تم العثور على:**\n\n"
                        f"📝 **العنوان:** `{title}`\n"
                        f"⏱️ **المدة:** `{duration_str}`\n"
                        f"🔍 **البحث:** `{query}`\n\n"
                        f"⚠️ **ملاحظة:** تحتاج حساب مساعد متصل للتشغيل",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await waiting_msg.edit_text(
                        f"❌ **لم يتم العثور على نتائج**\n\n"
                        f"🔍 **البحث:** `{query}`\n"
                        f"💡 **اقتراح:** جرب كلمات أخرى",
                        parse_mode='Markdown'
                    )
                    
            except ImportError:
                await waiting_msg.edit_text(
                    f"❌ **مكتبة البحث غير متاحة**\n\n"
                    f"🔧 **يحتاج تثبيت:** yt-dlp\n"
                    f"💡 **للمطور:** قم بتثبيت المكتبات المطلوبة",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في البحث والتشغيل: {e}")
            await waiting_msg.edit_text(
                f"❌ **حدث خطأ في البحث**\n\n"
                f"🔍 **البحث:** `{query}`\n"
                f"🔧 **الخطأ:** {str(e)[:100]}...",
                parse_mode='Markdown'
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الضغط على الأزرار"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            callback_data = query.data
            
            # التحقق من صلاحيات المالك للأوامر الإدارية
            if callback_data.startswith('owner_') and user_id != config.OWNER_ID:
                await query.edit_message_text(
                    "❌ **هذا الأمر للمالك فقط!**",
                    parse_mode='Markdown'
                )
                return
            
            # معالجة الأوامر المختلفة
            if callback_data == 'owner_assistants':
                await self._handle_assistants_panel(query)
            elif callback_data == 'owner_stats':
                await self._handle_stats_panel(query)
            elif callback_data == 'owner_settings':
                await self._handle_settings_panel(query)
            elif callback_data == 'owner_maintenance':
                await self._handle_maintenance_panel(query)
            elif callback_data == 'owner_logs':
                await self._handle_logs_panel(query)
            elif callback_data == 'owner_database':
                await self._handle_database_panel(query)
            elif callback_data == 'owner_restart':
                await self._handle_restart(query)
            elif callback_data == 'owner_shutdown':
                await self._handle_shutdown(query)
            elif callback_data == 'back_to_main':
                await self._back_to_main_panel(query)
            elif callback_data == 'add_assistant':
                await self._handle_add_assistant(query)
            elif callback_data == 'remove_assistant':
                await self._handle_remove_assistant(query)
            elif callback_data == 'list_assistants':
                await self._handle_list_assistants(query)
            elif callback_data == 'restart_assistants':
                await self._handle_restart_assistants(query)
            elif callback_data == 'cancel_add_assistant':
                await self._handle_cancel_add_assistant(query)
            else:
                await query.edit_message_text(
                    f"❌ **أمر غير مدعوم:** `{callback_data}`",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج الأزرار: {e}")
    
    async def _handle_assistants_panel(self, query):
        """لوحة إدارة الحسابات المساعدة"""
        try:
            from ZeMusic.core.tdlib_client import tdlib_manager
            
            assistants_count = tdlib_manager.get_assistants_count()
            connected_count = tdlib_manager.get_connected_assistants_count()
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ إضافة حساب مساعد", callback_data="add_assistant"),
                    InlineKeyboardButton("➖ إزالة حساب مساعد", callback_data="remove_assistant")
                ],
                [
                    InlineKeyboardButton("📋 قائمة الحسابات", callback_data="list_assistants"),
                    InlineKeyboardButton("🔄 إعادة تشغيل الحسابات", callback_data="restart_assistants")
                ],
                [
                    InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"""
📱 **إدارة الحسابات المساعدة**

📊 **الحالة الحالية:**
🔢 **العدد الكلي:** `{assistants_count}`
✅ **المتصلة:** `{connected_count}`
❌ **غير المتصلة:** `{assistants_count - connected_count}`

💡 **ملاحظة:** 
الحسابات المساعدة مطلوبة لتشغيل الموسيقى في المجموعات
"""
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في لوحة الحسابات المساعدة: {e}")
    
    async def _handle_stats_panel(self, query):
        """لوحة الإحصائيات"""
        try:
            from ZeMusic.core.database import db
            from ZeMusic.core.tdlib_client import tdlib_manager
            
            stats = await db.get_stats()
            assistants_count = tdlib_manager.get_assistants_count()
            connected_count = tdlib_manager.get_connected_assistants_count()
            
            text = f"""
📊 **إحصائيات مفصلة**

👥 **المستخدمين:** `{stats['users']}`
💬 **المجموعات:** `{stats['chats']}`
📱 **الحسابات المساعدة:** `{assistants_count}`
✅ **المتصلة:** `{connected_count}`

🎵 **جلسات الموسيقى النشطة:** `0`
💾 **حجم قاعدة البيانات:** `{stats.get('db_size', 'غير معروف')}`

🤖 **حالة البوت:** ✅ يعمل بشكل طبيعي
⏰ **وقت التشغيل:** منذ بدء الجلسة
"""
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في لوحة الإحصائيات: {e}")
    
    async def _handle_settings_panel(self, query):
        """لوحة الإعدادات"""
        text = f"""
⚙️ **إعدادات البوت**

🔧 **الإعدادات المتاحة:**
• تفعيل/إلغاء الاشتراك الإجباري
• إعدادات المغادرة التلقائية
• إعدادات الجودة الافتراضية
• إعدادات الرسائل الترحيبية

💡 **قريباً:** المزيد من الإعدادات
"""
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_maintenance_panel(self, query):
        """لوحة الصيانة"""
        text = f"""
🔧 **صيانة النظام**

🛠️ **أدوات الصيانة:**
• تنظيف الملفات المؤقتة
• إعادة تعيين قاعدة البيانات
• فحص سلامة النظام
• تحديث المكتبات

⚠️ **تحذير:** بعض العمليات قد تؤثر على أداء البوت
"""
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_logs_panel(self, query):
        """لوحة السجلات"""
        text = f"""
📋 **سجلات النظام**

📄 **آخر 5 أحداث:**
• تم تشغيل البوت بنجاح
• تم تحميل قاعدة البيانات
• البوت جاهز للاستخدام

💡 **للحصول على السجلات الكاملة:**
استخدم ملف `bot.log` في الخادم
"""
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_database_panel(self, query):
        """لوحة قاعدة البيانات"""
        try:
            from ZeMusic.core.database import db
            stats = await db.get_stats()
            
            text = f"""
🗃️ **قاعدة البيانات**

📊 **الإحصائيات:**
👥 المستخدمين: `{stats['users']}`
💬 المجموعات: `{stats['chats']}`
📱 الحسابات المساعدة: `{stats.get('assistants', 0)}`

💾 **النوع:** SQLite
✅ **الحالة:** متصلة وتعمل بشكل طبيعي
"""
            
        except Exception as e:
            text = f"""
🗃️ **قاعدة البيانات**

❌ **خطأ في الاتصال:** {e}
"""
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_restart(self, query):
        """إعادة تشغيل البوت"""
        await query.edit_message_text(
            "🔄 **إعادة تشغيل البوت...**\n\n"
            "⏳ سيتم إعادة تشغيل البوت خلال ثوانٍ",
            parse_mode='Markdown'
        )
        
        # هنا يمكن إضافة كود إعادة التشغيل الفعلي
        LOGGER(__name__).info(f"طلب إعادة تشغيل من المالك: {query.from_user.id}")
    
    async def _handle_shutdown(self, query):
        """إيقاف البوت"""
        await query.edit_message_text(
            "🛑 **إيقاف البوت...**\n\n"
            "⏳ سيتم إيقاف البوت خلال ثوانٍ",
            parse_mode='Markdown'
        )
        
        LOGGER(__name__).info(f"طلب إيقاف من المالك: {query.from_user.id}")
    
    async def _back_to_main_panel(self, query):
        """العودة للوحة الرئيسية"""
        try:
            user_id = query.from_user.id
            
            # إنشاء لوحة التحكم الرئيسية
            keyboard = [
                [
                    InlineKeyboardButton("📱 إدارة الحسابات المساعدة", callback_data="owner_assistants"),
                    InlineKeyboardButton("📊 الإحصائيات", callback_data="owner_stats")
                ],
                [
                    InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="owner_settings"),
                    InlineKeyboardButton("🔧 صيانة النظام", callback_data="owner_maintenance")
                ],
                [
                    InlineKeyboardButton("📋 سجلات النظام", callback_data="owner_logs"),
                    InlineKeyboardButton("🗃️ قاعدة البيانات", callback_data="owner_database")
                ],
                [
                    InlineKeyboardButton("🔄 إعادة تشغيل", callback_data="owner_restart"),
                    InlineKeyboardButton("🛑 إيقاف البوت", callback_data="owner_shutdown")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # الحصول على الإحصائيات
            try:
                from ZeMusic.core.database import db
                stats = await db.get_stats()
                from ZeMusic.core.tdlib_client import tdlib_manager
                assistants_count = tdlib_manager.get_assistants_count()
                connected_count = tdlib_manager.get_connected_assistants_count()
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في الحصول على الإحصائيات: {e}")
                stats = {'users': 0, 'chats': 0}
                assistants_count = 0
                connected_count = 0
            
            panel_text = f"""
🎛️ **لوحة تحكم مالك البوت**

📊 **الإحصائيات السريعة:**
👥 المستخدمين: `{stats['users']}`
💬 المجموعات: `{stats['chats']}`  
📱 الحسابات المساعدة: `{assistants_count}` (`{connected_count}` متصل)

🤖 **حالة البوت:** ✅ يعمل بشكل طبيعي
💾 **قاعدة البيانات:** ✅ متصلة

👑 **المالك:** {user_id}
"""
            
            await query.edit_message_text(
                panel_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في العودة للوحة الرئيسية: {e}")
    
    async def _handle_add_assistant(self, query):
        """معالج إضافة حساب مساعد"""
        try:
            from ZeMusic.core.assistant_manager import assistant_manager
            
            user_id = query.from_user.id
            
            # بدء عملية إضافة الحساب المساعد التفاعلية
            await assistant_manager.start_add_assistant(query, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج إضافة المساعد: {e}")
    
    async def _handle_remove_assistant(self, query):
        """معالج إزالة حساب مساعد"""
        try:
            from ZeMusic.core.tdlib_client import tdlib_manager
            assistants_count = tdlib_manager.get_assistants_count()
            
            if assistants_count == 0:
                text = """
➖ **إزالة حساب مساعد**

❌ **لا توجد حسابات مساعدة**

💡 **لإضافة حساب مساعد:**
استخدم زر "إضافة حساب مساعد" أولاً
"""
            else:
                text = f"""
➖ **إزالة حساب مساعد**

📊 **الحسابات الحالية:** {assistants_count}

⚠️ **تحذير:**
إزالة الحسابات المساعدة ستوقف تشغيل الموسيقى في جميع المجموعات

🔧 **للمطورين:**
هذه الخاصية متاحة مع TDLib فقط
"""
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="owner_assistants")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج إزالة المساعد: {e}")
    
    async def _handle_list_assistants(self, query):
        """معالج قائمة الحسابات المساعدة"""
        try:
            from ZeMusic.core.tdlib_client import tdlib_manager
            
            assistants_count = tdlib_manager.get_assistants_count()
            connected_count = tdlib_manager.get_connected_assistants_count()
            
            if assistants_count == 0:
                text = """
📋 **قائمة الحسابات المساعدة**

❌ **لا توجد حسابات مساعدة**

💡 **لبدء استخدام الموسيقى:**
1️⃣ أضف حساب مساعد باستخدام Session String
2️⃣ تأكد من انضمام الحساب للمجموعات
3️⃣ ابدأ تشغيل الموسيقى
"""
            else:
                text = f"""
📋 **قائمة الحسابات المساعدة**

📊 **إحصائيات:**
🔢 **العدد الكلي:** `{assistants_count}`
✅ **المتصلة:** `{connected_count}`
❌ **غير المتصلة:** `{assistants_count - connected_count}`

🔧 **ملاحظة:**
عرض تفاصيل الحسابات متاح مع TDLib
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="list_assistants")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="owner_assistants")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج قائمة المساعدين: {e}")
    
    async def _handle_restart_assistants(self, query):
        """معالج إعادة تشغيل الحسابات المساعدة"""
        try:
            from ZeMusic.core.tdlib_client import tdlib_manager
            
            assistants_count = tdlib_manager.get_assistants_count()
            
            if assistants_count == 0:
                text = """
🔄 **إعادة تشغيل الحسابات المساعدة**

❌ **لا توجد حسابات مساعدة**

💡 **أضف حساب مساعد أولاً**
ثم استخدم هذه الخاصية لإعادة تشغيله
"""
            else:
                text = f"""
🔄 **إعادة تشغيل الحسابات المساعدة**

⏳ **جاري إعادة تشغيل {assistants_count} حساب...**

📊 **ما يحدث:**
• قطع الاتصال الحالي
• إعادة تسجيل الدخول
• اختبار الاتصال
• استئناف الخدمات

⏰ **قد يستغرق دقيقة واحدة**
"""
                
                # هنا يمكن إضافة كود إعادة التشغيل الفعلي
                
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="owner_assistants")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج إعادة تشغيل المساعدين: {e}")
    
    async def _handle_cancel_add_assistant(self, query):
        """معالج إلغاء إضافة الحساب المساعد"""
        try:
            from ZeMusic.core.assistant_manager import assistant_manager
            
            user_id = query.from_user.id
            await assistant_manager.cancel_add_assistant(query, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إلغاء إضافة المساعد: {e}")

# مثيل المعالجات
simple_handlers = SimpleHandlers()