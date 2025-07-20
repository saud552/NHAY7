import asyncio
import platform
import psutil
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Tuple

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db
from ZeMusic.core.music_manager import music_manager

class StatsHandler:
    """معالج إحصائيات البوت المفصلة والدقيقة"""
    
    def __init__(self):
        self.cache_duration = 30  # مدة الكاش بالثواني
        self.last_cache_time = 0
        self.cached_stats = None
        
    async def show_detailed_stats(self, user_id: int) -> Dict:
        """عرض الإحصائيات التفصيلية والدقيقة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            # جمع الإحصائيات الدقيقة والمحدثة
            stats_data = await self._get_comprehensive_stats()
            
            message = self._format_comprehensive_stats_message(stats_data)
            
            keyboard = [
                [
                    {'text': '🔄 تحديث الإحصائيات', 'callback_data': 'admin_stats'},
                    {'text': '📈 تفاصيل إضافية', 'callback_data': 'detailed_stats_extra'}
                ],
                [
                    {'text': '👥 تفاصيل المستخدمين', 'callback_data': 'users_breakdown'},
                    {'text': '💬 تفاصيل المجموعات', 'callback_data': 'chats_breakdown'}
                ],
                [
                    {'text': '🎵 إحصائيات الموسيقى', 'callback_data': 'music_stats'},
                    {'text': '🤖 حالة الحسابات المساعدة', 'callback_data': 'assistants_status'}
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
                'message': "❌ حدث خطأ في جمع الإحصائيات، يرجى المحاولة مرة أخرى"
            }
    
    async def _get_comprehensive_stats(self) -> Dict:
        """الحصول على إحصائيات شاملة ودقيقة"""
        current_time = asyncio.get_event_loop().time()
        
        # استخدام الكاش إذا كان حديث
        if (self.cached_stats and 
            current_time - self.last_cache_time < self.cache_duration):
            return self.cached_stats
        
        try:
            # جمع الإحصائيات من مصادر متعددة
            users_stats = await self._get_precise_users_stats()
            chats_stats = await self._get_precise_chats_stats()
            system_stats = await self._get_detailed_system_stats()
            bot_stats = await self._get_comprehensive_bot_stats()
            database_stats = await self._get_database_health_stats()
            performance_stats = await self._get_performance_metrics()
            
            comprehensive_stats = {
                'users': users_stats,
                'chats': chats_stats,
                'system': system_stats,
                'bot': bot_stats,
                'database': database_stats,
                'performance': performance_stats,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # تحديث الكاش
            self.cached_stats = comprehensive_stats
            self.last_cache_time = current_time
            
            return comprehensive_stats
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في جمع الإحصائيات الشاملة: {e}")
            raise
    
    async def _get_precise_users_stats(self) -> Dict:
        """الحصول على إحصائيات المستخدمين الدقيقة"""
        try:
            # الاتصال المباشر بقاعدة البيانات لإحصائيات دقيقة
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # إجمالي المستخدمين
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                # المستخدمين النشطين (آخر 7 أيام)
                week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("SELECT COUNT(*) FROM users WHERE last_seen >= ?", (week_ago,))
                active_users_week = cursor.fetchone()[0]
                
                # المستخدمين الجدد اليوم
                today = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("SELECT COUNT(*) FROM users WHERE join_date >= ?", (today,))
                new_users_today = cursor.fetchone()[0]
                
                # المستخدمين الجدد هذا الأسبوع
                cursor.execute("SELECT COUNT(*) FROM users WHERE join_date >= ?", (week_ago,))
                new_users_week = cursor.fetchone()[0]
                
                # المستخدمين المحظورين
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
                banned_users = cursor.fetchone()[0]
                
                # المديرين
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_sudo = 1")
                sudo_users = cursor.fetchone()[0]
                
                # أكثر المستخدمين نشاطاً
                cursor.execute("""
                    SELECT user_id, COUNT(*) as activity_count 
                    FROM usage_stats 
                    WHERE timestamp >= ? 
                    GROUP BY user_id 
                    ORDER BY activity_count DESC 
                    LIMIT 5
                """, (week_ago,))
                most_active = cursor.fetchall()
                
                return {
                    'total': total_users,
                    'active_week': active_users_week,
                    'new_today': new_users_today,
                    'new_week': new_users_week,
                    'banned': banned_users,
                    'sudoers': sudo_users,
                    'most_active': most_active,
                    'private_chats': total_users  # كل المستخدمين = محادثات خاصة
                }
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات المستخدمين: {e}")
            return {
                'total': 0, 'active_week': 0, 'new_today': 0,
                'new_week': 0, 'banned': 0, 'sudoers': 0,
                'most_active': [], 'private_chats': 0
            }
    
    async def _get_precise_chats_stats(self) -> Dict:
        """الحصول على إحصائيات المجموعات والقنوات الدقيقة"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # إجمالي المحادثات
                cursor.execute("SELECT COUNT(*) FROM chats")
                total_chats = cursor.fetchone()[0]
                
                # المحادثات النشطة (آخر 24 ساعة)
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("SELECT COUNT(*) FROM chats WHERE last_active >= ?", (yesterday,))
                active_chats = cursor.fetchone()[0]
                
                # تصنيف المحادثات حسب النوع
                cursor.execute("SELECT chat_type, COUNT(*) FROM chats GROUP BY chat_type")
                chat_types = cursor.fetchall()
                
                groups_count = 0
                channels_count = 0
                supergroups_count = 0
                
                for chat_type, count in chat_types:
                    if chat_type in ['group', 'supergroup']:
                        if chat_type == 'supergroup':
                            supergroups_count += count
                        else:
                            groups_count += count
                    elif chat_type == 'channel':
                        channels_count += count
                
                # المحادثات المحظورة
                cursor.execute("SELECT COUNT(*) FROM chats WHERE is_blacklisted = 1")
                blacklisted_chats = cursor.fetchone()[0]
                
                # أكثر المجموعات نشاطاً
                cursor.execute("""
                    SELECT chat_id, COUNT(*) as activity_count 
                    FROM usage_stats 
                    WHERE timestamp >= ? AND chat_id < 0
                    GROUP BY chat_id 
                    ORDER BY activity_count DESC 
                    LIMIT 5
                """, (yesterday,))
                most_active_chats = cursor.fetchall()
                
                return {
                    'total': total_chats,
                    'active_24h': active_chats,
                    'groups': groups_count,
                    'supergroups': supergroups_count,
                    'channels': channels_count,
                    'blacklisted': blacklisted_chats,
                    'most_active': most_active_chats
                }
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات المحادثات: {e}")
            return {
                'total': 0, 'active_24h': 0, 'groups': 0,
                'supergroups': 0, 'channels': 0, 'blacklisted': 0,
                'most_active': []
            }
    
    async def _get_detailed_system_stats(self) -> Dict:
        """الحصول على إحصائيات النظام المفصلة"""
        try:
            # معلومات المعالج
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # معلومات الذاكرة
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # معلومات التخزين
            disk = psutil.disk_usage('/')
            
            # معلومات الشبكة
            network = psutil.net_io_counters()
            
            # معلومات العمليات
            process = psutil.Process()
            
            return {
                'cpu': {
                    'percent': round(cpu_percent, 2),
                    'count': cpu_count,
                    'frequency': round(cpu_freq.current, 2) if cpu_freq else 0
                },
                'memory': {
                    'total': self._bytes_to_mb(memory.total),
                    'used': self._bytes_to_mb(memory.used),
                    'available': self._bytes_to_mb(memory.available),
                    'percent': round(memory.percent, 2)
                },
                'swap': {
                    'total': self._bytes_to_mb(swap.total),
                    'used': self._bytes_to_mb(swap.used),
                    'percent': round(swap.percent, 2)
                },
                'disk': {
                    'total': self._bytes_to_gb(disk.total),
                    'used': self._bytes_to_gb(disk.used),
                    'free': self._bytes_to_gb(disk.free),
                    'percent': round((disk.used / disk.total) * 100, 2)
                },
                'network': {
                    'bytes_sent': self._bytes_to_mb(network.bytes_sent),
                    'bytes_recv': self._bytes_to_mb(network.bytes_recv),
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'process': {
                    'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                    'cpu_percent': round(process.cpu_percent(), 2),
                    'threads': process.num_threads()
                },
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'python_version': platform.python_version()
                }
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات النظام: {e}")
            return {}
    
    async def _get_comprehensive_bot_stats(self) -> Dict:
        """الحصول على إحصائيات البوت الشاملة"""
        try:
            # إحصائيات الحسابات المساعدة
            assistants_total = tdlib_manager.get_assistants_count()
            assistants_connected = tdlib_manager.get_connected_assistants_count()
            
            # إحصائيات الجلسات الموسيقية
            active_sessions = len(music_manager.active_sessions)
            
            # حالة البوت الرئيسي
            bot_connected = (tdlib_manager.bot_client and 
                           tdlib_manager.bot_client.is_connected)
            
            # إحصائيات تفصيلية للحسابات المساعدة
            assistants_details = []
            for assistant in tdlib_manager.assistants:
                assistant_info = {
                    'id': assistant.assistant_id,
                    'connected': assistant.is_connected,
                    'active_calls': assistant.get_active_calls_count(),
                    'last_activity': assistant.last_activity
                }
                assistants_details.append(assistant_info)
            
            # إحصائيات الاستخدام من قاعدة البيانات
            usage_stats = await self._get_usage_statistics()
            
            return {
                'main_bot': {
                    'connected': bot_connected,
                    'version': config.APPLICATION_VERSION,
                    'uptime': self._get_uptime()
                },
                'assistants': {
                    'total': assistants_total,
                    'connected': assistants_connected,
                    'disconnected': assistants_total - assistants_connected,
                    'details': assistants_details
                },
                'music': {
                    'active_sessions': active_sessions,
                    'total_plays_today': usage_stats['plays_today'],
                    'total_plays_week': usage_stats['plays_week']
                },
                'commands': {
                    'today': usage_stats['commands_today'],
                    'week': usage_stats['commands_week'],
                    'most_used': usage_stats['most_used_commands']
                }
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات البوت: {e}")
            return {}
    
    async def _get_database_health_stats(self) -> Dict:
        """الحصول على إحصائيات صحة قاعدة البيانات"""
        try:
            # حجم قاعدة البيانات
            db_size = os.path.getsize(config.DATABASE_PATH)
            
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # عدد الجداول
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
                tables_count = cursor.fetchone()[0]
                
                # إحصائيات كل جدول
                table_stats = {}
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    table_stats[table_name] = row_count
                
                # فحص سلامة قاعدة البيانات
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                return {
                    'size_mb': round(db_size / (1024 * 1024), 2),
                    'tables_count': tables_count,
                    'table_stats': table_stats,
                    'integrity': integrity_result == 'ok',
                    'cache_enabled': config.ENABLE_DATABASE_CACHE,
                    'path': config.DATABASE_PATH
                }
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات قاعدة البيانات: {e}")
            return {}
    
    async def _get_performance_metrics(self) -> Dict:
        """الحصول على مقاييس الأداء"""
        try:
            # وقت الاستجابة التقديري
            start_time = asyncio.get_event_loop().time()
            await db.get_stats()  # اختبار سرعة قاعدة البيانات
            db_response_time = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
            
            return {
                'db_response_ms': db_response_time,
                'memory_usage_mb': self._get_memory_usage(),
                'cpu_usage_percent': psutil.Process().cpu_percent(),
                'load_average': self._get_load_average()
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في مقاييس الأداء: {e}")
            return {}
    
    async def _get_usage_statistics(self) -> Dict:
        """الحصول على إحصائيات الاستخدام"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                today = datetime.now().strftime("%Y-%m-%d")
                week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                
                # تشغيل الموسيقى اليوم
                cursor.execute("""
                    SELECT COUNT(*) FROM usage_stats 
                    WHERE action_type = 'play_music' AND timestamp >= ?
                """, (today,))
                plays_today = cursor.fetchone()[0]
                
                # تشغيل الموسيقى هذا الأسبوع
                cursor.execute("""
                    SELECT COUNT(*) FROM usage_stats 
                    WHERE action_type = 'play_music' AND timestamp >= ?
                """, (week_ago,))
                plays_week = cursor.fetchone()[0]
                
                # الأوامر اليوم
                cursor.execute("""
                    SELECT COUNT(*) FROM usage_stats 
                    WHERE timestamp >= ?
                """, (today,))
                commands_today = cursor.fetchone()[0]
                
                # الأوامر هذا الأسبوع
                cursor.execute("""
                    SELECT COUNT(*) FROM usage_stats 
                    WHERE timestamp >= ?
                """, (week_ago,))
                commands_week = cursor.fetchone()[0]
                
                # أكثر الأوامر استخداماً
                cursor.execute("""
                    SELECT action_type, COUNT(*) as count 
                    FROM usage_stats 
                    WHERE timestamp >= ?
                    GROUP BY action_type 
                    ORDER BY count DESC 
                    LIMIT 5
                """, (week_ago,))
                most_used = cursor.fetchall()
                
                return {
                    'plays_today': plays_today,
                    'plays_week': plays_week,
                    'commands_today': commands_today,
                    'commands_week': commands_week,
                    'most_used_commands': most_used
                }
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات الاستخدام: {e}")
            return {
                'plays_today': 0, 'plays_week': 0,
                'commands_today': 0, 'commands_week': 0,
                'most_used_commands': []
            }
    
    def _format_comprehensive_stats_message(self, stats_data: Dict) -> str:
        """تنسيق رسالة الإحصائيات الشاملة"""
        
        users = stats_data.get('users', {})
        chats = stats_data.get('chats', {})
        system = stats_data.get('system', {})
        bot = stats_data.get('bot', {})
        database = stats_data.get('database', {})
        performance = stats_data.get('performance', {})
        
        message = (
            "📊 **إحصائيات البوت التفصيلية والدقيقة**\n\n"
            
            "👥 **المستخدمين (المحادثات الخاصة):**\n"
            f"📈 إجمالي المستخدمين: `{users.get('total', 0):,}`\n"
            f"🟢 نشطين هذا الأسبوع: `{users.get('active_week', 0):,}`\n"
            f"🆕 مستخدمين جدد اليوم: `{users.get('new_today', 0)}`\n"
            f"📅 مستخدمين جدد هذا الأسبوع: `{users.get('new_week', 0)}`\n"
            f"🚫 محظورين: `{users.get('banned', 0)}`\n"
            f"👨‍💼 مديرين: `{users.get('sudoers', 0)}`\n\n"
            
            "💬 **المجموعات والقنوات:**\n"
            f"📊 إجمالي المحادثات: `{chats.get('total', 0):,}`\n"
            f"👥 مجموعات عادية: `{chats.get('groups', 0)}`\n"
            f"👥 مجموعات كبيرة: `{chats.get('supergroups', 0)}`\n"
            f"📢 قنوات: `{chats.get('channels', 0)}`\n"
            f"🟢 نشطة (24 ساعة): `{chats.get('active_24h', 0)}`\n"
            f"🚫 محظورة: `{chats.get('blacklisted', 0)}`\n\n"
            
            "🤖 **الحسابات المساعدة:**\n"
            f"📱 إجمالي الحسابات: `{bot.get('assistants', {}).get('total', 0)}`\n"
            f"🟢 متصل: `{bot.get('assistants', {}).get('connected', 0)}`\n"
            f"🔴 غير متصل: `{bot.get('assistants', {}).get('disconnected', 0)}`\n"
            f"🎵 جلسات موسيقية نشطة: `{bot.get('music', {}).get('active_sessions', 0)}`\n\n"
            
            "📈 **الاستخدام والأداء:**\n"
            f"🎼 تشغيل موسيقى اليوم: `{bot.get('music', {}).get('total_plays_today', 0)}`\n"
            f"📅 تشغيل موسيقى هذا الأسبوع: `{bot.get('music', {}).get('total_plays_week', 0)}`\n"
            f"⌨️ أوامر اليوم: `{bot.get('commands', {}).get('today', 0)}`\n"
            f"📊 أوامر هذا الأسبوع: `{bot.get('commands', {}).get('week', 0)}`\n"
            f"⚡ استجابة قاعدة البيانات: `{performance.get('db_response_ms', 0)} ms`\n\n"
            
            "🖥️ **موارد النظام:**\n"
            f"🧠 المعالج: `{system.get('cpu', {}).get('percent', 0)}%` "
            f"(`{system.get('cpu', {}).get('count', 0)} cores`)\n"
            f"💾 الذاكرة: `{system.get('memory', {}).get('used', 0)} MB / "
            f"{system.get('memory', {}).get('total', 0)} MB "
            f"({system.get('memory', {}).get('percent', 0)}%)`\n"
            f"💿 التخزين: `{system.get('disk', {}).get('used', 0)} GB / "
            f"{system.get('disk', {}).get('total', 0)} GB "
            f"({system.get('disk', {}).get('percent', 0)}%)`\n"
            f"🔧 ذاكرة البوت: `{performance.get('memory_usage_mb', 0)} MB`\n\n"
            
            "💾 **قاعدة البيانات:**\n"
            f"📂 حجم قاعدة البيانات: `{database.get('size_mb', 0)} MB`\n"
            f"📋 عدد الجداول: `{database.get('tables_count', 0)}`\n"
            f"✅ سلامة البيانات: `{'سليمة' if database.get('integrity', False) else 'تحتاج فحص'}`\n"
            f"⚡ الكاش: `{'مفعل' if database.get('cache_enabled', False) else 'معطل'}`\n\n"
            
            f"🔧 **حالة النظام:** `{bot.get('main_bot', {}).get('connected', False) and 'نشط' or 'خطأ'}`\n"
            f"📱 **إصدار البوت:** `{bot.get('main_bot', {}).get('version', 'غير متاح')}`\n"
            f"⏰ **وقت التشغيل:** `{bot.get('main_bot', {}).get('uptime', 'غير متاح')}`\n"
            f"🔄 **آخر تحديث:** `{stats_data.get('last_updated', 'غير متاح')}`"
        )
        
        return message
    
    def _bytes_to_mb(self, bytes_value: int) -> float:
        """تحويل البايتات إلى ميجابايت"""
        return round(bytes_value / (1024 * 1024), 1)
    
    def _bytes_to_gb(self, bytes_value: int) -> float:
        """تحويل البايتات إلى جيجابايت"""
        return round(bytes_value / (1024 * 1024 * 1024), 2)
    
    def _get_uptime(self) -> str:
        """الحصول على وقت التشغيل"""
        try:
            import time
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}d {hours}h {minutes}m"
        except:
            return "غير متاح"
    
    def _get_memory_usage(self) -> float:
        """الحصول على استخدام الذاكرة للبوت"""
        try:
            process = psutil.Process()
            return round(process.memory_info().rss / 1024 / 1024, 2)
        except:
            return 0.0
    
    def _get_load_average(self) -> str:
        """الحصول على متوسط الحمولة"""
        try:
            if hasattr(os, 'getloadavg'):
                load1, load5, load15 = os.getloadavg()
                return f"{load1:.2f}, {load5:.2f}, {load15:.2f}"
            else:
                return "غير متاح"
        except:
            return "غير متاح"

# إنشاء مثيل عام لمعالج الإحصائيات
stats_handler = StatsHandler()