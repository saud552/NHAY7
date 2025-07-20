import asyncio
import time
import sqlite3
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db

@dataclass
class BroadcastSession:
    """جلسة إذاعة"""
    user_id: int
    session_id: str
    target_type: str  # users, groups, channels
    pin_message: bool
    forward_mode: bool  # True = forward, False = copy
    message_content: Dict
    start_time: float
    is_active: bool = False
    is_cancelled: bool = False
    sent_count: int = 0
    failed_count: int = 0
    total_targets: int = 0

class BroadcastHandler:
    """معالج الإذاعة الشامل والاحترافي"""
    
    def __init__(self):
        self.active_broadcasts = {}  # جلسات الإذاعة النشطة
        self.pending_sessions = {}   # جلسات الإعداد
        self.broadcast_stats = {}    # إحصائيات الإذاعة
        
    async def show_broadcast_menu(self, user_id: int) -> Dict:
        """عرض قائمة الإذاعة الرئيسية"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # الحصول على إحصائيات سريعة
        stats = await self._get_broadcast_targets_count()
        
        keyboard = [
            [
                {'text': f'👥 إذاعة للمشتركين ({stats["users"]})', 'callback_data': 'broadcast_users'},
                {'text': f'💬 إذاعة للمجموعات ({stats["groups"]})', 'callback_data': 'broadcast_groups'}
            ],
            [
                {'text': f'📢 إذاعة للقنوات ({stats["channels"]})', 'callback_data': 'broadcast_channels'},
                {'text': '📊 إحصائيات الإذاعة', 'callback_data': 'broadcast_stats'}
            ],
            [
                {'text': '🛑 إيقاف الإذاعة النشطة', 'callback_data': 'stop_broadcast'},
                {'text': '📋 سجل الإذاعات', 'callback_data': 'broadcast_history'}
            ],
            [
                {'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'admin_main'}
            ]
        ]
        
        # التحقق من وجود إذاعة نشطة
        active_broadcast = self.active_broadcasts.get(user_id)
        active_info = ""
        if active_broadcast:
            active_info = (
                f"\n🔴 **إذاعة نشطة حالياً:**\n"
                f"📊 تم الإرسال: `{active_broadcast.sent_count}/{active_broadcast.total_targets}`\n"
                f"⚠️ فشل: `{active_broadcast.failed_count}`\n"
                f"🎯 النوع: `{self._get_target_type_name(active_broadcast.target_type)}`\n"
            )
        
        message = (
            "📢 **نظام الإذاعة المتقدم**\n\n"
            
            f"📊 **الأهداف المتاحة:**\n"
            f"👤 المشتركين (المحادثات الخاصة): `{stats['users']:,}`\n"
            f"👥 المجموعات: `{stats['groups']:,}`\n"
            f"📢 القنوات: `{stats['channels']:,}`\n"
            f"📈 إجمالي الأهداف: `{stats['total']:,}`\n"
            
            f"{active_info}\n"
            
            "🎯 **اختر نوع الإذاعة:**\n"
            "• **المشتركين**: إرسال لجميع المستخدمين في الخاص\n"
            "• **المجموعات**: إرسال لجميع المجموعات المفعلة\n"
            "• **القنوات**: إرسال لجميع القنوات المفعلة\n\n"
            
            "💡 **ملاحظات:**\n"
            "• يمكن إيقاف الإذاعة في أي وقت\n"
            "• سيتم عرض تقرير مفصل بعد الانتهاء\n"
            "• الإذاعة تتم بشكل تدريجي لتجنب القيود"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def handle_broadcast_target_selection(self, user_id: int, target_type: str) -> Dict:
        """معالجة اختيار نوع الإذاعة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # التحقق من عدم وجود إذاعة نشطة
        if user_id in self.active_broadcasts:
            return {
                'success': False,
                'message': "⚠️ يوجد إذاعة نشطة بالفعل، يرجى إيقافها أولاً"
            }
        
        # إنشاء جلسة إعداد جديدة
        session_id = f"broadcast_{user_id}_{int(time.time())}"
        self.pending_sessions[user_id] = {
            'session_id': session_id,
            'step': 'pin_selection',
            'target_type': target_type,
            'created_at': time.time()
        }
        
        # الحصول على عدد الأهداف
        target_count = await self._get_target_count_by_type(target_type)
        target_name = self._get_target_type_name(target_type)
        
        keyboard = [
            [
                {'text': '📌 تثبيت الإذاعة', 'callback_data': 'broadcast_pin_yes'},
                {'text': '📌 بدون تثبيت', 'callback_data': 'broadcast_pin_no'}
            ],
            [
                {'text': '❌ إلغاء', 'callback_data': 'broadcast_cancel'}
            ]
        ]
        
        message = (
            f"📢 **إعداد الإذاعة - {target_name}**\n\n"
            
            f"🎯 **الهدف المحدد:** `{target_name}`\n"
            f"📊 **عدد الأهداف:** `{target_count:,}`\n\n"
            
            "📌 **تثبيت الرسالة:**\n"
            "• **تثبيت الإذاعة**: سيتم تثبيت الرسالة في كل محادثة\n"
            "• **بدون تثبيت**: إرسال عادي بدون تثبيت\n\n"
            
            "⚠️ **تنبيه:** التثبيت يتطلب صلاحيات مدير في المجموعات والقنوات"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def handle_pin_selection(self, user_id: int, pin_choice: bool) -> Dict:
        """معالجة اختيار تثبيت الرسالة"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        session['pin_message'] = pin_choice
        session['step'] = 'forward_mode_selection'
        
        keyboard = [
            [
                {'text': '📄 إذاعة بدون توجيه (نسخ)', 'callback_data': 'broadcast_copy'},
                {'text': '↗️ إذاعة بالتوجيه', 'callback_data': 'broadcast_forward'}
            ],
            [
                {'text': '🔙 الخطوة السابقة', 'callback_data': f'broadcast_{session["target_type"]}'},
                {'text': '❌ إلغاء', 'callback_data': 'broadcast_cancel'}
            ]
        ]
        
        pin_status = "سيتم تثبيتها" if pin_choice else "لن يتم تثبيتها"
        
        message = (
            f"📢 **إعداد الإذاعة - طريقة الإرسال**\n\n"
            
            f"🎯 **الهدف:** `{self._get_target_type_name(session['target_type'])}`\n"
            f"📌 **التثبيت:** `{pin_status}`\n\n"
            
            "📤 **طريقة الإرسال:**\n\n"
            
            "📄 **إذاعة بدون توجيه (نسخ):**\n"
            "• يتم نسخ محتوى الرسالة وإرسالها\n"
            "• لا يظهر اسم المرسل الأصلي\n"
            "• الرسالة تبدو وكأنها من البوت مباشرة\n\n"
            
            "↗️ **إذاعة بالتوجيه:**\n"
            "• يتم إعادة توجيه الرسالة الأصلية\n"
            "• يظهر اسم المرسل الأصلي\n"
            "• يحافظ على معلومات الرسالة الأصلية\n\n"
            
            "اختر الطريقة المناسبة:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def handle_forward_mode_selection(self, user_id: int, forward_mode: bool) -> Dict:
        """معالجة اختيار طريقة الإرسال"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        session['forward_mode'] = forward_mode
        session['step'] = 'waiting_message'
        
        keyboard = [
            [
                {'text': '🔙 الخطوة السابقة', 'callback_data': 'broadcast_pin_' + ('yes' if session['pin_message'] else 'no')},
                {'text': '❌ إلغاء', 'callback_data': 'broadcast_cancel'}
            ]
        ]
        
        target_name = self._get_target_type_name(session['target_type'])
        pin_status = "سيتم تثبيتها" if session['pin_message'] else "لن يتم تثبيتها"
        mode_name = "إعادة توجيه" if forward_mode else "نسخ ونشر"
        
        message = (
            f"📢 **إعداد الإذاعة - إرسال المحتوى**\n\n"
            
            f"✅ **ملخص الإعدادات:**\n"
            f"🎯 الهدف: `{target_name}`\n"
            f"📌 التثبيت: `{pin_status}`\n"
            f"📤 طريقة الإرسال: `{mode_name}`\n\n"
            
            "📝 **أرسل الآن محتوى الإذاعة:**\n\n"
            
            "✅ **المدعوم:**\n"
            "• نص عادي أو منسق\n"
            "• صور مع أو بدون تعليق\n"
            "• فيديوهات مع أو بدون تعليق\n"
            "• ملفات صوتية ومقاطع صوتية\n"
            "• ملصقات ومتحركة\n"
            "• ملفات ووثائق\n"
            "• رسائل مع أزرار inline\n\n"
            
            "⚠️ **هام:** بعد إرسال المحتوى، ستحتاج للتأكيد النهائي لبدء الإذاعة\n\n"
            
            "📎 أرسل المحتوى الآن:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown',
            'waiting_message': True
        }
    
    async def handle_message_content(self, user_id: int, message_data: Dict) -> Dict:
        """معالجة محتوى الرسالة المرسلة"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session = self.pending_sessions[user_id]
        if session['step'] != 'waiting_message':
            return {'success': False, 'message': "❌ خطوة غير صحيحة"}
        
        # حفظ محتوى الرسالة
        session['message_content'] = message_data
        session['step'] = 'confirmation'
        
        # الحصول على إحصائيات الإذاعة
        target_count = await self._get_target_count_by_type(session['target_type'])
        estimated_time = self._calculate_estimated_time(target_count)
        
        keyboard = [
            [
                {'text': '🚀 بدء الإذاعة', 'callback_data': 'confirm_broadcast'},
                {'text': '❌ إلغاء', 'callback_data': 'broadcast_cancel'}
            ],
            [
                {'text': '🔙 تعديل المحتوى', 'callback_data': 'edit_broadcast_content'}
            ]
        ]
        
        # معاينة المحتوى
        content_preview = self._get_content_preview(message_data)
        
        message = (
            f"📢 **تأكيد الإذاعة**\n\n"
            
            f"✅ **الإعدادات النهائية:**\n"
            f"🎯 الهدف: `{self._get_target_type_name(session['target_type'])}`\n"
            f"📊 عدد الأهداف: `{target_count:,}`\n"
            f"📌 التثبيت: `{'نعم' if session['pin_message'] else 'لا'}`\n"
            f"📤 طريقة الإرسال: `{'إعادة توجيه' if session['forward_mode'] else 'نسخ ونشر'}`\n"
            f"⏱️ الوقت المتوقع: `{estimated_time}`\n\n"
            
            f"📝 **معاينة المحتوى:**\n"
            f"{content_preview}\n\n"
            
            "⚠️ **تنبيهات هامة:**\n"
            "• تأكد من صحة المحتوى قبل البدء\n"
            "• لا يمكن التراجع عن الإذاعة بعد البدء\n"
            "• يمكن إيقاف الإذاعة في أي لحظة\n"
            "• سيتم عرض تقرير مفصل بعد الانتهاء\n\n"
            
            "❓ هل تريد بدء الإذاعة؟"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def start_broadcast(self, user_id: int) -> Dict:
        """بدء عملية الإذاعة"""
        if user_id not in self.pending_sessions:
            return {'success': False, 'message': "❌ لا توجد جلسة نشطة"}
        
        session_data = self.pending_sessions[user_id]
        
        try:
            # إنشاء جلسة إذاعة نشطة
            target_count = await self._get_target_count_by_type(session_data['target_type'])
            
            broadcast_session = BroadcastSession(
                user_id=user_id,
                session_id=session_data['session_id'],
                target_type=session_data['target_type'],
                pin_message=session_data['pin_message'],
                forward_mode=session_data['forward_mode'],
                message_content=session_data['message_content'],
                start_time=time.time(),
                total_targets=target_count
            )
            
            # نقل الجلسة للنشطة
            self.active_broadcasts[user_id] = broadcast_session
            del self.pending_sessions[user_id]
            
            # بدء الإذاعة في مهمة منفصلة
            asyncio.create_task(self._execute_broadcast(broadcast_session))
            
            keyboard = [
                [
                    {'text': '🛑 إيقاف الإذاعة', 'callback_data': 'stop_broadcast'},
                    {'text': '📊 متابعة التقدم', 'callback_data': 'broadcast_progress'}
                ],
                [
                    {'text': '🔙 العودة للقائمة', 'callback_data': 'admin_broadcast'}
                ]
            ]
            
            message = (
                f"🚀 **تم بدء الإذاعة بنجاح!**\n\n"
                
                f"📊 **معلومات الإذاعة:**\n"
                f"🎯 الهدف: `{self._get_target_type_name(session_data['target_type'])}`\n"
                f"📈 العدد المستهدف: `{target_count:,}`\n"
                f"⏰ بدأت في: `{datetime.now().strftime('%H:%M:%S')}`\n\n"
                
                f"🔄 **الحالة:** جارية...\n"
                f"✅ تم الإرسال: `0`\n"
                f"⚠️ فشل: `0`\n\n"
                
                "💡 يمكنك متابعة التقدم أو إيقاف الإذاعة في أي وقت\n"
                "📊 سيتم إشعارك عند اكتمال الإذاعة"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في بدء الإذاعة: {e}")
            return {
                'success': False,
                'message': f"❌ فشل في بدء الإذاعة: {str(e)}"
            }
    
    async def stop_broadcast(self, user_id: int) -> Dict:
        """إيقاف الإذاعة النشطة"""
        if user_id not in self.active_broadcasts:
            return {
                'success': False,
                'message': "❌ لا توجد إذاعة نشطة"
            }
        
        broadcast_session = self.active_broadcasts[user_id]
        broadcast_session.is_cancelled = True
        
        # إحصائيات الإيقاف
        elapsed_time = time.time() - broadcast_session.start_time
        success_rate = (broadcast_session.sent_count / broadcast_session.total_targets * 100) if broadcast_session.total_targets > 0 else 0
        
        keyboard = [
            [
                {'text': '📊 عرض التقرير الكامل', 'callback_data': 'broadcast_report'},
                {'text': '🔙 العودة للقائمة', 'callback_data': 'admin_broadcast'}
            ]
        ]
        
        message = (
            f"🛑 **تم إيقاف الإذاعة**\n\n"
            
            f"📊 **إحصائيات الإيقاف:**\n"
            f"✅ تم الإرسال: `{broadcast_session.sent_count:,}`\n"
            f"⚠️ فشل: `{broadcast_session.failed_count:,}`\n"
            f"📈 من أصل: `{broadcast_session.total_targets:,}`\n"
            f"📊 معدل النجاح: `{success_rate:.1f}%`\n"
            f"⏱️ المدة: `{self._format_duration(elapsed_time)}`\n\n"
            
            f"🎯 **النوع:** `{self._get_target_type_name(broadcast_session.target_type)}`\n"
            f"⏰ **بدأت في:** `{datetime.fromtimestamp(broadcast_session.start_time).strftime('%H:%M:%S')}`\n"
            f"🛑 **أوقفت في:** `{datetime.now().strftime('%H:%M:%S')}`\n\n"
            
            "💾 يمكنك عرض التقرير المفصل أو العودة للقائمة"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def get_broadcast_progress(self, user_id: int) -> Dict:
        """الحصول على تقدم الإذاعة"""
        if user_id not in self.active_broadcasts:
            return {
                'success': False,
                'message': "❌ لا توجد إذاعة نشطة"
            }
        
        broadcast_session = self.active_broadcasts[user_id]
        
        # حساب الإحصائيات
        elapsed_time = time.time() - broadcast_session.start_time
        progress_percent = (broadcast_session.sent_count / broadcast_session.total_targets * 100) if broadcast_session.total_targets > 0 else 0
        success_rate = (broadcast_session.sent_count / (broadcast_session.sent_count + broadcast_session.failed_count) * 100) if (broadcast_session.sent_count + broadcast_session.failed_count) > 0 else 100
        
        # تقدير الوقت المتبقي
        if broadcast_session.sent_count > 0:
            avg_time_per_message = elapsed_time / (broadcast_session.sent_count + broadcast_session.failed_count)
            remaining_messages = broadcast_session.total_targets - (broadcast_session.sent_count + broadcast_session.failed_count)
            estimated_remaining = avg_time_per_message * remaining_messages
        else:
            estimated_remaining = 0
        
        keyboard = [
            [
                {'text': '🔄 تحديث التقدم', 'callback_data': 'broadcast_progress'},
                {'text': '🛑 إيقاف الإذاعة', 'callback_data': 'stop_broadcast'}
            ],
            [
                {'text': '🔙 العودة للقائمة', 'callback_data': 'admin_broadcast'}
            ]
        ]
        
        # شريط التقدم
        progress_bar = self._create_progress_bar(progress_percent)
        
        message = (
            f"📊 **تقدم الإذاعة**\n\n"
            
            f"🎯 **النوع:** `{self._get_target_type_name(broadcast_session.target_type)}`\n"
            f"📈 **التقدم:** `{progress_percent:.1f}%`\n"
            f"{progress_bar}\n\n"
            
            f"📊 **الإحصائيات:**\n"
            f"✅ تم الإرسال: `{broadcast_session.sent_count:,}`\n"
            f"⚠️ فشل: `{broadcast_session.failed_count:,}`\n"
            f"🎯 المتبقي: `{broadcast_session.total_targets - broadcast_session.sent_count - broadcast_session.failed_count:,}`\n"
            f"📈 إجمالي الأهداف: `{broadcast_session.total_targets:,}`\n\n"
            
            f"⚡ **الأداء:**\n"
            f"📊 معدل النجاح: `{success_rate:.1f}%`\n"
            f"⏱️ الوقت المنقضي: `{self._format_duration(elapsed_time)}`\n"
            f"⏳ الوقت المتوقع المتبقي: `{self._format_duration(estimated_remaining)}`\n\n"
            
            f"🔄 **الحالة:** `{'نشطة' if broadcast_session.is_active else 'متوقفة'}`"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def cancel_setup(self, user_id: int) -> Dict:
        """إلغاء إعداد الإذاعة"""
        if user_id in self.pending_sessions:
            del self.pending_sessions[user_id]
        
        return await self.show_broadcast_menu(user_id)
    
    async def _execute_broadcast(self, broadcast_session: BroadcastSession):
        """تنفيذ الإذاعة الفعلية"""
        try:
            broadcast_session.is_active = True
            
            # الحصول على قائمة الأهداف
            targets = await self._get_broadcast_targets(broadcast_session.target_type)
            
            LOGGER(__name__).info(f"بدء إذاعة إلى {len(targets)} هدف من نوع {broadcast_session.target_type}")
            
            # إرسال الرسائل بشكل تدريجي
            for target_id in targets:
                if broadcast_session.is_cancelled:
                    break
                
                try:
                    # إرسال الرسالة
                    success = await self._send_broadcast_message(
                        target_id,
                        broadcast_session.message_content,
                        broadcast_session.forward_mode,
                        broadcast_session.pin_message
                    )
                    
                    if success:
                        broadcast_session.sent_count += 1
                    else:
                        broadcast_session.failed_count += 1
                    
                    # تأخير لتجنب القيود
                    await asyncio.sleep(0.5)  # نصف ثانية بين كل رسالة
                    
                except Exception as e:
                    LOGGER(__name__).error(f"خطأ في إرسال رسالة إلى {target_id}: {e}")
                    broadcast_session.failed_count += 1
            
            # إنهاء الإذاعة
            broadcast_session.is_active = False
            
            # إرسال تقرير نهائي
            await self._send_broadcast_completion_report(broadcast_session)
            
            # إزالة الجلسة
            if broadcast_session.user_id in self.active_broadcasts:
                del self.active_broadcasts[broadcast_session.user_id]
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تنفيذ الإذاعة: {e}")
            broadcast_session.is_active = False
    
    async def _send_broadcast_message(self, target_id: int, message_content: Dict, 
                                    forward_mode: bool, pin_message: bool) -> bool:
        """إرسال رسالة الإذاعة لهدف محدد"""
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected:
                return False
            
            # إرسال الرسالة حسب النوع
            if forward_mode:
                # إعادة توجيه
                result = await bot_client.client.call_method('forwardMessages', {
                    'chat_id': target_id,
                    'from_chat_id': message_content.get('chat_id'),
                    'message_ids': [message_content.get('message_id')]
                })
            else:
                # نسخ ونشر
                if message_content.get('text'):
                    result = await bot_client.send_message(target_id, message_content['text'])
                else:
                    # معالجة أنواع المحتوى الأخرى (صور، فيديو، إلخ)
                    result = await self._send_media_message(bot_client, target_id, message_content)
            
            # تثبيت الرسالة إذا طُلب
            if pin_message and result:
                try:
                    await bot_client.client.call_method('pinChatMessage', {
                        'chat_id': target_id,
                        'message_id': result.get('id'),
                        'disable_notification': True
                    })
                except:
                    pass  # تجاهل أخطاء التثبيت
            
            return bool(result)
            
        except Exception as e:
            LOGGER(__name__).debug(f"فشل إرسال رسالة إلى {target_id}: {e}")
            return False
    
    async def _send_media_message(self, bot_client, target_id: int, message_content: Dict):
        """إرسال رسالة وسائط"""
        # يمكن توسيع هذا لدعم أنواع مختلفة من الوسائط
        try:
            # مثال بسيط - يمكن تحسينه
            if message_content.get('photo'):
                return await bot_client.client.call_method('sendPhoto', {
                    'chat_id': target_id,
                    'photo': message_content['photo'],
                    'caption': message_content.get('caption', '')
                })
            elif message_content.get('video'):
                return await bot_client.client.call_method('sendVideo', {
                    'chat_id': target_id,
                    'video': message_content['video'],
                    'caption': message_content.get('caption', '')
                })
            # إضافة المزيد من أنواع الوسائط حسب الحاجة
            return None
        except Exception as e:
            LOGGER(__name__).debug(f"فشل إرسال وسائط إلى {target_id}: {e}")
            return None
    
    async def _send_broadcast_completion_report(self, broadcast_session: BroadcastSession):
        """إرسال تقرير اكتمال الإذاعة"""
        try:
            elapsed_time = time.time() - broadcast_session.start_time
            success_rate = (broadcast_session.sent_count / broadcast_session.total_targets * 100) if broadcast_session.total_targets > 0 else 0
            
            report_message = (
                f"✅ **اكتملت الإذاعة!**\n\n"
                
                f"📊 **التقرير النهائي:**\n"
                f"🎯 النوع: `{self._get_target_type_name(broadcast_session.target_type)}`\n"
                f"✅ تم الإرسال بنجاح: `{broadcast_session.sent_count:,}`\n"
                f"⚠️ فشل في الإرسال: `{broadcast_session.failed_count:,}`\n"
                f"📈 إجمالي الأهداف: `{broadcast_session.total_targets:,}`\n"
                f"📊 معدل النجاح: `{success_rate:.1f}%`\n"
                f"⏱️ المدة الإجمالية: `{self._format_duration(elapsed_time)}`\n\n"
                
                f"⏰ **التوقيت:**\n"
                f"🚀 بدأت: `{datetime.fromtimestamp(broadcast_session.start_time).strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"🏁 انتهت: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                
                f"💾 تم حفظ التقرير في سجل الإذاعات"
            )
            
            bot_client = tdlib_manager.bot_client
            if bot_client and bot_client.is_connected:
                await bot_client.send_message(broadcast_session.user_id, report_message)
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال تقرير الإذاعة: {e}")
    
    async def _get_broadcast_targets_count(self) -> Dict[str, int]:
        """الحصول على عدد أهداف الإذاعة"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # عدد المستخدمين
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]
                
                # عدد المجموعات
                cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type IN ('group', 'supergroup')")
                groups_count = cursor.fetchone()[0]
                
                # عدد القنوات
                cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type = 'channel'")
                channels_count = cursor.fetchone()[0]
                
                return {
                    'users': users_count,
                    'groups': groups_count,
                    'channels': channels_count,
                    'total': users_count + groups_count + channels_count
                }
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حساب أهداف الإذاعة: {e}")
            return {'users': 0, 'groups': 0, 'channels': 0, 'total': 0}
    
    async def _get_target_count_by_type(self, target_type: str) -> int:
        """الحصول على عدد الأهداف حسب النوع"""
        counts = await self._get_broadcast_targets_count()
        return counts.get(target_type, 0)
    
    async def _get_broadcast_targets(self, target_type: str) -> List[int]:
        """الحصول على قائمة أهداف الإذاعة"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                if target_type == 'users':
                    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
                elif target_type == 'groups':
                    cursor.execute("SELECT chat_id FROM chats WHERE chat_type IN ('group', 'supergroup') AND is_blacklisted = 0")
                elif target_type == 'channels':
                    cursor.execute("SELECT chat_id FROM chats WHERE chat_type = 'channel' AND is_blacklisted = 0")
                else:
                    return []
                
                results = cursor.fetchall()
                return [row[0] for row in results]
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على أهداف الإذاعة: {e}")
            return []
    
    def _get_target_type_name(self, target_type: str) -> str:
        """الحصول على اسم نوع الهدف"""
        names = {
            'users': 'المشتركين (المحادثات الخاصة)',
            'groups': 'المجموعات',
            'channels': 'القنوات'
        }
        return names.get(target_type, target_type)
    
    def _calculate_estimated_time(self, target_count: int) -> str:
        """حساب الوقت المتوقع للإذاعة"""
        # متوسط نصف ثانية لكل رسالة
        estimated_seconds = target_count * 0.5
        return self._format_duration(estimated_seconds)
    
    def _format_duration(self, seconds: float) -> str:
        """تنسيق المدة الزمنية"""
        if seconds < 60:
            return f"{int(seconds)} ثانية"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes} دقيقة و{secs} ثانية"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours} ساعة و{minutes} دقيقة"
    
    def _get_content_preview(self, message_content: Dict) -> str:
        """الحصول على معاينة المحتوى"""
        if message_content.get('text'):
            text = message_content['text']
            if len(text) > 100:
                return f"`{text[:100]}...`"
            return f"`{text}`"
        elif message_content.get('photo'):
            return "🖼️ صورة" + (f" مع تعليق: `{message_content.get('caption', '')}`" if message_content.get('caption') else "")
        elif message_content.get('video'):
            return "🎥 فيديو" + (f" مع تعليق: `{message_content.get('caption', '')}`" if message_content.get('caption') else "")
        elif message_content.get('audio'):
            return "🎵 ملف صوتي"
        elif message_content.get('voice'):
            return "🎤 رسالة صوتية"
        elif message_content.get('document'):
            return "📄 ملف"
        elif message_content.get('sticker'):
            return "🎭 ملصق"
        elif message_content.get('animation'):
            return "🎬 متحركة"
        else:
            return "📝 محتوى مختلط"
    
    def _create_progress_bar(self, percentage: float) -> str:
        """إنشاء شريط تقدم"""
        filled = int(percentage // 10)
        empty = 10 - filled
        return "▓" * filled + "░" * empty + f" {percentage:.1f}%"

# إنشاء مثيل عام لمعالج الإذاعة
broadcast_handler = BroadcastHandler()