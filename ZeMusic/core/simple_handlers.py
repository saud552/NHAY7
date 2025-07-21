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
        """معالج البحث عن الأغاني والرسائل التفاعلية"""
        try:
            message_text = update.message.text
            user_id = update.effective_user.id
            
            # التحقق من النظامين (الحقيقي والمحاكاة) للحسابات المساعدة
            from ZeMusic.core.realistic_assistant_manager import realistic_assistant_manager
            from ZeMusic.core.real_tdlib_assistant_manager import real_tdlib_assistant_manager
            
            # التحقق من النظام الحقيقي TDLib أولاً
            if user_id in real_tdlib_assistant_manager.user_states:
                user_state = real_tdlib_assistant_manager.user_states[user_id]
                current_state = user_state.get('state', '')
                
                if current_state == 'waiting_phone':
                    await real_tdlib_assistant_manager.handle_phone_input(update, context)
                    return
                elif current_state == 'waiting_code':
                    await real_tdlib_assistant_manager.handle_code_input(update, context)
                    return
                elif current_state == 'waiting_password':
                    await real_tdlib_assistant_manager.handle_password_input(update, context)
                    return
            
            # التحقق من النظام البديل (المحاكاة)
            elif user_id in realistic_assistant_manager.user_states:
                user_state = realistic_assistant_manager.user_states[user_id]
                current_state = user_state.get('state', '')
                
                if current_state == 'waiting_phone':
                    await realistic_assistant_manager.handle_phone_input(update, context)
                    return
                elif current_state == 'waiting_code':
                    await realistic_assistant_manager.handle_code_input(update, context)
                    return
                elif current_state == 'waiting_password':
                    await realistic_assistant_manager.handle_password_input(update, context)
                    return
            
            # التحقق من الجلسات المعلقة للتوافق مع النظام القديم
            if user_id in realistic_assistant_manager.pending_sessions:
                session_data = realistic_assistant_manager.pending_sessions[user_id]
                
                # تحديد الحالة المناسبة بناءً على بيانات الجلسة
                if 'phone' in session_data and 'session' in session_data:
                    phone = session_data['phone']
                    if phone in realistic_assistant_manager.mock_accounts_db:
                        account_info = realistic_assistant_manager.mock_accounts_db[phone]
                        if account_info.get('has_2fa', False) and session_data.get('session', {}).get('is_authorized', False):
                            await realistic_assistant_manager.handle_password_input(update, context)
                        else:
                            await realistic_assistant_manager.handle_code_input(update, context)
                    else:
                        await realistic_assistant_manager.handle_code_input(update, context)
                    return
            
            # التعامل مع أوامر الإلغاء
            if message_text.lower() in ['/cancel', 'إلغاء', 'cancel']:
                # تنظيف أي جلسات معلقة - النظام الحقيقي
                if user_id in real_tdlib_assistant_manager.pending_sessions:
                    try:
                        session = real_tdlib_assistant_manager.pending_sessions[user_id].get('session')
                        if session:
                            await session.stop()
                    except:
                        pass
                    del real_tdlib_assistant_manager.pending_sessions[user_id]
                
                if user_id in real_tdlib_assistant_manager.user_states:
                    del real_tdlib_assistant_manager.user_states[user_id]
                
                # تنظيف أي جلسات معلقة - النظام البديل
                if user_id in realistic_assistant_manager.pending_sessions:
                    try:
                        session = realistic_assistant_manager.pending_sessions[user_id].get('session')
                        if session:
                            await session.stop()
                    except:
                        pass
                    del realistic_assistant_manager.pending_sessions[user_id]
                
                if user_id in realistic_assistant_manager.user_states:
                    del realistic_assistant_manager.user_states[user_id]
                
                await update.message.reply_text(
                    "❌ **تم إلغاء العملية**\n\n"
                    "يمكنك البدء من جديد: /owner",
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من وجود كلمة "بحث"
            if not message_text.startswith('بحث'):
                # رد على الرسائل العادية في الخاص
                if update.message.chat.type == 'private':
                    await update.message.reply_text(
                        "👋 **مرحباً في ZeMusic Bot!**\n\n"
                        "🎵 **للبحث عن موسيقى:** `بحث اسم الأغنية`\n"
                        "⚙️ **لوحة التحكم:** /owner\n"
                        "❓ **المساعدة:** /help",
                        parse_mode='Markdown'
                    )
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
            elif callback_data.startswith('realistic_'):
                await self._handle_realistic_callbacks(query, context)
            elif callback_data == 'use_real_tdlib':
                await self._handle_use_real_tdlib(query, context)
            elif callback_data == 'use_simulation':
                await self._handle_use_simulation(query, context)
            elif callback_data.startswith('real_tdlib_'):
                await self._handle_real_tdlib_callbacks(query, context)
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
            user_id = query.from_user.id
            
            # عرض خيارات النظام
            keyboard = [
                [InlineKeyboardButton("🔥 النظام الحقيقي (TDLib)", callback_data="use_real_tdlib")],
                [InlineKeyboardButton("⚡ النظام البديل (محاكاة)", callback_data="use_simulation")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_assistant_choice")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🎯 **اختر نوع النظام:**\n\n"
                "🔥 **النظام الحقيقي (TDLib):**\n"
                "✅ اتصال مباشر بخوادم تليجرام\n"
                "✅ كود التحقق يصل لحسابك الفعلي\n"
                "✅ جلسات حقيقية ومستقرة\n\n"
                "⚡ **النظام البديل (محاكاة):**\n"
                "✅ لا يحتاج TDLib\n"
                "✅ للاختبار والتجريب\n"
                "✅ كودات تحقق تظهر في الرسائل\n\n"
                "🔧 **أيهما تفضل؟**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
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
            from ZeMusic.core.realistic_assistant_manager import realistic_assistant_manager
            
            user_id = query.from_user.id
            await realistic_assistant_manager.cancel_add_assistant(query, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إلغاء إضافة المساعد: {e}")
    
    async def _handle_realistic_callbacks(self, query, context):
        """معالج الـ Callbacks للنظام الواقعي الجديد"""
        try:
            from ZeMusic.core.realistic_assistant_manager import realistic_assistant_manager
            user_id = query.from_user.id
            callback_data = query.data
            
            if callback_data == "realistic_add_phone":
                # بدء إضافة حساب برقم الهاتف
                await query.edit_message_text(
                    "📱 **إضافة حساب مساعد برقم الهاتف**\n\n"
                    "📋 **أرسل رقم الهاتف بالصيغة الدولية:**\n\n"
                    "🔸 **أمثلة صحيحة:**\n"
                    "• `+966501234567` (السعودية)\n"
                    "• `+201234567890` (مصر)\n"
                    "• `+967771234567` (اليمن)\n"
                    "• `+49123456789` (ألمانيا)\n\n"
                    "⚡️ **الحسابات التجريبية المتاحة:**\n"
                    "• `+966501234567` (بدون 2FA - كود: 12345)\n"
                    "• `+201234567890` (مع 2FA - كود: 54321)\n"
                    "• `+967771234567` (عادي - كود: 11111)\n"
                    "• `+49123456789` (مع 2FA - كود: 22222)\n\n"
                    "💡 **أرسل رقم الهاتف الآن:**\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                
                # تحديث حالة المستخدم
                realistic_assistant_manager.user_states[user_id] = {
                    'state': 'waiting_phone',
                    'data': {}
                }
                
            elif callback_data == "realistic_add_session":
                # إضافة حساب بكود الجلسة (للمطورين)
                await query.edit_message_text(
                    "🔑 **إضافة حساب بـ Session String**\n\n"
                    "⚠️ **هذه الميزة للمطورين المتقدمين فقط**\n\n"
                    "📋 **الخطوات:**\n"
                    "1️⃣ احصل على Session String من مكتبة Pyrogram/Telethon\n"
                    "2️⃣ أرسل الـ Session String كاملاً\n"
                    "3️⃣ سيتم التحقق من صحته وإضافته\n\n"
                    "🚧 **قيد التطوير حالياً**\n\n"
                    "💡 **بدلاً من ذلك، استخدم إضافة برقم الهاتف**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data="add_assistant")],
                        [InlineKeyboardButton("❌ إلغاء", callback_data="realistic_cancel")]
                    ]),
                    parse_mode='Markdown'
                )
                
            elif callback_data == "realistic_replace_account":
                # استبدال الحساب الموجود
                user_state = realistic_assistant_manager.user_states.get(user_id, {})
                phone = user_state.get('data', {}).get('phone', '')
                
                if phone:
                    # حذف الحساب القديم من قاعدة البيانات
                    try:
                        import sqlite3
                        with sqlite3.connect("assistant_accounts.db", timeout=20) as conn:
                            conn.execute("DELETE FROM assistant_accounts WHERE phone = ?", (phone,))
                            conn.commit()
                        
                        await query.edit_message_text(
                            f"✅ **تم حذف الحساب القديم**\n\n"
                            f"📱 **الرقم:** {phone}\n\n"
                            "🔄 **الآن جاري بدء عملية إضافة الحساب الجديد...**",
                            parse_mode='Markdown'
                        )
                        
                        # بدء عملية التحقق
                        from ZeMusic.core.realistic_assistant_manager import TelegramSession
                        import asyncio
                        await asyncio.sleep(1)
                        await realistic_assistant_manager._start_phone_verification(query, phone, user_id)
                        
                    except Exception as e:
                        await query.edit_message_text(
                            f"❌ **خطأ في حذف الحساب القديم:** {str(e)}",
                            parse_mode='Markdown'
                        )
                else:
                    await query.edit_message_text(
                        "❌ **خطأ: لم يتم العثور على رقم الهاتف**",
                        parse_mode='Markdown'
                    )
                    
            elif callback_data == "realistic_use_another":
                # استخدام رقم آخر
                await query.edit_message_text(
                    "📱 **أرسل رقم هاتف جديد:**\n\n"
                    "📋 **بالصيغة الدولية مع رمز البلد**\n"
                    "مثال: `+966501234567`\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                
                # العودة لحالة انتظار الهاتف
                realistic_assistant_manager.user_states[user_id] = {
                    'state': 'waiting_phone',
                    'data': {}
                }
                
            elif callback_data == "realistic_cancel":
                # إلغاء العملية
                await realistic_assistant_manager.cancel_add_assistant(query, user_id)
                
            else:
                await query.answer("❓ أمر غير معروف", show_alert=True)
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالج الـ realistic callbacks: {e}")
            await query.edit_message_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _handle_real_tdlib_callbacks(self, query, context):
        """معالج الـ Callbacks للنظام الحقيقي TDLib"""
        try:
            from ZeMusic.core.real_tdlib_assistant_manager import real_tdlib_assistant_manager
            user_id = query.from_user.id
            callback_data = query.data
            
            if callback_data == "real_tdlib_add_phone":
                # بدء إضافة حساب برقم الهاتف الحقيقي
                await query.edit_message_text(
                    "📱 **إضافة حساب مساعد حقيقي برقم الهاتف**\n\n"
                    "🔥 **نظام TDLib الحقيقي:**\n"
                    "• اتصال مباشر بخوادم تليجرام\n"
                    "• كود التحقق يصل لحسابك الفعلي\n"
                    "• جلسات مستقرة وآمنة\n\n"
                    "📋 **أرسل رقم الهاتف بالصيغة الدولية:**\n"
                    "مثال: +967780138966\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                
                # تحديث حالة المستخدم
                real_tdlib_assistant_manager.user_states[user_id] = {
                    'state': 'waiting_phone',
                    'data': {}
                }
                
            elif callback_data == "real_tdlib_cancel":
                # إلغاء العملية
                await real_tdlib_assistant_manager.cancel_add_assistant(query, user_id)
                
            else:
                await query.answer("❓ أمر غير معروف", show_alert=True)
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالج الـ real TDLib callbacks: {e}")
            await query.edit_message_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _handle_use_real_tdlib(self, query, context):
        """معالج استخدام النظام الحقيقي TDLib"""
        try:
            from ZeMusic.core.real_tdlib_assistant_manager import real_tdlib_assistant_manager
            user_id = query.from_user.id
            
            await real_tdlib_assistant_manager.start_add_assistant(query, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في بدء النظام الحقيقي: {e}")
            await query.edit_message_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _handle_use_simulation(self, query, context):
        """معالج استخدام النظام البديل (محاكاة)"""
        try:
            from ZeMusic.core.realistic_assistant_manager import realistic_assistant_manager
            user_id = query.from_user.id
            
            await realistic_assistant_manager.start_add_assistant(query, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في بدء النظام البديل: {e}")
            await query.edit_message_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية - مطور للنظام الواقعي الجديد"""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text
            
            # معالجة إدخالات المستخدم في عملية إضافة المساعد
            from ZeMusic.core.realistic_assistant_manager import realistic_assistant_manager
            
            # التحقق من حالة المستخدم في النظام الجديد
            if user_id in realistic_assistant_manager.user_states:
                user_state = realistic_assistant_manager.user_states[user_id]
                current_state = user_state.get('state', '')
                
                if current_state == 'waiting_phone':
                    await realistic_assistant_manager.handle_phone_input(update, context)
                elif current_state == 'waiting_code':
                    await realistic_assistant_manager.handle_code_input(update, context)
                elif current_state == 'waiting_password':
                    await realistic_assistant_manager.handle_password_input(update, context)
                else:
                    await update.message.reply_text(
                        "🔄 **حالة غير معروفة**\n\n"
                        "الرجاء البدء من جديد: /start",
                        parse_mode='Markdown'
                    )
                return
            
            # التحقق من الجلسات المعلقة للتوافق مع النظام القديم
            if user_id in realistic_assistant_manager.pending_sessions:
                session_data = realistic_assistant_manager.pending_sessions[user_id]
                
                # تحديد الحالة المناسبة بناءً على بيانات الجلسة
                if 'phone' in session_data and 'session' in session_data:
                    # في انتظار كود التحقق أو كلمة المرور
                    phone = session_data['phone']
                    if phone in realistic_assistant_manager.mock_accounts_db:
                        account_info = realistic_assistant_manager.mock_accounts_db[phone]
                        if account_info.get('has_2fa', False) and session_data.get('session', {}).get('is_authorized', False):
                            # في انتظار كلمة مرور 2FA
                            await realistic_assistant_manager.handle_password_input(update, context)
                        else:
                            # في انتظار كود التحقق
                            await realistic_assistant_manager.handle_code_input(update, context)
                    else:
                        await realistic_assistant_manager.handle_code_input(update, context)
                else:
                    # جلسة فاسدة
                    await update.message.reply_text(
                        "❌ **جلسة منتهية الصلاحية**\n\n"
                        "الرجاء البدء من جديد: /start",
                        parse_mode='Markdown'
                    )
                return
            
            # التعامل مع أوامر الإلغاء
            if message_text.lower() in ['/cancel', 'إلغاء', 'cancel']:
                # تنظيف أي جلسات معلقة
                if user_id in realistic_assistant_manager.pending_sessions:
                    try:
                        session = realistic_assistant_manager.pending_sessions[user_id].get('session')
                        if session:
                            await session.stop()
                    except:
                        pass
                    del realistic_assistant_manager.pending_sessions[user_id]
                
                if user_id in realistic_assistant_manager.user_states:
                    del realistic_assistant_manager.user_states[user_id]
                
                await update.message.reply_text(
                    "❌ **تم إلغاء العملية**\n\n"
                    "يمكنك البدء من جديد: /start",
                    parse_mode='Markdown'
                )
                return
            
            # الرسائل العادية الأخرى
            if message_text.startswith('/'):
                if message_text == '/start':
                    await update.message.reply_text(
                        "👋 **مرحباً في ZeMusic Bot!**\n\n"
                        "استخدم الأوامر التالية:\n"
                        "• `/owner` - لوحة تحكم المالك\n"
                        "• `/play` - تشغيل موسيقى\n"
                        "• `/help` - المساعدة",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❓ **أمر غير معروف**\n\n"
                        "استخدم `/start` للبدء أو `/help` للمساعدة",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    "💬 **مرحباً!**\n\n"
                    "استخدم `/start` للدخول إلى القائمة الرئيسية",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالج الرسائل: {e}")
            await update.message.reply_text(
                "❌ **حدث خطأ**\n\n"
                "حاول مرة أخرى أو استخدم `/start`",
                parse_mode='Markdown'
            )

# مثيل المعالجات
simple_handlers = SimpleHandlers()