import sqlite3
import json
import asyncio
import threading
import time
from typing import Dict, List, Union, Optional, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from config import DATABASE_PATH, ENABLE_DATABASE_CACHE

logger = logging.getLogger(__name__)

@dataclass
class ChatSettings:
    """إعدادات المجموعة"""
    chat_id: int
    language: str = "ar"
    play_mode: str = "Direct"
    play_type: str = "Everyone"
    assistant_id: int = None
    auto_end: bool = False
    auth_enabled: bool = False
    welcome_enabled: bool = False
    log_enabled: bool = False
    search_enabled: bool = False
    upvote_count: int = 3

@dataclass
class UserData:
    """بيانات المستخدم"""
    user_id: int
    first_name: str = ""
    username: str = ""
    join_date: str = ""
    is_banned: bool = False
    is_sudo: bool = False

@dataclass
class ChatData:
    """بيانات المجموعة"""
    chat_id: int
    chat_title: str = ""
    chat_type: str = ""
    join_date: str = ""
    is_blacklisted: bool = False

@dataclass
class AssistantData:
    """بيانات الحساب المساعد"""
    assistant_id: int
    session_string: str
    name: str
    is_active: bool = True
    added_date: str = ""
    last_used: str = ""
    total_calls: int = 0

class DatabaseManager:
    """مدير قاعدة البيانات المحسّن لـ TDLib"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
        
        # كاش في الذاكرة للبيانات المتكررة
        self.cache_enabled = ENABLE_DATABASE_CACHE
        if self.cache_enabled:
            self.cache = {
                'settings': {},
                'users': {},
                'chats': {},
                'assistants': {},
                'temp': {}
            }
        else:
            self.cache = {}
        
    def _init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول إعدادات المجموعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_settings (
                    chat_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'ar',
                    play_mode TEXT DEFAULT 'Direct',
                    play_type TEXT DEFAULT 'Everyone',
                    assistant_id INTEGER DEFAULT NULL,
                    auto_end BOOLEAN DEFAULT 0,
                    auth_enabled BOOLEAN DEFAULT 0,
                    welcome_enabled BOOLEAN DEFAULT 0,
                    log_enabled BOOLEAN DEFAULT 0,
                    search_enabled BOOLEAN DEFAULT 0,
                    upvote_count INTEGER DEFAULT 3,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned BOOLEAN DEFAULT 0,
                    is_sudo BOOLEAN DEFAULT 0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول المجموعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    chat_type TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blacklisted BOOLEAN DEFAULT 0,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الحسابات المساعدة (جديد)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assistants (
                    assistant_id INTEGER PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_calls INTEGER DEFAULT 0,
                    user_info TEXT DEFAULT '{}',
                    UNIQUE(session_string)
                )
            ''')
            
            # جدول المصرح لهم في المجموعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    user_id INTEGER,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, user_id)
                )
            ''')
            
            # جدول الحالات المؤقتة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS temp_states (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول إحصائيات الاستخدام (جديد)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    assistant_id INTEGER,
                    action_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            # إنشاء فهارس للأداء
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_settings_chat_id ON chat_settings(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_assistants_id ON assistants(assistant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_assistants_active ON assistants(is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_users_chat_user ON auth_users(chat_id, user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_chat ON usage_stats(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_assistant ON usage_stats(assistant_id)')
            
            conn.commit()
            logger.info("✅ تم إنشاء قاعدة البيانات SQLite بنجاح")

    @contextmanager
    def _get_connection(self):
        """الحصول على اتصال آمن بقاعدة البيانات"""
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    # ========================================
    # وظائف إدارة الحسابات المساعدة (جديد)
    # ========================================
    
    async def add_assistant(self, assistant_id: int, session_string: str, name: str) -> bool:
        """إضافة حساب مساعد جديد"""
        def _add():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        INSERT INTO assistants (assistant_id, session_string, name, added_date)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (assistant_id, session_string, name))
                    conn.commit()
                    
                    # تحديث الكاش
                    if self.cache_enabled:
                        self.cache.setdefault('assistants', {})[assistant_id] = {
                            'assistant_id': assistant_id,
                            'session_string': session_string,
                            'name': name,
                            'is_active': True,
                            'added_date': datetime.now().isoformat(),
                            'last_used': datetime.now().isoformat(),
                            'total_calls': 0
                        }
                    
                    return True
                except sqlite3.IntegrityError:
                    return False  # المساعد موجود بالفعل
        
        return await asyncio.get_event_loop().run_in_executor(None, _add)
    
    async def remove_assistant(self, assistant_id: int) -> bool:
        """إزالة حساب مساعد"""
        def _remove():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM assistants WHERE assistant_id = ?', (assistant_id,))
                success = cursor.rowcount > 0
                conn.commit()
                
                # تحديث الكاش
                if self.cache_enabled and 'assistants' in self.cache:
                    self.cache['assistants'].pop(assistant_id, None)
                
                return success
        
        return await asyncio.get_event_loop().run_in_executor(None, _remove)
    
    async def get_assistant(self, assistant_id: int) -> Optional[Dict]:
        """الحصول على معلومات المساعد"""
        # التحقق من الكاش أولاً
        if self.cache_enabled and assistant_id in self.cache.get('assistants', {}):
            return self.cache['assistants'][assistant_id]
        
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM assistants WHERE assistant_id = ?', (assistant_id,))
                row = cursor.fetchone()
                
                if row:
                    assistant_data = {
                        'assistant_id': row['assistant_id'],
                        'session_string': row['session_string'],
                        'name': row['name'],
                        'is_active': bool(row['is_active']),
                        'added_date': row['added_date'],
                        'last_used': row['last_used'],
                        'total_calls': row['total_calls']
                    }
                    
                    # حفظ في الكاش
                    if self.cache_enabled:
                        self.cache.setdefault('assistants', {})[assistant_id] = assistant_data
                    
                    return assistant_data
                return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def get_all_assistants(self) -> List[Dict]:
        """الحصول على جميع الحسابات المساعدة"""
        def _get_all():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM assistants WHERE is_active = 1 ORDER BY assistant_id')
                rows = cursor.fetchall()
                
                assistants = []
                for row in rows:
                    assistant_data = {
                        'assistant_id': row['assistant_id'],
                        'session_string': row['session_string'],
                        'name': row['name'],
                        'is_active': bool(row['is_active']),
                        'added_date': row['added_date'],
                        'last_used': row['last_used'],
                        'total_calls': row['total_calls']
                    }
                    assistants.append(assistant_data)
                    
                    # تحديث الكاش
                    if self.cache_enabled:
                        self.cache.setdefault('assistants', {})[row['assistant_id']] = assistant_data
                
                return assistants
        
        return await asyncio.get_event_loop().run_in_executor(None, _get_all)
    
    async def update_assistant_usage(self, assistant_id: int):
        """تحديث إحصائيات استخدام المساعد"""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE assistants 
                    SET last_used = CURRENT_TIMESTAMP, total_calls = total_calls + 1
                    WHERE assistant_id = ?
                ''', (assistant_id,))
                conn.commit()
                
                # تحديث الكاش
                if self.cache_enabled and assistant_id in self.cache.get('assistants', {}):
                    self.cache['assistants'][assistant_id]['last_used'] = datetime.now().isoformat()
                    self.cache['assistants'][assistant_id]['total_calls'] += 1
        
        await asyncio.get_event_loop().run_in_executor(None, _update)
    
    async def deactivate_assistant(self, assistant_id: int) -> bool:
        """إلغاء تفعيل مساعد"""
        def _deactivate():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE assistants SET is_active = 0 WHERE assistant_id = ?
                ''', (assistant_id,))
                success = cursor.rowcount > 0
                conn.commit()
                
                # تحديث الكاش
                if self.cache_enabled and assistant_id in self.cache.get('assistants', {}):
                    self.cache['assistants'][assistant_id]['is_active'] = False
                
                return success
        
        return await asyncio.get_event_loop().run_in_executor(None, _deactivate)
    
    async def activate_assistant(self, assistant_id: int) -> bool:
        """تفعيل مساعد"""
        def _activate():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE assistants SET is_active = 1 WHERE assistant_id = ?
                ''', (assistant_id,))
                success = cursor.rowcount > 0
                conn.commit()
                
                # تحديث الكاش
                if self.cache_enabled and assistant_id in self.cache.get('assistants', {}):
                    self.cache['assistants'][assistant_id]['is_active'] = True
                
                return success
        
        return await asyncio.get_event_loop().run_in_executor(None, _activate)

    # ========================================
    # وظائف إعدادات المجموعات
    # ========================================
    
    async def get_chat_settings(self, chat_id: int) -> ChatSettings:
        """الحصول على إعدادات المجموعة"""
        # التحقق من الكاش أولاً
        if self.cache_enabled and chat_id in self.cache.get('settings', {}):
            return self.cache['settings'][chat_id]
            
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM chat_settings WHERE chat_id = ?', (chat_id,))
                row = cursor.fetchone()
                
                if row:
                    settings = ChatSettings(
                        chat_id=row['chat_id'],
                        language=row['language'],
                        play_mode=row['play_mode'],
                        play_type=row['play_type'],
                        assistant_id=row['assistant_id'],
                        auto_end=bool(row['auto_end']),
                        auth_enabled=bool(row['auth_enabled']),
                        welcome_enabled=bool(row['welcome_enabled']),
                        log_enabled=bool(row['log_enabled']),
                        search_enabled=bool(row['search_enabled']),
                        upvote_count=row['upvote_count']
                    )
                else:
                    # إعدادات افتراضية
                    settings = ChatSettings(chat_id=chat_id)
                    # حفظ الإعدادات الافتراضية
                    cursor.execute('''
                        INSERT OR REPLACE INTO chat_settings 
                        (chat_id, language, play_mode, play_type, upvote_count) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (chat_id, settings.language, settings.play_mode, 
                          settings.play_type, settings.upvote_count))
                    conn.commit()
                
                # حفظ في الكاش
                if self.cache_enabled:
                    self.cache.setdefault('settings', {})[chat_id] = settings
                
                return settings
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def update_chat_setting(self, chat_id: int, **kwargs):
        """تحديث إعداد معين للمجموعة"""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # بناء استعلام التحديث الديناميكي
                set_clause = []
                values = []
                
                valid_fields = ['language', 'play_mode', 'play_type', 'assistant_id', 
                              'auto_end', 'auth_enabled', 'welcome_enabled', 
                              'log_enabled', 'search_enabled', 'upvote_count']
                
                for key, value in kwargs.items():
                    if key in valid_fields:
                        set_clause.append(f"{key} = ?")
                        values.append(value)
                
                if set_clause:
                    values.append(chat_id)
                    query = f"UPDATE chat_settings SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?"
                    cursor.execute(query, values)
                    
                    # إذا لم يتم التحديث (السجل غير موجود), أنشئ سجل جديد
                    if cursor.rowcount == 0:
                        cursor.execute('''
                            INSERT INTO chat_settings (chat_id, language, play_mode, play_type, upvote_count)
                            VALUES (?, 'ar', 'Direct', 'Everyone', 3)
                        ''', (chat_id,))
                        
                        # تحديث القيم المطلوبة
                        for key, value in kwargs.items():
                            if key in valid_fields:
                                cursor.execute(f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id))
                    
                    conn.commit()
                    
                    # تحديث الكاش
                    if self.cache_enabled and chat_id in self.cache.get('settings', {}):
                        for key, value in kwargs.items():
                            if hasattr(self.cache['settings'][chat_id], key):
                                setattr(self.cache['settings'][chat_id], key, value)
        
        await asyncio.get_event_loop().run_in_executor(None, _update)

    # ========================================
    # باقي الوظائف (مشابهة للنسخة السابقة)
    # ========================================
    
    async def add_user(self, user_id: int, first_name: str = "", username: str = ""):
        """إضافة مستخدم جديد"""
        def _add():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, first_name, username, last_seen)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, first_name, username))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _add)

    async def add_chat(self, chat_id: int, chat_title: str = "", chat_type: str = ""):
        """إضافة مجموعة جديدة"""
        def _add():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO chats (chat_id, chat_title, chat_type, last_active)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (chat_id, chat_title, chat_type))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _add)

    async def ban_user(self, user_id: int):
        """حظر مستخدم"""
        await self._update_user(user_id, is_banned=True)

    async def unban_user(self, user_id: int):
        """إلغاء حظر مستخدم"""
        await self._update_user(user_id, is_banned=False)

    async def is_banned(self, user_id: int) -> bool:
        """التحقق من حظر المستخدم"""
        def _check():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                return bool(row['is_banned']) if row else False
        
        return await asyncio.get_event_loop().run_in_executor(None, _check)

    async def add_sudo(self, user_id: int):
        """إضافة مستخدم كمدير"""
        await self._update_user(user_id, is_sudo=True)

    async def remove_sudo(self, user_id: int):
        """إزالة صلاحيات المدير"""
        await self._update_user(user_id, is_sudo=False)

    async def get_sudoers(self) -> List[int]:
        """الحصول على قائمة المديرين"""
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE is_sudo = 1')
                return [row['user_id'] for row in cursor.fetchall()]
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def _update_user(self, user_id: int, **kwargs):
        """تحديث بيانات المستخدم"""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                set_clause = []
                values = []
                
                valid_fields = ['first_name', 'username', 'is_banned', 'is_sudo']
                
                for key, value in kwargs.items():
                    if key in valid_fields:
                        set_clause.append(f"{key} = ?")
                        values.append(value)
                
                if set_clause:
                    values.append(user_id)
                    query = f"UPDATE users SET {', '.join(set_clause)}, last_seen = CURRENT_TIMESTAMP WHERE user_id = ?"
                    cursor.execute(query, values)
                    
                    if cursor.rowcount == 0:
                        # إنشاء المستخدم إذا لم يكن موجوداً
                        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                        cursor.execute(query, values)
                    
                    conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _update)

    async def add_auth_user(self, chat_id: int, user_id: int):
        """إضافة مستخدم للمصرح لهم في المجموعة"""
        def _add():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO auth_users (chat_id, user_id)
                    VALUES (?, ?)
                ''', (chat_id, user_id))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _add)

    async def remove_auth_user(self, chat_id: int, user_id: int):
        """إزالة مستخدم من المصرح لهم"""
        def _remove():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM auth_users WHERE chat_id = ? AND user_id = ?', (chat_id, user_id))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _remove)

    async def is_auth_user(self, chat_id: int, user_id: int) -> bool:
        """التحقق من تصريح المستخدم في المجموعة"""
        def _check():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM auth_users WHERE chat_id = ? AND user_id = ?', (chat_id, user_id))
                return cursor.fetchone() is not None
        
        return await asyncio.get_event_loop().run_in_executor(None, _check)

    async def get_stats(self) -> Dict[str, int]:
        """الحصول على إحصائيات قاعدة البيانات"""
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) as count FROM users')
                users_count = cursor.fetchone()['count']
                
                cursor.execute('SELECT COUNT(*) as count FROM chats')
                chats_count = cursor.fetchone()['count']
                
                cursor.execute('SELECT COUNT(*) as count FROM assistants WHERE is_active = 1')
                assistants_count = cursor.fetchone()['count']
                
                cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_sudo = 1')
                sudoers_count = cursor.fetchone()['count']
                
                cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_banned = 1')
                banned_count = cursor.fetchone()['count']
                
                return {
                    'users': users_count,
                    'chats': chats_count,
                    'assistants': assistants_count,
                    'sudoers': sudoers_count,
                    'banned': banned_count
                }
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)

    # وظائف للحالات المؤقتة
    async def set_temp_state(self, key: str, value: Any):
        """حفظ حالة مؤقتة"""
        if self.cache_enabled:
            self.cache.setdefault('temp', {})[key] = value
        
        def _save():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO temp_states (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, json.dumps(value)))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _save)

    async def get_temp_state(self, key: str, default=None):
        """الحصول على حالة مؤقتة"""
        # التحقق من الكاش أولاً
        if self.cache_enabled and 'temp' in self.cache and key in self.cache['temp']:
            return self.cache['temp'][key]
            
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM temp_states WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    value = json.loads(row['value'])
                    if self.cache_enabled:
                        self.cache.setdefault('temp', {})[key] = value
                    return value
                return default
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def clear_cache(self):
        """مسح الكاش"""
        if self.cache_enabled:
            self.cache.clear()
            logger.info("تم مسح كاش قاعدة البيانات")

    async def log_usage(self, chat_id: int, assistant_id: int, action_type: str, metadata: Dict = None):
        """تسجيل إحصائيات الاستخدام"""
        def _log():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO usage_stats (chat_id, assistant_id, action_type, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (chat_id, assistant_id, action_type, json.dumps(metadata or {})))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _log)

# إنشاء مثيل مدير قاعدة البيانات
db = DatabaseManager()

logger.info("✅ نظام قاعدة البيانات TDLib جاهز للاستخدام")