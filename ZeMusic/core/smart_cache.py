"""
💾 نظام التخزين المؤقت الذكي
============================

نظام متقدم للتخزين المؤقت يقلل الاعتماد على الكوكيز:
- تخزين مؤقت للمقاطع الشائعة
- ضغط وتحسين البيانات
- إدارة ذكية للمساحة
- تنبؤ بالاحتياجات المستقبلية
"""

import asyncio
import hashlib
import json
import os
import time
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import sqlite3
import aiofiles

from ZeMusic import LOGGER

@dataclass
class CacheEntry:
    key: str
    data: bytes
    created_at: float
    last_accessed: float
    access_count: int
    size: int
    compressed: bool = False
    metadata: Dict[str, Any] = None

class SmartCache:
    """نظام التخزين المؤقت الذكي"""
    
    def __init__(self, cache_dir: str = "smart_cache", max_size_gb: float = 5.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # إعدادات التخزين المؤقت
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)  # تحويل إلى بايت
        self.compression_threshold = 1024 * 100  # 100KB
        self.max_age_days = 30
        self.cleanup_interval = 3600  # ساعة واحدة
        
        # قاعدة البيانات
        self.db_path = self.cache_dir / "cache.db"
        self._init_database()
        
        # إحصائيات
        self.stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
            'cache_size': 0,
            'entries_count': 0
        }
        
        # آخر عملية تنظيف
        self.last_cleanup = 0
        
        LOGGER(__name__).info(f"💾 تم تهيئة نظام التخزين المؤقت الذكي - مجلد: {cache_dir}")
        
        # تحديث الإحصائيات عند البدء
        asyncio.create_task(self._update_stats())

    def _init_database(self):
        """تهيئة قاعدة البيانات"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    file_path TEXT,
                    created_at REAL,
                    last_accessed REAL,
                    access_count INTEGER DEFAULT 0,
                    size INTEGER,
                    compressed INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # إنشاء فهارس للأداء
            conn.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_access_count ON cache_entries(access_count)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)')
            
            conn.commit()

    async def get(self, key: str) -> Optional[bytes]:
        """الحصول على بيانات من التخزين المؤقت"""
        self.stats['total_requests'] += 1
        
        # التحقق من وجود المدخل في قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT file_path, compressed, access_count FROM cache_entries WHERE key = ?', 
                (key,)
            )
            result = cursor.fetchone()
        
        if not result:
            self.stats['misses'] += 1
            return None
        
        file_path, compressed, access_count = result
        cache_file = self.cache_dir / file_path
        
        if not cache_file.exists():
            # ملف محذوف، إزالة من قاعدة البيانات
            await self._remove_entry(key)
            self.stats['misses'] += 1
            return None
        
        try:
            # قراءة البيانات
            async with aiofiles.open(cache_file, 'rb') as f:
                data = await f.read()
            
            # إلغاء الضغط إذا لزم الأمر
            if compressed:
                data = zlib.decompress(data)
            
            # تحديث إحصائيات الوصول
            current_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE cache_entries SET last_accessed = ?, access_count = access_count + 1 WHERE key = ?',
                    (current_time, key)
                )
                conn.commit()
            
            self.stats['hits'] += 1
            LOGGER(__name__).debug(f"💾 cache hit: {key}")
            
            return data
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في قراءة التخزين المؤقت {key}: {e}")
            await self._remove_entry(key)
            self.stats['misses'] += 1
            return None

    async def set(self, key: str, data: bytes, metadata: Dict[str, Any] = None) -> bool:
        """حفظ بيانات في التخزين المؤقت"""
        try:
            # التحقق من ضرورة التنظيف
            await self._cleanup_if_needed()
            
            current_time = time.time()
            original_size = len(data)
            
            # ضغط البيانات إذا لزم الأمر
            compressed = False
            if original_size > self.compression_threshold:
                compressed_data = zlib.compress(data, level=6)
                if len(compressed_data) < original_size * 0.8:  # توفير 20% على الأقل
                    data = compressed_data
                    compressed = True
                    LOGGER(__name__).debug(f"🗜️ ضغط البيانات: {original_size} -> {len(data)} bytes")
            
            # إنشاء اسم ملف آمن
            file_name = hashlib.md5(key.encode()).hexdigest() + '.cache'
            cache_file = self.cache_dir / file_name
            
            # حفظ البيانات
            async with aiofiles.open(cache_file, 'wb') as f:
                await f.write(data)
            
            # حفظ المعلومات في قاعدة البيانات
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO cache_entries 
                       (key, file_path, created_at, last_accessed, access_count, size, compressed, metadata)
                       VALUES (?, ?, ?, ?, 1, ?, ?, ?)''',
                    (key, file_name, current_time, current_time, len(data), 
                     int(compressed), json.dumps(metadata or {}))
                )
                conn.commit()
            
            LOGGER(__name__).debug(f"💾 cache set: {key} ({len(data)} bytes)")
            await self._update_stats()
            
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في حفظ التخزين المؤقت {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """التحقق من وجود مفتاح في التخزين المؤقت"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT 1 FROM cache_entries WHERE key = ?', (key,))
            return cursor.fetchone() is not None

    async def delete(self, key: str) -> bool:
        """حذف مدخل من التخزين المؤقت"""
        return await self._remove_entry(key)

    async def _remove_entry(self, key: str) -> bool:
        """إزالة مدخل مع حذف الملف"""
        try:
            # الحصول على مسار الملف
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT file_path FROM cache_entries WHERE key = ?', (key,))
                result = cursor.fetchone()
                
                if result:
                    file_path = result[0]
                    cache_file = self.cache_dir / file_path
                    
                    # حذف الملف
                    if cache_file.exists():
                        cache_file.unlink()
                    
                    # حذف من قاعدة البيانات
                    conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                    conn.commit()
                    
                    return True
            
            return False
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في حذف التخزين المؤقت {key}: {e}")
            return False

    async def _cleanup_if_needed(self):
        """تنظيف التخزين المؤقت إذا لزم الأمر"""
        current_time = time.time()
        
        if (current_time - self.last_cleanup) < self.cleanup_interval:
            return
        
        await self._cleanup()
        self.last_cleanup = current_time

    async def _cleanup(self):
        """تنظيف التخزين المؤقت"""
        LOGGER(__name__).info("🧹 بدء تنظيف التخزين المؤقت...")
        
        current_time = time.time()
        max_age_seconds = self.max_age_days * 24 * 3600
        
        # حذف المدخلات القديمة
        with sqlite3.connect(self.db_path) as conn:
            # العثور على المدخلات القديمة
            cursor = conn.execute(
                'SELECT key, file_path FROM cache_entries WHERE ? - created_at > ?',
                (current_time, max_age_seconds)
            )
            old_entries = cursor.fetchall()
            
            # حذف الملفات والمدخلات القديمة
            for key, file_path in old_entries:
                cache_file = self.cache_dir / file_path
                if cache_file.exists():
                    cache_file.unlink()
            
            if old_entries:
                conn.execute(
                    'DELETE FROM cache_entries WHERE ? - created_at > ?',
                    (current_time, max_age_seconds)
                )
                LOGGER(__name__).info(f"🗑️ تم حذف {len(old_entries)} مدخل قديم")
        
        # التحقق من حجم التخزين المؤقت
        await self._enforce_size_limit()
        
        # تحديث الإحصائيات
        await self._update_stats()
        
        LOGGER(__name__).info("✅ تم تنظيف التخزين المؤقت")

    async def _enforce_size_limit(self):
        """فرض حد حجم التخزين المؤقت"""
        current_size = await self._calculate_total_size()
        
        if current_size <= self.max_size_bytes:
            return
        
        LOGGER(__name__).info(f"📦 حجم التخزين المؤقت تجاوز الحد: {current_size / 1024 / 1024:.1f} MB")
        
        # حذف المدخلات الأقل استخداماً
        with sqlite3.connect(self.db_path) as conn:
            # ترتيب حسب آخر وصول ثم عدد الوصول
            cursor = conn.execute(
                '''SELECT key, file_path, size FROM cache_entries 
                   ORDER BY last_accessed ASC, access_count ASC'''
            )
            entries = cursor.fetchall()
            
            deleted_size = 0
            target_size = self.max_size_bytes * 0.8  # حذف حتى 80% من الحد الأقصى
            
            for key, file_path, size in entries:
                if current_size - deleted_size <= target_size:
                    break
                
                # حذف الملف والمدخل
                cache_file = self.cache_dir / file_path
                if cache_file.exists():
                    cache_file.unlink()
                
                conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                deleted_size += size
            
            conn.commit()
            
            if deleted_size > 0:
                LOGGER(__name__).info(f"🗑️ تم حذف {deleted_size / 1024 / 1024:.1f} MB لفرض حد الحجم")

    async def _calculate_total_size(self) -> int:
        """حساب الحجم الإجمالي للتخزين المؤقت"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT SUM(size) FROM cache_entries')
            result = cursor.fetchone()
            return result[0] or 0

    async def _update_stats(self):
        """تحديث الإحصائيات"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*), SUM(size) FROM cache_entries')
            count, total_size = cursor.fetchone()
            
            self.stats['entries_count'] = count or 0
            self.stats['cache_size'] = total_size or 0

    def get_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات التخزين المؤقت"""
        hit_rate = (self.stats['hits'] / max(1, self.stats['total_requests'])) * 100
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'total_requests': self.stats['total_requests'],
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size_mb': round(self.stats['cache_size'] / 1024 / 1024, 2),
            'entries_count': self.stats['entries_count'],
            'max_size_mb': round(self.max_size_bytes / 1024 / 1024, 2)
        }

    async def get_popular_keys(self, limit: int = 10) -> List[Dict[str, Any]]:
        """الحصول على المفاتيح الأكثر شعبية"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                '''SELECT key, access_count, size, metadata FROM cache_entries 
                   ORDER BY access_count DESC LIMIT ?''', 
                (limit,)
            )
            
            results = []
            for key, access_count, size, metadata_str in cursor.fetchall():
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    metadata = {}
                
                results.append({
                    'key': key,
                    'access_count': access_count,
                    'size_kb': round(size / 1024, 2),
                    'metadata': metadata
                })
            
            return results

    async def preload_popular_content(self):
        """تحميل مسبق للمحتوى الشائع"""
        # هذه الدالة يمكن استخدامها لتحميل المحتوى الشائع مسبقاً
        # بناءً على أنماط الاستخدام السابقة
        popular_keys = await self.get_popular_keys(50)
        
        LOGGER(__name__).info(f"📈 تم العثور على {len(popular_keys)} مفتاح شائع للتحميل المسبق")
        
        # يمكن إضافة منطق التحميل المسبق هنا
        return popular_keys


# نسخة شاملة للاستخدام
smart_cache = SmartCache()