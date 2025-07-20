import asyncio
import json
from typing import Dict, List, Optional

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db

class AdminPanel:
    """لوحة أوامر المطور الرئيسية"""
    
    def __init__(self):
        self.active_sessions = {}  # جلسات المطور النشطة
        
    async def show_main_panel(self, user_id: int) -> Dict:
        """عرض اللوحة الرئيسية لأوامر المطور"""
        if user_id != config.OWNER_ID:
            return {
                'success': False,
                'message': "❌ هذا الأمر مخصص لمطور البوت فقط"
            }
        
        # الحصول على إحصائيات سريعة
        quick_stats = await self._get_quick_stats()
        
        keyboard = [
            [
                {'text': '📊 الإحصائيات', 'callback_data': 'admin_stats'},
                {'text': '📢 الإذاعة', 'callback_data': 'admin_broadcast'}
            ],
            [
                {'text': '🔐 الاشتراك الإجباري', 'callback_data': 'admin_force_subscribe'},
                {'text': '📱 إدارة الحسابات المساعدة', 'callback_data': 'admin_assistants'}
            ],
            [
                {'text': '💬 إدارة المجموعات', 'callback_data': 'admin_groups'},
                {'text': '🔧 صيانة النظام', 'callback_data': 'admin_maintenance'}
            ],
            [
                {'text': '⚙️ إعدادات البوت', 'callback_data': 'admin_settings'},
                {'text': '📋 سجلات النظام', 'callback_data': 'admin_logs'}
            ],
            [
                {'text': '🔄 إعادة تشغيل', 'callback_data': 'admin_restart'},
                {'text': '🛑 إيقاف البوت', 'callback_data': 'admin_shutdown'}
            ]
        ]
        
        message = (
            "🎛️ **لوحة أوامر المطور**\n\n"
            f"👋 أهلاً وسهلاً **{config.BOT_NAME}** Developer\n\n"
            
            f"📊 **نظرة سريعة:**\n"
            f"👤 المستخدمين: `{quick_stats['users']}`\n"
            f"💬 المجموعات: `{quick_stats['groups']}`\n"
            f"📢 القنوات: `{quick_stats['channels']}`\n"
            f"🤖 الحسابات المساعدة: `{quick_stats['assistants_connected']}/{quick_stats['assistants_total']}`\n"
            f"🎵 الجلسات النشطة: `{quick_stats['active_sessions']}`\n\n"
            
            f"🔧 **حالة النظام:** `{quick_stats['system_status']}`\n"
            f"⚡ **وقت التشغيل:** `{quick_stats['uptime']}`\n\n"
            
            "اختر الإجراء المطلوب:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def handle_callback(self, user_id: int, callback_data: str, message_id: int = None) -> Dict:
        """معالج الضغط على الأزرار"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # توجيه إلى المعالج المناسب
        if callback_data == 'admin_stats':
            from ZeMusic.plugins.owner.stats_handler import stats_handler
            return await stats_handler.show_detailed_stats(user_id)
            
        elif callback_data == 'admin_broadcast':
            from ZeMusic.plugins.owner.broadcast_handler import broadcast_handler
            return await broadcast_handler.show_broadcast_menu(user_id)
            
        elif callback_data == 'admin_force_subscribe':
            from ZeMusic.plugins.owner.force_subscribe_handler import force_subscribe_handler
            return await force_subscribe_handler.show_force_subscribe_menu(user_id)
            
        elif callback_data == 'admin_assistants':
            from ZeMusic.plugins.owner.owner_panel import owner_panel
            return await owner_panel.show_assistants_panel(user_id)
            
        elif callback_data == 'admin_main':
            return await self.show_main_panel(user_id)
            
        else:
            return {
                'success': True,
                'message': f"🔧 **{callback_data}**\n\nهذه الميزة قيد التطوير...",
                'keyboard': [[{'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'admin_main'}]]
            }
    
    async def _get_quick_stats(self) -> Dict:
        """الحصول على إحصائيات سريعة"""
        try:
            # إحصائيات قاعدة البيانات
            stats = await db.get_stats()
            
            # إحصائيات الحسابات المساعدة
            assistants_total = tdlib_manager.get_assistants_count()
            assistants_connected = tdlib_manager.get_connected_assistants_count()
            
            # إحصائيات الجلسات النشطة
            from ZeMusic.core.music_manager import music_manager
            active_sessions = len(music_manager.active_sessions)
            
            # تفريق المجموعات والقنوات
            groups_count, channels_count = await self._get_groups_channels_count()
            
            return {
                'users': stats['users'],
                'groups': groups_count,
                'channels': channels_count,
                'assistants_total': assistants_total,
                'assistants_connected': assistants_connected,
                'active_sessions': active_sessions,
                'system_status': 'نشط' if assistants_connected > 0 else 'محدود',
                'uptime': self._get_uptime()
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على الإحصائيات: {e}")
            return {
                'users': 0, 'groups': 0, 'channels': 0,
                'assistants_total': 0, 'assistants_connected': 0,
                'active_sessions': 0, 'system_status': 'خطأ', 'uptime': 'غير متاح'
            }
    
    async def _get_groups_channels_count(self) -> tuple:
        """الحصول على عدد المجموعات والقنوات منفصلة"""
        try:
            # هنا يمكن إضافة منطق للتمييز بين المجموعات والقنوات
            # حالياً نستخدم العدد الإجمالي مقسوم
            total_chats = (await db.get_stats())['chats']
            # تقدير: 70% مجموعات، 30% قنوات
            groups = int(total_chats * 0.7)
            channels = total_chats - groups
            return groups, channels
        except:
            return 0, 0
    
    def _get_uptime(self) -> str:
        """الحصول على وقت التشغيل"""
        # يمكن حفظ وقت البدء في متغير عام وحساب الفرق
        return "غير متاح"
    
    async def clear_session(self, user_id: int):
        """مسح جلسة المطور"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

# إنشاء مثيل عام للوحة المطور
admin_panel = AdminPanel()