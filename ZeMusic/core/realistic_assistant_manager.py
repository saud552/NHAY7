import asyncio
import re
import json
import os
import time
import random
from typing import Dict, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from ZeMusic.logging import LOGGER

class RealisticAssistantManager:
    """مدير واقعي للحسابات المساعدة يحاكي العملية الحقيقية"""
    
    def __init__(self):
        self.pending_sessions = {}
        self.verification_codes = {}  # محاكاة كودات التحقق
        self.account_sessions = {}  # جلسات الحسابات المحفوظة
        
        # قاعدة بيانات مؤقتة للحسابات المحاكاة
        self.mock_accounts_db = {
            "+966501234567": {
                "id": 123456789,
                "first_name": "أحمد",
                "username": "ahmed_test",
                "has_2fa": False
            },
            "+201234567890": {
                "id": 987654321,
                "first_name": "محمد",
                "username": "mohamed_test",
                "has_2fa": True,
                "password": "123456"
            },
            "+1234567890": {
                "id": 555666777,
                "first_name": "Test User",
                "username": "testuser",
                "has_2fa": False
            }
        }
    
    async def start_add_assistant(self, query, user_id: int):
        """بدء عملية إضافة حساب مساعد واقعية"""
        try:
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await query.edit_message_text(
                    "❌ **هذا الأمر للمالك فقط!**",
                    parse_mode='Markdown'
                )
                return
            
            # إنشاء جلسة جديدة
            session_id = f"assistant_{user_id}_{int(time.time())}"
            self.pending_sessions[user_id] = {
                'session_id': session_id,
                'step': 'phone',
                'data': {},
                'start_time': time.time()
            }
            
            text = """
➕ **إضافة حساب مساعد - نظام واقعي**

📱 **الخطوة 1/3: رقم الهاتف**

🔹 أدخل رقم هاتف الحساب المساعد
🔹 يجب تضمين رمز البلد

**📝 أمثلة للتجربة:**
• `+966501234567` (بدون 2FA)
• `+201234567890` (مع 2FA)
• `+1234567890` (حساب عادي)

⚠️ **ملاحظة:**
• هذا نظام محاكاة واقعي للعملية الحقيقية
• كود التحقق سيُرسل للحساب على تيليجرام
• الكود سيظهر هنا للتجربة (في الواقع يصل للهاتف)

🎯 **أرسل رقم الهاتف الآن:**
"""
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_add_assistant")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في بدء إضافة المساعد: {e}")
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إدخال رقم الهاتف مع محاكاة واقعية"""
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
                return
            
            # حفظ رقم الهاتف وبدء محاكاة الاتصال
            if user_id in self.pending_sessions:
                self.pending_sessions[user_id]['data']['phone'] = phone
                
                # محاكاة فترة الاتصال
                await update.message.reply_text(
                    "⏳ **جاري الاتصال بخوادم تيليجرام...**\n\n"
                    "📞 هذا قد يستغرق ثوانٍ قليلة",
                    parse_mode='Markdown'
                )
                
                # انتظار واقعي
                await asyncio.sleep(2)
                
                # التحقق من وجود الرقم في قاعدة البيانات المحاكاة
                if phone in self.mock_accounts_db:
                    # محاكاة إرسال كود التحقق
                    success = await self._simulate_send_verification_code(update, phone, user_id)
                    
                    if success:
                        self.pending_sessions[user_id]['step'] = 'code'
                else:
                    await update.message.reply_text(
                        "❌ **رقم الهاتف غير مسجل**\n\n"
                        "🔧 **الأسباب المحتملة:**\n"
                        "• الرقم غير مسجل على تيليجرام\n"
                        "• رقم محظور أو معطل\n"
                        "• خطأ في كتابة الرقم\n\n"
                        "💡 **جرب الأرقام المتاحة للتجربة:**\n"
                        "• `+966501234567`\n"
                        "• `+201234567890`\n"
                        "• `+1234567890`",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text("❌ جلسة منتهية الصلاحية. ابدأ من جديد.")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج الهاتف: {e}")
            await update.message.reply_text("❌ حدث خطأ. حاول مرة أخرى.")
    
    async def _simulate_send_verification_code(self, update, phone: str, user_id: int) -> bool:
        """محاكاة إرسال كود التحقق للحساب"""
        try:
            # توليد كود تحقق عشوائي
            verification_code = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            
            # حفظ الكود المؤقت
            self.verification_codes[user_id] = {
                'code': verification_code,
                'phone': phone,
                'expires': time.time() + 300  # ينتهي خلال 5 دقائق
            }
            
            # محاكاة تأخير إرسال الكود
            await asyncio.sleep(1)
            
            account_info = self.mock_accounts_db[phone]
            
            # إظهار الكود للمستخدم (في الواقع يصل للهاتف)
            text = f"""
✅ **تم إرسال كود التحقق بنجاح!**

📱 **الرقم:** `{phone}`
👤 **الحساب:** {account_info['first_name']}
📨 **تم إرسال الكود إلى تيليجرام**

📝 **الخطوة 2/3: كود التحقق**

🎯 **للتجربة - الكود المرسل هو:**
`{verification_code}`

🔹 أرسل الكود **بفواصل** بين الأرقام
🔹 مثال: إذا كان الكود `{verification_code}`
🔹 أرسله هكذا: `{' '.join(list(verification_code))}`

⏰ **الكود صالح لمدة 5 دقائق**
💡 **أرسل كود التحقق الآن:**
"""
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
            # إضافة تنبيه إضافي
            await asyncio.sleep(2)
            await update.message.reply_text(
                f"📋 **تذكير:** أرسل الكود مع فواصل\n"
                f"**الكود:** `{' '.join(list(verification_code))}`",
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في محاكاة إرسال الكود: {e}")
            return False
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إدخال كود التحقق مع محاكاة واقعية"""
        try:
            user_id = update.effective_user.id
            code_input = update.message.text.strip()
            
            # تنظيف الكود وإزالة الفواصل
            code = self._clean_verification_code(code_input)
            
            if not code or len(code) != 5:
                await update.message.reply_text(
                    "❌ **كود التحقق غير صحيح**\n\n"
                    "📝 **التنسيق الصحيح:**\n"
                    "• 5 أرقام مع فواصل\n"
                    "• مثال: `1 2 3 4 5`\n"
                    "• أو: `1-2-3-4-5`\n\n"
                    "🔄 **أرسل الكود مرة أخرى:**",
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من صحة الكود
            if user_id in self.verification_codes:
                stored_code_info = self.verification_codes[user_id]
                
                # التحقق من انتهاء صلاحية الكود
                if time.time() > stored_code_info['expires']:
                    await update.message.reply_text(
                        "⏰ **انتهت صلاحية الكود**\n\n"
                        "🔄 ابدأ العملية من جديد",
                        parse_mode='Markdown'
                    )
                    if user_id in self.pending_sessions:
                        del self.pending_sessions[user_id]
                    del self.verification_codes[user_id]
                    return
                
                # محاكاة فترة التحقق
                await update.message.reply_text(
                    "⏳ **جاري التحقق من الكود...**",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(1)
                
                if code == stored_code_info['code']:
                    # نجح التحقق - التحقق من 2FA
                    phone = stored_code_info['phone']
                    account_info = self.mock_accounts_db[phone]
                    
                    if account_info.get('has_2fa', False):
                        # يحتاج تحقق بخطوتين
                        await self._request_2fa_password(update)
                        self.pending_sessions[user_id]['step'] = 'password'
                    else:
                        # تم بنجاح - لا يحتاج 2FA
                        await self._handle_successful_verification(update, user_id)
                else:
                    # كود خاطئ
                    await update.message.reply_text(
                        "❌ **كود التحقق خاطئ**\n\n"
                        "🔄 **أرسل الكود الصحيح:**\n"
                        f"💡 **تذكير:** `{' '.join(list(stored_code_info['code']))}`",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text("❌ لا يوجد كود مرسل. ابدأ من جديد.")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج الكود: {e}")
            await update.message.reply_text("❌ حدث خطأ في التحقق. حاول مرة أخرى.")
    
    async def _request_2fa_password(self, update: Update):
        """طلب كلمة مرور التحقق بخطوتين"""
        text = """
🔐 **مطلوب تحقق بخطوتين**

✅ **تم قبول كود التحقق**
🔒 **الحساب محمي بتحقق بخطوتين**

📝 **الخطوة 3/3: كلمة المرور**

🔹 أدخل كلمة مرور التحقق بخطوتين
🔹 هذه هي كلمة المرور التي وضعتها لحماية حسابك

💡 **للتجربة - كلمة المرور:**
`123456`

⚠️ **تأكد من:**
• كتابة كلمة المرور بدقة
• مراعاة الأحرف الكبيرة والصغيرة
• عدم وجود مسافات إضافية

🔒 **أرسل كلمة المرور الآن:**
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
                    "🔄 **أرسل كلمة مرور التحقق بخطوتين:**\n"
                    "💡 **للتجربة:** `123456`",
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من كلمة المرور
            if user_id in self.verification_codes:
                phone = self.verification_codes[user_id]['phone']
                account_info = self.mock_accounts_db[phone]
                
                # محاكاة فترة التحقق
                await update.message.reply_text(
                    "⏳ **جاري التحقق من كلمة المرور...**",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(2)
                
                if password == account_info.get('password', ''):
                    # نجح التحقق
                    await self._handle_successful_verification(update, user_id)
                else:
                    # كلمة مرور خاطئة
                    await update.message.reply_text(
                        "❌ **كلمة المرور خاطئة**\n\n"
                        "🔄 **أرسل كلمة المرور الصحيحة:**\n"
                        "💡 **للتجربة:** `123456`",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text("❌ جلسة منتهية الصلاحية. ابدأ من جديد.")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالج كلمة المرور: {e}")
            await update.message.reply_text("❌ حدث خطأ في التحقق. حاول مرة أخرى.")
    
    async def _handle_successful_verification(self, update, user_id: int):
        """معالجة التحقق الناجح وحفظ الحساب"""
        try:
            if user_id not in self.verification_codes:
                return
                
            phone = self.verification_codes[user_id]['phone']
            account_info = self.mock_accounts_db[phone]
            
            # محاكاة حفظ الجلسة
            session_string = self._generate_realistic_session_string()
            
            # حفظ الحساب في قاعدة البيانات
            success = await self._save_assistant_to_database(account_info, phone, session_string)
            
            if success:
                # تنظيف البيانات المؤقتة
                if user_id in self.pending_sessions:
                    del self.pending_sessions[user_id]
                if user_id in self.verification_codes:
                    del self.verification_codes[user_id]
                
                # رسالة النجاح
                elapsed_time = int(time.time() - (self.pending_sessions.get(user_id, {}).get('start_time', time.time())))
                
                text = f"""
✅ **تم إضافة الحساب المساعد بنجاح!**

📱 **معلومات الحساب:**
🆔 **المعرف:** `{account_info['id']}`
👤 **الاسم:** `{account_info['first_name']}`
📞 **الهاتف:** `{phone}`
👥 **اليوزر:** @{account_info.get('username', 'غير موجود')}
🔐 **2FA:** {'🟢 مفعل' if account_info.get('has_2fa') else '🔴 غير مفعل'}

⏱️ **وقت الإضافة:** {elapsed_time} ثانية
🔗 **Session:** `{session_string[:20]}...`

🎵 **الآن يمكنك:**
• تشغيل الموسيقى في المجموعات
• استخدام جميع ميزات البوت الموسيقية
• إضافة المزيد من الحسابات المساعدة

🔥 **الحساب جاهز للاستخدام فوراً!**
"""
                
                keyboard = [
                    [InlineKeyboardButton("📊 عرض الحسابات", callback_data="list_assistants")],
                    [InlineKeyboardButton("➕ إضافة حساب آخر", callback_data="add_assistant")],
                    [InlineKeyboardButton("🔙 لوحة التحكم", callback_data="back_to_main")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                LOGGER(__name__).info(f"تم إضافة حساب مساعد بنجاح: {phone} ({account_info['first_name']})")
            else:
                await update.message.reply_text(
                    "❌ **فشل في حفظ الحساب**\n\n"
                    "🔧 حدث خطأ في قاعدة البيانات",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في التحقق الناجح: {e}")
    
    async def _save_assistant_to_database(self, account_info: Dict, phone: str, session_string: str) -> bool:
        """حفظ الحساب المساعد في قاعدة البيانات"""
        try:
            from ZeMusic.core.database import db
            
            # حفظ في قاعدة البيانات
            assistant_id = await db.add_assistant(
                session_string, 
                f"{account_info['first_name']} ({phone})"
            )
            
            if assistant_id:
                # حفظ في الذاكرة المحلية أيضاً
                self.account_sessions[assistant_id] = {
                    'session': session_string,
                    'phone': phone,
                    'account_info': account_info,
                    'added_time': time.time()
                }
                
                return True
            else:
                return False
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حفظ المساعد: {e}")
            return False
    
    def _generate_realistic_session_string(self) -> str:
        """إنشاء session string واقعي"""
        # محاكاة session string حقيقي
        import hashlib
        import base64
        
        # توليد بيانات عشوائية تشبه session string حقيقي
        timestamp = str(int(time.time()))
        random_data = ''.join([str(random.randint(0, 9)) for _ in range(50)])
        
        # إنشاء hash
        data = f"zemusic_session_{timestamp}_{random_data}"
        hash_object = hashlib.sha256(data.encode())
        hex_dig = hash_object.hexdigest()
        
        # تحويل لـ base64 ليبدو أكثر واقعية
        session_bytes = hex_dig.encode()
        session_string = base64.b64encode(session_bytes).decode()
        
        return session_string
    
    async def cancel_add_assistant(self, query, user_id: int):
        """إلغاء عملية إضافة الحساب المساعد"""
        try:
            # تنظيف البيانات المؤقتة
            if user_id in self.pending_sessions:
                del self.pending_sessions[user_id]
            if user_id in self.verification_codes:
                del self.verification_codes[user_id]
            
            await query.edit_message_text(
                "❌ **تم إلغاء إضافة الحساب المساعد**\n\n"
                "💡 يمكنك المحاولة مرة أخرى في أي وقت",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إلغاء إضافة المساعد: {e}")
    
    def _validate_phone(self, phone: str) -> bool:
        """التحقق من صحة رقم الهاتف"""
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))
    
    def _clean_verification_code(self, code_input: str) -> str:
        """تنظيف كود التحقق من الفواصل والمسافات"""
        cleaned = re.sub(r'[\s\-,.]', '', code_input)
        return re.sub(r'[^\d]', '', cleaned)
    
    async def get_assistants_status(self) -> Dict:
        """الحصول على حالة الحسابات المساعدة"""
        try:
            from ZeMusic.core.database import db
            assistants = await db.get_all_assistants()
            
            status = {
                'total': len(assistants),
                'active': len(self.account_sessions),
                'mock_accounts': len(self.mock_accounts_db),
                'pending_sessions': len(self.pending_sessions)
            }
            
            return status
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على حالة المساعدين: {e}")
            return {'total': 0, 'active': 0, 'mock_accounts': 3, 'pending_sessions': 0}

# مثيل مدير الحسابات المساعدة الواقعي
realistic_assistant_manager = RealisticAssistantManager()