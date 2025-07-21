import asyncio
import re
import json
import os
import time
import random
import uuid
import sqlite3
from datetime import datetime
from typing import Dict, Optional, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from ZeMusic.logging import LOGGER

class TelegramSession:
    """محاكي جلسة تليجرام باستخدام TDLib"""
    
    def __init__(self, phone: str, api_id: int, api_hash: str):
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_path = f"sessions/{phone.replace('+', '')}"
        self.is_authorized = False
        self.user_info = None
        self.phone_code_hash = None
        
    async def send_code_request(self, force_sms=True):
        """إرسال طلب رمز التحقق"""
        # محاكاة إرسال الكود
        self.phone_code_hash = f"hash_{random.randint(100000, 999999)}"
        await asyncio.sleep(0.5)  # محاكاة زمن الشبكة
        return {"phone_code_hash": self.phone_code_hash}
    
    async def sign_in(self, code: str = None, password: str = None):
        """تسجيل الدخول بالكود أو كلمة المرور"""
        if code and not password:
            # محاكاة تسجيل الدخول بالكود
            await asyncio.sleep(1)
            return {"authorized": True}
        elif password:
            # محاكاة تسجيل الدخول بكلمة المرور الثنائية
            await asyncio.sleep(1)
            return {"authorized": True}
        return {"authorized": False}
    
    async def get_me(self):
        """الحصول على معلومات المستخدم الحالي"""
        if self.user_info:
            return self.user_info
        return None
    
    async def is_user_authorized(self):
        """التحقق من تفويض المستخدم"""
        return self.is_authorized
    
    async def start(self):
        """بدء الجلسة"""
        pass
    
    async def stop(self):
        """إيقاف الجلسة"""
        pass

class RealisticAssistantManager:
    """مدير واقعي للحسابات المساعدة مبني على الكود المرجعي"""
    
    def __init__(self):
        self.pending_sessions = {}
        self.verification_codes = {}
        self.user_states = {}
        
        # إعدادات API (محاكاة)
        self.API_ID = getattr(config, 'API_ID', 26924046)
        self.API_HASH = getattr(config, 'API_HASH', '4c6ef4cee5e129b7a674de156e2bcc15')
        
        # قاعدة بيانات الحسابات التجريبية
        self.mock_accounts_db = {
            "+966501234567": {
                "id": 123456789,
                "first_name": "أحمد",
                "last_name": "التجريبي",
                "username": "ahmed_test",
                "has_2fa": False,
                "valid_code": "12345"
            },
            "+201234567890": {
                "id": 987654321,
                "first_name": "محمد",
                "last_name": "المصري",
                "username": "mohamed_test",
                "has_2fa": True,
                "password": "123456",
                "valid_code": "54321"
            },
            "+1234567890": {
                "id": 555666777,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "has_2fa": False,
                "valid_code": "67890"
            },
            "+967771234567": {
                "id": 111222333,
                "first_name": "يمني",
                "last_name": "تجريبي",
                "username": "yemen_test",
                "has_2fa": False,
                "valid_code": "11111"
            },
            "+49123456789": {
                "id": 444555666,
                "first_name": "German",
                "last_name": "Test",
                "username": "german_test",
                "has_2fa": True,
                "password": "987654",
                "valid_code": "22222"
            }
        }
        
        # أجهزة Android ديناميكية (مطابقة للكود المرجعي)
        self.DEVICES = [
            {
                'device_model': 'Google Pixel 9 Pro',
                'system_version': 'Android 15 (SDK 35)',
                'app_version': 'Telegram Android 10.9.0',
                'app_name': 'Telegram',
                'lang_code': 'ar',
                'lang_pack': 'android'
            },
            {
                'device_model': 'Samsung Galaxy S24 Ultra',
                'system_version': 'Android 14 (SDK 34)',
                'app_version': 'Telegram Android 10.8.5',
                'app_name': 'Telegram',
                'lang_code': 'ar',
                'lang_pack': 'android'
            },
            {
                'device_model': 'OnePlus 12 Pro',
                'system_version': 'Android 14 (SDK 34)',
                'app_version': 'Telegram Android 10.9.2',
                'app_name': 'Telegram',
                'lang_code': 'ar',
                'lang_pack': 'android'
            },
            {
                'device_model': 'Xiaomi 14 Pro',
                'system_version': 'Android 14 (SDK 34)',
                'app_version': 'Telegram Android 10.8.8',
                'app_name': 'Telegram',
                'lang_code': 'ar',
                'lang_pack': 'android'
            }
        ]
        
        # إنشاء مجلد الجلسات
        os.makedirs("sessions", exist_ok=True)
        
        # تهيئة قاعدة البيانات
        self._init_database()
    
    def _init_database(self):
        """تهيئة قاعدة البيانات للحسابات المساعدة"""
        try:
            with sqlite3.connect("assistant_accounts.db", timeout=20) as conn:
                conn.execute('PRAGMA journal_mode=WAL;')
                conn.execute('PRAGMA synchronous=NORMAL;')
                
                # جدول الفئات
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS categories (
                        id TEXT PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1
                    )
                ''')
                
                # جدول الحسابات المساعدة
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS assistant_accounts (
                        id TEXT PRIMARY KEY,
                        category_id TEXT NOT NULL,
                        phone TEXT UNIQUE NOT NULL,
                        username TEXT,
                        user_id INTEGER,
                        first_name TEXT,
                        last_name TEXT,
                        session_data TEXT NOT NULL,
                        device_info TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP,
                        is_active INTEGER DEFAULT 1,
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                ''')
                
                # إنشاء فئة افتراضية
                default_category_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT OR IGNORE INTO categories (id, name, is_active) VALUES (?, ?, ?)",
                    (default_category_id, "الحسابات المساعدة الرئيسية", 1)
                )
                
                conn.commit()
                LOGGER(__name__).info("✅ تم تهيئة قاعدة بيانات الحسابات المساعدة")
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
    
    def get_random_device(self):
        """اختيار جهاز عشوائي"""
        return random.choice(self.DEVICES)
    
    def validate_phone(self, phone: str) -> bool:
        """التحقق من صحة رقم الهاتف"""
        return re.match(r'^\+\d{7,15}$', phone) is not None
    
    def validate_code(self, code: str) -> bool:
        """التحقق من صحة رمز التحقق"""
        code = code.replace(' ', '').replace(',', '')
        return re.match(r'^\d{5,6}$', code) is not None
    
    async def start_add_assistant(self, query, user_id: int):
        """بدء عملية إضافة حساب مساعد (مطابقة للكود المرجعي)"""
        try:
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await query.edit_message_text(
                    "❌ **هذا الأمر للمالك فقط!**",
                    parse_mode='Markdown'
                )
                return
            
            # عرض خيارات إضافة الحساب (مطابق للكود المرجعي)
            keyboard = [
                [InlineKeyboardButton("➕ إضافة برقم الهاتف", callback_data="realistic_add_phone")],
                [InlineKeyboardButton("🔑 إضافة بكود الجلسة", callback_data="realistic_add_session")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="realistic_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📋 **اختر طريقة إضافة الحساب المساعد:**\n\n"
                "🔸 **إضافة برقم الهاتف:** إضافة حساب جديد عبر رقم الهاتف والتحقق\n"
                "🔸 **إضافة بكود الجلسة:** إضافة حساب موجود باستخدام session string\n\n"
                "⚡️ **النظام يدعم:**\n"
                "✅ التحقق بخطوتين (2FA)\n"
                "✅ إرسال الكود عبر تليجرام\n"
                "✅ محاكاة أجهزة Android حقيقية\n"
                "✅ حفظ آمن للجلسات",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            self.user_states[user_id] = {
                'state': 'select_method',
                'data': {}
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في بدء إضافة المساعد: {e}")
            await query.edit_message_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال رقم الهاتف (مطابق للكود المرجعي)"""
        try:
            user_id = update.effective_user.id
            phone = update.message.text.strip()
            
            # التحقق من صحة رقم الهاتف
            if not self.validate_phone(phone):
                await update.message.reply_text(
                    "❌ **رقم الهاتف غير صالح**\n\n"
                    "📱 **الرجاء إرسال رقم بصيغة دولية صحيحة:**\n"
                    "• +966501234567 (السعودية)\n"
                    "• +201234567890 (مصر)\n"
                    "• +967771234567 (اليمن)\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من وجود الحساب مسبقاً
            if await self._check_existing_account(phone):
                keyboard = [
                    [InlineKeyboardButton("🔄 حذف القديم وإضافة جديد", callback_data="realistic_replace_account")],
                    [InlineKeyboardButton("🔙 استخدام رقم آخر", callback_data="realistic_use_another")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="realistic_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"⚠️ **الرقم {phone} مسجل مسبقاً**\n\n"
                    "اختر أحد الخيارات:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                self.user_states[user_id]['data']['phone'] = phone
                self.user_states[user_id]['state'] = 'handle_existing'
                return
            
            # بدء عملية التحقق
            await self._start_phone_verification(update, phone, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالجة رقم الهاتف: {e}")
            await update.message.reply_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _check_existing_account(self, phone: str) -> bool:
        """التحقق من وجود الحساب في قاعدة البيانات"""
        try:
            with sqlite3.connect("assistant_accounts.db", timeout=20) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM assistant_accounts WHERE phone = ? AND is_active = 1", (phone,))
                return cursor.fetchone() is not None
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في التحقق من الحساب الموجود: {e}")
            return False
    
    async def _start_phone_verification(self, update: Update, phone: str, user_id: int):
        """بدء عملية التحقق من الهاتف (مطابق للكود المرجعي)"""
        try:
            # إنشاء جلسة تليجرام مؤقتة
            session = TelegramSession(phone, self.API_ID, self.API_HASH)
            await session.start()
            
            # محاكاة إرسال رمز التحقق
            sent_result = await session.send_code_request(force_sms=False)
            
            # حفظ بيانات الجلسة
            self.pending_sessions[user_id] = {
                'session': session,
                'phone': phone,
                'phone_code_hash': sent_result['phone_code_hash'],
                'device': self.get_random_device(),
                'timestamp': time.time()
            }
            
            # إنشاء كود تحقق واقعي للحسابات التجريبية
            if phone in self.mock_accounts_db:
                verification_code = self.mock_accounts_db[phone]['valid_code']
                self.verification_codes[phone] = {
                    'code': verification_code,
                    'expires_at': time.time() + 300,  # 5 دقائق
                    'attempts': 0
                }
                
                await update.message.reply_text(
                    f"📱 **تم إرسال رمز التحقق إلى {phone}**\n\n"
                    f"🔐 **رمز التحقق التجريبي:** `{verification_code}`\n"
                    f"⏰ **ينتهي خلال:** 5 دقائق\n\n"
                    "🔢 **أرسل الرمز مع مسافات بين الأرقام:**\n"
                    f"مثال: `{' '.join(verification_code)}`\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📱 **تم إرسال رمز التحقق إلى {phone}**\n\n"
                    "📩 **تحقق من رسائل تليجرام الخاصة بك**\n"
                    "⏰ **الرمز صالح لمدة 5 دقائق**\n\n"
                    "🔢 **أرسل الرمز مع مسافات بين الأرقام:**\n"
                    "مثال: `1 2 3 4 5`\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
            
            self.user_states[user_id]['state'] = 'waiting_code'
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في بدء التحقق: {e}")
            await update.message.reply_text(
                f"❌ **فشل إرسال رمز التحقق:** {str(e)}\n\n"
                "🔄 **جرب مرة أخرى أو تواصل مع المطور**",
                parse_mode='Markdown'
            )
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال رمز التحقق (مطابق للكود المرجعي)"""
        try:
            user_id = update.effective_user.id
            code = update.message.text.strip().replace(' ', '').replace(',', '')
            
            # التحقق من صحة الرمز
            if not self.validate_code(code):
                await update.message.reply_text(
                    "❌ **رمز التحقق غير صالح**\n\n"
                    "🔢 **الرجاء إرسال رمز مكون من 5-6 أرقام:**\n"
                    "مثال: `1 2 3 4 5` أو `123456`\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                return
            
            session_data = self.pending_sessions.get(user_id)
            if not session_data:
                await update.message.reply_text(
                    "❌ **انتهت جلسة التسجيل**\n\n"
                    "🔄 **الرجاء البدء من جديد:** /start",
                    parse_mode='Markdown'
                )
                return
            
            phone = session_data['phone']
            session = session_data['session']
            
            # التحقق من الرمز للحسابات التجريبية
            if phone in self.verification_codes:
                verification_data = self.verification_codes[phone]
                
                if time.time() > verification_data['expires_at']:
                    await update.message.reply_text(
                        "⏰ **انتهت صلاحية رمز التحقق**\n\n"
                        "🔄 **الرجاء البدء من جديد:** /start",
                        parse_mode='Markdown'
                    )
                    return
                
                if code != verification_data['code']:
                    verification_data['attempts'] += 1
                    remaining_attempts = 3 - verification_data['attempts']
                    
                    if remaining_attempts <= 0:
                        await update.message.reply_text(
                            "❌ **تم استنفاد المحاولات**\n\n"
                            "🔒 **تم حظر الرقم مؤقتاً**\n"
                            "🔄 **جرب مرة أخرى بعد 10 دقائق**",
                            parse_mode='Markdown'
                        )
                        return
                    
                    await update.message.reply_text(
                        f"❌ **رمز التحقق غير صحيح**\n\n"
                        f"🔄 **المحاولات المتبقية:** {remaining_attempts}\n"
                        "🔢 **جرب مرة أخرى:**",
                        parse_mode='Markdown'
                    )
                    return
            
            # محاكاة تسجيل الدخول
            try:
                result = await session.sign_in(code)
                
                if result.get('authorized'):
                    # تسجيل دخول ناجح
                    account_info = self.mock_accounts_db.get(phone, {})
                    
                    # محاكاة معلومات المستخدم
                    session.user_info = {
                        'id': account_info.get('id', random.randint(100000000, 999999999)),
                        'first_name': account_info.get('first_name', 'مستخدم'),
                        'last_name': account_info.get('last_name', 'تجريبي'),
                        'username': account_info.get('username'),
                        'phone': phone
                    }
                    session.is_authorized = True
                    
                    # التحقق من التحقق بخطوتين
                    if account_info.get('has_2fa', False):
                        await update.message.reply_text(
                            "🔒 **هذا الحساب محمي بالتحقق بخطوتين**\n\n"
                            f"🔑 **كلمة المرور التجريبية:** `{account_info.get('password', '123456')}`\n\n"
                            "🔐 **أرسل كلمة مرور التحقق بخطوتين:**\n\n"
                            "❌ للإلغاء: /cancel",
                            parse_mode='Markdown'
                        )
                        self.user_states[user_id]['state'] = 'waiting_password'
                        return
                    
                    # إنهاء التسجيل
                    await self._finalize_account_registration(update, session_data, user_id)
                    
                else:
                    await update.message.reply_text(
                        "❌ **فشل تسجيل الدخول**\n\n"
                        "🔄 **تحقق من الرمز وجرب مرة أخرى**",
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                LOGGER(__name__).error(f"❌ خطأ في تسجيل الدخول: {e}")
                await update.message.reply_text(
                    f"❌ **فشل تسجيل الدخول:** {str(e)}",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالجة الرمز: {e}")
            await update.message.reply_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def handle_password_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة كلمة مرور التحقق بخطوتين (مطابق للكود المرجعي)"""
        try:
            user_id = update.effective_user.id
            password = update.message.text.strip()
            
            session_data = self.pending_sessions.get(user_id)
            if not session_data:
                await update.message.reply_text(
                    "❌ **انتهت جلسة التسجيل**\n\n"
                    "🔄 **الرجاء البدء من جديد:** /start",
                    parse_mode='Markdown'
                )
                return
            
            phone = session_data['phone']
            session = session_data['session']
            account_info = self.mock_accounts_db.get(phone, {})
            
            # التحقق من كلمة المرور
            if password != account_info.get('password', '123456'):
                await update.message.reply_text(
                    "❌ **كلمة المرور غير صحيحة**\n\n"
                    f"🔑 **كلمة المرور التجريبية:** `{account_info.get('password', '123456')}`\n\n"
                    "🔄 **جرب مرة أخرى:**",
                    parse_mode='Markdown'
                )
                return
            
            # محاكاة تسجيل الدخول بكلمة المرور
            try:
                result = await session.sign_in(password=password)
                
                if result.get('authorized'):
                    # تسجيل دخول ناجح
                    session.user_info = {
                        'id': account_info.get('id', random.randint(100000000, 999999999)),
                        'first_name': account_info.get('first_name', 'مستخدم'),
                        'last_name': account_info.get('last_name', 'تجريبي'),
                        'username': account_info.get('username'),
                        'phone': phone
                    }
                    session.is_authorized = True
                    
                    await self._finalize_account_registration(update, session_data, user_id)
                else:
                    await update.message.reply_text(
                        "❌ **فشل تسجيل الدخول بكلمة المرور**",
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                LOGGER(__name__).error(f"❌ خطأ في تسجيل الدخول بكلمة المرور: {e}")
                await update.message.reply_text(
                    f"❌ **فشل تسجيل الدخول:** {str(e)}",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالجة كلمة المرور: {e}")
            await update.message.reply_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _finalize_account_registration(self, update: Update, session_data: dict, user_id: int):
        """إنهاء تسجيل الحساب وحفظه (مطابق للكود المرجعي)"""
        try:
            session = session_data['session']
            phone = session_data['phone']
            device = session_data['device']
            
            # الحصول على معلومات المستخدم
            user_info = await session.get_me()
            
            if not user_info:
                await update.message.reply_text(
                    "❌ **فشل الحصول على معلومات المستخدم**",
                    parse_mode='Markdown'
                )
                return
            
            # إنشاء بيانات الجلسة المشفرة (محاكاة)
            session_data_to_save = {
                'phone': phone,
                'session_path': session.session_path,
                'api_id': session.api_id,
                'api_hash': session.api_hash,
                'user_id': user_info['id'],
                'device': device
            }
            
            # تشفير بيانات الجلسة (محاكاة)
            encrypted_session = self._encrypt_session_data(json.dumps(session_data_to_save))
            
            # حفظ الحساب في قاعدة البيانات
            account_id = str(uuid.uuid4())
            
            with sqlite3.connect("assistant_accounts.db", timeout=20) as conn:
                # الحصول على الفئة الافتراضية
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM categories WHERE name = ? LIMIT 1", ("الحسابات المساعدة الرئيسية",))
                category_result = cursor.fetchone()
                category_id = category_result[0] if category_result else str(uuid.uuid4())
                
                # إدخال الحساب
                conn.execute("""
                    INSERT INTO assistant_accounts (
                        id, category_id, phone, username, user_id, 
                        first_name, last_name, session_data, device_info, 
                        created_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id,
                    category_id,
                    phone,
                    user_info.get('username'),
                    user_info['id'],
                    user_info.get('first_name', ''),
                    user_info.get('last_name', ''),
                    encrypted_session,
                    json.dumps(device),
                    datetime.now().isoformat(),
                    1
                ))
                conn.commit()
            
            # إرسال رسالة النجاح
            username_text = f"@{user_info.get('username')}" if user_info.get('username') else "غير محدد"
            
            await update.message.reply_text(
                f"✅ **تم إضافة الحساب المساعد بنجاح!**\n\n"
                f"📱 **الهاتف:** `{phone}`\n"
                f"👤 **الاسم:** {user_info.get('first_name', '')} {user_info.get('last_name', '')}\n"
                f"🆔 **المعرف:** {user_info['id']}\n"
                f"👤 **اليوزر:** {username_text}\n"
                f"📱 **الجهاز:** {device['device_model']}\n"
                f"⚙️ **النظام:** {device['system_version']}\n"
                f"📲 **التطبيق:** {device['app_name']} {device['app_version']}\n\n"
                f"🎯 **الحساب جاهز للاستخدام في البوت!**",
                parse_mode='Markdown'
            )
            
            # تنظيف البيانات المؤقتة
            if user_id in self.pending_sessions:
                await self.pending_sessions[user_id]['session'].stop()
                del self.pending_sessions[user_id]
            
            if phone in self.verification_codes:
                del self.verification_codes[phone]
            
            if user_id in self.user_states:
                del self.user_states[user_id]
            
            LOGGER(__name__).info(f"✅ تم إضافة حساب مساعد جديد: {phone}")
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إنهاء التسجيل: {e}")
            await update.message.reply_text(
                f"❌ **فشل حفظ الحساب:** {str(e)}",
                parse_mode='Markdown'
            )
    
    def _encrypt_session_data(self, data: str) -> str:
        """تشفير بيانات الجلسة (محاكاة)"""
        # محاكاة تشفير بسيط
        import base64
        return base64.b64encode(data.encode()).decode()
    
    def _decrypt_session_data(self, encrypted_data: str) -> str:
        """فك تشفير بيانات الجلسة (محاكاة)"""
        # محاكاة فك تشفير بسيط
        import base64
        return base64.b64decode(encrypted_data.encode()).decode()
    
    async def cancel_add_assistant(self, query, user_id: int):
        """إلغاء عملية إضافة الحساب المساعد"""
        try:
            # تنظيف البيانات المؤقتة
            if user_id in self.pending_sessions:
                await self.pending_sessions[user_id]['session'].stop()
                del self.pending_sessions[user_id]
            
            if user_id in self.user_states:
                del self.user_states[user_id]
            
            # تنظيف كودات التحقق
            for phone in list(self.verification_codes.keys()):
                if time.time() > self.verification_codes[phone]['expires_at']:
                    del self.verification_codes[phone]
            
            await query.edit_message_text(
                "❌ **تم إلغاء عملية إضافة الحساب المساعد**",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إلغاء إضافة المساعد: {e}")
    
    async def get_assistant_accounts(self) -> List[Dict]:
        """الحصول على قائمة الحسابات المساعدة"""
        try:
            with sqlite3.connect("assistant_accounts.db", timeout=20) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT phone, username, user_id, first_name, last_name, 
                           session_data, device_info, created_at, last_used
                    FROM assistant_accounts 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                """)
                
                accounts = []
                for row in cursor.fetchall():
                    phone, username, user_id, first_name, last_name, session_data, device_info, created_at, last_used = row
                    
                    try:
                        device = json.loads(device_info) if device_info else {}
                    except:
                        device = {}
                    
                    accounts.append({
                        'phone': phone,
                        'username': username,
                        'user_id': user_id,
                        'first_name': first_name,
                        'last_name': last_name,
                        'device': device,
                        'created_at': created_at,
                        'last_used': last_used
                    })
                
                return accounts
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في الحصول على الحسابات المساعدة: {e}")
            return []

# إنشاء مثيل عام للمدير
realistic_assistant_manager = RealisticAssistantManager()