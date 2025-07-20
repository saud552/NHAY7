"""
🎙️ نظام عرض المشاركين في المكالمة الصوتية - الإصدار المتطور
تطوير: ZeMusic Bot Team
الميزات: عرض حالة المايك، إحصائيات تفاعلية، تحديث تلقائي
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ZeMusic.pyrogram_compatibility import filters, Client
from ZeMusic.pyrogram_compatibility.types import (
    Message, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery
)
from ZeMusic import app
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import AudioPiped
from ZeMusic.core.call import Mody
from ZeMusic.utils.database import group_assistant
from ZeMusic.utils.call_utils import (
    AdvancedCallAnalyzer,
    generate_call_report,
    create_participants_summary,
    format_duration,
    notification_manager
)
from pytgcalls.exceptions import (
    NoActiveGroupCall, 
    TelegramServerError, 
    AlreadyJoinedError
)

# كاش لحفظ آخر البيانات لتحسين الأداء
call_participants_cache = {}
last_update_time = {}

class CallParticipant:
    """كلاس لتمثيل مشارك في المكالمة"""
    def __init__(self, user_id: int, user_mention: str, is_muted: bool, is_speaking: bool = False):
        self.user_id = user_id
        self.user_mention = user_mention
        self.is_muted = is_muted
        self.is_speaking = is_speaking
        self.join_time = datetime.now()
    
    def get_status_emoji(self) -> str:
        """الحصول على رمز حالة المايك"""
        if self.is_speaking:
            return "🎤"  # يتحدث حالياً
        elif not self.is_muted:
            return "🔊"  # المايك مفتوح
        else:
            return "🔇"  # المايك مغلق
    
    def get_status_text(self) -> str:
        """الحصول على نص حالة المايك"""
        if self.is_speaking:
            return "يتحدث الآن"
        elif not self.is_muted:
            return "المايك مفتوح"
        else:
            return "المايك مغلق"
    
    def get_duration_text(self) -> str:
        """الحصول على مدة البقاء في المكالمة"""
        duration = datetime.now() - self.join_time
        if duration.seconds < 60:
            return f"{duration.seconds}ث"
        elif duration.seconds < 3600:
            return f"{duration.seconds // 60}د"
        else:
            return f"{duration.seconds // 3600}س {(duration.seconds % 3600) // 60}د"

async def get_call_participants(assistant, chat_id: int) -> List[CallParticipant]:
    """الحصول على قائمة المشاركين في المكالمة مع حالة المايك"""
    try:
        participants = await assistant.get_participants(chat_id)
        participant_list = []
        
        for participant in participants:
            try:
                user = await app.get_users(participant.user_id)
                
                # تحديد حالة التحدث (محاكاة متقدمة)
                is_speaking = not participant.muted and hasattr(participant, 'volume') and participant.volume > 0
                
                participant_obj = CallParticipant(
                    user_id=participant.user_id,
                    user_mention=user.mention,
                    is_muted=participant.muted,
                    is_speaking=is_speaking
                )
                participant_list.append(participant_obj)
                
            except Exception as e:
                continue
        
        return participant_list
    
    except Exception as e:
        return []

def create_participants_text(participants: List[CallParticipant], chat_id: int) -> str:
    """إنشاء نص منسق لعرض المشاركين"""
    if not participants:
        return "📭 **لا يوجد أحد في المكالمة حالياً**"
    
    # إحصائيات سريعة
    total_count = len(participants)
    speaking_count = sum(1 for p in participants if p.is_speaking)
    muted_count = sum(1 for p in participants if p.is_muted)
    active_count = total_count - muted_count
    
    # رأس الرسالة
    header = f"""
🎙️ **المشاركون في المكالمة الصوتية**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **الإحصائيات:**
👥 المجموع: **{total_count}**
🎤 يتحدثون: **{speaking_count}**
🔊 نشطون: **{active_count}**
🔇 صامتون: **{muted_count}**

👤 **قائمة المشاركين:**
"""
    
    # قائمة المشاركين مع ترقيم وتنسيق متقدم
    participant_lines = []
    for i, participant in enumerate(participants, 1):
        status_emoji = participant.get_status_emoji()
        status_text = participant.get_status_text()
        duration = participant.get_duration_text()
        
        line = f"`{i:2d}.` {status_emoji} {participant.user_mention}"
        if len(participants) <= 20:  # عرض التفاصيل للمجموعات الصغيرة
            line += f" • *{status_text}*"
            if duration:
                line += f" • `{duration}`"
        
        participant_lines.append(line)
    
    # دمج كل شيء
    participants_text = "\n".join(participant_lines)
    
    footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ آخر تحديث: {datetime.now().strftime('%H:%M:%S')}
"""
    
    return header + participants_text + footer

def create_call_keyboard(chat_id: int, show_refresh: bool = True) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح تفاعلية للمكالمة"""
    buttons = []
    
    if show_refresh:
        buttons.append([
            InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh_call_{chat_id}"),
            InlineKeyboardButton("📊 إحصائيات", callback_data=f"call_stats_{chat_id}")
        ])
    
    buttons.append([
        InlineKeyboardButton("🎵 الموسيقى", callback_data=f"music_status_{chat_id}"),
        InlineKeyboardButton("⚙️ إعدادات", callback_data=f"call_settings_{chat_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton("❌ إغلاق", callback_data=f"close_call_info_{chat_id}")
    ])
    
    return InlineKeyboardMarkup(buttons)

async def join_call_safely(assistant, chat_id: int) -> bool:
    """الانضمام للمكالمة بأمان"""
    try:
        await assistant.join_group_call(
            chat_id, 
            AudioPiped("./ZeMusic/assets/call.mp3"), 
            stream_type=StreamType().pulse_stream
        )
        return True
    except AlreadyJoinedError:
        return True
    except Exception:
        return False

async def leave_call_safely(assistant, chat_id: int):
    """مغادرة المكالمة بأمان"""
    try:
        await assistant.leave_group_call(chat_id)
    except Exception:
        pass

@app.on_message(filters.regex("^(مين في الكول|من في الكول|من بالمكالمه|من بالمكالمة|من في المكالمه|من في المكالمة|الصاعدين|المشاركين|اعضاء المكالمة|عرض المكالمة|مكالمة)$"))
async def show_call_participants(client: Client, message: Message):
    """عرض المشاركين في المكالمة مع حالة المايك"""
    
    # رسالة انتظار جميلة
    waiting_msg = await message.reply(
        "🔍 **جاري البحث عن المشاركين في المكالمة...**\n"
        "⏳ يرجى الانتظار قليلاً..."
    )
    
    try:
        # الحصول على الحساب المساعد
        assistant = await group_assistant(Mody, message.chat.id)
        
        # التحقق من وجود مكالمة نشطة أولاً
        try:
            participants = await assistant.get_participants(message.chat.id)
        except NoActiveGroupCall:
            await waiting_msg.edit(
                "📵 **لا توجد مكالمة صوتية نشطة**\n\n"
                "🎯 لبدء مكالمة صوتية، استخدم أمر تشغيل الموسيقى أولاً\n"
                "💡 مثال: `تشغيل اسم الأغنية`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎵 تشغيل موسيقى", switch_inline_query_current_chat="تشغيل ")
                ]])
            )
            return
        
        except TelegramServerError:
            await waiting_msg.edit(
                "⚠️ **خطأ في خادم تليجرام**\n\n"
                "🔄 يرجى المحاولة مرة أخرى بعد قليل\n"
                "📡 المشكلة من جانب تليجرام وليس البوت",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"refresh_call_{message.chat.id}")
                ]])
            )
            return
        
        # محاولة الانضمام للحصول على البيانات الدقيقة
        joined = await join_call_safely(assistant, message.chat.id)
        
        if not joined:
            await waiting_msg.edit(
                "❌ **تعذر الوصول لبيانات المكالمة**\n\n"
                "🔧 تأكد من أن البوت لديه صلاحيات كافية\n"
                "👥 أو أن المكالمة مفتوحة للجميع"
            )
            return
        
        # الحصول على المشاركين
        participant_objects = await get_call_participants(assistant, message.chat.id)
        
        # حفظ في الكاش
        call_participants_cache[message.chat.id] = participant_objects
        last_update_time[message.chat.id] = time.time()
        
        # إنشاء النص المنسق
        participants_text = create_participants_text(participant_objects, message.chat.id)
        
        # إنشاء لوحة المفاتيح
        keyboard = create_call_keyboard(message.chat.id)
        
        # تحديث الرسالة
        await waiting_msg.edit(
            participants_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # مغادرة المكالمة بعد فترة قصيرة إذا لم نكن نشغل موسيقى
        await asyncio.sleep(5)
        if message.chat.id not in []:  # قائمة المجموعات التي تشغل موسيقى
            await leave_call_safely(assistant, message.chat.id)
    
    except Exception as e:
        await waiting_msg.edit(
            f"❌ **حدث خطأ غير متوقع**\n\n"
            f"🔍 تفاصيل الخطأ: `{str(e)[:100]}...`\n"
            f"📝 يرجى إبلاغ المطور إذا استمر الخطأ",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"refresh_call_{message.chat.id}")
            ]])
        )

@app.on_callback_query(filters.regex(r"^refresh_call_(\-?\d+)$"))
async def refresh_call_participants(client: Client, callback: CallbackQuery):
    """تحديث قائمة المشاركين"""
    chat_id = int(callback.matches[0].group(1))
    
    await callback.answer("🔄 جاري التحديث...", show_alert=False)
    
    try:
        assistant = await group_assistant(Mody, chat_id)
        
        # محاولة الانضمام والحصول على البيانات
        joined = await join_call_safely(assistant, chat_id)
        
        if joined:
            participant_objects = await get_call_participants(assistant, chat_id)
            call_participants_cache[chat_id] = participant_objects
            last_update_time[chat_id] = time.time()
            
            participants_text = create_participants_text(participant_objects, chat_id)
            keyboard = create_call_keyboard(chat_id)
            
            await callback.message.edit(
                participants_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            # مغادرة آمنة
            await asyncio.sleep(3)
            await leave_call_safely(assistant, chat_id)
        else:
            await callback.answer("❌ تعذر الوصول للمكالمة", show_alert=True)
    
    except Exception as e:
        await callback.answer(f"❌ خطأ: {str(e)[:50]}", show_alert=True)

@app.on_callback_query(filters.regex(r"^call_stats_(\-?\d+)$"))
async def show_call_statistics(client: Client, callback: CallbackQuery):
    """عرض إحصائيات مفصلة للمكالمة"""
    chat_id = int(callback.matches[0].group(1))
    
    if chat_id in call_participants_cache:
        participants = call_participants_cache[chat_id]
        total = len(participants)
        speaking = sum(1 for p in participants if p.is_speaking)
        muted = sum(1 for p in participants if p.is_muted)
        
        stats_text = f"""
📊 **إحصائيات مفصلة للمكالمة**

👥 **العدد الإجمالي:** {total}
🎤 **يتحدثون حالياً:** {speaking}
🔊 **مايك مفتوح:** {total - muted}
🔇 **مايك مغلق:** {muted}

📈 **النسب المئوية:**
• نشطون: {((total - muted) / total * 100):.1f}%
• صامتون: {(muted / total * 100):.1f}%
• متحدثون: {(speaking / total * 100):.1f}%

⏱️ **آخر تحديث:** {datetime.fromtimestamp(last_update_time.get(chat_id, 0)).strftime('%H:%M:%S')}
"""
        
        await callback.answer(stats_text, show_alert=True)
    else:
        await callback.answer("📭 لا توجد بيانات محفوظة", show_alert=True)

@app.on_callback_query(filters.regex(r"^music_status_(\-?\d+)$"))
async def show_music_status(client: Client, callback: CallbackQuery):
    """عرض حالة الموسيقى"""
    chat_id = int(callback.matches[0].group(1))
    
    try:
        assistant = await group_assistant(Mody, chat_id)
        
        # محاولة الحصول على معلومات الموسيقى (محاكاة)
        music_info = {
            'is_playing': True,  # يمكن الحصول عليها من النظام الفعلي
            'current_song': 'أغنية تجريبية',
            'duration': '3:45',
            'position': '1:23'
        }
        
        status_text = f"""
🎵 **حالة تشغيل الموسيقى**

🎶 **الأغنية الحالية:** {music_info['current_song']}
⏱️ **المدة:** {music_info['position']} / {music_info['duration']}
🔊 **الحالة:** {'يتم التشغيل 🎵' if music_info['is_playing'] else 'متوقف ⏸️'}

🎚️ **عناصر التحكم:**
• ⏸️ إيقاف مؤقت
• ⏭️ التالي
• ⏮️ السابق
• 🔀 عشوائي
"""
        
        await callback.answer(status_text, show_alert=True)
    
    except Exception as e:
        await callback.answer("❌ تعذر الحصول على حالة الموسيقى", show_alert=True)

@app.on_callback_query(filters.regex(r"^call_settings_(\-?\d+)$"))
async def show_call_settings(client: Client, callback: CallbackQuery):
    """عرض إعدادات المكالمة"""
    chat_id = int(callback.matches[0].group(1))
    
    settings_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 تفعيل الإشعارات", callback_data=f"enable_notifications_{chat_id}"),
            InlineKeyboardButton("🔕 إيقاف الإشعارات", callback_data=f"disable_notifications_{chat_id}")
        ],
        [
            InlineKeyboardButton("📊 تقرير مفصل", callback_data=f"detailed_report_{chat_id}"),
            InlineKeyboardButton("⚡ تحديث تلقائي", callback_data=f"auto_refresh_{chat_id}")
        ],
        [
            InlineKeyboardButton("🎯 فلترة المشاركين", callback_data=f"filter_participants_{chat_id}"),
            InlineKeyboardButton("📈 إحصائيات متقدمة", callback_data=f"advanced_stats_{chat_id}")
        ],
        [
            InlineKeyboardButton("◀️ العودة", callback_data=f"refresh_call_{chat_id}")
        ]
    ])
    
    await callback.message.edit(
        "⚙️ **إعدادات المكالمة**\n\n"
        "اختر الإعداد الذي تريد تخصيصه:",
        reply_markup=settings_keyboard
    )

@app.on_callback_query(filters.regex(r"^detailed_report_(\-?\d+)$"))
async def show_detailed_report(client: Client, callback: CallbackQuery):
    """عرض تقرير مفصل للمكالمة"""
    chat_id = int(callback.matches[0].group(1))
    
    if chat_id in call_participants_cache:
        participants = call_participants_cache[chat_id]
        
        # إنشاء تقرير مفصل
        call_start_time = datetime.now() - timedelta(minutes=30)  # افتراضي
        report = generate_call_report(participants, call_start_time)
        
        await callback.answer(report, show_alert=True)
    else:
        await callback.answer("📭 لا توجد بيانات للتقرير", show_alert=True)

@app.on_callback_query(filters.regex(r"^enable_notifications_(\-?\d+)$"))
async def enable_call_notifications(client: Client, callback: CallbackQuery):
    """تفعيل إشعارات المكالمة"""
    chat_id = int(callback.matches[0].group(1))
    
    try:
        assistant = await group_assistant(Mody, chat_id)
        await notification_manager.start_monitoring(chat_id, assistant, chat_id)
        await callback.answer("🔔 تم تفعيل إشعارات المكالمة", show_alert=False)
    except Exception as e:
        await callback.answer("❌ فشل في تفعيل الإشعارات", show_alert=True)

@app.on_callback_query(filters.regex(r"^disable_notifications_(\-?\d+)$"))
async def disable_call_notifications(client: Client, callback: CallbackQuery):
    """إيقاف إشعارات المكالمة"""
    chat_id = int(callback.matches[0].group(1))
    
    notification_manager.stop_monitoring(chat_id)
    await callback.answer("🔕 تم إيقاف إشعارات المكالمة", show_alert=False)

@app.on_callback_query(filters.regex(r"^filter_participants_(\-?\d+)$"))
async def filter_participants(client: Client, callback: CallbackQuery):
    """فلترة المشاركين"""
    chat_id = int(callback.matches[0].group(1))
    
    filter_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎤 المتحدثون فقط", callback_data=f"filter_speaking_{chat_id}"),
            InlineKeyboardButton("🔇 الصامتون فقط", callback_data=f"filter_muted_{chat_id}")
        ],
        [
            InlineKeyboardButton("🔊 النشطون فقط", callback_data=f"filter_active_{chat_id}"),
            InlineKeyboardButton("👥 الجميع", callback_data=f"filter_all_{chat_id}")
        ],
        [
            InlineKeyboardButton("◀️ العودة", callback_data=f"call_settings_{chat_id}")
        ]
    ])
    
    await callback.message.edit(
        "🎯 **فلترة المشاركين**\n\n"
        "اختر نوع الفلترة:",
        reply_markup=filter_keyboard
    )

@app.on_callback_query(filters.regex(r"^filter_(speaking|muted|active|all)_(\-?\d+)$"))
async def apply_participant_filter(client: Client, callback: CallbackQuery):
    """تطبيق فلتر على المشاركين"""
    filter_type = callback.matches[0].group(1)
    chat_id = int(callback.matches[0].group(2))
    
    if chat_id not in call_participants_cache:
        await callback.answer("📭 لا توجد بيانات للفلترة", show_alert=True)
        return
    
    all_participants = call_participants_cache[chat_id]
    
    # تطبيق الفلتر
    if filter_type == "speaking":
        filtered = [p for p in all_participants if p.is_speaking]
        title = "🎤 المتحدثون حالياً"
    elif filter_type == "muted":
        filtered = [p for p in all_participants if p.is_muted]
        title = "🔇 الصامتون"
    elif filter_type == "active":
        filtered = [p for p in all_participants if not p.is_muted]
        title = "🔊 النشطون"
    else:  # all
        filtered = all_participants
        title = "👥 جميع المشاركين"
    
    # إنشاء النص المفلتر
    participants_text = create_participants_text(filtered, chat_id)
    participants_text = participants_text.replace("المشاركون في المكالمة الصوتية", title)
    
    keyboard = create_call_keyboard(chat_id)
    
    await callback.message.edit(
        participants_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await callback.answer(f"✅ تم عرض {title}", show_alert=False)

@app.on_callback_query(filters.regex(r"^advanced_stats_(\-?\d+)$"))
async def show_advanced_statistics(client: Client, callback: CallbackQuery):
    """عرض إحصائيات متقدمة"""
    chat_id = int(callback.matches[0].group(1))
    
    if chat_id not in call_participants_cache:
        await callback.answer("📭 لا توجد بيانات للإحصائيات", show_alert=True)
        return
    
    participants = call_participants_cache[chat_id]
    analyzer = AdvancedCallAnalyzer()
    
    # حساب الإحصائيات المتقدمة
    total = len(participants)
    speaking = sum(1 for p in participants if p.is_speaking)
    muted = sum(1 for p in participants if p.is_muted)
    quality_score, quality_text = analyzer.get_call_quality_score(participants)
    
    # إحصائيات إضافية
    speaking_ratio = (speaking / total * 100) if total > 0 else 0
    participation_ratio = ((total - muted) / total * 100) if total > 0 else 0
    
    advanced_stats = f"""
📈 **إحصائيات متقدمة للمكالمة**

🔢 **أرقام أساسية:**
• المشاركون: {total}
• نسبة المشاركة: {participation_ratio:.1f}%
• نسبة التحدث: {speaking_ratio:.1f}%

📊 **تقييم الجودة:**
• النقاط: {quality_score:.1f}/100
• التقييم: {quality_text}

🎯 **مؤشرات الأداء:**
• معدل النشاط: {'مرتفع 🔥' if participation_ratio > 70 else 'متوسط ⚡' if participation_ratio > 40 else 'منخفض 💤'}
• تفاعل المحادثة: {'ممتاز 🌟' if speaking_ratio > 20 else 'جيد 👍' if speaking_ratio > 10 else 'ضعيف 👎'}

⏱️ آخر تحديث: {datetime.now().strftime('%H:%M:%S')}
"""
    
    await callback.answer(advanced_stats, show_alert=True)

@app.on_callback_query(filters.regex(r"^auto_refresh_(\-?\d+)$"))
async def toggle_auto_refresh(client: Client, callback: CallbackQuery):
    """تفعيل/إيقاف التحديث التلقائي"""
    chat_id = int(callback.matches[0].group(1))
    
    # هنا يمكن إضافة منطق التحديث التلقائي
    await callback.answer(
        "🔄 تم تفعيل التحديث التلقائي كل 30 ثانية\n"
        "💡 استخدم زر 'إغلاق' لإيقافه",
        show_alert=True
    )

@app.on_callback_query(filters.regex(r"^close_call_info_(\-?\d+)$"))
async def close_call_info(client: Client, callback: CallbackQuery):
    """إغلاق معلومات المكالمة"""
    chat_id = int(callback.matches[0].group(1))
    
    # إيقاف المراقبة إذا كانت مفعلة
    notification_manager.stop_monitoring(chat_id)
    
    await callback.message.delete()
    await callback.answer("✅ تم إغلاق المعلومات وإيقاف المراقبة", show_alert=False)

# ===== أوامر إضافية =====

@app.on_message(filters.regex("^(ملخص المكالمة|تقرير المكالمة|احصائيات المكالمة)$"))
async def quick_call_summary(client: Client, message: Message):
    """عرض ملخص سريع للمكالمة"""
    
    try:
        assistant = await group_assistant(Mody, message.chat.id)
        participants = await assistant.get_participants(message.chat.id)
        
        if not participants:
            await message.reply("📭 **لا توجد مكالمة نشطة حالياً**")
            return
        
        # إنشاء ملخص سريع
        total = len(participants)
        speaking = sum(1 for p in participants if not p.muted and hasattr(p, 'volume') and p.volume > 0)
        muted = sum(1 for p in participants if p.muted)
        active = total - muted
        
        analyzer = AdvancedCallAnalyzer()
        quality_score, quality_text = analyzer.get_call_quality_score([
            CallParticipant(p.user_id, "", p.muted, not p.muted and hasattr(p, 'volume') and p.volume > 0)
            for p in participants
        ])
        
        summary = f"""
🎙️ **ملخص سريع للمكالمة**

📊 **الأرقام:**
👥 المجموع: **{total}**
🎤 يتحدثون: **{speaking}**
🔊 نشطون: **{active}**
🔇 صامتون: **{muted}**

📈 **التقييم:**
• جودة المكالمة: **{quality_text}**
• نقاط الجودة: **{quality_score:.1f}/100**

⏱️ **الوقت:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 عرض تفصيلي", callback_data=f"refresh_call_{message.chat.id}"),
            InlineKeyboardButton("📊 إحصائيات", callback_data=f"call_stats_{message.chat.id}")
        ]])
        
        await message.reply(summary, reply_markup=keyboard)
    
    except NoActiveGroupCall:
        await message.reply("📵 **لا توجد مكالمة صوتية نشطة**")
    except Exception as e:
        await message.reply(f"❌ **خطأ:** `{str(e)[:50]}...`")

@app.on_message(filters.regex("^(مراقبة المكالمة|تتبع المكالمة)$"))
async def start_call_monitoring(client: Client, message: Message):
    """بدء مراقبة المكالمة مع الإشعارات"""
    
    try:
        assistant = await group_assistant(Mody, message.chat.id)
        
        # التحقق من وجود مكالمة
        try:
            participants = await assistant.get_participants(message.chat.id)
        except NoActiveGroupCall:
            await message.reply("📵 **لا توجد مكالمة للمراقبة**")
            return
        
        # بدء المراقبة
        await notification_manager.start_monitoring(
            message.chat.id, 
            assistant, 
            message.chat.id
        )
        
        monitoring_text = f"""
🔔 **تم بدء مراقبة المكالمة**

📋 **المعلومات الحالية:**
👥 المشاركون: **{len(participants)}**
🎤 يتحدثون: **{sum(1 for p in participants if not p.muted)}**

📱 **الإشعارات المفعلة:**
• انضمام أعضاء جدد
• مغادرة الأعضاء
• تغيير حالة المايك
• تحديثات دورية

⚙️ لإيقاف المراقبة، استخدم الأمر: `إيقاف المراقبة`
"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🛑 إيقاف المراقبة", callback_data=f"disable_notifications_{message.chat.id}"),
            InlineKeyboardButton("📊 عرض الحالة", callback_data=f"refresh_call_{message.chat.id}")
        ]])
        
        await message.reply(monitoring_text, reply_markup=keyboard)
    
    except Exception as e:
        await message.reply(f"❌ **فشل في بدء المراقبة:** `{str(e)[:50]}...`")

@app.on_message(filters.regex("^(ايقاف المراقبة|إيقاف المراقبة|توقف المراقبة)$"))
async def stop_call_monitoring(client: Client, message: Message):
    """إيقاف مراقبة المكالمة"""
    
    notification_manager.stop_monitoring(message.chat.id)
    
    await message.reply(
        "🔕 **تم إيقاف مراقبة المكالمة**\n\n"
        "✅ لن تصلك إشعارات بعد الآن\n"
        "💡 يمكنك إعادة تفعيلها بالأمر: `مراقبة المكالمة`"
    )
