import asyncio
from typing import Union

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db
from ZeMusic.core.music_manager import music_manager
from ZeMusic.plugins.owner.owner_panel import owner_panel

class BasicCommandHandler:
    """معالج الأوامر الأساسية"""
    
    @staticmethod
    async def start_command(update, context):
        """معالج أمر /start"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            first_name = update.effective_user.first_name or ""
            username = update.effective_user.username or ""
            
            # إضافة المستخدم لقاعدة البيانات
            await db.add_user(user_id, first_name, username)
            await db.add_chat(chat_id)
            
            # رسالة الترحيب
            welcome_message = (
                f"🎵 **مرحباً {first_name}!**\n\n"
                f"أنا **{config.BOT_NAME}** - بوت الموسيقى الخاص بك\n\n"
                f"🎶 **الميزات المتاحة:**\n"
                f"{'✅' if tdlib_manager.get_assistants_count() > 0 else '⚠️'} تشغيل الموسيقى في المكالمات الصوتية\n"
                f"✅ البحث عن الأغاني\n"
                f"✅ قوائم التشغيل\n"
                f"✅ التحكم في التشغيل\n"
                f"✅ إدارة المجموعات\n\n"
                f"📱 **الأوامر الأساسية:**\n"
                f"🎵 `/play [اسم الأغنية]` - تشغيل موسيقى\n"
                f"⏸️ `/pause` - إيقاف مؤقت\n"
                f"▶️ `/resume` - استئناف\n"
                f"⏹️ `/stop` - إيقاف\n"
                f"⏭️ `/skip` - تخطي\n"
                f"📋 `/queue` - قائمة الانتظار\n\n"
                f"💡 **نصيحة:** أضفني للمجموعة واجعلني مدير لتشغيل الموسيقى!"
            )
            
            # إضافة تحذير إذا لم توجد حسابات مساعدة
            if tdlib_manager.get_assistants_count() == 0:
                welcome_message += (
                    f"\n\n⚠️ **ملاحظة:** لا توجد حسابات مساعدة حالياً\n"
                    f"📞 للمساعدة: {config.SUPPORT_CHAT or '@YourSupport'}"
                )
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر start: {e}")
            await update.message.reply_text("❌ حدث خطأ، حاول مرة أخرى")
    
    @staticmethod
    async def help_command(update, context):
        """معالج أمر /help"""
        try:
            help_message = (
                "📖 **دليل الاستخدام - ZeMusic Bot**\n\n"
                
                "🎵 **أوامر الموسيقى:**\n"
                "`/play [اسم الأغنية]` - تشغيل موسيقى\n"
                "`/pause` - إيقاف مؤقت\n"
                "`/resume` - استئناف التشغيل\n"
                "`/stop` - إيقاف التشغيل\n"
                "`/skip` - تخطي للأغنية التالية\n"
                "`/queue` - عرض قائمة الانتظار\n"
                "`/current` - الأغنية الحالية\n\n"
                
                "🎛️ **أوامر التحكم:**\n"
                "`/volume [1-100]` - ضبط مستوى الصوت\n"
                "`/shuffle` - خلط قائمة الانتظار\n"
                "`/loop` - تكرار الأغنية\n"
                "`/clear` - مسح قائمة الانتظار\n\n"
                
                "⚙️ **أوامر الإعدادات:**\n"
                "`/settings` - إعدادات المجموعة\n"
                "`/language` - تغيير اللغة\n"
                "`/mode` - تغيير وضع التشغيل\n\n"
                
                "👥 **أوامر الإدارة:**\n"
                "`/auth` - إضافة مستخدم للمصرحين\n"
                "`/unauth` - إزالة مستخدم من المصرحين\n"
                "`/authlist` - قائمة المصرحين\n\n"
                
                f"📞 **للدعم:** {config.SUPPORT_CHAT or '@YourSupport'}\n"
                f"👨‍💻 **المطور:** [اضغط هنا](tg://user?id={config.OWNER_ID})"
            )
            
            await update.message.reply_text(help_message, parse_mode='Markdown')
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر help: {e}")
            await update.message.reply_text("❌ حدث خطأ في عرض المساعدة")
    
    @staticmethod
    async def play_command(update, context):
        """معالج أمر /play"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # التحقق من النص المطلوب
            if not context.args:
                await update.message.reply_text(
                    "🎵 **تشغيل الموسيقى**\n\n"
                    "📝 **الاستخدام:** `/play [اسم الأغنية أو الرابط]`\n\n"
                    "💡 **أمثلة:**\n"
                    "`/play عمرو دياب نور العين`\n"
                    "`/play https://youtu.be/...`\n"
                    "`/play fairuz`",
                    parse_mode='Markdown'
                )
                return
            
            query = " ".join(context.args)
            
            # إضافة المستخدم والمجموعة لقاعدة البيانات
            await db.add_user(user_id)
            await db.add_chat(chat_id)
            
            # رسالة المعالجة
            processing_msg = await update.message.reply_text(
                "🔍 **جارٍ البحث...**\n⏳ يرجى الانتظار",
                parse_mode='Markdown'
            )
            
            # محاولة تشغيل الموسيقى
            result = await music_manager.play_music(chat_id, query, user_id)
            
            if result['success']:
                session = result['session']
                song_info = result['song_info']
                
                success_message = (
                    f"🎵 **بدء التشغيل**\n\n"
                    f"🎼 **العنوان:** `{song_info['title']}`\n"
                    f"⏱️ **المدة:** `{song_info.get('duration', 'غير محدد')}`\n"
                    f"🤖 **المساعد:** `{result['assistant_id']}`\n"
                    f"👤 **بواسطة:** {update.effective_user.first_name}\n\n"
                    f"🎛️ **التحكم:** /pause | /resume | /stop | /skip"
                )
                
                await processing_msg.edit_text(success_message, parse_mode='Markdown')
                
            else:
                error_message = result['message']
                await processing_msg.edit_text(error_message, parse_mode='Markdown')
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر play: {e}")
            await update.message.reply_text("❌ حدث خطأ في تشغيل الموسيقى")
    
    @staticmethod
    async def pause_command(update, context):
        """معالج أمر /pause"""
        try:
            chat_id = update.effective_chat.id
            
            session = await music_manager.get_current_session(chat_id)
            if not session:
                await update.message.reply_text("❌ لا يوجد تشغيل حالياً")
                return
            
            success = await music_manager.pause_music(chat_id)
            if success:
                await update.message.reply_text("⏸️ **تم إيقاف التشغيل مؤقتاً**")
            else:
                await update.message.reply_text("❌ فشل في إيقاف التشغيل")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر pause: {e}")
            await update.message.reply_text("❌ حدث خطأ")
    
    @staticmethod
    async def resume_command(update, context):
        """معالج أمر /resume"""
        try:
            chat_id = update.effective_chat.id
            
            session = await music_manager.get_current_session(chat_id)
            if not session:
                await update.message.reply_text("❌ لا يوجد تشغيل حالياً")
                return
            
            success = await music_manager.resume_music(chat_id)
            if success:
                await update.message.reply_text("▶️ **تم استئناف التشغيل**")
            else:
                await update.message.reply_text("❌ فشل في استئناف التشغيل")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر resume: {e}")
            await update.message.reply_text("❌ حدث خطأ")
    
    @staticmethod
    async def stop_command(update, context):
        """معالج أمر /stop"""
        try:
            chat_id = update.effective_chat.id
            
            session = await music_manager.get_current_session(chat_id)
            if not session:
                await update.message.reply_text("❌ لا يوجد تشغيل حالياً")
                return
            
            success = await music_manager.stop_music(chat_id)
            if success:
                await update.message.reply_text("⏹️ **تم إيقاف التشغيل**")
            else:
                await update.message.reply_text("❌ فشل في إيقاف التشغيل")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر stop: {e}")
            await update.message.reply_text("❌ حدث خطأ")
    
    @staticmethod
    async def skip_command(update, context):
        """معالج أمر /skip"""
        try:
            chat_id = update.effective_chat.id
            
            session = await music_manager.get_current_session(chat_id)
            if not session:
                await update.message.reply_text("❌ لا يوجد تشغيل حالياً")
                return
            
            success = await music_manager.skip_music(chat_id)
            if success:
                await update.message.reply_text("⏭️ **تم تخطي الأغنية**")
            else:
                await update.message.reply_text("❌ فشل في التخطي")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر skip: {e}")
            await update.message.reply_text("❌ حدث خطأ")
    
    @staticmethod
    async def current_command(update, context):
        """معالج أمر /current"""
        try:
            chat_id = update.effective_chat.id
            
            session = await music_manager.get_current_session(chat_id)
            if not session:
                await update.message.reply_text("❌ لا يوجد تشغيل حالياً")
                return
            
            import time
            duration = int(time.time() - session.start_time)
            mins, secs = divmod(duration, 60)
            
            current_message = (
                f"🎵 **التشغيل الحالي**\n\n"
                f"🎼 **العنوان:** `{session.song_title}`\n"
                f"⏱️ **مدة التشغيل:** `{mins:02d}:{secs:02d}`\n"
                f"🤖 **المساعد:** `{session.assistant_id}`\n"
                f"👤 **طلب بواسطة:** [المستخدم](tg://user?id={session.user_id})\n"
                f"📊 **الحالة:** `{'نشط' if session.is_active else 'متوقف مؤقتاً'}`"
            )
            
            await update.message.reply_text(current_message, parse_mode='Markdown')
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر current: {e}")
            await update.message.reply_text("❌ حدث خطأ")
    
    @staticmethod
    async def queue_command(update, context):
        """معالج أمر /queue"""
        try:
            chat_id = update.effective_chat.id
            
            queue = await music_manager.queue_manager.get_queue(chat_id)
            current_session = await music_manager.get_current_session(chat_id)
            
            if not current_session and not queue:
                await update.message.reply_text("📋 **قائمة الانتظار فارغة**")
                return
            
            message_parts = ["📋 **قائمة التشغيل:**\n"]
            
            if current_session:
                message_parts.append(
                    f"🎵 **قيد التشغيل:**\n"
                    f"└ `{current_session.song_title}`\n\n"
                )
            
            if queue:
                message_parts.append("⏳ **في الانتظار:**\n")
                for i, song in enumerate(queue[:5], 1):  # عرض أول 5 أغاني فقط
                    message_parts.append(f"{i}. `{song.get('title', 'أغنية')}`\n")
                
                if len(queue) > 5:
                    message_parts.append(f"\n... و {len(queue) - 5} أغنية أخرى")
            
            await update.message.reply_text(''.join(message_parts), parse_mode='Markdown')
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر queue: {e}")
            await update.message.reply_text("❌ حدث خطأ")
    
    @staticmethod
    async def owner_command(update, context):
        """معالج أمر /owner - لوحة تحكم المالك"""
        try:
            user_id = update.effective_user.id
            
            result = await owner_panel.show_main_panel(user_id)
            
            if result['success']:
                # هنا يجب إرسال الرسالة مع الكيبورد
                # يعتمد على مكتبة البوت المستخدمة
                await update.message.reply_text(
                    result['message'],
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(result['message'])
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر owner: {e}")
            await update.message.reply_text("❌ حدث خطأ في لوحة التحكم")
    
    @staticmethod
    async def stats_command(update, context):
        """معالج أمر /stats"""
        try:
            stats = await db.get_stats()
            assistants_count = tdlib_manager.get_assistants_count()
            connected_count = tdlib_manager.get_connected_assistants_count()
            active_sessions = len(music_manager.active_sessions)
            
            stats_message = (
                f"📊 **إحصائيات البوت**\n\n"
                f"👥 **المستخدمين:** `{stats['users']}`\n"
                f"💬 **المجموعات:** `{stats['chats']}`\n"
                f"🤖 **الحسابات المساعدة:** `{connected_count}/{assistants_count}`\n"
                f"🎵 **الجلسات النشطة:** `{active_sessions}`\n"
                f"👨‍💼 **المديرين:** `{stats['sudoers']}`\n\n"
                f"📈 **الحالة:** `نشط وجاهز`\n"
                f"💾 **قاعدة البيانات:** `SQLite محسّن`\n"
                f"🔧 **النسخة:** `2.0.0 TDLib Edition`"
            )
            
            await update.message.reply_text(stats_message, parse_mode='Markdown')
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في أمر stats: {e}")
            await update.message.reply_text("❌ حدث خطأ في عرض الإحصائيات")

# إنشاء مثيل معالج الأوامر
command_handler = BasicCommandHandler()