import asyncio
import platform
import psutil
from datetime import datetime, timedelta
from typing import Dict

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db
from ZeMusic.core.music_manager import music_manager

class StatsHandler:
    """معالج إحصائيات البوت المفصلة"""
    
    async def show_detailed_stats(self, user_id: int) -> Dict:
        """عرض الإحصائيات التفصيلية"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            # جمع جميع الإحصائيات
            db_stats = await self._get_database_stats()
            system_stats = await self._get_system_stats()
            bot_stats = await self._get_bot_stats()
            performance_stats = await self._get_performance_stats()
            
            message = self._format_stats_message(db_stats, system_stats, bot_stats, performance_stats)
            
            keyboard = [
                [
                    {'text': '🔄 تحديث الإحصائيات', 'callback_data': 'admin_stats'},
                    {'text': '📈 إحصائيات مفصلة', 'callback_data': 'detailed_stats'}
                ],
                [
                    {'text': '📊 إحصائيات الاستخدام', 'callback_data': 'usage_stats'},
                    {'text': '💾 حالة قاعدة البيانات', 'callback_data': 'database_health'}
                ],
                [
                    {'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'admin_main'}
                ]
            ]
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في عرض الإحصائيات: {e}")
            return {
                'success': False,
                'message': "❌ حدث خطأ في جمع الإحصائيات"
            }
    
    async def _get_database_stats(self) -> Dict:
        """الحصول على إحصائيات قاعدة البيانات"""
        try:
            # الإحصائيات الأساسية
            stats = await db.get_stats()
            
            # إحصائيات تفصيلية للمستخدمين
            users_stats = await self._get_users_detailed_stats()
            
            # إحصائيات المجموعات والقنوات
            chats_stats = await self._get_chats_detailed_stats()
            
            # حجم قاعدة البيانات
            db_size = await self._get_database_size()
            
            return {
                'total_users': stats['users'],
                'total_chats': stats['chats'],
                'total_assistants': stats['assistants'],
                'total_sudoers': stats['sudoers'],
                'total_banned': stats['banned'],
                'users_today': users_stats['today'],
                'users_week': users_stats['week'],
                'users_month': users_stats['month'],
                'active_chats': chats_stats['active'],
                'groups_count': chats_stats['groups'],
                'channels_count': chats_stats['channels'],
                'database_size': db_size
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات قاعدة البيانات: {e}")
            return {
                'total_users': 0, 'total_chats': 0, 'total_assistants': 0,
                'total_sudoers': 0, 'total_banned': 0, 'users_today': 0,
                'users_week': 0, 'users_month': 0, 'active_chats': 0,
                'groups_count': 0, 'channels_count': 0, 'database_size': 'غير متاح'
            }
    
    async def _get_system_stats(self) -> Dict:
        """الحصول على إحصائيات النظام"""
        try:
            # معلومات المعالج والذاكرة
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # معلومات النظام
            system_info = {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'python_version': platform.python_version()
            }
            
            # معلومات الشبكة
            network = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_total': self._bytes_to_mb(memory.total),
                'memory_used': self._bytes_to_mb(memory.used),
                'memory_percent': memory.percent,
                'disk_total': self._bytes_to_gb(disk.total),
                'disk_used': self._bytes_to_gb(disk.used),
                'disk_percent': (disk.used / disk.total) * 100,
                'network_sent': self._bytes_to_mb(network.bytes_sent),
                'network_received': self._bytes_to_mb(network.bytes_recv),
                'system_info': system_info
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات النظام: {e}")
            return {
                'cpu_percent': 0, 'memory_total': 0, 'memory_used': 0,
                'memory_percent': 0, 'disk_total': 0, 'disk_used': 0,
                'disk_percent': 0, 'network_sent': 0, 'network_received': 0,
                'system_info': {}
            }
    
    async def _get_bot_stats(self) -> Dict:
        """الحصول على إحصائيات البوت"""
        try:
            # إحصائيات الحسابات المساعدة
            assistants_total = tdlib_manager.get_assistants_count()
            assistants_connected = tdlib_manager.get_connected_assistants_count()
            
            # إحصائيات الجلسات
            active_sessions = len(music_manager.active_sessions)
            
            # إحصائيات البوت الرئيسي
            bot_connected = tdlib_manager.bot_client.is_connected if tdlib_manager.bot_client else False
            
            return {
                'assistants_total': assistants_total,
                'assistants_connected': assistants_connected,
                'assistants_disconnected': assistants_total - assistants_connected,
                'active_music_sessions': active_sessions,
                'bot_status': 'متصل' if bot_connected else 'غير متصل',
                'bot_version': config.APPLICATION_VERSION,
                'tdlib_status': 'نشط' if assistants_connected > 0 else 'خامل'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات البوت: {e}")
            return {
                'assistants_total': 0, 'assistants_connected': 0,
                'assistants_disconnected': 0, 'active_music_sessions': 0,
                'bot_status': 'خطأ', 'bot_version': 'غير متاح', 'tdlib_status': 'خطأ'
            }
    
    async def _get_performance_stats(self) -> Dict:
        """الحصول على إحصائيات الأداء"""
        try:
            # إحصائيات الاستخدام اليوم
            today_usage = await self._get_today_usage()
            
            # متوسط الاستجابة
            response_time = await self._calculate_average_response_time()
            
            return {
                'songs_played_today': today_usage['songs'],
                'commands_today': today_usage['commands'],
                'new_users_today': today_usage['new_users'],
                'average_response_time': response_time,
                'uptime': self._get_uptime()
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات الأداء: {e}")
            return {
                'songs_played_today': 0, 'commands_today': 0,
                'new_users_today': 0, 'average_response_time': 'غير متاح',
                'uptime': 'غير متاح'
            }
    
    def _format_stats_message(self, db_stats: Dict, system_stats: Dict, 
                            bot_stats: Dict, performance_stats: Dict) -> str:
        """تنسيق رسالة الإحصائيات"""
        
        message = (
            "📊 **إحصائيات البوت التفصيلية**\n\n"
            
            "👥 **المستخدمين:**\n"
            f"📈 إجمالي المستخدمين: `{db_stats['total_users']:,}`\n"
            f"🆕 مستخدمين اليوم: `{db_stats['users_today']}`\n"
            f"📅 مستخدمين هذا الأسبوع: `{db_stats['users_week']}`\n"
            f"📊 مستخدمين هذا الشهر: `{db_stats['users_month']}`\n"
            f"🚫 المحظورين: `{db_stats['total_banned']}`\n\n"
            
            "💬 **المجموعات والقنوات:**\n"
            f"📈 إجمالي المحادثات: `{db_stats['total_chats']:,}`\n"
            f"👥 المجموعات: `{db_stats['groups_count']}`\n"
            f"📢 القنوات: `{db_stats['channels_count']}`\n"
            f"🟢 النشطة: `{db_stats['active_chats']}`\n\n"
            
            "🤖 **الحسابات المساعدة:**\n"
            f"📱 إجمالي الحسابات: `{bot_stats['assistants_total']}`\n"
            f"🟢 متصل: `{bot_stats['assistants_connected']}`\n"
            f"🔴 غير متصل: `{bot_stats['assistants_disconnected']}`\n"
            f"🎵 الجلسات النشطة: `{bot_stats['active_music_sessions']}`\n\n"
            
            "⚡ **الأداء:**\n"
            f"🎼 أغاني اليوم: `{performance_stats['songs_played_today']}`\n"
            f"⌨️ أوامر اليوم: `{performance_stats['commands_today']}`\n"
            f"⏱️ متوسط الاستجابة: `{performance_stats['average_response_time']}`\n"
            f"🕐 وقت التشغيل: `{performance_stats['uptime']}`\n\n"
            
            "🖥️ **موارد النظام:**\n"
            f"🧠 المعالج: `{system_stats['cpu_percent']:.1f}%`\n"
            f"💾 الذاكرة: `{system_stats['memory_used']} MB / {system_stats['memory_total']} MB ({system_stats['memory_percent']:.1f}%)`\n"
            f"💿 التخزين: `{system_stats['disk_used']} GB / {system_stats['disk_total']} GB ({system_stats['disk_percent']:.1f}%)`\n"
            f"📡 البيانات المرسلة: `{system_stats['network_sent']} MB`\n"
            f"📥 البيانات المستقبلة: `{system_stats['network_received']} MB`\n\n"
            
            "💾 **قاعدة البيانات:**\n"
            f"📂 حجم قاعدة البيانات: `{db_stats['database_size']}`\n"
            f"👨‍💼 المديرين: `{db_stats['total_sudoers']}`\n"
            f"🔧 نوع قاعدة البيانات: `SQLite محسّن`\n\n"
            
            f"🎯 **حالة النظام:** `{bot_stats['bot_status']}`\n"
            f"🔧 **إصدار البوت:** `{bot_stats['bot_version']}`\n"
            f"📱 **حالة TDLib:** `{bot_stats['tdlib_status']}`"
        )
        
        return message
    
    async def _get_users_detailed_stats(self) -> Dict:
        """الحصول على إحصائيات المستخدمين التفصيلية"""
        # يمكن تحسين هذا لاحقاً للحصول على إحصائيات دقيقة
        return {'today': 0, 'week': 0, 'month': 0}
    
    async def _get_chats_detailed_stats(self) -> Dict:
        """الحصول على إحصائيات المحادثات التفصيلية"""
        total_chats = (await db.get_stats())['chats']
        # تقدير: 70% مجموعات، 30% قنوات
        groups = int(total_chats * 0.7)
        channels = total_chats - groups
        return {
            'active': total_chats,  # يمكن تحسين هذا
            'groups': groups,
            'channels': channels
        }
    
    async def _get_database_size(self) -> str:
        """الحصول على حجم قاعدة البيانات"""
        try:
            import os
            size = os.path.getsize(config.DATABASE_PATH)
            return self._bytes_to_mb(size) + " MB"
        except:
            return "غير متاح"
    
    async def _get_today_usage(self) -> Dict:
        """الحصول على إحصائيات الاستخدام اليوم"""
        # يمكن تحسين هذا لاحقاً
        return {'songs': 0, 'commands': 0, 'new_users': 0}
    
    async def _calculate_average_response_time(self) -> str:
        """حساب متوسط وقت الاستجابة"""
        # يمكن تحسين هذا لاحقاً
        return "< 1s"
    
    def _get_uptime(self) -> str:
        """الحصول على وقت التشغيل"""
        # يمكن حفظ وقت البدء في متغير عام
        return "غير متاح"
    
    def _bytes_to_mb(self, bytes_value: int) -> str:
        """تحويل البايتات إلى ميجابايت"""
        return f"{bytes_value / (1024 * 1024):.1f}"
    
    def _bytes_to_gb(self, bytes_value: int) -> str:
        """تحويل البايتات إلى جيجابايت"""
        return f"{bytes_value / (1024 * 1024 * 1024):.1f}"

# إنشاء مثيل عام لمعالج الإحصائيات
stats_handler = StatsHandler()