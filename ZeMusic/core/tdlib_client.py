import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, List, Optional, Any
from telegram.client import Telegram
from telegram.api import API

import config
from ZeMusic.logging import LOGGER

class TDLibClient:
    """عميل TDLib الأساسي"""
    
    def __init__(self, session_string: str = None, is_bot: bool = False, assistant_id: int = None):
        self.session_string = session_string
        self.is_bot = is_bot
        self.assistant_id = assistant_id
        self.client = None
        self.is_connected = False
        self.active_calls = set()
        self.last_activity = time.time()
        
        # إعدادات العميل
        self.client_config = {
            'api_id': config.API_ID,
            'api_hash': config.API_HASH,
            'database_encryption_key': f'zemusic_{assistant_id or "bot"}',
            'use_test_dc': False,
            'device_model': self._get_device_model(),
            'system_version': self._get_system_version(),
            'application_version': config.APPLICATION_VERSION,
            'system_language_code': 'ar',
            'database_directory': f'{config.TDLIB_FILES_PATH}/db_{assistant_id or "bot"}',
            'files_directory': f'{config.TDLIB_FILES_PATH}/files_{assistant_id or "bot"}',
            'use_chat_info_database': True,
            'use_message_database': False,  # توفير ذاكرة
            'use_secret_chats': False,
            'enable_storage_optimizer': True,
            'ignore_file_names': True
        }
        
        if is_bot:
            self.client_config['bot_token'] = config.BOT_TOKEN
        else:
            self.client_config['session_string'] = session_string
    
    def _get_device_model(self) -> str:
        """الحصول على نموذج جهاز عشوائي للتمويه"""
        devices = [
            "Samsung Galaxy S23", "iPhone 14 Pro", "Xiaomi 13 Pro",
            "OnePlus 11", "Google Pixel 7", "Huawei P50 Pro",
            "Desktop", "ZeMusic Bot"
        ]
        return random.choice(devices) if not self.is_bot else "ZeMusic Bot"
    
    def _get_system_version(self) -> str:
        """الحصول على إصدار نظام عشوائي"""
        systems = [
            "Android 13", "iOS 16.5", "Windows 11",
            "macOS 13.4", "Ubuntu 22.04", "Linux 6.2"
        ]
        return random.choice(systems) if not self.is_bot else config.SYSTEM_VERSION
    
    async def start(self) -> bool:
        """بدء العميل"""
        try:
            self.client = Telegram(**self.client_config)
            self.client.add_message_handler(self._handle_message)
            self.client.add_update_handler('updateUser', self._handle_user_update)
            self.client.add_update_handler('updateGroupCall', self._handle_group_call_update)
            
            await self.client.login()
            self.is_connected = True
            self.last_activity = time.time()
            
            # محاكاة سلوك طبيعي للحسابات المساعدة
            if not self.is_bot:
                await self._simulate_human_behavior()
            
            LOGGER(__name__).info(f"✅ تم تشغيل العميل {'البوت' if self.is_bot else f'المساعد {self.assistant_id}'}")
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ فشل تشغيل العميل: {e}")
            self.is_connected = False
            return False
    
    async def stop(self):
        """إيقاف العميل"""
        try:
            if self.client and self.is_connected:
                await self.client.stop()
                self.is_connected = False
                LOGGER(__name__).info(f"🛑 تم إيقاف العميل {'البوت' if self.is_bot else f'المساعد {self.assistant_id}'}")
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إيقاف العميل: {e}")
    
    async def _simulate_human_behavior(self):
        """محاكاة سلوك بشري طبيعي"""
        try:
            # تأخير عشوائي قبل بدء النشاط
            await asyncio.sleep(random.randint(5, 15))
            
            # الحصول على المحادثات
            chats = await self.client.call_method('getChats', {
                'limit': 20
            })
            
            # قراءة بعض المحادثات بشكل عشوائي
            for chat_id in chats.get('chat_ids', [])[:3]:
                try:
                    await asyncio.sleep(random.randint(1, 3))
                    await self.client.call_method('openChat', {'chat_id': chat_id})
                    await asyncio.sleep(random.randint(1, 2))
                    await self.client.call_method('closeChat', {'chat_id': chat_id})
                except:
                    continue
                    
        except Exception as e:
            LOGGER(__name__).debug(f"محاكاة السلوك البشري: {e}")
    
    async def _handle_message(self, update):
        """معالج الرسائل"""
        self.last_activity = time.time()
        # يمكن إضافة معالجة خاصة هنا
    
    async def _handle_user_update(self, update):
        """معالج تحديثات المستخدم"""
        self.last_activity = time.time()
    
    async def _handle_group_call_update(self, update):
        """معالج تحديثات المكالمات الجماعية"""
        self.last_activity = time.time()
        # تحديث حالة المكالمات النشطة
        if update.get('group_call'):
            call_id = update['group_call'].get('id')
            if call_id:
                if update['group_call'].get('is_active'):
                    self.active_calls.add(call_id)
                else:
                    self.active_calls.discard(call_id)
    
    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> Optional[Dict]:
        """إرسال رسالة"""
        try:
            if not self.is_connected:
                return None
                
            message_content = {
                '@type': 'inputMessageText',
                'text': {
                    '@type': 'formattedText',
                    'text': text
                }
            }
            
            result = await self.client.call_method('sendMessage', {
                'chat_id': chat_id,
                'input_message_content': message_content,
                'reply_markup': reply_markup
            })
            
            self.last_activity = time.time()
            return result
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال الرسالة: {e}")
            return None
    
    async def join_group_call(self, chat_id: int) -> bool:
        """الانضمام للمكالمة الجماعية"""
        try:
            if not self.is_connected:
                return False
            
            # البحث عن المكالمة الجماعية
            group_call = await self.client.call_method('getGroupCall', {
                'group_call_id': await self._get_group_call_id(chat_id)
            })
            
            if not group_call:
                # إنشاء مكالمة جديدة إذا لم توجد
                result = await self.client.call_method('createGroupCall', {
                    'chat_id': chat_id,
                    'title': "🎵 ZeMusic"
                })
                group_call_id = result.get('id')
            else:
                group_call_id = group_call.get('id')
            
            # الانضمام للمكالمة
            await self.client.call_method('joinGroupCall', {
                'group_call_id': group_call_id,
                'source': random.randint(1, 1000000),
                'muted': False,
                'is_my_video_enabled': False
            })
            
            self.active_calls.add(group_call_id)
            self.last_activity = time.time()
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الانضمام للمكالمة: {e}")
            return False
    
    async def leave_group_call(self, chat_id: int) -> bool:
        """مغادرة المكالمة الجماعية"""
        try:
            group_call_id = await self._get_group_call_id(chat_id)
            if not group_call_id:
                return True
            
            await self.client.call_method('leaveGroupCall', {
                'group_call_id': group_call_id
            })
            
            self.active_calls.discard(group_call_id)
            self.last_activity = time.time()
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في مغادرة المكالمة: {e}")
            return False
    
    async def _get_group_call_id(self, chat_id: int) -> Optional[int]:
        """الحصول على معرف المكالمة الجماعية"""
        try:
            chat = await self.client.call_method('getChat', {'chat_id': chat_id})
            voice_chat = chat.get('voice_chat')
            if voice_chat:
                return voice_chat.get('group_call_id')
            return None
        except:
            return None
    
    async def stream_audio(self, chat_id: int, audio_source: str) -> bool:
        """تشغيل الصوت في المكالمة"""
        try:
            group_call_id = await self._get_group_call_id(chat_id)
            if not group_call_id:
                return False
            
            # تشغيل الصوت
            await self.client.call_method('setGroupCallParticipantIsSpeaking', {
                'group_call_id': group_call_id,
                'source': random.randint(1, 1000000),
                'is_speaking': True
            })
            
            # هنا يمكن إضافة التكامل مع py-tgcalls
            # لتشغيل الصوت الفعلي
            
            self.last_activity = time.time()
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تشغيل الصوت: {e}")
            return False
    
    async def get_me(self) -> Optional[Dict]:
        """الحصول على معلومات الحساب"""
        try:
            if not self.is_connected:
                return None
            return await self.client.call_method('getMe')
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على معلومات الحساب: {e}")
            return None
    
    async def get_chat(self, chat_id: int) -> Optional[Dict]:
        """الحصول على معلومات المحادثة"""
        try:
            if not self.is_connected:
                return None
            return await self.client.call_method('getChat', {'chat_id': chat_id})
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على معلومات المحادثة: {e}")
            return None
    
    async def get_chat_member(self, chat_id: int, user_id: int) -> Optional[Dict]:
        """الحصول على معلومات عضو المحادثة"""
        try:
            if not self.is_connected:
                return None
            return await self.client.call_method('getChatMember', {
                'chat_id': chat_id,
                'member_id': {'@type': 'messageSenderUser', 'user_id': user_id}
            })
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على معلومات العضو: {e}")
            return None
    
    def is_idle(self, max_idle_time: int = 300) -> bool:
        """التحقق من الخمول"""
        return (time.time() - self.last_activity) > max_idle_time
    
    def get_active_calls_count(self) -> int:
        """الحصول على عدد المكالمات النشطة"""
        return len(self.active_calls)


class TDLibManager:
    """مدير عملاء TDLib"""
    
    def __init__(self):
        self.bot_client = None
        self.assistants: List[TDLibClient] = []
        self.assistant_sessions = {}
        self.assistant_usage = {}
        
    async def initialize_bot(self) -> bool:
        """تهيئة البوت الرئيسي"""
        try:
            self.bot_client = TDLibClient(is_bot=True)
            success = await self.bot_client.start()
            if success:
                LOGGER(__name__).info("🤖 تم تشغيل البوت الرئيسي بنجاح")
            return success
        except Exception as e:
            LOGGER(__name__).error(f"❌ فشل تشغيل البوت الرئيسي: {e}")
            return False
    
    async def load_assistants_from_database(self):
        """تحميل الحسابات المساعدة من قاعدة البيانات"""
        try:
            from ZeMusic.core.database import db
            assistants_data = await db.get_all_assistants()
            
            for assistant_data in assistants_data:
                await self.add_assistant(
                    assistant_data['session_string'],
                    assistant_data['assistant_id'],
                    assistant_data['name']
                )
                
            LOGGER(__name__).info(f"📱 تم تحميل {len(self.assistants)} حساب مساعد من قاعدة البيانات")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تحميل الحسابات المساعدة: {e}")
    
    async def add_assistant(self, session_string: str, assistant_id: int, name: str = None) -> bool:
        """إضافة حساب مساعد جديد"""
        try:
            # التحقق من عدم وجود مساعد بنفس المعرف
            for assistant in self.assistants:
                if assistant.assistant_id == assistant_id:
                    LOGGER(__name__).warning(f"⚠️ المساعد {assistant_id} موجود بالفعل")
                    return False
            
            assistant = TDLibClient(
                session_string=session_string,
                is_bot=False,
                assistant_id=assistant_id
            )
            
            success = await assistant.start()
            if success:
                self.assistants.append(assistant)
                self.assistant_sessions[assistant_id] = session_string
                self.assistant_usage[assistant_id] = 0
                
                # حفظ في قاعدة البيانات
                from ZeMusic.core.database import db
                await db.add_assistant(assistant_id, session_string, name or f"Assistant {assistant_id}")
                
                LOGGER(__name__).info(f"✅ تم إضافة المساعد {assistant_id} بنجاح")
                return True
            else:
                LOGGER(__name__).error(f"❌ فشل تشغيل المساعد {assistant_id}")
                return False
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إضافة المساعد: {e}")
            return False
    
    async def remove_assistant(self, assistant_id: int) -> bool:
        """إزالة حساب مساعد"""
        try:
            for i, assistant in enumerate(self.assistants):
                if assistant.assistant_id == assistant_id:
                    await assistant.stop()
                    self.assistants.pop(i)
                    self.assistant_sessions.pop(assistant_id, None)
                    self.assistant_usage.pop(assistant_id, None)
                    
                    # حذف من قاعدة البيانات
                    from ZeMusic.core.database import db
                    await db.remove_assistant(assistant_id)
                    
                    LOGGER(__name__).info(f"🗑️ تم إزالة المساعد {assistant_id}")
                    return True
            
            LOGGER(__name__).warning(f"⚠️ المساعد {assistant_id} غير موجود")
            return False
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إزالة المساعد: {e}")
            return False
    
    def get_available_assistant(self, chat_id: int = None) -> Optional[TDLibClient]:
        """الحصول على أفضل مساعد متاح"""
        if not self.assistants:
            return None
        
        # فلترة المساعدين المتصلين
        connected_assistants = [a for a in self.assistants if a.is_connected]
        if not connected_assistants:
            return None
        
        # اختيار المساعد الأقل استخداماً
        best_assistant = min(
            connected_assistants,
            key=lambda a: a.get_active_calls_count()
        )
        
        # تحديث إحصائيات الاستخدام
        if best_assistant.assistant_id:
            self.assistant_usage[best_assistant.assistant_id] += 1
        
        return best_assistant
    
    def get_assistants_count(self) -> int:
        """الحصول على عدد المساعدين"""
        return len(self.assistants)
    
    def get_connected_assistants_count(self) -> int:
        """الحصول على عدد المساعدين المتصلين"""
        return len([a for a in self.assistants if a.is_connected])
    
    async def cleanup_idle_assistants(self):
        """تنظيف المساعدين الخاملين"""
        try:
            for assistant in self.assistants:
                if assistant.is_idle(max_idle_time=1800):  # 30 دقيقة
                    await assistant.stop()
                    await asyncio.sleep(60)  # راحة دقيقة
                    await assistant.start()
                    
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تنظيف المساعدين: {e}")
    
    async def stop_all(self):
        """إيقاف جميع العملاء"""
        try:
            if self.bot_client:
                await self.bot_client.stop()
            
            for assistant in self.assistants:
                await assistant.stop()
                
            LOGGER(__name__).info("🛑 تم إيقاف جميع العملاء")
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إيقاف العملاء: {e}")


# مثيل عام لمدير TDLib
tdlib_manager = TDLibManager()