"""
🍪 نظام تدوير الكوكيز التلقائي المتطور
=====================================

نظام ذكي لتدوير الكوكيز ومنع الحظر مع:
- تدوير تلقائي متعدد الحسابات
- مراقبة حالة الكوكيز
- استبدال تلقائي عند الحظر
- تشفير آمن للكوكيز
"""

import os
import json
import asyncio
import random
import hashlib
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
from cryptography.fernet import Fernet

from ZeMusic import LOGGER

class CookiesRotator:
    """نظام تدوير الكوكيز المتطور"""
    
    def __init__(self, cookies_dir: str = "cookies", max_usage_per_cookie: int = 50):
        self.cookies_dir = Path(cookies_dir)
        self.cookies_dir.mkdir(exist_ok=True)
        
        # إعدادات التدوير
        self.max_usage_per_cookie = max_usage_per_cookie
        self.cookie_cooldown = 300  # 5 دقائق راحة بين الاستخدامات
        self.rotation_interval = 1800  # 30 دقيقة بين التدوير
        
        # تتبع الاستخدام
        self.cookie_usage = {}
        self.cookie_health = {}
        self.last_rotation = 0
        self.current_cookie_index = 0
        
        # تشفير الكوكيز
        self.cipher = self._init_encryption()
        
        # قائمة الكوكيز
        self.cookies_list = []
        self._load_cookies()
        
        LOGGER(__name__).info(f"🍪 تم تهيئة نظام تدوير الكوكيز - {len(self.cookies_list)} كوكيز محمل")

    def _init_encryption(self) -> Fernet:
        """تهيئة تشفير الكوكيز"""
        key_file = self.cookies_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # إخفاء الملف في أنظمة Unix
            if os.name != 'nt':
                os.chmod(key_file, 0o600)
        
        return Fernet(key)

    def _load_cookies(self):
        """تحميل جميع ملفات الكوكيز"""
        self.cookies_list = []
        
        # البحث عن ملفات الكوكيز المشفرة
        for cookie_file in self.cookies_dir.glob("cookies_*.enc"):
            try:
                with open(cookie_file, 'rb') as f:
                    encrypted_data = f.read()
                
                decrypted_data = self.cipher.decrypt(encrypted_data)
                cookie_data = json.loads(decrypted_data.decode())
                
                cookie_info = {
                    'file': cookie_file.name,
                    'data': cookie_data,
                    'account_name': cookie_data.get('account_name', f'حساب_{len(self.cookies_list)+1}'),
                    'last_used': 0,
                    'usage_count': 0,
                    'health_score': 100,
                    'banned': False
                }
                
                self.cookies_list.append(cookie_info)
                LOGGER(__name__).debug(f"✅ تم تحميل كوكيز: {cookie_info['account_name']}")
                
            except Exception as e:
                LOGGER(__name__).error(f"❌ خطأ في تحميل {cookie_file}: {e}")
        
        # البحث عن ملفات الكوكيز غير المشفرة (للتحويل)
        for cookie_file in self.cookies_dir.glob("cookies_*.txt"):
            self._convert_plain_cookie(cookie_file)

    def _convert_plain_cookie(self, cookie_file: Path):
        """تحويل ملف كوكيز عادي إلى مشفر"""
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_content = f.read()
            
            # إنشاء بيانات الكوكيز
            cookie_data = {
                'account_name': cookie_file.stem,
                'cookies': cookie_content,
                'created_at': datetime.now().isoformat(),
                'source': 'converted'
            }
            
            # تشفير وحفظ
            encrypted_file = self.cookies_dir / f"{cookie_file.stem}.enc"
            self._save_encrypted_cookie(encrypted_file, cookie_data)
            
            # حذف الملف الأصلي
            cookie_file.unlink()
            
            LOGGER(__name__).info(f"🔒 تم تحويل وتشفير: {cookie_file.name}")
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في تحويل {cookie_file}: {e}")

    def _save_encrypted_cookie(self, file_path: Path, cookie_data: dict):
        """حفظ كوكيز مشفر"""
        try:
            json_data = json.dumps(cookie_data, ensure_ascii=False, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في حفظ الكوكيز المشفر: {e}")

    async def get_current_cookies(self) -> Optional[Dict[str, Any]]:
        """الحصول على الكوكيز الحالي للاستخدام"""
        if not self.cookies_list:
            LOGGER(__name__).warning("⚠️ لا توجد كوكيز متاحة!")
            return None
        
        # التحقق من ضرورة التدوير
        current_time = time.time()
        if (current_time - self.last_rotation) > self.rotation_interval:
            await self._rotate_cookies()
        
        # العثور على أفضل كوكيز متاح
        best_cookie = await self._find_best_cookie()
        
        if best_cookie:
            # تسجيل الاستخدام
            best_cookie['usage_count'] += 1
            best_cookie['last_used'] = current_time
            
            LOGGER(__name__).debug(f"🍪 استخدام كوكيز: {best_cookie['account_name']} (الاستخدام: {best_cookie['usage_count']})")
            
            return best_cookie['data']
        
        LOGGER(__name__).warning("⚠️ لا توجد كوكيز صالحة متاحة!")
        return None

    async def _find_best_cookie(self) -> Optional[Dict]:
        """العثور على أفضل كوكيز للاستخدام"""
        current_time = time.time()
        available_cookies = []
        
        for cookie in self.cookies_list:
            # تجاهل الكوكيز المحظورة
            if cookie['banned']:
                continue
            
            # تجاهل الكوكيز المستخدمة بكثرة
            if cookie['usage_count'] >= self.max_usage_per_cookie:
                continue
            
            # تجاهل الكوكيز في فترة الراحة
            if (current_time - cookie['last_used']) < self.cookie_cooldown:
                continue
            
            # حساب نقاط الأولوية
            priority_score = cookie['health_score'] - cookie['usage_count']
            available_cookies.append((priority_score, cookie))
        
        if available_cookies:
            # ترتيب حسب الأولوية واختيار الأفضل
            available_cookies.sort(key=lambda x: x[0], reverse=True)
            return available_cookies[0][1]
        
        # إذا لم تكن هناك كوكيز متاحة، استخدم أي كوكيز غير محظور
        for cookie in self.cookies_list:
            if not cookie['banned']:
                return cookie
        
        return None

    async def _rotate_cookies(self):
        """تدوير الكوكيز وإعادة ضبط العدادات"""
        LOGGER(__name__).info("🔄 بدء تدوير الكوكيز...")
        
        # إعادة ضبط عدادات الاستخدام
        for cookie in self.cookies_list:
            if not cookie['banned']:
                cookie['usage_count'] = max(0, cookie['usage_count'] - 10)
                cookie['health_score'] = min(100, cookie['health_score'] + 5)
        
        # خلط ترتيب الكوكيز
        random.shuffle(self.cookies_list)
        
        self.last_rotation = time.time()
        LOGGER(__name__).info("✅ تم تدوير الكوكيز بنجاح")

    async def report_cookie_failure(self, cookie_data: Dict, error_type: str = "unknown"):
        """الإبلاغ عن فشل في الكوكيز"""
        # العثور على الكوكيز المقابل
        for cookie in self.cookies_list:
            if cookie['data'] == cookie_data:
                cookie['health_score'] -= 20
                
                # إذا انخفضت النقاط كثيراً، اعتبره محظور
                if cookie['health_score'] <= 0:
                    cookie['banned'] = True
                    LOGGER(__name__).warning(f"🚫 تم تعطيل كوكيز: {cookie['account_name']} (السبب: {error_type})")
                    
                    # إشعار المطور
                    await self._notify_developer_cookie_banned(cookie['account_name'], error_type)
                else:
                    LOGGER(__name__).warning(f"⚠️ انخفاض نقاط كوكيز: {cookie['account_name']} -> {cookie['health_score']}")
                break

    async def _notify_developer_cookie_banned(self, account_name: str, reason: str):
        """إشعار المطور بحظر الكوكيز"""
        try:
            from ZeMusic import config, tdlib_manager
            
            if hasattr(config, 'OWNER_ID') and tdlib_manager.bot_client:
                message = f"""
🚨 **تحذير: تم حظر كوكيز!**

📱 **الحساب:** {account_name}
❌ **السبب:** {reason}
🕐 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **الإجراء المطلوب:**
- إضافة كوكيز جديدة
- التحقق من حالة الحسابات
- تحديث الكوكيز الموجودة

📊 **إحصائيات الكوكيز:**
- المتاحة: {len([c for c in self.cookies_list if not c['banned']])}
- المحظورة: {len([c for c in self.cookies_list if c['banned']])}
                """
                
                await tdlib_manager.bot_client.client.call_method('sendMessage', {
                    'chat_id': config.OWNER_ID,
                    'input_message_content': {
                        '@type': 'inputMessageText',
                        'text': {'@type': 'formattedText', 'text': message.strip()}
                    }
                })
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال إشعار المطور: {e}")

    async def add_new_cookies(self, cookies_content: str, account_name: str) -> bool:
        """إضافة كوكيز جديدة"""
        try:
            # إنشاء بيانات الكوكيز
            cookie_data = {
                'account_name': account_name,
                'cookies': cookies_content,
                'created_at': datetime.now().isoformat(),
                'source': 'manual_add'
            }
            
            # حفظ مشفر
            file_name = f"cookies_{account_name}_{int(time.time())}.enc"
            encrypted_file = self.cookies_dir / file_name
            self._save_encrypted_cookie(encrypted_file, cookie_data)
            
            # إضافة للقائمة
            cookie_info = {
                'file': file_name,
                'data': cookie_data,
                'account_name': account_name,
                'last_used': 0,
                'usage_count': 0,
                'health_score': 100,
                'banned': False
            }
            
            self.cookies_list.append(cookie_info)
            
            LOGGER(__name__).info(f"✅ تم إضافة كوكيز جديدة: {account_name}")
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إضافة الكوكيز: {e}")
            return False

    def get_cookies_stats(self) -> Dict:
        """إحصائيات الكوكيز"""
        total = len(self.cookies_list)
        active = len([c for c in self.cookies_list if not c['banned']])
        banned = total - active
        
        return {
            'total': total,
            'active': active,
            'banned': banned,
            'health_avg': sum(c['health_score'] for c in self.cookies_list) / max(1, total),
            'usage_avg': sum(c['usage_count'] for c in self.cookies_list) / max(1, total)
        }

    async def health_check(self) -> Dict:
        """فحص صحة جميع الكوكيز"""
        LOGGER(__name__).info("🔍 بدء فحص صحة الكوكيز...")
        
        results = {
            'healthy': [],
            'degraded': [],
            'failed': []
        }
        
        for cookie in self.cookies_list:
            if cookie['banned']:
                results['failed'].append(cookie['account_name'])
            elif cookie['health_score'] < 50:
                results['degraded'].append(cookie['account_name'])
            else:
                results['healthy'].append(cookie['account_name'])
        
        LOGGER(__name__).info(f"📊 نتائج الفحص - صحية: {len(results['healthy'])}, متدهورة: {len(results['degraded'])}, فاشلة: {len(results['failed'])}")
        
        return results


# نسخة شاملة للتكامل مع البوت
cookies_rotator = CookiesRotator()