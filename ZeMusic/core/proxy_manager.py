"""
🌐 نظام إدارة البروكسي المتقدم
================================

نظام شامل لإدارة البروكسي مع:
- تدوير تلقائي للبروكسي
- اختبار صحة البروكسي
- توزيع الأحمال
- دعم أنواع مختلفة من البروكسي
"""

import asyncio
import random
import time
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from ZeMusic import LOGGER

class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class ProxyInfo:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: ProxyType = ProxyType.HTTP
    last_used: float = 0
    success_count: int = 0
    failure_count: int = 0
    response_time: float = 0
    is_working: bool = True
    country: Optional[str] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0

    @property
    def url(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"

class ProxyManager:
    """نظام إدارة البروكسي المتقدم"""
    
    def __init__(self, proxies_file: str = "proxies.json"):
        self.proxies_file = Path(proxies_file)
        self.proxies: List[ProxyInfo] = []
        self.current_proxy_index = 0
        self.rotation_interval = 300  # 5 دقائق
        self.last_rotation = 0
        self.max_failures_before_disable = 3
        
        self._load_proxies()
        LOGGER(__name__).info(f"🌐 تم تهيئة مدير البروكسي - {len(self.proxies)} بروكسي محمل")

    def _load_proxies(self):
        """تحميل قائمة البروكسي"""
        if not self.proxies_file.exists():
            # إنشاء ملف أمثلة
            sample_proxies = [
                {
                    "host": "proxy1.example.com",
                    "port": 8080,
                    "username": "user1",
                    "password": "pass1",
                    "proxy_type": "http",
                    "country": "US"
                },
                {
                    "host": "proxy2.example.com", 
                    "port": 1080,
                    "proxy_type": "socks5",
                    "country": "DE"
                }
            ]
            
            with open(self.proxies_file, 'w') as f:
                json.dump(sample_proxies, f, indent=2)
            
            LOGGER(__name__).info(f"📝 تم إنشاء ملف البروكسي النموذجي: {self.proxies_file}")
            return

        try:
            with open(self.proxies_file, 'r') as f:
                proxies_data = json.load(f)
            
            for proxy_data in proxies_data:
                proxy = ProxyInfo(
                    host=proxy_data['host'],
                    port=proxy_data['port'],
                    username=proxy_data.get('username'),
                    password=proxy_data.get('password'),
                    proxy_type=ProxyType(proxy_data.get('proxy_type', 'http')),
                    country=proxy_data.get('country')
                )
                self.proxies.append(proxy)
                
            LOGGER(__name__).info(f"✅ تم تحميل {len(self.proxies)} بروكسي")
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في تحميل البروكسي: {e}")

    async def get_working_proxy(self) -> Optional[ProxyInfo]:
        """الحصول على بروكسي يعمل"""
        if not self.proxies:
            return None

        # التحقق من ضرورة التدوير
        current_time = time.time()
        if (current_time - self.last_rotation) > self.rotation_interval:
            await self._rotate_proxies()

        # البحث عن بروكسي يعمل
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            # إعادة اختبار جميع البروكسي
            await self._test_all_proxies()
            working_proxies = [p for p in self.proxies if p.is_working]
        
        if working_proxies:
            # اختيار بروكسي بناءً على الأداء
            best_proxy = min(working_proxies, 
                           key=lambda p: (p.failure_count, p.response_time, p.last_used))
            
            best_proxy.last_used = current_time
            return best_proxy
        
        return None

    async def _rotate_proxies(self):
        """تدوير البروكسي"""
        LOGGER(__name__).info("🔄 بدء تدوير البروكسي...")
        
        # خلط ترتيب البروكسي
        random.shuffle(self.proxies)
        
        # إعادة ضبط بعض الإحصائيات
        for proxy in self.proxies:
            if proxy.failure_count > 0:
                proxy.failure_count = max(0, proxy.failure_count - 1)
        
        self.last_rotation = time.time()
        LOGGER(__name__).info("✅ تم تدوير البروكسي بنجاح")

    async def test_proxy(self, proxy: ProxyInfo, timeout: int = 10) -> bool:
        """اختبار بروكسي واحد"""
        try:
            start_time = time.time()
            
            # URLs للاختبار
            test_urls = [
                "https://httpbin.org/ip",
                "https://api.ipify.org?format=json",
                "https://ipapi.co/json/"
            ]
            
            connector = aiohttp.TCPConnector()
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_obj
            ) as session:
                
                for test_url in test_urls[:2]:  # اختبار أول URL فقط للسرعة
                    try:
                        async with session.get(
                            test_url,
                            proxy=proxy.url
                        ) as response:
                            
                            if response.status == 200:
                                response_time = time.time() - start_time
                                proxy.response_time = response_time
                                proxy.success_count += 1
                                proxy.is_working = True
                                
                                LOGGER(__name__).debug(f"✅ بروكسي يعمل: {proxy.host}:{proxy.port} ({response_time:.2f}s)")
                                return True
                                
                    except Exception as e:
                        LOGGER(__name__).debug(f"❌ خطأ في اختبار {proxy.host}:{proxy.port}: {e}")
                        continue
                
            # إذا فشل في جميع URLs
            proxy.failure_count += 1
            if proxy.failure_count >= self.max_failures_before_disable:
                proxy.is_working = False
                LOGGER(__name__).warning(f"🚫 تم تعطيل البروكسي: {proxy.host}:{proxy.port}")
            
            return False
            
        except Exception as e:
            proxy.failure_count += 1
            LOGGER(__name__).debug(f"❌ خطأ في اختبار البروكسي {proxy.host}:{proxy.port}: {e}")
            return False

    async def _test_all_proxies(self):
        """اختبار جميع البروكسي"""
        LOGGER(__name__).info("🔍 بدء اختبار جميع البروكسي...")
        
        # اختبار متوازي للبروكسي
        tasks = [self.test_proxy(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_count = sum(1 for result in results if result is True)
        LOGGER(__name__).info(f"📊 نتائج الاختبار: {working_count}/{len(self.proxies)} بروكسي يعمل")

    async def report_proxy_failure(self, proxy: ProxyInfo, error_type: str = "unknown"):
        """الإبلاغ عن فشل البروكسي"""
        proxy.failure_count += 1
        
        LOGGER(__name__).warning(f"⚠️ فشل البروكسي: {proxy.host}:{proxy.port} (السبب: {error_type})")
        
        if proxy.failure_count >= self.max_failures_before_disable:
            proxy.is_working = False
            LOGGER(__name__).warning(f"🚫 تم تعطيل البروكسي: {proxy.host}:{proxy.port}")
            
            # إشعار إذا انخفض عدد البروكسي العاملة كثيراً
            working_proxies = len([p for p in self.proxies if p.is_working])
            if working_proxies < len(self.proxies) * 0.3:  # أقل من 30%
                await self._notify_low_proxy_count(working_proxies)

    async def _notify_low_proxy_count(self, working_count: int):
        """إشعار بانخفاض عدد البروكسي العاملة"""
        try:
            from ZeMusic import config, tdlib_manager
            
            if hasattr(config, 'OWNER_ID') and tdlib_manager.bot_client:
                message = f"""
🚨 **تحذير: انخفاض عدد البروكسي العاملة!**

📊 **الإحصائيات:**
- العاملة: {working_count}
- المجموع: {len(self.proxies)}
- النسبة: {(working_count/len(self.proxies)*100):.1f}%

⚠️ **الإجراء المطلوب:**
- إضافة بروكسي جديدة
- التحقق من البروكسي الحالية
- مراجعة إعدادات الشبكة
                """
                
                await tdlib_manager.bot_client.client.call_method('sendMessage', {
                    'chat_id': config.OWNER_ID,
                    'input_message_content': {
                        '@type': 'inputMessageText',
                        'text': {'@type': 'formattedText', 'text': message.strip()}
                    }
                })
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال إشعار البروكسي: {e}")

    def get_proxy_stats(self) -> Dict:
        """إحصائيات البروكسي"""
        if not self.proxies:
            return {'total': 0, 'working': 0, 'failed': 0, 'avg_response_time': 0, 'avg_success_rate': 0}
        
        working = [p for p in self.proxies if p.is_working]
        failed = len(self.proxies) - len(working)
        
        avg_response_time = sum(p.response_time for p in working) / len(working) if working else 0
        avg_success_rate = sum(p.success_rate for p in self.proxies) / len(self.proxies) if self.proxies else 0
        
        return {
            'total': len(self.proxies),
            'working': len(working),
            'failed': failed,
            'avg_response_time': avg_response_time,
            'avg_success_rate': avg_success_rate
        }

    async def add_proxy(self, host: str, port: int, username: str = None, 
                       password: str = None, proxy_type: str = "http", country: str = None) -> bool:
        """إضافة بروكسي جديد"""
        try:
            proxy = ProxyInfo(
                host=host,
                port=port,
                username=username,
                password=password,
                proxy_type=ProxyType(proxy_type),
                country=country
            )
            
            # اختبار البروكسي قبل الإضافة
            if await self.test_proxy(proxy):
                self.proxies.append(proxy)
                await self._save_proxies()
                LOGGER(__name__).info(f"✅ تم إضافة بروكسي جديد: {host}:{port}")
                return True
            else:
                LOGGER(__name__).warning(f"❌ البروكسي لا يعمل: {host}:{port}")
                return False
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إضافة البروكسي: {e}")
            return False

    async def _save_proxies(self):
        """حفظ قائمة البروكسي"""
        try:
            proxies_data = []
            for proxy in self.proxies:
                proxy_dict = {
                    'host': proxy.host,
                    'port': proxy.port,
                    'proxy_type': proxy.proxy_type.value
                }
                
                if proxy.username:
                    proxy_dict['username'] = proxy.username
                if proxy.password:
                    proxy_dict['password'] = proxy.password
                if proxy.country:
                    proxy_dict['country'] = proxy.country
                
                proxies_data.append(proxy_dict)
            
            with open(self.proxies_file, 'w') as f:
                json.dump(proxies_data, f, indent=2)
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في حفظ البروكسي: {e}")


# النسخة الشاملة للاستخدام
proxy_manager = ProxyManager()