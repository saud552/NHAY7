import asyncio
import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db

@dataclass
class MusicSession:
    """جلسة تشغيل موسيقى"""
    chat_id: int
    assistant_id: int
    song_title: str
    song_url: str
    user_id: int
    start_time: float
    is_active: bool = True

class MusicManager:
    """مدير تشغيل الموسيقى مع TDLib"""
    
    def __init__(self):
        self.active_sessions: Dict[int, MusicSession] = {}
        self.queue_manager = QueueManager()
        self.assistant_allocator = AssistantAllocator()
        
    async def play_music(self, chat_id: int, query: str, user_id: int) -> Dict[str, Any]:
        """تشغيل موسيقى - الوظيفة الرئيسية"""
        try:
            # التحقق من وجود حساب مساعد متاح
            assistant = await self._get_available_assistant(chat_id)
            if not assistant:
                return {
                    'success': False,
                    'error': 'no_assistant',
                    'message': config.ASSISTANT_NOT_FOUND_MESSAGE.format(
                        SUPPORT_CHAT=config.SUPPORT_CHAT,
                        OWNER_ID=config.OWNER_ID
                    )
                }
            
            # البحث عن الموسيقى
            search_result = await self._search_music(query)
            if not search_result:
                return {
                    'success': False,
                    'error': 'not_found',
                    'message': "❌ لم يتم العثور على نتائج للبحث"
                }
            
            # إيقاف التشغيل السابق إذا وجد
            if chat_id in self.active_sessions:
                await self._stop_current_session(chat_id)
            
            # الانضمام للمكالمة الصوتية
            join_success = await assistant.join_group_call(chat_id)
            if not join_success:
                return {
                    'success': False,
                    'error': 'join_failed',
                    'message': "❌ فشل الانضمام للمكالمة الصوتية"
                }
            
            # بدء تشغيل الموسيقى
            stream_success = await assistant.stream_audio(chat_id, search_result['url'])
            if not stream_success:
                await assistant.leave_group_call(chat_id)
                return {
                    'success': False,
                    'error': 'stream_failed',
                    'message': "❌ فشل في تشغيل الموسيقى"
                }
            
            # إنشاء جلسة جديدة
            session = MusicSession(
                chat_id=chat_id,
                assistant_id=assistant.assistant_id,
                song_title=search_result['title'],
                song_url=search_result['url'],
                user_id=user_id,
                start_time=time.time()
            )
            
            self.active_sessions[chat_id] = session
            
            # تحديث إحصائيات المساعد
            await db.update_assistant_usage(assistant.assistant_id)
            await db.log_usage(chat_id, assistant.assistant_id, 'play_music', {
                'song_title': search_result['title'],
                'user_id': user_id
            })
            
            return {
                'success': True,
                'session': session,
                'assistant_id': assistant.assistant_id,
                'song_info': search_result
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تشغيل الموسيقى: {e}")
            return {
                'success': False,
                'error': 'unknown',
                'message': f"❌ خطأ غير متوقع: {str(e)}"
            }
    
    async def stop_music(self, chat_id: int) -> bool:
        """إيقاف تشغيل الموسيقى"""
        try:
            return await self._stop_current_session(chat_id)
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إيقاف الموسيقى: {e}")
            return False
    
    async def pause_music(self, chat_id: int) -> bool:
        """إيقاف مؤقت للموسيقى"""
        try:
            if chat_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[chat_id]
            assistant = self._get_assistant_by_id(session.assistant_id)
            
            if assistant:
                # هنا يمكن إضافة إيقاف مؤقت فعلي
                session.is_active = False
                return True
            
            return False
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الإيقاف المؤقت: {e}")
            return False
    
    async def resume_music(self, chat_id: int) -> bool:
        """استئناف تشغيل الموسيقى"""
        try:
            if chat_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[chat_id]
            assistant = self._get_assistant_by_id(session.assistant_id)
            
            if assistant:
                # هنا يمكن إضافة استئناف فعلي
                session.is_active = True
                return True
            
            return False
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الاستئناف: {e}")
            return False
    
    async def skip_music(self, chat_id: int) -> bool:
        """تخطي للأغنية التالية"""
        try:
            # إيقاف الحالية
            await self._stop_current_session(chat_id)
            
            # تشغيل التالية من القائمة
            next_song = await self.queue_manager.get_next(chat_id)
            if next_song:
                return await self.play_music(chat_id, next_song['query'], next_song['user_id'])
            
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في التخطي: {e}")
            return False
    
    async def get_current_session(self, chat_id: int) -> Optional[MusicSession]:
        """الحصول على الجلسة الحالية"""
        return self.active_sessions.get(chat_id)
    
    async def _get_available_assistant(self, chat_id: int) -> Optional[Any]:
        """الحصول على أفضل مساعد متاح"""
        return await self.assistant_allocator.get_best_assistant(chat_id)
    
    async def _search_music(self, query: str) -> Optional[Dict]:
        """البحث عن الموسيقى"""
        try:
            # هنا يتم التكامل مع محركات البحث
            # يمكن استخدام YouTube API, yt-dlp, إلخ
            
            # مثال بسيط (يجب استبداله بمحرك بحث حقيقي)
            return {
                'title': f"🎵 {query}",
                'url': f"https://example.com/music/{query}",
                'duration': "3:30",
                'thumbnail': "https://example.com/thumbnail.jpg"
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في البحث: {e}")
            return None
    
    async def _stop_current_session(self, chat_id: int) -> bool:
        """إيقاف الجلسة الحالية"""
        try:
            if chat_id not in self.active_sessions:
                return True
            
            session = self.active_sessions[chat_id]
            assistant = self._get_assistant_by_id(session.assistant_id)
            
            if assistant:
                await assistant.leave_group_call(chat_id)
            
            # إزالة الجلسة
            del self.active_sessions[chat_id]
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إيقاف الجلسة: {e}")
            return False
    
    def _get_assistant_by_id(self, assistant_id: int) -> Optional[Any]:
        """الحصول على المساعد بالمعرف"""
        for assistant in tdlib_manager.assistants:
            if assistant.assistant_id == assistant_id:
                return assistant
        return None
    
    async def cleanup_sessions(self):
        """تنظيف الجلسات المنتهية"""
        try:
            current_time = time.time()
            expired_sessions = []
            
            for chat_id, session in self.active_sessions.items():
                # تنظيف الجلسات القديمة (أكثر من ساعة)
                if current_time - session.start_time > 3600:
                    expired_sessions.append(chat_id)
            
            for chat_id in expired_sessions:
                await self._stop_current_session(chat_id)
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تنظيف الجلسات: {e}")


class QueueManager:
    """مدير قوائم انتظار الموسيقى"""
    
    def __init__(self):
        self.queues: Dict[int, List[Dict]] = {}
    
    async def add_to_queue(self, chat_id: int, song_info: Dict):
        """إضافة أغنية لقائمة الانتظار"""
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        
        self.queues[chat_id].append(song_info)
    
    async def get_next(self, chat_id: int) -> Optional[Dict]:
        """الحصول على الأغنية التالية"""
        if chat_id in self.queues and self.queues[chat_id]:
            return self.queues[chat_id].pop(0)
        return None
    
    async def get_queue(self, chat_id: int) -> List[Dict]:
        """الحصول على قائمة الانتظار"""
        return self.queues.get(chat_id, [])
    
    async def clear_queue(self, chat_id: int):
        """مسح قائمة الانتظار"""
        if chat_id in self.queues:
            self.queues[chat_id].clear()


class AssistantAllocator:
    """مخصص الحسابات المساعدة"""
    
    async def get_best_assistant(self, chat_id: int = None) -> Optional[Any]:
        """الحصول على أفضل مساعد متاح"""
        try:
            # الحصول على المساعد من إعدادات المجموعة أولاً
            if chat_id:
                settings = await db.get_chat_settings(chat_id)
                if settings.assistant_id:
                    specific_assistant = self._get_assistant_by_id(settings.assistant_id)
                    if specific_assistant and specific_assistant.is_connected:
                        return specific_assistant
            
            # البحث عن أفضل مساعد متاح
            available_assistants = [
                a for a in tdlib_manager.assistants 
                if a.is_connected and a.get_active_calls_count() < 10
            ]
            
            if not available_assistants:
                return None
            
            # اختيار الأقل استخداماً
            best_assistant = min(
                available_assistants,
                key=lambda a: a.get_active_calls_count()
            )
            
            return best_assistant
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في اختيار المساعد: {e}")
            return None
    
    def _get_assistant_by_id(self, assistant_id: int) -> Optional[Any]:
        """الحصول على المساعد بالمعرف"""
        for assistant in tdlib_manager.assistants:
            if assistant.assistant_id == assistant_id:
                return assistant
        return None
    
    async def assign_assistant_to_chat(self, chat_id: int, assistant_id: int) -> bool:
        """تخصيص مساعد لمجموعة معينة"""
        try:
            assistant = self._get_assistant_by_id(assistant_id)
            if assistant and assistant.is_connected:
                await db.update_chat_setting(chat_id, assistant_id=assistant_id)
                return True
            return False
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تخصيص المساعد: {e}")
            return False
    
    async def unassign_assistant_from_chat(self, chat_id: int) -> bool:
        """إلغاء تخصيص المساعد من المجموعة"""
        try:
            await db.update_chat_setting(chat_id, assistant_id=None)
            return True
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إلغاء تخصيص المساعد: {e}")
            return False


class VoiceChatManager:
    """مدير المكالمات الصوتية"""
    
    @staticmethod
    async def create_voice_chat(chat_id: int, title: str = "🎵 ZeMusic") -> bool:
        """إنشاء مكالمة صوتية جديدة"""
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected:
                return False
            
            result = await bot_client.client.call_method('createGroupCall', {
                'chat_id': chat_id,
                'title': title
            })
            
            return bool(result)
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إنشاء المكالمة الصوتية: {e}")
            return False
    
    @staticmethod
    async def end_voice_chat(chat_id: int) -> bool:
        """إنهاء المكالمة الصوتية"""
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected:
                return False
            
            # الحصول على معرف المكالمة
            chat = await bot_client.get_chat(chat_id)
            if chat and chat.get('voice_chat'):
                group_call_id = chat['voice_chat'].get('group_call_id')
                if group_call_id:
                    await bot_client.client.call_method('endGroupCall', {
                        'group_call_id': group_call_id
                    })
                    return True
            
            return False
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إنهاء المكالمة الصوتية: {e}")
            return False


# إنشاء مثيل عام لمدير الموسيقى
music_manager = MusicManager()

# مهمة تنظيف دورية
async def cleanup_task():
    """مهمة تنظيف دورية"""
    while True:
        try:
            await asyncio.sleep(1800)  # كل 30 دقيقة
            await music_manager.cleanup_sessions()
            await tdlib_manager.cleanup_idle_assistants()
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في مهمة التنظيف: {e}")

# بدء مهمة التنظيف
asyncio.create_task(cleanup_task())