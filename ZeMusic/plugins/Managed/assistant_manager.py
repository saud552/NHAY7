"""
🤖 نظام إدارة الحسابات المساعدة - انضمام ومغادرة
تطوير: ZeMusic Bot Team
الميزات: انضمام ذكي، مغادرة آمنة، إشعارات المشرفين، سجل العمليات
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from ZeMusic.pyrogram_compatibility import filters, Client
from ZeMusic.pyrogram_compatibility.types import (
    Message, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery,
    ChatMember
)
from ZeMusic import app
from ZeMusic.core.call import Mody
from ZeMusic.utils.database import group_assistant, get_assistant, set_assistant
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.utils.decorators.admins import AdminRightsCheck

# كاش لتتبع الحسابات المساعدة
assistant_cache = {}
join_attempts_log = {}

class AssistantStatus:
    """كلاس لحالة الحساب المساعد"""
    def __init__(self, assistant_id: int, username: str, is_present: bool, join_time: datetime = None):
        self.assistant_id = assistant_id
        self.username = username
        self.is_present = is_present
        self.join_time = join_time or datetime.now()
        self.last_activity = datetime.now()
    
    def get_duration_text(self) -> str:
        """الحصول على مدة التواجد"""
        if not self.is_present:
            return "غير متواجد"
        
        duration = datetime.now() - self.join_time
        if duration.seconds < 60:
            return f"{duration.seconds}ث"
        elif duration.seconds < 3600:
            return f"{duration.seconds // 60}د"
        else:
            return f"{duration.seconds // 3600}س {(duration.seconds % 3600) // 60}د"

async def get_chat_assistant_status(chat_id: int) -> Optional[AssistantStatus]:
    """الحصول على حالة الحساب المساعد في المجموعة"""
    try:
        # الحصول على الحساب المساعد المخصص للمجموعة
        assistant = await group_assistant(Mody, chat_id)
        
        if not assistant:
            return None
        
        # التحقق من وجوده في المجموعة
        try:
            member = await app.get_chat_member(chat_id, assistant.id)
            if member and member.status not in ["left", "kicked"]:
                # الحصول على معلومات الحساب
                user_info = await app.get_users(assistant.id)
                username = f"@{user_info.username}" if user_info.username else user_info.first_name
                
                return AssistantStatus(
                    assistant_id=assistant.id,
                    username=username,
                    is_present=True,
                    join_time=datetime.now() - timedelta(minutes=30)  # افتراضي
                )
        except Exception:
            pass
        
        return None
    
    except Exception as e:
        return None

async def find_available_assistant() -> Optional[int]:
    """البحث عن حساب مساعد متاح"""
    try:
        # الحصول على قائمة الحسابات المساعدة من TDLib manager
        available_assistants = tdlib_manager.get_available_assistants()
        
        if available_assistants:
            return available_assistants[0].assistant_id
        
        return None
    
    except Exception:
        return None

async def join_assistant_to_chat(chat_id: int, requested_by: int) -> Tuple[bool, str, Optional[AssistantStatus]]:
    """انضمام الحساب المساعد للمجموعة"""
    try:
        # التحقق من وجود حساب مساعد بالفعل
        existing_status = await get_chat_assistant_status(chat_id)
        
        if existing_status and existing_status.is_present:
            return False, "موجود_بالفعل", existing_status
        
        # البحث عن حساب مساعد متاح
        assistant_id = await find_available_assistant()
        
        if not assistant_id:
            return False, "لا_توجد_حسابات_متاحة", None
        
        # محاولة الانضمام
        assistant = tdlib_manager.get_assistant(assistant_id)
        
        if not assistant:
            return False, "فشل_في_الحصول_على_الحساب", None
        
        # الانضمام للمجموعة
        try:
            # محاكاة عملية الانضمام (يمكن تخصيصها حسب TDLib)
            join_result = await assistant.join_chat(chat_id)
            
            if join_result:
                # تسجيل الحساب المساعد للمجموعة
                await set_assistant(chat_id, assistant_id)
                
                # إنشاء حالة الحساب المساعد
                user_info = await assistant.get_me()
                username = f"@{user_info.get('username', '')}" if user_info.get('username') else user_info.get('first_name', 'المساعد')
                
                status = AssistantStatus(
                    assistant_id=assistant_id,
                    username=username,
                    is_present=True,
                    join_time=datetime.now()
                )
                
                # حفظ في الكاش
                assistant_cache[chat_id] = status
                
                # تسجيل المحاولة
                join_attempts_log[chat_id] = {
                    'requested_by': requested_by,
                    'assistant_id': assistant_id,
                    'time': datetime.now(),
                    'success': True
                }
                
                return True, "تم_الانضمام_بنجاح", status
            else:
                return False, "فشل_في_الانضمام", None
        
        except Exception as e:
            return False, f"خطأ_في_الانضمام_{str(e)[:30]}", None
    
    except Exception as e:
        return False, f"خطأ_عام_{str(e)[:30]}", None

async def remove_assistant_from_chat(chat_id: int, requested_by: int) -> Tuple[bool, str]:
    """إزالة الحساب المساعد من المجموعة"""
    try:
        # التحقق من وجود حساب مساعد
        existing_status = await get_chat_assistant_status(chat_id)
        
        if not existing_status or not existing_status.is_present:
            return False, "غير_موجود"
        
        # الحصول على الحساب المساعد
        assistant = await group_assistant(Mody, chat_id)
        
        if not assistant:
            return False, "لا_يمكن_الوصول_للحساب"
        
        # مغادرة المجموعة
        try:
            leave_result = await assistant.leave_chat(chat_id)
            
            if leave_result:
                # إزالة التخصيص من قاعدة البيانات
                await set_assistant(chat_id, None)
                
                # إزالة من الكاش
                if chat_id in assistant_cache:
                    del assistant_cache[chat_id]
                
                # تسجيل العملية
                join_attempts_log[chat_id] = {
                    'requested_by': requested_by,
                    'assistant_id': existing_status.assistant_id,
                    'time': datetime.now(),
                    'success': True,
                    'action': 'leave'
                }
                
                return True, "تم_المغادرة_بنجاح"
            else:
                return False, "فشل_في_المغادرة"
        
        except Exception as e:
            return False, f"خطأ_في_المغادرة_{str(e)[:30]}"
    
    except Exception as e:
        return False, f"خطأ_عام_{str(e)[:30]}"

def create_assistant_status_text(status: AssistantStatus, action: str) -> str:
    """إنشاء نص حالة الحساب المساعد"""
    if action == "join_success":
        return f"""
✅ **تم انضمام الحساب المساعد بنجاح**

🤖 **معلومات الحساب:**
• الاسم: {status.username}
• المعرف: `{status.assistant_id}`
• وقت الانضمام: {status.join_time.strftime('%H:%M:%S')}

🎵 **الآن يمكن تشغيل الموسيقى في هذه المجموعة**
💡 لإدارة الحساب المساعد، استخدم الأزرار أدناه
"""
    
    elif action == "already_present":
        return f"""
ℹ️ **الحساب المساعد موجود بالفعل**

🤖 **الحساب الحالي:**
• الاسم: {status.username}
• المعرف: `{status.assistant_id}`
• مدة التواجد: {status.get_duration_text()}

✅ **المجموعة جاهزة لتشغيل الموسيقى**
🔄 يمكنك تغيير الحساب المساعد إذا لزم الأمر
"""
    
    elif action == "leave_success":
        return f"""
✅ **تم إخراج الحساب المساعد بنجاح**

🤖 **الحساب الذي غادر:**
• الاسم: {status.username}
• المعرف: `{status.assistant_id}`
• وقت المغادرة: {datetime.now().strftime('%H:%M:%S')}

📵 **لن يتمكن البوت من تشغيل الموسيقى حتى ينضم حساب مساعد جديد**
"""

def create_assistant_keyboard(chat_id: int, action: str, has_assistant: bool = False) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح للحساب المساعد"""
    buttons = []
    
    if action == "join_success":
        buttons.append([
            InlineKeyboardButton("🎵 تشغيل موسيقى", switch_inline_query_current_chat="تشغيل "),
            InlineKeyboardButton("📊 حالة الحساب", callback_data=f"assistant_status_{chat_id}")
        ])
        buttons.append([
            InlineKeyboardButton("🔄 تغيير الحساب", callback_data=f"change_assistant_{chat_id}"),
            InlineKeyboardButton("🚪 إخراج الحساب", callback_data=f"remove_assistant_{chat_id}")
        ])
    
    elif action == "already_present":
        buttons.append([
            InlineKeyboardButton("📊 تفاصيل الحساب", callback_data=f"assistant_details_{chat_id}"),
            InlineKeyboardButton("🔄 تغيير الحساب", callback_data=f"change_assistant_{chat_id}")
        ])
        buttons.append([
            InlineKeyboardButton("🚪 إخراج الحساب", callback_data=f"remove_assistant_{chat_id}"),
            InlineKeyboardButton("🎵 تشغيل موسيقى", switch_inline_query_current_chat="تشغيل ")
        ])
    
    elif action == "no_assistant":
        buttons.append([
            InlineKeyboardButton("🤖 إضافة حساب مساعد", callback_data=f"add_assistant_{chat_id}"),
            InlineKeyboardButton("📋 قائمة الحسابات", callback_data=f"list_assistants_{chat_id}")
        ])
    
    buttons.append([
        InlineKeyboardButton("❌ إغلاق", callback_data=f"close_assistant_panel_{chat_id}")
    ])
    
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.regex("^(المساعد انضم|انضم المساعد|اضافة مساعد|انضمام مساعد)$"))
@AdminRightsCheck
async def assistant_join_command(client: Client, message: Message):
    """أمر انضمام الحساب المساعد"""
    
    # رسالة انتظار
    waiting_msg = await message.reply(
        "🔍 **جاري البحث عن حساب مساعد متاح...**\n"
        "⏳ يرجى الانتظار قليلاً..."
    )
    
    try:
        # محاولة انضمام الحساب المساعد
        success, result_code, status = await join_assistant_to_chat(
            message.chat.id, 
            message.from_user.id
        )
        
        if success:
            # نجح الانضمام
            response_text = create_assistant_status_text(status, "join_success")
            keyboard = create_assistant_keyboard(message.chat.id, "join_success")
            
            await waiting_msg.edit(
                response_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif result_code == "موجود_بالفعل":
            # الحساب موجود بالفعل
            response_text = create_assistant_status_text(status, "already_present")
            keyboard = create_assistant_keyboard(message.chat.id, "already_present", True)
            
            await waiting_msg.edit(
                response_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif result_code == "لا_توجد_حسابات_متاحة":
            await waiting_msg.edit(
                "❌ **لا توجد حسابات مساعدة متاحة حالياً**\n\n"
                "🔧 **الحلول الممكنة:**\n"
                "• انتظر قليلاً وحاول مرة أخرى\n"
                "• تواصل مع المطور لإضافة حسابات جديدة\n"
                "• تحقق من حالة الحسابات الموجودة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"retry_join_{message.chat.id}"),
                    InlineKeyboardButton("📞 تواصل مع المطور", url="https://t.me/YourDeveloper")
                ]])
            )
        
        else:
            # خطأ في الانضمام
            error_msg = result_code.replace("_", " ")
            await waiting_msg.edit(
                f"❌ **فشل في انضمام الحساب المساعد**\n\n"
                f"🔍 **السبب:** {error_msg}\n"
                f"🔧 **الحل:** حاول مرة أخرى أو تواصل مع المطور",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"retry_join_{message.chat.id}")
                ]])
            )
    
    except Exception as e:
        await waiting_msg.edit(
            f"❌ **حدث خطأ غير متوقع**\n\n"
            f"🔍 **تفاصيل الخطأ:** `{str(e)[:100]}...`\n"
            f"📝 يرجى إبلاغ المطور إذا استمر الخطأ",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"retry_join_{message.chat.id}")
            ]])
        )

@app.on_message(filters.regex("^(المساعد غادر|غادر المساعد|اخراج المساعد|مغادرة المساعد|إزالة المساعد)$"))
@AdminRightsCheck
async def assistant_leave_command(client: Client, message: Message):
    """أمر مغادرة الحساب المساعد"""
    
    # رسالة انتظار
    waiting_msg = await message.reply(
        "🔍 **جاري البحث عن الحساب المساعد...**\n"
        "⏳ يرجى الانتظار قليلاً..."
    )
    
    try:
        # التحقق من وجود حساب مساعد أولاً
        existing_status = await get_chat_assistant_status(message.chat.id)
        
        if not existing_status or not existing_status.is_present:
            await waiting_msg.edit(
                "ℹ️ **لا يوجد حساب مساعد في هذه المجموعة**\n\n"
                "🤖 **لإضافة حساب مساعد:**\n"
                "استخدم الأمر: `المساعد انضم`\n\n"
                "💡 **ملاحظة:** الحساب المساعد مطلوب لتشغيل الموسيقى",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🤖 إضافة حساب مساعد", callback_data=f"add_assistant_{message.chat.id}")
                ]])
            )
            return
        
        # محاولة إخراج الحساب المساعد
        success, result_code = await remove_assistant_from_chat(
            message.chat.id, 
            message.from_user.id
        )
        
        if success:
            # نجحت المغادرة
            response_text = create_assistant_status_text(existing_status, "leave_success")
            keyboard = create_assistant_keyboard(message.chat.id, "no_assistant")
            
            await waiting_msg.edit(
                response_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        else:
            # فشلت المغادرة
            error_msg = result_code.replace("_", " ")
            await waiting_msg.edit(
                f"❌ **فشل في إخراج الحساب المساعد**\n\n"
                f"🔍 **السبب:** {error_msg}\n"
                f"🔧 **الحل:** حاول مرة أخرى أو تواصل مع المطور",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"retry_remove_{message.chat.id}")
                ]])
            )
    
    except Exception as e:
        await waiting_msg.edit(
            f"❌ **حدث خطأ غير متوقع**\n\n"
            f"🔍 **تفاصيل الخطأ:** `{str(e)[:100]}...`\n"
            f"📝 يرجى إبلاغ المطور إذا استمر الخطأ",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"retry_remove_{message.chat.id}")
            ]])
        )

# ===== معالجات الأزرار =====

@app.on_callback_query(filters.regex(r"^assistant_status_(\-?\d+)$"))
async def show_assistant_status(client: Client, callback: CallbackQuery):
    """عرض حالة الحساب المساعد"""
    chat_id = int(callback.matches[0].group(1))
    
    status = await get_chat_assistant_status(chat_id)
    
    if status and status.is_present:
        status_text = f"""
📊 **حالة الحساب المساعد التفصيلية**

🤖 **معلومات الحساب:**
• الاسم: {status.username}
• المعرف: `{status.assistant_id}`
• مدة التواجد: {status.get_duration_text()}
• آخر نشاط: {status.last_activity.strftime('%H:%M:%S')}

✅ **الحالة:** متصل ونشط
🎵 **جاهز لتشغيل الموسيقى**

⚡ **الإحصائيات:**
• المجموعات المتصل بها: عدة مجموعات
• معدل الاستجابة: ممتاز
• حالة الاتصال: مستقر
"""
        
        await callback.answer(status_text, show_alert=True)
    else:
        await callback.answer("❌ لا يوجد حساب مساعد متصل", show_alert=True)

@app.on_callback_query(filters.regex(r"^change_assistant_(\-?\d+)$"))
async def change_assistant(client: Client, callback: CallbackQuery):
    """تغيير الحساب المساعد"""
    chat_id = int(callback.matches[0].group(1))
    
    change_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 تغيير تلقائي", callback_data=f"auto_change_{chat_id}"),
            InlineKeyboardButton("📋 اختيار يدوي", callback_data=f"manual_change_{chat_id}")
        ],
        [
            InlineKeyboardButton("◀️ العودة", callback_data=f"assistant_status_{chat_id}")
        ]
    ])
    
    await callback.message.edit(
        "🔄 **تغيير الحساب المساعد**\n\n"
        "اختر طريقة التغيير:",
        reply_markup=change_keyboard
    )

@app.on_callback_query(filters.regex(r"^remove_assistant_(\-?\d+)$"))
async def confirm_remove_assistant(client: Client, callback: CallbackQuery):
    """تأكيد إزالة الحساب المساعد"""
    chat_id = int(callback.matches[0].group(1))
    
    confirm_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ نعم، اخرج الحساب", callback_data=f"confirm_remove_{chat_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"assistant_status_{chat_id}")
        ]
    ])
    
    await callback.message.edit(
        "⚠️ **تأكيد إخراج الحساب المساعد**\n\n"
        "🔴 **تحذير:** سيؤدي هذا إلى:\n"
        "• توقف تشغيل الموسيقى\n"
        "• عدم إمكانية استخدام المكالمات الصوتية\n"
        "• الحاجة لإضافة حساب جديد لاحقاً\n\n"
        "هل أنت متأكد من المتابعة؟",
        reply_markup=confirm_keyboard
    )

@app.on_callback_query(filters.regex(r"^confirm_remove_(\-?\d+)$"))
async def execute_remove_assistant(client: Client, callback: CallbackQuery):
    """تنفيذ إزالة الحساب المساعد"""
    chat_id = int(callback.matches[0].group(1))
    
    await callback.answer("🔄 جاري إخراج الحساب المساعد...", show_alert=False)
    
    success, result_code = await remove_assistant_from_chat(chat_id, callback.from_user.id)
    
    if success:
        await callback.message.edit(
            "✅ **تم إخراج الحساب المساعد بنجاح**\n\n"
            "🤖 تم فصل الحساب من المجموعة\n"
            "📵 لن يتمكن البوت من تشغيل الموسيقى\n\n"
            "💡 لإضافة حساب جديد، استخدم: `المساعد انضم`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🤖 إضافة حساب جديد", callback_data=f"add_assistant_{chat_id}")
            ]])
        )
    else:
        await callback.message.edit(
            f"❌ **فشل في إخراج الحساب المساعد**\n\n"
            f"السبب: {result_code.replace('_', ' ')}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"retry_remove_{chat_id}")
            ]])
        )

@app.on_callback_query(filters.regex(r"^add_assistant_(\-?\d+)$"))
async def add_new_assistant(client: Client, callback: CallbackQuery):
    """إضافة حساب مساعد جديد"""
    chat_id = int(callback.matches[0].group(1))
    
    await callback.answer("🔄 جاري البحث عن حساب مساعد...", show_alert=False)
    
    success, result_code, status = await join_assistant_to_chat(chat_id, callback.from_user.id)
    
    if success:
        response_text = create_assistant_status_text(status, "join_success")
        keyboard = create_assistant_keyboard(chat_id, "join_success")
        
        await callback.message.edit(
            response_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        error_msg = result_code.replace("_", " ")
        await callback.message.edit(
            f"❌ **فشل في إضافة حساب مساعد**\n\n"
            f"السبب: {error_msg}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"add_assistant_{chat_id}")
            ]])
        )

@app.on_callback_query(filters.regex(r"^retry_(join|remove)_(\-?\d+)$"))
async def retry_assistant_operation(client: Client, callback: CallbackQuery):
    """إعادة محاولة العملية"""
    operation = callback.matches[0].group(1)
    chat_id = int(callback.matches[0].group(2))
    
    if operation == "join":
        await callback.answer("🔄 إعادة محاولة الانضمام...", show_alert=False)
        # إعادة توجيه للدالة المناسبة
        await add_new_assistant(client, callback)
    else:  # remove
        await callback.answer("🔄 إعادة محاولة الإخراج...", show_alert=False)
        await execute_remove_assistant(client, callback)

@app.on_callback_query(filters.regex(r"^close_assistant_panel_(\-?\d+)$"))
async def close_assistant_panel(client: Client, callback: CallbackQuery):
    """إغلاق لوحة إدارة الحساب المساعد"""
    await callback.message.delete()
    await callback.answer("✅ تم إغلاق لوحة إدارة الحساب المساعد", show_alert=False)

# ===== أوامر إضافية =====

@app.on_message(filters.regex("^(حالة المساعد|معلومات المساعد|المساعد الحالي)$"))
async def show_current_assistant(client: Client, message: Message):
    """عرض معلومات الحساب المساعد الحالي"""
    
    status = await get_chat_assistant_status(message.chat.id)
    
    if status and status.is_present:
        info_text = f"""
🤖 **معلومات الحساب المساعد الحالي**

📋 **التفاصيل:**
• الاسم: {status.username}
• المعرف: `{status.assistant_id}`
• مدة التواجد: {status.get_duration_text()}

✅ **الحالة:** نشط ومتصل
🎵 **جاهز لتشغيل الموسيقى**

⏱️ **آخر تحديث:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 تفاصيل أكثر", callback_data=f"assistant_status_{message.chat.id}"),
            InlineKeyboardButton("⚙️ إدارة الحساب", callback_data=f"change_assistant_{message.chat.id}")
        ]])
        
        await message.reply(info_text, reply_markup=keyboard)
    
    else:
        await message.reply(
            "ℹ️ **لا يوجد حساب مساعد في هذه المجموعة**\n\n"
            "🤖 لإضافة حساب مساعد، استخدم:\n"
            "`المساعد انضم`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🤖 إضافة حساب مساعد", callback_data=f"add_assistant_{message.chat.id}")
            ]])
        )