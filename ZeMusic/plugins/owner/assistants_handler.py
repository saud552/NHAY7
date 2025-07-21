import asyncio
import sqlite3
import time
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db

class AssistantsHandler:
    """معالج إدارة الحسابات المساعدة المتطور"""
    
    def __init__(self):
        self.pending_sessions = {}  # جلسات إضافة الحسابات
        self.auto_leave_enabled = False
        self.auto_leave_timeout = 300  # 5 دقائق
        self.load_auto_leave_settings()
        self._auto_leave_task_started = False
        
    async def start_auto_leave_task(self):
        """بدء مهمة المغادرة التلقائية"""
        if not self._auto_leave_task_started:
            self._auto_leave_task_started = True
            asyncio.create_task(self._auto_leave_task())
    
    def load_auto_leave_settings(self):
        """تحميل إعدادات المغادرة التلقائية"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # إنشاء جدول إعدادات المغادرة التلقائية
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auto_leave_settings (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        enabled BOOLEAN DEFAULT FALSE,
                        timeout_minutes INTEGER DEFAULT 5,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("INSERT OR IGNORE INTO auto_leave_settings (id) VALUES (1)")
                
                # تحميل الإعدادات
                cursor.execute("SELECT enabled, timeout_minutes FROM auto_leave_settings WHERE id = 1")
                row = cursor.fetchone()
                
                if row:
                    self.auto_leave_enabled = bool(row[0])
                    self.auto_leave_timeout = row[1] * 60  # تحويل للثواني
                    
                conn.commit()
                LOGGER(__name__).info(f"تم تحميل إعدادات المغادرة التلقائية - مفعل: {self.auto_leave_enabled}")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تحميل إعدادات المغادرة التلقائية: {e}")
    
    def save_auto_leave_settings(self):
        """حفظ إعدادات المغادرة التلقائية"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE auto_leave_settings 
                    SET enabled = ?, timeout_minutes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (self.auto_leave_enabled, self.auto_leave_timeout // 60))
                conn.commit()
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حفظ إعدادات المغادرة التلقائية: {e}")
    
    async def show_assistants_panel(self, user_id: int) -> Dict:
        """عرض لوحة إدارة الحسابات المساعدة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # الحصول على إحصائيات الحسابات المساعدة
        assistants_stats = await self._get_assistants_stats()
        
        keyboard = [
            [
                {'text': '➕ إضافة حساب مساعد', 'callback_data': 'assistants_add'},
                {'text': '🗑️ حذف حساب مساعد', 'callback_data': 'assistants_remove'}
            ],
            [
                {'text': '📋 عرض الحسابات المساعدة', 'callback_data': 'assistants_list'},
                {'text': '🔄 إعادة تشغيل الحسابات', 'callback_data': 'assistants_restart'}
            ],
            [
                {'text': f'🚪 المغادرة التلقائية: {"🟢 مفعل" if self.auto_leave_enabled else "🔴 معطل"}', 
                 'callback_data': 'assistants_auto_leave_toggle'},
                {'text': '⚙️ إعدادات المغادرة', 'callback_data': 'assistants_auto_leave_settings'}
            ],
            [
                {'text': '🧪 اختبار الحسابات', 'callback_data': 'assistants_test'},
                {'text': '📊 إحصائيات مفصلة', 'callback_data': 'assistants_detailed_stats'}
            ],
            [
                {'text': '🔄 تحديث الحالة', 'callback_data': 'assistants_refresh'},
                {'text': '🔧 صيانة الحسابات', 'callback_data': 'assistants_maintenance'}
            ],
            [
                {'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'admin_main'}
            ]
        ]
        
        auto_leave_status = "🟢 مفعل" if self.auto_leave_enabled else "🔴 معطل"
        auto_leave_time = f"{self.auto_leave_timeout // 60} دقائق"
        
        message = (
            f"📱 **إدارة الحسابات المساعدة**\n\n"
            
            f"📊 **الإحصائيات:**\n"
            f"🤖 إجمالي الحسابات: `{assistants_stats['total']}`\n"
            f"🟢 متصلة: `{assistants_stats['connected']}`\n"
            f"🔴 غير متصلة: `{assistants_stats['disconnected']}`\n"
            f"⚡ نشطة: `{assistants_stats['active']}`\n"
            f"🎵 في مكالمات: `{assistants_stats['in_calls']}`\n\n"
            
            f"🚪 **المغادرة التلقائية:** {auto_leave_status}\n"
            f"⏱️ **مدة عدم النشاط:** `{auto_leave_time}`\n\n"
            
            f"💡 **معلومات:**\n"
            f"• الحسابات المساعدة تساعد في تشغيل الموسيقى\n"
            f"• يُنصح بوجود 2-3 حسابات للأداء الأمثل\n"
            f"• المغادرة التلقائية توفر الموارد\n"
            f"• TDLib يحمي من حذف الحسابات\n\n"
            
            f"🎯 اختر الإجراء المطلوب:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def start_add_assistant(self, user_id: int) -> Dict:
        """بدء عملية إضافة حساب مساعد"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # إنشاء جلسة إضافة جديدة
        session_id = f"add_assistant_{user_id}_{int(time.time())}"
        self.pending_sessions[user_id] = {
            'session_id': session_id,
            'step': 'waiting_session_string',
            'created_at': time.time()
        }
        
        keyboard = [
            [
                {'text': '❌ إلغاء الإضافة', 'callback_data': 'assistants_cancel_add'}
            ]
        ]
        
        message = (
            f"➕ **إضافة حساب مساعد جديد**\n\n"
            
            f"📋 **خطوات الإضافة:**\n"
            f"1️⃣ الحصول على session string\n"
            f"2️⃣ إرسال session string للبوت\n"
            f"3️⃣ اختيار اسم للحساب\n"
            f"4️⃣ تأكيد الإضافة\n\n"
            
            f"🔐 **الحصول على Session String:**\n"
            f"• استخدم @StringFatherBot\n"
            f"• أو استخدم Pyrogram session generator\n"
            f"• أو استخدم أي أداة TDLib session\n\n"
            
            f"⚠️ **تنبيهات مهمة:**\n"
            f"• تأكد من صحة session string\n"
            f"• لا تشارك session string مع أحد\n"
            f"• الحساب يجب أن يكون نشط\n"
            f"• يُفضل حسابات عمرها أكثر من سنة\n\n"
            
            f"📝 **أرسل الآن session string للحساب المساعد:**"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown',
            'waiting_session': True
        }
    
    async def process_session_string(self, user_id: int, session_string: str) -> Dict:
        """معالجة session string المرسل"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة إضافة نشطة"}
        
        try:
            # تنظيف session string
            session_string = session_string.strip()
            
            # التحقق من صحة session string
            if not self._validate_session_string(session_string):
                return {
                    'success': False,
                    'message': "❌ session string غير صحيح\nيرجى التأكد من صحة البيانات والمحاولة مرة أخرى"
                }
            
            # حفظ session string في الجلسة
            self.pending_sessions[user_id]['session_string'] = session_string
            self.pending_sessions[user_id]['step'] = 'waiting_name'
            
            keyboard = [
                [
                    {'text': '⏭️ استخدام اسم افتراضي', 'callback_data': 'assistants_default_name'},
                    {'text': '❌ إلغاء', 'callback_data': 'assistants_cancel_add'}
                ]
            ]
            
            message = (
                f"✅ **تم قبول session string بنجاح!**\n\n"
                
                f"📝 **أرسل الآن اسماً للحساب المساعد:**\n"
                f"• مثال: `Assistant 1`\n"
                f"• مثال: `Music Helper`\n"
                f"• مثال: `المساعد الأول`\n\n"
                
                f"💡 أو يمكنك استخدام اسم افتراضي\n\n"
                
                f"📎 أرسل الاسم المطلوب:"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown',
                'waiting_name': True
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالجة session string: {e}")
            return {
                'success': False,
                'message': f"❌ حدث خطأ في معالجة session string: {str(e)}"
            }
    
    async def process_assistant_name(self, user_id: int, name: str) -> Dict:
        """معالجة اسم الحساب المساعد"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        session['assistant_name'] = name.strip()
        session['step'] = 'confirmation'
        
        keyboard = [
            [
                {'text': '✅ تأكيد الإضافة', 'callback_data': 'assistants_confirm_add'},
                {'text': '❌ إلغاء', 'callback_data': 'assistants_cancel_add'}
            ],
            [
                {'text': '✏️ تعديل الاسم', 'callback_data': 'assistants_edit_name'}
            ]
        ]
        
        message = (
            f"📋 **تأكيد إضافة الحساب المساعد**\n\n"
            
            f"✅ **تفاصيل الحساب:**\n"
            f"📛 الاسم: `{name}`\n"
            f"🔐 Session: `محفوظ بأمان`\n"
            f"⏰ تاريخ الإضافة: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
            
            f"🔄 **ما سيحدث عند التأكيد:**\n"
            f"• إضافة الحساب لقاعدة البيانات\n"
            f"• محاولة الاتصال بالحساب\n"
            f"• تفعيل الحساب للاستخدام\n"
            f"• إضافته لمدير الحسابات المساعدة\n\n"
            
            f"❓ هل تريد تأكيد الإضافة؟"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def confirm_add_assistant(self, user_id: int) -> Dict:
        """تأكيد إضافة الحساب المساعد"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        
        try:
            # إضافة الحساب لقاعدة البيانات
            assistant_id = await db.add_assistant(
                session['session_string'],
                session['assistant_name']
            )
            
            # محاولة الاتصال بالحساب
            connection_result = await tdlib_manager.add_assistant(
                session['session_string'],
                session['assistant_name']
            )
            
            # إنهاء الجلسة
            del self.pending_sessions[user_id]
            
            keyboard = [
                [
                    {'text': '📋 عرض الحسابات', 'callback_data': 'assistants_list'},
                    {'text': '🧪 اختبار الحساب', 'callback_data': 'assistants_test'}
                ],
                [
                    {'text': '🔙 العودة لإدارة الحسابات', 'callback_data': 'admin_assistants'}
                ]
            ]
            
            if connection_result:
                status = "✅ متصل ونشط"
                status_detail = "الحساب جاهز للاستخدام فوراً"
            else:
                status = "⚠️ مضاف لكن غير متصل"
                status_detail = "سيتم المحاولة لاحقاً"
            
            message = (
                f"🎉 **تم إضافة الحساب المساعد بنجاح!**\n\n"
                
                f"📱 **تفاصيل الحساب:**\n"
                f"🆔 المعرف: `{assistant_id}`\n"
                f"📛 الاسم: `{session['assistant_name']}`\n"
                f"🔌 الحالة: {status}\n"
                f"📊 التفاصيل: {status_detail}\n\n"
                
                f"🔄 **الخطوات التالية:**\n"
                f"• الحساب مضاف لقاعدة البيانات\n"
                f"• متاح للاستخدام في تشغيل الموسيقى\n"
                f"• يمكن مراقبته من لوحة الإدارة\n\n"
                
                f"💡 **نصيحة:** يمكنك إضافة المزيد من الحسابات لتحسين الأداء"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إضافة الحساب المساعد: {e}")
            return {
                'success': False,
                'message': f"❌ فشل في إضافة الحساب: {str(e)}"
            }
    
    async def start_remove_assistant(self, user_id: int) -> Dict:
        """بدء عملية حذف حساب مساعد"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # الحصول على قائمة الحسابات المساعدة
        assistants = await db.get_assistants()
        
        if not assistants:
            keyboard = [
                [
                    {'text': '➕ إضافة حساب مساعد', 'callback_data': 'assistants_add'},
                    {'text': '🔙 العودة', 'callback_data': 'admin_assistants'}
                ]
            ]
            
            return {
                'success': True,
                'message': "❌ لا توجد حسابات مساعدة مضافة\n\n💡 أضف حساب مساعد أولاً",
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
        
        # إنشاء جلسة حذف
        session_id = f"remove_assistant_{user_id}_{int(time.time())}"
        self.pending_sessions[user_id] = {
            'session_id': session_id,
            'step': 'select_assistant',
            'created_at': time.time()
        }
        
        # إنشاء keyboard مع الحسابات
        keyboard = []
        for assistant in assistants:
            status_emoji = "🟢" if assistant.get('is_active') else "🔴"
            button_text = f"{status_emoji} {assistant['name']} (ID: {assistant['assistant_id']})"
            keyboard.append([{
                'text': button_text,
                'callback_data': f'remove_assistant_{assistant["assistant_id"]}'
            }])
        
        keyboard.append([
            {'text': '❌ إلغاء الحذف', 'callback_data': 'assistants_cancel_remove'}
        ])
        
        message = (
            f"🗑️ **حذف حساب مساعد**\n\n"
            
            f"📋 **الحسابات المتاحة للحذف:**\n"
            f"• اختر الحساب المراد حذفه من القائمة أدناه\n"
            f"• سيتم فصل الحساب وحذفه نهائياً\n\n"
            
            f"⚠️ **تحذير:**\n"
            f"• الحذف نهائي ولا يمكن التراجع عنه\n"
            f"• الحساب سيتوقف عن العمل فوراً\n"
            f"• سيتم إخراجه من جميع المكالمات\n\n"
            
            f"🎯 **اختر الحساب المراد حذفه:**"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def confirm_remove_assistant(self, user_id: int, assistant_id: int) -> Dict:
        """تأكيد حذف حساب مساعد"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            # الحصول على معلومات الحساب
            assistant_info = await db.get_assistant_by_id(assistant_id)
            if not assistant_info:
                return {
                    'success': False,
                    'message': "❌ لم يتم العثور على الحساب المحدد"
                }
            
            # حذف الحساب من قاعدة البيانات
            await db.remove_assistant(assistant_id)
            
            # إيقاف الحساب في tdlib_manager
            await tdlib_manager.remove_assistant(assistant_id)
            
            # إنهاء الجلسة
            if user_id in self.pending_sessions:
                del self.pending_sessions[user_id]
            
            keyboard = [
                [
                    {'text': '📋 عرض الحسابات المتبقية', 'callback_data': 'assistants_list'},
                    {'text': '➕ إضافة حساب جديد', 'callback_data': 'assistants_add'}
                ],
                [
                    {'text': '🔙 العودة لإدارة الحسابات', 'callback_data': 'admin_assistants'}
                ]
            ]
            
            message = (
                f"✅ **تم حذف الحساب المساعد بنجاح!**\n\n"
                
                f"🗑️ **الحساب المحذوف:**\n"
                f"📛 الاسم: `{assistant_info['name']}`\n"
                f"🆔 المعرف: `{assistant_id}`\n"
                f"⏰ تاريخ الحذف: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
                
                f"✅ **تم تنفيذ:**\n"
                f"• حذف الحساب من قاعدة البيانات\n"
                f"• إيقاف جميع اتصالات الحساب\n"
                f"• إخراجه من المكالمات النشطة\n"
                f"• تحديث قائمة الحسابات المساعدة\n\n"
                
                f"💡 يمكنك إضافة حسابات جديدة في أي وقت"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حذف الحساب المساعد: {e}")
            return {
                'success': False,
                'message': f"❌ فشل في حذف الحساب: {str(e)}"
            }
    
    async def show_assistants_list(self, user_id: int) -> Dict:
        """عرض قائمة الحسابات المساعدة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            assistants = await db.get_assistants()
            
            if not assistants:
                keyboard = [
                    [
                        {'text': '➕ إضافة حساب مساعد', 'callback_data': 'assistants_add'},
                        {'text': '🔙 العودة', 'callback_data': 'admin_assistants'}
                    ]
                ]
                
                return {
                    'success': True,
                    'message': "📋 **قائمة الحسابات المساعدة**\n\n❌ لا توجد حسابات مساعدة مضافة\n\n💡 أضف حساب مساعد للبدء",
                    'keyboard': keyboard,
                    'parse_mode': 'Markdown'
                }
            
            # تجميع معلومات الحسابات
            accounts_info = []
            for i, assistant in enumerate(assistants, 1):
                # التحقق من حالة الاتصال
                is_connected = tdlib_manager.is_assistant_connected(assistant['assistant_id'])
                
                # الحصول على معلومات إضافية
                calls_count = tdlib_manager.get_assistant_calls_count(assistant['assistant_id'])
                last_activity = assistant.get('last_activity', 'غير متاح')
                
                status_emoji = "🟢" if is_connected else "🔴"
                status_text = "متصل" if is_connected else "غير متصل"
                
                account_info = (
                    f"**{i}. {assistant['name']}**\n"
                    f"├ 🆔 المعرف: `{assistant['assistant_id']}`\n"
                    f"├ {status_emoji} الحالة: `{status_text}`\n"
                    f"├ 🎵 المكالمات النشطة: `{calls_count}`\n"
                    f"└ ⏰ آخر نشاط: `{last_activity}`\n"
                )
                accounts_info.append(account_info)
            
            # إنشاء أزرار إدارة سريعة
            keyboard = [
                [
                    {'text': '🔄 تحديث القائمة', 'callback_data': 'assistants_list'},
                    {'text': '📊 إحصائيات مفصلة', 'callback_data': 'assistants_detailed_stats'}
                ],
                [
                    {'text': '➕ إضافة حساب', 'callback_data': 'assistants_add'},
                    {'text': '🗑️ حذف حساب', 'callback_data': 'assistants_remove'}
                ],
                [
                    {'text': '🔄 إعادة التشغيل', 'callback_data': 'assistants_restart'},
                    {'text': '🧪 اختبار الحسابات', 'callback_data': 'assistants_test'}
                ],
                [
                    {'text': '🔙 العودة لإدارة الحسابات', 'callback_data': 'admin_assistants'}
                ]
            ]
            
            total_assistants = len(assistants)
            connected_count = sum(1 for a in assistants if tdlib_manager.is_assistant_connected(a['assistant_id']))
            
            message = (
                f"📋 **قائمة الحسابات المساعدة**\n\n"
                
                f"📊 **الملخص:**\n"
                f"🤖 إجمالي الحسابات: `{total_assistants}`\n"
                f"🟢 متصلة: `{connected_count}`\n"
                f"🔴 غير متصلة: `{total_assistants - connected_count}`\n\n"
                
                f"📱 **تفاصيل الحسابات:**\n\n"
                + "\n".join(accounts_info) + "\n\n"
                
                f"🔄 آخر تحديث: `{datetime.now().strftime('%H:%M:%S')}`"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في عرض قائمة الحسابات: {e}")
            return {
                'success': False,
                'message': "❌ حدث خطأ في عرض قائمة الحسابات"
            }
    
    async def restart_assistants(self, user_id: int) -> Dict:
        """إعادة تشغيل الحسابات المساعدة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            # إعادة تحميل الحسابات من قاعدة البيانات
            restart_result = await tdlib_manager.restart_assistants()
            
            # الحصول على إحصائيات بعد إعادة التشغيل
            stats = await self._get_assistants_stats()
            
            keyboard = [
                [
                    {'text': '📋 عرض الحسابات', 'callback_data': 'assistants_list'},
                    {'text': '🧪 اختبار الحسابات', 'callback_data': 'assistants_test'}
                ],
                [
                    {'text': '🔙 العودة لإدارة الحسابات', 'callback_data': 'admin_assistants'}
                ]
            ]
            
            message = (
                f"🔄 **تم إعادة تشغيل الحسابات المساعدة!**\n\n"
                
                f"✅ **نتائج إعادة التشغيل:**\n"
                f"🤖 إجمالي الحسابات: `{stats['total']}`\n"
                f"🟢 متصلة بنجاح: `{stats['connected']}`\n"
                f"🔴 فشل الاتصال: `{stats['disconnected']}`\n"
                f"⚡ نشطة ومتاحة: `{stats['active']}`\n\n"
                
                f"🔄 **العمليات المنفذة:**\n"
                f"• إعادة تحميل من قاعدة البيانات\n"
                f"• إعادة إنشاء الاتصالات\n"
                f"• تحديث حالة الحسابات\n"
                f"• فحص صحة الحسابات\n\n"
                
                f"⏰ **وقت التحديث:** `{datetime.now().strftime('%H:%M:%S')}`\n\n"
                
                f"💡 **ملاحظة:** قد تحتاج بعض الحسابات لوقت إضافي للاتصال"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إعادة تشغيل الحسابات: {e}")
            return {
                'success': False,
                'message': f"❌ فشل في إعادة تشغيل الحسابات: {str(e)}"
            }
    
    async def toggle_auto_leave(self, user_id: int) -> Dict:
        """تفعيل/تعطيل المغادرة التلقائية"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # تبديل الحالة
        self.auto_leave_enabled = not self.auto_leave_enabled
        self.save_auto_leave_settings()
        
        status = "🟢 مفعل" if self.auto_leave_enabled else "🔴 معطل"
        action = "تفعيل" if self.auto_leave_enabled else "تعطيل"
        
        keyboard = [
            [
                {'text': '⚙️ إعدادات المغادرة', 'callback_data': 'assistants_auto_leave_settings'},
                {'text': '🧪 اختبار النظام', 'callback_data': 'assistants_test_auto_leave'}
            ],
            [
                {'text': '🔙 العودة لإدارة الحسابات', 'callback_data': 'admin_assistants'}
            ]
        ]
        
        message = (
            f"🚪 **تم {action} المغادرة التلقائية!**\n\n"
            
            f"📊 **الحالة الحالية:** {status}\n"
            f"⏱️ **مدة عدم النشاط:** `{self.auto_leave_timeout // 60} دقائق`\n\n"
            
            f"💡 **كيف تعمل المغادرة التلقائية:**\n"
            f"• مراقبة نشاط الحسابات المساعدة\n"
            f"• عند عدم النشاط لفترة محددة\n"
            f"• مغادرة المجموعات والقنوات تلقائياً\n"
            f"• توفير الموارد وتحسين الأداء\n\n"
            
            f"🎯 **الفوائد:**\n"
            f"{'• تنظيف تلقائي للمجموعات غير النشطة' if self.auto_leave_enabled else '• لا توجد مغادرة تلقائية'}\n"
            f"{'• توفير موارد النظام' if self.auto_leave_enabled else '• الحسابات تبقى في جميع المجموعات'}\n"
            f"{'• تقليل احتمالية المشاكل' if self.auto_leave_enabled else '• قد تحتاج لتنظيف يدوي'}"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def check_no_assistants_and_notify(self, user_id: int, user_name: str, chat_id: int) -> bool:
        """فحص عدم وجود حسابات مساعدة وإرسال تنبيه"""
        try:
            # فحص الحسابات المساعدة النشطة
            active_assistants = tdlib_manager.get_connected_assistants_count()
            
            if active_assistants == 0:
                # إرسال رسالة للمستخدم
                user_message = (
                    f"⚠️ **عذراً {user_name}**\n\n"
                    f"🤖 **خلل في النظام:**\n"
                    f"لا توجد حسابات مساعدة نشطة حالياً\n\n"
                    f"📞 **الحلول:**\n"
                    f"• تواصل مع مطور البوت\n"
                    f"• انتظر حتى يتم إصلاح المشكلة\n"
                    f"• جرب مرة أخرى بعد قليل\n\n"
                    f"🔧 **تم إرسال تنبيه للمطور**"
                )
                
                # إرسال رسالة للمستخدم
                bot_client = tdlib_manager.bot_client
                if bot_client and bot_client.is_connected:
                    await bot_client.send_message(chat_id, user_message)
                
                # إرسال تنبيه للمطور
                developer_alert = (
                    f"🚨 **تنبيه: لا توجد حسابات مساعدة نشطة!**\n\n"
                    
                    f"👤 **طلب من:**\n"
                    f"الاسم: `{user_name}`\n"
                    f"المعرف: `{user_id}`\n"
                    f"المجموعة: `{chat_id}`\n\n"
                    
                    f"⏰ **الوقت:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                    
                    f"🔧 **مطلوب:**\n"
                    f"• فحص الحسابات المساعدة\n"
                    f"• إعادة تشغيل النظام إذا لزم الأمر\n"
                    f"• التأكد من اتصال الحسابات\n\n"
                    
                    f"📱 استخدم `/admin` ← إدارة الحسابات المساعدة"
                )
                
                # إرسال للمطور
                if bot_client and bot_client.is_connected:
                    await bot_client.send_message(config.OWNER_ID, developer_alert)
                
                return True  # يوجد مشكلة
            
            return False  # لا توجد مشكلة
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في فحص الحسابات المساعدة: {e}")
            return False
    
    # الدوال المساعدة
    async def _get_assistants_stats(self) -> Dict:
        """الحصول على إحصائيات الحسابات المساعدة"""
        try:
            total = tdlib_manager.get_assistants_count()
            connected = tdlib_manager.get_connected_assistants_count()
            
            # حساب النشطة (المتصلة وليس لديها مشاكل)
            active = 0
            in_calls = 0
            
            for assistant in tdlib_manager.assistants:
                if assistant.is_connected:
                    active += 1
                    in_calls += len(assistant.active_calls)
            
            return {
                'total': total,
                'connected': connected,
                'disconnected': total - connected,
                'active': active,
                'in_calls': in_calls
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حساب إحصائيات الحسابات: {e}")
            return {
                'total': 0, 'connected': 0, 'disconnected': 0, 
                'active': 0, 'in_calls': 0
            }
    
    def _validate_session_string(self, session_string: str) -> bool:
        """التحقق من صحة session string"""
        try:
            # التحقق الأساسي من طول وشكل session string
            if len(session_string) < 100:
                return False
            
            # يمكن إضافة فحص أكثر تفصيلاً لـ TDLib session format
            # هذا فحص أساسي
            
            return True
            
        except:
            return False
    
    async def _auto_leave_task(self):
        """مهمة المغادرة التلقائية"""
        while True:
            try:
                if self.auto_leave_enabled:
                    await self._check_and_leave_inactive_chats()
                
                # فحص كل دقيقة
                await asyncio.sleep(60)
                
            except Exception as e:
                LOGGER(__name__).error(f"خطأ في مهمة المغادرة التلقائية: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_leave_inactive_chats(self):
        """فحص ومغادرة المحادثات غير النشطة"""
        try:
            current_time = time.time()
            
            for assistant in tdlib_manager.assistants:
                if not assistant.is_connected:
                    continue
                
                # فحص آخر نشاط للحساب
                if (current_time - assistant.last_activity) > self.auto_leave_timeout:
                    # الحساب غير نشط، مغادرة المحادثات
                    await self._leave_assistant_chats(assistant)
                    
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في فحص المحادثات غير النشطة: {e}")
    
    async def _leave_assistant_chats(self, assistant):
        """مغادرة محادثات الحساب المساعد"""
        try:
            # الحصول على قائمة المحادثات
            chats = await assistant.client.call_method('getChats', {
                'chat_list': {'@type': 'chatListMain'},
                'limit': 100
            })
            
            for chat_id in chats.get('chat_ids', []):
                try:
                    # مغادرة المحادثة
                    await assistant.client.call_method('leaveChat', {
                        'chat_id': chat_id
                    })
                    
                    # تأخير قصير بين المغادرات
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    LOGGER(__name__).debug(f"خطأ في مغادرة المحادثة {chat_id}: {e}")
            
            LOGGER(__name__).info(f"تم تنظيف محادثات الحساب المساعد {assistant.assistant_id}")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في مغادرة محادثات الحساب المساعد: {e}")

# إنشاء مثيل عام لمعالج الحسابات المساعدة
assistants_handler = AssistantsHandler()