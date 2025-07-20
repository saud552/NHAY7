import asyncio
import json
from typing import Dict, List

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db
from ZeMusic.core.music_manager import music_manager

class OwnerPanel:
    """لوحة تحكم مالك البوت"""
    
    def __init__(self):
        self.pending_sessions = {}  # جلسات انتظار إضافة الحسابات
    
    async def show_main_panel(self, user_id: int) -> Dict:
        """عرض اللوحة الرئيسية"""
        if user_id != config.OWNER_ID:
            return {
                'success': False,
                'message': "❌ هذا الأمر مخصص لمالك البوت فقط"
            }
        
        stats = await self._get_bot_stats()
        
        keyboard = [
            [
                {'text': '📱 إدارة الحسابات المساعدة', 'callback_data': 'owner_assistants'},
                {'text': '📊 الإحصائيات', 'callback_data': 'owner_stats'}
            ],
            [
                {'text': '⚙️ إعدادات البوت', 'callback_data': 'owner_settings'},
                {'text': '🔧 صيانة النظام', 'callback_data': 'owner_maintenance'}
            ],
            [
                {'text': '📋 سجلات النظام', 'callback_data': 'owner_logs'},
                {'text': '🗃️ قاعدة البيانات', 'callback_data': 'owner_database'}
            ],
            [
                {'text': '🔄 إعادة تشغيل', 'callback_data': 'owner_restart'},
                {'text': '🛑 إيقاف البوت', 'callback_data': 'owner_shutdown'}
            ]
        ]
        
        message = (
            "🎛️ **لوحة تحكم مالك البوت**\n\n"
            f"📊 **الإحصائيات السريعة:**\n"
            f"👥 المستخدمين: `{stats['users']}`\n"
            f"💬 المجموعات: `{stats['chats']}`\n"
            f"🤖 الحسابات المساعدة: `{stats['assistants']}`\n"
            f"🎵 الجلسات النشطة: `{stats['active_sessions']}`\n\n"
            f"🕐 آخر تحديث: `{stats['last_update']}`"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard
        }
    
    async def show_assistants_panel(self, user_id: int) -> Dict:
        """عرض لوحة إدارة الحسابات المساعدة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        assistants = await db.get_all_assistants()
        connected_count = tdlib_manager.get_connected_assistants_count()
        
        keyboard = [
            [
                {'text': '➕ إضافة حساب مساعد', 'callback_data': 'add_assistant'},
                {'text': '🗑️ حذف حساب مساعد', 'callback_data': 'remove_assistant'}
            ],
            [
                {'text': '📋 قائمة الحسابات', 'callback_data': 'list_assistants'},
                {'text': '🔄 إعادة تشغيل الحسابات', 'callback_data': 'restart_assistants'}
            ],
            [
                {'text': '⚠️ إلغاء تفعيل حساب', 'callback_data': 'deactivate_assistant'},
                {'text': '✅ تفعيل حساب', 'callback_data': 'activate_assistant'}
            ],
            [
                {'text': '📊 إحصائيات مفصلة', 'callback_data': 'assistant_stats'},
                {'text': '🧹 تنظيف الحسابات الخاملة', 'callback_data': 'cleanup_assistants'}
            ],
            [
                {'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'owner_main'}
            ]
        ]
        
        message = (
            "📱 **إدارة الحسابات المساعدة**\n\n"
            f"📊 **الحالة الحالية:**\n"
            f"🤖 إجمالي الحسابات: `{len(assistants)}`\n"
            f"🟢 متصل: `{connected_count}`\n"
            f"🔴 غير متصل: `{len(assistants) - connected_count}`\n\n"
            f"⚡ **الأداء:**\n"
            f"🎵 الجلسات النشطة: `{len(music_manager.active_sessions)}`\n"
            f"📈 الحد الأقصى: `{config.MAX_ASSISTANTS}`\n"
            f"📉 الحد الأدنى: `{config.MIN_ASSISTANTS}`\n\n"
            "اختر العملية المطلوبة:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard
        }
    
    async def start_add_assistant(self, user_id: int) -> Dict:
        """بدء عملية إضافة حساب مساعد"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # إنشاء جلسة انتظار
        session_id = f"add_assistant_{user_id}_{int(asyncio.get_event_loop().time())}"
        self.pending_sessions[user_id] = {
            'type': 'add_assistant',
            'session_id': session_id,
            'step': 'waiting_session'
        }
        
        keyboard = [
            [{'text': '❌ إلغاء', 'callback_data': 'cancel_add_assistant'}]
        ]
        
        message = (
            "➕ **إضافة حساب مساعد جديد**\n\n"
            "📝 **الخطوات:**\n"
            "1️⃣ أرسل session string للحساب\n"
            "2️⃣ أدخل اسم مميز للحساب\n"
            "3️⃣ تأكيد الإضافة\n\n"
            "🔗 **ملاحظة:** تأكد من صحة الـ session string\n"
            "⚠️ يُفضل استخدام حسابات عمرها أكثر من سنة\n\n"
            "📎 أرسل session string الآن:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'waiting_input': True
        }
    
    async def process_add_assistant_input(self, user_id: int, text: str) -> Dict:
        """معالجة إدخالات إضافة الحساب المساعد"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        
        if session['step'] == 'waiting_session':
            # التحقق من صيغة session string
            if not self._validate_session_string(text):
                return {
                    'success': False,
                    'message': "❌ صيغة session string غير صحيحة\nأرسل session string صحيح:"
                }
            
            session['session_string'] = text
            session['step'] = 'waiting_name'
            
            keyboard = [
                [{'text': '❌ إلغاء', 'callback_data': 'cancel_add_assistant'}]
            ]
            
            return {
                'success': True,
                'message': "✅ تم قبول session string\n\n📝 الآن أرسل اسم مميز للحساب المساعد:",
                'keyboard': keyboard,
                'waiting_input': True
            }
        
        elif session['step'] == 'waiting_name':
            if len(text) < 3 or len(text) > 50:
                return {
                    'success': False,
                    'message': "❌ الاسم يجب أن يكون بين 3-50 حرف\nأرسل اسم صحيح:"
                }
            
            session['name'] = text
            session['step'] = 'confirmation'
            
            # اختيار معرف تلقائي
            assistants = await db.get_all_assistants()
            used_ids = [a['assistant_id'] for a in assistants]
            assistant_id = 1
            while assistant_id in used_ids:
                assistant_id += 1
            
            session['assistant_id'] = assistant_id
            
            keyboard = [
                [
                    {'text': '✅ تأكيد الإضافة', 'callback_data': 'confirm_add_assistant'},
                    {'text': '❌ إلغاء', 'callback_data': 'cancel_add_assistant'}
                ]
            ]
            
            message = (
                "📋 **تأكيد إضافة الحساب المساعد**\n\n"
                f"🆔 **المعرف:** `{assistant_id}`\n"
                f"📝 **الاسم:** `{text}`\n"
                f"🔗 **Session:** `{session['session_string'][:20]}...`\n\n"
                "❓ هل تريد إضافة هذا الحساب؟"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard
            }
        
        return {'success': False, 'message': "❌ خطأ في المعالجة"}
    
    async def confirm_add_assistant(self, user_id: int) -> Dict:
        """تأكيد إضافة الحساب المساعد"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        
        try:
            # إضافة الحساب للنظام
            success = await tdlib_manager.add_assistant(
                session['session_string'],
                session['assistant_id'],
                session['name']
            )
            
            if success:
                # تنظيف الجلسة
                del self.pending_sessions[user_id]
                
                keyboard = [
                    [{'text': '📱 إدارة الحسابات', 'callback_data': 'owner_assistants'}]
                ]
                
                message = (
                    "✅ **تم إضافة الحساب المساعد بنجاح!**\n\n"
                    f"🆔 المعرف: `{session['assistant_id']}`\n"
                    f"📝 الاسم: `{session['name']}`\n"
                    f"🟢 الحالة: متصل ونشط\n\n"
                    "🎵 الحساب جاهز لتشغيل الموسيقى الآن!"
                )
                
                return {
                    'success': True,
                    'message': message,
                    'keyboard': keyboard
                }
            else:
                return {
                    'success': False,
                    'message': "❌ فشل في إضافة الحساب\nتحقق من صحة session string وحاول مرة أخرى"
                }
        
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إضافة المساعد: {e}")
            return {
                'success': False,
                'message': f"❌ خطأ في إضافة الحساب: {str(e)}"
            }
    
    async def list_assistants(self, user_id: int) -> Dict:
        """عرض قائمة الحسابات المساعدة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        assistants = await db.get_all_assistants()
        
        if not assistants:
            keyboard = [
                [{'text': '➕ إضافة حساب مساعد', 'callback_data': 'add_assistant'}],
                [{'text': '🔙 العودة', 'callback_data': 'owner_assistants'}]
            ]
            
            return {
                'success': True,
                'message': "📝 **قائمة الحسابات المساعدة**\n\n❌ لا توجد حسابات مساعدة مضافة",
                'keyboard': keyboard
            }
        
        message_parts = ["📝 **قائمة الحسابات المساعدة:**\n"]
        
        for assistant in assistants:
            # التحقق من حالة الاتصال
            is_connected = False
            active_calls = 0
            
            for tdlib_assistant in tdlib_manager.assistants:
                if tdlib_assistant.assistant_id == assistant['assistant_id']:
                    is_connected = tdlib_assistant.is_connected
                    active_calls = tdlib_assistant.get_active_calls_count()
                    break
            
            status_emoji = "🟢" if is_connected else "🔴"
            status_text = "متصل" if is_connected else "غير متصل"
            
            assistant_info = (
                f"\n{status_emoji} **الحساب {assistant['assistant_id']}**\n"
                f"📝 الاسم: `{assistant['name']}`\n"
                f"🔌 الحالة: `{status_text}`\n"
                f"🎵 المكالمات النشطة: `{active_calls}`\n"
                f"📊 إجمالي الاستخدام: `{assistant['total_calls']}`\n"
                f"🕐 آخر استخدام: `{assistant['last_used'][:19]}`\n"
            )
            
            message_parts.append(assistant_info)
        
        keyboard = [
            [
                {'text': '➕ إضافة حساب', 'callback_data': 'add_assistant'},
                {'text': '🗑️ حذف حساب', 'callback_data': 'remove_assistant'}
            ],
            [
                {'text': '🔄 تحديث القائمة', 'callback_data': 'list_assistants'},
                {'text': '🔙 العودة', 'callback_data': 'owner_assistants'}
            ]
        ]
        
        return {
            'success': True,
            'message': ''.join(message_parts),
            'keyboard': keyboard
        }
    
    async def show_detailed_stats(self, user_id: int) -> Dict:
        """عرض إحصائيات مفصلة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        stats = await db.get_stats()
        
        # إحصائيات الحسابات المساعدة
        assistants = await db.get_all_assistants()
        connected_assistants = tdlib_manager.get_connected_assistants_count()
        
        # إحصائيات الجلسات النشطة
        active_sessions = len(music_manager.active_sessions)
        
        # إحصائيات النظام
        import psutil
        import platform
        
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        message = (
            "📊 **إحصائيات البوت المفصلة**\n\n"
            
            "👥 **المستخدمين والمجموعات:**\n"
            f"👤 إجمالي المستخدمين: `{stats['users']}`\n"
            f"💬 إجمالي المجموعات: `{stats['chats']}`\n"
            f"👨‍💼 المديرين: `{stats['sudoers']}`\n"
            f"🚫 المحظورين: `{stats['banned']}`\n\n"
            
            "🤖 **الحسابات المساعدة:**\n"
            f"📱 إجمالي الحسابات: `{len(assistants)}`\n"
            f"🟢 متصل: `{connected_assistants}`\n"
            f"🔴 غير متصل: `{len(assistants) - connected_assistants}`\n"
            f"🎵 الجلسات النشطة: `{active_sessions}`\n\n"
            
            "🖥️ **موارد النظام:**\n"
            f"🧠 المعالج: `{cpu_percent}%`\n"
            f"💾 الذاكرة: `{memory.percent}%`\n"
            f"💿 التخزين: `{disk.percent}%`\n"
            f"🖥️ النظام: `{platform.system()}`\n\n"
            
            "📈 **الأداء:**\n"
            f"⚡ وقت التشغيل: `{self._get_uptime()}`\n"
            f"🔄 آخر إعادة تشغيل: `{self._get_last_restart()}`\n"
        )
        
        keyboard = [
            [
                {'text': '🔄 تحديث الإحصائيات', 'callback_data': 'owner_stats'},
                {'text': '📊 إحصائيات الاستخدام', 'callback_data': 'usage_stats'}
            ],
            [
                {'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'owner_main'}
            ]
        ]
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard
        }
    
    def _validate_session_string(self, session_string: str) -> bool:
        """التحقق من صحة session string"""
        try:
            # التحقق الأساسي من طول وتشفير session string
            if len(session_string) < 50:
                return False
            
            # يمكن إضافة المزيد من التحققات هنا
            return True
            
        except Exception:
            return False
    
    def _get_uptime(self) -> str:
        """الحصول على وقت التشغيل"""
        # يمكن حفظ وقت البدء في متغير عام
        return "غير متاح"
    
    def _get_last_restart(self) -> str:
        """الحصول على وقت آخر إعادة تشغيل"""
        return "غير متاح"
    
    async def _get_bot_stats(self) -> Dict:
        """الحصول على إحصائيات سريعة للبوت"""
        stats = await db.get_stats()
        stats['active_sessions'] = len(music_manager.active_sessions)
        stats['last_update'] = "الآن"
        return stats
    
    async def cancel_operation(self, user_id: int) -> Dict:
        """إلغاء العملية الحالية"""
        if user_id in self.pending_sessions:
            del self.pending_sessions[user_id]
        
        return await self.show_assistants_panel(user_id)

# إنشاء مثيل عام للوحة التحكم
owner_panel = OwnerPanel()