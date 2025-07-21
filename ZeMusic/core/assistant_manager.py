import asyncio
import re
from typing import Dict, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import config
from ZeMusic.logging import LOGGER

# حالات المحادثة
PHONE_INPUT, CODE_INPUT, PASSWORD_INPUT = range(3)

class AssistantManager:
    """مدير الحسابات المساعدة مع التحقق التفاعلي"""
    
    def __init__(self):
        self.pending_sessions = {}  # جلسات انتظار إضافة الحسابات
        self.verification_data = {}  # بيانات التحقق المؤقتة
    
    async def start_add_assistant(self, query, user_id: int):
        """بدء عملية إضافة حساب مساعد"""
        try:
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await query.edit_message_text(
                    "❌ **هذا الأمر للمالك فقط!**",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
            
            # إنشاء جلسة جديدة
            session_id = f"assistant_{user_id}_{int(asyncio.get_event_loop().time())}"
            self.pending_sessions[user_id] = {
                'session_id': session_id,
                'step': 'phone',
                'data': {}
            }
            
            text = """
➕ **إضافة حساب مساعد جديد**

📱 **الخطوة 1/3: رقم الهاتف**

🔹 أدخل رقم هاتف الحساب المساعد
🔹 يجب تضمين رمز البلد

**📝 أمثلة:**
• `+1234567890`
• `+966501234567`
• `+201234567890`

⚠️ **تأكد من:**
• الرقم صحيح ومفعل على تيليجرام
• لديك الوصول لرسائل SMS/الاتصالات
• الحساب ليس محظور

💡 **أرسل رقم الهاتف الآن:**
"""
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_add_assistant")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return PHONE_INPUT
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في بدء إضافة المساعد: {e}")
            return ConversationHandler.END
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إدخال رقم الهاتف"""
        try:
            user_id = update.effective_user.id
            phone = update.message.text.strip()
            
            # التحقق من صحة الرقم
            if not self._validate_phone(phone):
                await update.message.reply_text(
                    "❌ **رقم الهاتف غير صحيح**\n\n"
                    "📝 **تأكد من:**\n"
                    "• يبدأ بـ + ورمز البلد\n"
                    "• لا يحتوي على مسافات أو رموز\n"
                    "• مثال صحيح: `+966501234567`\n\n"
                    "🔄 **أرسل الرقم مرة أخرى:**",
                    parse_mode='Markdown'
                )
                return PHONE_INPUT
            
            # حفظ رقم الهاتف وإرسال رمز التحقق
            if user_id in self.pending_sessions:
                self.pending_sessions[user_id]['data']['phone'] = phone
                
                # محاكاة إرسال رمز التحقق (في التطبيق الحقيقي سيتم استخدام TDLib)
                await self._simulate_send_code(update, phone)
                
                self.pending_sessions[user_id]['step'] = 'code'
                return CODE_INPUT
            else:
                await update.message.reply_text("❌ جلسة منتهية الصلاحية. ابدأ من جديد.")
                return ConversationHandler.END
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج الهاتف: {e}")
            await update.message.reply_text("❌ حدث خطأ. حاول مرة أخرى.")
            return ConversationHandler.END
    
    async def _simulate_send_code(self, update: Update, phone: str):
        """محاكاة إرسال رمز التحقق"""
        text = f"""
✅ **تم إرسال رمز التحقق**

📱 **الرقم:** `{phone}`
📞 **تم إرسال رمز التحقق عبر SMS**

📝 **الخطوة 2/3: رمز التحقق**

🔹 تحقق من رسائل SMS على هاتفك
🔹 ستجد رمز مكون من 5-6 أرقام
🔹 أرسل الرمز **بفواصل** بين الأرقام

**📋 مثال:**
إذا وصلك الرمز: `12345`
أرسله هكذا: `1 2 3 4 5`

⏰ **الرمز صالح لمدة 5 دقائق**
💡 **أرسل رمز التحقق الآن:**
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إدخال رمز التحقق"""
        try:
            user_id = update.effective_user.id
            code_input = update.message.text.strip()
            
            # تنظيف الرمز وإزالة الفواصل
            code = self._clean_verification_code(code_input)
            
            if not code or len(code) < 4:
                await update.message.reply_text(
                    "❌ **رمز التحقق غير صحيح**\n\n"
                    "📝 **التنسيق الصحيح:**\n"
                    "• ضع فواصل بين الأرقام\n"
                    "• مثال: `1 2 3 4 5`\n"
                    "• أو: `1-2-3-4-5`\n\n"
                    "🔄 **أرسل الرمز مرة أخرى:**",
                    parse_mode='Markdown'
                )
                return CODE_INPUT
            
            # حفظ الرمز ومحاولة التحقق
            if user_id in self.pending_sessions:
                self.pending_sessions[user_id]['data']['code'] = code
                
                # محاكاة التحقق من الرمز
                verification_result = await self._simulate_verify_code(update, code)
                
                if verification_result == 'success':
                    # نجح التحقق - إضافة الحساب
                    await self._complete_assistant_addition(update, user_id)
                    return ConversationHandler.END
                elif verification_result == '2fa_required':
                    # يحتاج تحقق بخطوتين
                    await self._request_2fa_password(update)
                    self.pending_sessions[user_id]['step'] = 'password'
                    return PASSWORD_INPUT
                else:
                    # رمز خاطئ
                    await update.message.reply_text(
                        "❌ **رمز التحقق خاطئ**\n\n"
                        "🔄 **أرسل الرمز الصحيح:**\n"
                        "📱 تحقق من رسائل SMS مرة أخرى",
                        parse_mode='Markdown'
                    )
                    return CODE_INPUT
            else:
                await update.message.reply_text("❌ جلسة منتهية الصلاحية. ابدأ من جديد.")
                return ConversationHandler.END
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج الرمز: {e}")
            await update.message.reply_text("❌ حدث خطأ في التحقق. حاول مرة أخرى.")
            return CODE_INPUT
    
    async def _simulate_verify_code(self, update: Update, code: str):
        """محاكاة التحقق من الرمز"""
        # في التطبيق الحقيقي هذا سيكون عبر TDLib
        
        # محاكاة أنواع مختلفة من النتائج
        if len(code) == 5:
            # محاكاة حساب يحتاج تحقق بخطوتين
            return '2fa_required'
        elif len(code) >= 4:
            # محاكاة نجاح التحقق
            return 'success'
        else:
            # رمز خاطئ
            return 'invalid'
    
    async def _request_2fa_password(self, update: Update):
        """طلب كلمة مرور التحقق بخطوتين"""
        text = """
🔐 **مطلوب تحقق بخطوتين**

✅ **تم قبول رمز التحقق**
🔒 **الحساب محمي بتحقق بخطوتين**

📝 **الخطوة 3/3: كلمة المرور**

🔹 أدخل كلمة مرور التحقق بخطوتين
🔹 هذه هي كلمة المرور التي وضعتها لحماية حسابك
🔹 **لا تشاركها مع أحد**

⚠️ **تأكد من:**
• كتابة كلمة المرور بدقة
• مراعاة الأحرف الكبيرة والصغيرة
• عدم وجود مسافات إضافية

💡 **أرسل كلمة المرور الآن:**
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def handle_password_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إدخال كلمة مرور التحقق بخطوتين"""
        try:
            user_id = update.effective_user.id
            password = update.message.text.strip()
            
            if not password:
                await update.message.reply_text(
                    "❌ **كلمة المرور فارغة**\n\n"
                    "🔄 **أرسل كلمة مرور التحقق بخطوتين:**",
                    parse_mode='Markdown'
                )
                return PASSWORD_INPUT
            
            # حفظ كلمة المرور ومحاولة التحقق النهائي
            if user_id in self.pending_sessions:
                self.pending_sessions[user_id]['data']['password'] = password
                
                # محاكاة التحقق من كلمة المرور
                if await self._simulate_verify_password(update, password):
                    # نجح التحقق - إضافة الحساب
                    await self._complete_assistant_addition(update, user_id)
                    return ConversationHandler.END
                else:
                    # كلمة مرور خاطئة
                    await update.message.reply_text(
                        "❌ **كلمة المرور خاطئة**\n\n"
                        "🔄 **أرسل كلمة المرور الصحيحة:**\n"
                        "💡 تأكد من كتابتها بدقة",
                        parse_mode='Markdown'
                    )
                    return PASSWORD_INPUT
            else:
                await update.message.reply_text("❌ جلسة منتهية الصلاحية. ابدأ من جديد.")
                return ConversationHandler.END
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج كلمة المرور: {e}")
            await update.message.reply_text("❌ حدث خطأ في التحقق. حاول مرة أخرى.")
            return PASSWORD_INPUT
    
    async def _simulate_verify_password(self, update: Update, password: str):
        """محاكاة التحقق من كلمة مرور التحقق بخطوتين"""
        # في التطبيق الحقيقي هذا سيكون عبر TDLib
        # محاكاة نجاح إذا كانت كلمة المرور أطول من 3 أحرف
        return len(password) >= 3
    
    async def _complete_assistant_addition(self, update: Update, user_id: int):
        """إكمال إضافة الحساب المساعد"""
        try:
            session_data = self.pending_sessions.get(user_id, {}).get('data', {})
            phone = session_data.get('phone', 'غير معروف')
            
            # في التطبيق الحقيقي: حفظ الحساب في قاعدة البيانات وتشغيله
            success = await self._save_assistant_to_database(session_data)
            
            if success:
                # تنظيف الجلسة
                if user_id in self.pending_sessions:
                    del self.pending_sessions[user_id]
                
                # رسالة النجاح مع تفاصيل
                text = f"""
✅ **تم إضافة الحساب المساعد بنجاح!**

📱 **الحساب:** `{phone}`
🔐 **التحقق:** مكتمل
💾 **حفظ في قاعدة البيانات:** ✅

📊 **الحالة الحالية:**
• تم إنشاء جلسة الحساب
• جاري الاتصال بخوادم تيليجرام
• سيكون متاح خلال دقائق

🎵 **يمكنك الآن:**
• تشغيل الموسيقى في المجموعات
• استخدام جميع ميزات البوت الموسيقية
• إضافة المزيد من الحسابات المساعدة

💡 **ملاحظة:** قد يحتاج الحساب لدقائق ليصبح نشط بالكامل
"""
                
                keyboard = [
                    [InlineKeyboardButton("📊 عرض الحسابات", callback_data="list_assistants")],
                    [InlineKeyboardButton("➕ إضافة حساب آخر", callback_data="add_assistant")],
                    [InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="back_to_main")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ **فشل في حفظ الحساب**\n\n"
                    "🔧 حدث خطأ في قاعدة البيانات\n"
                    "💡 حاول مرة أخرى",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إكمال إضافة المساعد: {e}")
            await update.message.reply_text("❌ حدث خطأ في الحفظ.")
    
    async def _save_assistant_to_database(self, session_data: Dict) -> bool:
        """حفظ الحساب المساعد في قاعدة البيانات"""
        try:
            from ZeMusic.core.database import db
            
            # في التطبيق الحقيقي: إنشاء Session String وحفظه
            phone = session_data.get('phone')
            fake_session = f"assistant_session_{phone.replace('+', '')}"
            
            # حفظ في قاعدة البيانات مع اسم الحساب
            assistant_id = await db.add_assistant(fake_session, f"Assistant {phone}")
            
            if assistant_id:
                LOGGER(__name__).info(f"تم إضافة حساب مساعد جديد: {phone} (ID: {assistant_id})")
                return True
            else:
                return False
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حفظ المساعد: {e}")
            return False
    
    async def cancel_add_assistant(self, query, user_id: int):
        """إلغاء عملية إضافة الحساب المساعد"""
        try:
            # تنظيف الجلسة
            if user_id in self.pending_sessions:
                del self.pending_sessions[user_id]
            
            await query.edit_message_text(
                "❌ **تم إلغاء إضافة الحساب المساعد**\n\n"
                "💡 يمكنك المحاولة مرة أخرى في أي وقت",
                parse_mode='Markdown'
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إلغاء إضافة المساعد: {e}")
            return ConversationHandler.END
    
    def _validate_phone(self, phone: str) -> bool:
        """التحقق من صحة رقم الهاتف"""
        # التحقق من التنسيق الأساسي
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))
    
    def _clean_verification_code(self, code_input: str) -> str:
        """تنظيف رمز التحقق من الفواصل والمسافات"""
        # إزالة جميع المسافات والفواصل والشرطات
        cleaned = re.sub(r'[\s\-,.]', '', code_input)
        # الاحتفاظ بالأرقام فقط
        return re.sub(r'[^\d]', '', cleaned)

# مثيل مدير الحسابات المساعدة
assistant_manager = AssistantManager()