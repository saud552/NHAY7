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

try:
    import tdjson
    TDLIB_AVAILABLE = True
    LOGGER(__name__).info("✅ TDLib متاح ومُثبت")
except ImportError:
    TDLIB_AVAILABLE = False
    LOGGER(__name__).error("❌ TDLib غير متاح")

class RealTDLibSession:
    """جلسة TDLib حقيقية"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        self.session_path = f"tdlib_sessions/{phone.replace('+', '')}"
        self.is_authorized = False
        self.user_info = None
        self.phone_code_hash = None
        
        # إنشاء مجلد الجلسات
        os.makedirs("tdlib_sessions", exist_ok=True)
    
    async def start(self):
        """بدء جلسة TDLib"""
        try:
            if not TDLIB_AVAILABLE:
                raise Exception("TDLib غير مثبت")
            
            # إعداد TDLib
            self.client = tdjson.TDJson()
            
            # إعداد معاملات TDLib
            self.client.send({
                '@type': 'setTdlibParameters',
                'database_directory': self.session_path,
                'files_directory': f"{self.session_path}/files",
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'system_language_code': 'ar',
                'device_model': 'ZeMusic Bot',
                'application_version': '1.0',
                'enable_storage_optimizer': True,
                'ignore_file_names': False
            })
            
            # انتظار إتمام التهيئة
            await asyncio.sleep(1)
            
            LOGGER(__name__).info(f"✅ تم بدء جلسة TDLib للرقم {self.phone}")
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ فشل بدء جلسة TDLib: {e}")
            return False
    
    async def send_code_request(self):
        """إرسال طلب كود التحقق"""
        try:
            if not self.client:
                raise Exception("الجلسة غير مبدوءة")
            
            # إرسال طلب رقم الهاتف
            self.client.send({
                '@type': 'setAuthenticationPhoneNumber',
                'phone_number': self.phone
            })
            
            # انتظار الاستجابة
            await asyncio.sleep(2)
            
            # معالجة الاستجابات
            while True:
                response = self.client.receive(1.0)
                if response:
                    response_data = json.loads(response)
                    
                    if response_data.get('@type') == 'authorizationStateWaitCode':
                        LOGGER(__name__).info(f"✅ تم إرسال كود التحقق إلى {self.phone}")
                        return {'success': True, 'message': 'تم إرسال الكود'}
                    
                    elif response_data.get('@type') == 'error':
                        error_msg = response_data.get('message', 'خطأ غير معروف')
                        LOGGER(__name__).error(f"❌ خطأ TDLib: {error_msg}")
                        return {'success': False, 'error': error_msg}
                else:
                    break
            
            return {'success': True, 'message': 'تم إرسال الطلب'}
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إرسال كود التحقق: {e}")
            return {'success': False, 'error': str(e)}
    
    async def check_code(self, code: str):
        """التحقق من كود التحقق"""
        try:
            if not self.client:
                raise Exception("الجلسة غير مبدوءة")
            
            # إرسال كود التحقق
            self.client.send({
                '@type': 'checkAuthenticationCode',
                'code': code.replace(' ', '')
            })
            
            # انتظار الاستجابة
            await asyncio.sleep(2)
            
            # معالجة الاستجابات
            while True:
                response = self.client.receive(1.0)
                if response:
                    response_data = json.loads(response)
                    
                    if response_data.get('@type') == 'authorizationStateWaitPassword':
                        LOGGER(__name__).info(f"⚠️ الحساب {self.phone} يتطلب كلمة مرور 2FA")
                        return {'success': True, 'requires_2fa': True}
                    
                    elif response_data.get('@type') == 'authorizationStateReady':
                        LOGGER(__name__).info(f"✅ تم تسجيل الدخول بنجاح للرقم {self.phone}")
                        self.is_authorized = True
                        await self._get_user_info()
                        return {'success': True, 'authorized': True}
                    
                    elif response_data.get('@type') == 'error':
                        error_msg = response_data.get('message', 'كود خاطئ')
                        LOGGER(__name__).error(f"❌ خطأ في كود التحقق: {error_msg}")
                        return {'success': False, 'error': error_msg}
                else:
                    break
            
            return {'success': False, 'error': 'لم يتم الحصول على استجابة'}
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في التحقق من الكود: {e}")
            return {'success': False, 'error': str(e)}
    
    async def check_password(self, password: str):
        """التحقق من كلمة مرور 2FA"""
        try:
            if not self.client:
                raise Exception("الجلسة غير مبدوءة")
            
            # إرسال كلمة المرور
            self.client.send({
                '@type': 'checkAuthenticationPassword',
                'password': password
            })
            
            # انتظار الاستجابة
            await asyncio.sleep(2)
            
            # معالجة الاستجابات
            while True:
                response = self.client.receive(1.0)
                if response:
                    response_data = json.loads(response)
                    
                    if response_data.get('@type') == 'authorizationStateReady':
                        LOGGER(__name__).info(f"✅ تم تسجيل الدخول بكلمة المرور للرقم {self.phone}")
                        self.is_authorized = True
                        await self._get_user_info()
                        return {'success': True, 'authorized': True}
                    
                    elif response_data.get('@type') == 'error':
                        error_msg = response_data.get('message', 'كلمة مرور خاطئة')
                        LOGGER(__name__).error(f"❌ خطأ في كلمة المرور: {error_msg}")
                        return {'success': False, 'error': error_msg}
                else:
                    break
            
            return {'success': False, 'error': 'لم يتم الحصول على استجابة'}
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في التحقق من كلمة المرور: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_user_info(self):
        """الحصول على معلومات المستخدم"""
        try:
            if not self.client:
                return
            
            # طلب معلومات المستخدم
            self.client.send({
                '@type': 'getMe'
            })
            
            # انتظار الاستجابة
            await asyncio.sleep(1)
            
            while True:
                response = self.client.receive(1.0)
                if response:
                    response_data = json.loads(response)
                    
                    if response_data.get('@type') == 'user':
                        self.user_info = {
                            'id': response_data.get('id'),
                            'first_name': response_data.get('first_name', ''),
                            'last_name': response_data.get('last_name', ''),
                            'username': response_data.get('username'),
                            'phone': self.phone
                        }
                        LOGGER(__name__).info(f"✅ تم الحصول على معلومات المستخدم: {self.user_info}")
                        break
                else:
                    break
                    
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في الحصول على معلومات المستخدم: {e}")
    
    async def stop(self):
        """إيقاف الجلسة"""
        try:
            if self.client:
                self.client.send({'@type': 'close'})
                await asyncio.sleep(1)
            LOGGER(__name__).info(f"✅ تم إيقاف جلسة TDLib للرقم {self.phone}")
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إيقاف الجلسة: {e}")

class RealTDLibAssistantManager:
    """مدير حقيقي للحسابات المساعدة باستخدام TDLib"""
    
    def __init__(self):
        self.pending_sessions = {}
        self.user_states = {}
        
        # إعدادات API الحقيقية
        self.API_ID = getattr(config, 'API_ID', 26924046)
        self.API_HASH = getattr(config, 'API_HASH', '4c6ef4cee5e129b7a674de156e2bcc15')
        
        # تهيئة قاعدة البيانات
        self._init_database()
    
    def _init_database(self):
        """تهيئة قاعدة البيانات للحسابات المساعدة الحقيقية"""
        try:
            with sqlite3.connect("real_assistant_accounts.db", timeout=20) as conn:
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
                
                # جدول الحسابات المساعدة الحقيقية
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS real_assistant_accounts (
                        id TEXT PRIMARY KEY,
                        category_id TEXT NOT NULL,
                        phone TEXT UNIQUE NOT NULL,
                        username TEXT,
                        user_id INTEGER,
                        first_name TEXT,
                        last_name TEXT,
                        session_path TEXT NOT NULL,
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
                    (default_category_id, "الحسابات المساعدة الحقيقية", 1)
                )
                
                conn.commit()
                LOGGER(__name__).info("✅ تم تهيئة قاعدة بيانات الحسابات المساعدة الحقيقية")
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
    
    def validate_phone(self, phone: str) -> bool:
        """التحقق من صحة رقم الهاتف"""
        return re.match(r'^\+\d{7,15}$', phone) is not None
    
    def validate_code(self, code: str) -> bool:
        """التحقق من صحة رمز التحقق"""
        code = code.replace(' ', '').replace(',', '')
        return re.match(r'^\d{5,6}$', code) is not None
    
    async def start_add_assistant(self, query, user_id: int):
        """بدء عملية إضافة حساب مساعد حقيقي"""
        try:
            # التحقق من صلاحيات المالك
            if user_id != config.OWNER_ID:
                await query.edit_message_text(
                    "❌ **هذا الأمر للمالك فقط!**",
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من توفر TDLib
            if not TDLIB_AVAILABLE:
                await query.edit_message_text(
                    "❌ **TDLib غير متاح**\n\n"
                    "🔧 **لاستخدام النظام الحقيقي، يجب تثبيت TDLib:**\n"
                    "```\n"
                    "pip install tdjson\n"
                    "```\n\n"
                    "⚠️ **حالياً سيتم استخدام النظام البديل**",
                    parse_mode='Markdown'
                )
                return
            
            # عرض خيارات إضافة الحساب
            keyboard = [
                [InlineKeyboardButton("📱 إضافة برقم الهاتف (TDLib)", callback_data="real_tdlib_add_phone")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="real_tdlib_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🔥 **نظام الحسابات المساعدة الحقيقي (TDLib)**\n\n"
                "⚡️ **المميزات:**\n"
                "✅ اتصال مباشر بخوادم تليجرام\n"
                "✅ كود التحقق يصل لحسابك الفعلي\n"
                "✅ دعم التحقق بخطوتين الحقيقي\n"
                "✅ جلسات حقيقية ومستقرة\n\n"
                "🎯 **اختر طريقة الإضافة:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            self.user_states[user_id] = {
                'state': 'select_method',
                'data': {}
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في بدء إضافة المساعد الحقيقي: {e}")
            await query.edit_message_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال رقم الهاتف الحقيقي"""
        try:
            user_id = update.effective_user.id
            phone = update.message.text.strip()
            
            # التحقق من صحة رقم الهاتف
            if not self.validate_phone(phone):
                await update.message.reply_text(
                    "❌ **رقم الهاتف غير صالح**\n\n"
                    "📱 **الرجاء إرسال رقم بصيغة دولية صحيحة:**\n"
                    "مثال: +967780138966\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من وجود الحساب مسبقاً
            if await self._check_existing_account(phone):
                keyboard = [
                    [InlineKeyboardButton("🔄 حذف القديم وإضافة جديد", callback_data="real_tdlib_replace")],
                    [InlineKeyboardButton("🔙 استخدام رقم آخر", callback_data="real_tdlib_use_another")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="real_tdlib_cancel")]
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
            
            # بدء عملية التحقق الحقيقية
            await self._start_real_phone_verification(update, phone, user_id)
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالجة رقم الهاتف الحقيقي: {e}")
            await update.message.reply_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _check_existing_account(self, phone: str) -> bool:
        """التحقق من وجود الحساب في قاعدة البيانات"""
        try:
            with sqlite3.connect("real_assistant_accounts.db", timeout=20) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM real_assistant_accounts WHERE phone = ? AND is_active = 1", (phone,))
                return cursor.fetchone() is not None
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في التحقق من الحساب الموجود: {e}")
            return False
    
    async def _start_real_phone_verification(self, update: Update, phone: str, user_id: int):
        """بدء عملية التحقق الحقيقية من الهاتف"""
        try:
            # إرسال رسالة التجهيز
            waiting_msg = await update.message.reply_text(
                f"⏳ **جاري الاتصال بخوادم تليجرام...**\n\n"
                f"📱 **الرقم:** {phone}\n"
                "🔄 **قد يستغرق هذا بضع ثوانٍ**",
                parse_mode='Markdown'
            )
            
            # إنشاء جلسة TDLib حقيقية
            session = RealTDLibSession(self.API_ID, self.API_HASH, phone)
            
            # بدء الجلسة
            if not await session.start():
                await waiting_msg.edit_text(
                    "❌ **فشل في الاتصال بخوادم تليجرام**\n\n"
                    "🔧 **تحقق من:**\n"
                    "• اتصال الإنترنت\n"
                    "• إعدادات API_ID و API_HASH\n"
                    "• تثبيت TDLib بشكل صحيح",
                    parse_mode='Markdown'
                )
                return
            
            # إرسال طلب كود التحقق
            result = await session.send_code_request()
            
            if result['success']:
                # حفظ بيانات الجلسة
                self.pending_sessions[user_id] = {
                    'session': session,
                    'phone': phone,
                    'timestamp': time.time()
                }
                
                await waiting_msg.edit_text(
                    f"✅ **تم إرسال كود التحقق بنجاح!**\n\n"
                    f"📱 **الرقم:** {phone}\n"
                    f"📩 **تحقق من رسائل تليجرام في حسابك**\n"
                    f"⏰ **الكود صالح لمدة 5 دقائق**\n\n"
                    "🔢 **أرسل الكود مع مسافات بين الأرقام:**\n"
                    "مثال: `1 2 3 4 5`\n\n"
                    "❌ للإلغاء: /cancel",
                    parse_mode='Markdown'
                )
                
                self.user_states[user_id]['state'] = 'waiting_code'
                
            else:
                await waiting_msg.edit_text(
                    f"❌ **فشل إرسال كود التحقق**\n\n"
                    f"🔧 **السبب:** {result.get('error', 'خطأ غير معروف')}\n\n"
                    "💡 **الحلول:**\n"
                    "• تحقق من صحة رقم الهاتف\n"
                    "• تأكد من أن الرقم مسجل في تليجرام\n"
                    "• جرب مرة أخرى بعد دقيقة",
                    parse_mode='Markdown'
                )
                
                # إيقاف الجلسة
                await session.stop()
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في بدء التحقق الحقيقي: {e}")
            await update.message.reply_text(
                f"❌ **فشل بدء عملية التحقق:** {str(e)}\n\n"
                "🔄 **جرب مرة أخرى أو تواصل مع المطور**",
                parse_mode='Markdown'
            )
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال كود التحقق الحقيقي"""
        try:
            user_id = update.effective_user.id
            code = update.message.text.strip()
            
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
                    "🔄 **الرجاء البدء من جديد:** /owner",
                    parse_mode='Markdown'
                )
                return
            
            session = session_data['session']
            phone = session_data['phone']
            
            # إرسال رسالة التحقق
            checking_msg = await update.message.reply_text(
                "⏳ **جاري التحقق من الكود...**",
                parse_mode='Markdown'
            )
            
            # التحقق من الكود
            result = await session.check_code(code)
            
            if result['success']:
                if result.get('requires_2fa'):
                    # يتطلب كلمة مرور 2FA
                    await checking_msg.edit_text(
                        "🔒 **هذا الحساب محمي بالتحقق بخطوتين**\n\n"
                        "🔑 **أرسل كلمة مرور التحقق بخطوتين:**\n\n"
                        "❌ للإلغاء: /cancel",
                        parse_mode='Markdown'
                    )
                    self.user_states[user_id]['state'] = 'waiting_password'
                    
                elif result.get('authorized'):
                    # تم تسجيل الدخول بنجاح
                    await checking_msg.edit_text(
                        "✅ **تم التحقق بنجاح!**\n\n"
                        "🔄 **جاري حفظ الحساب...**",
                        parse_mode='Markdown'
                    )
                    await self._finalize_real_account_registration(update, session_data, user_id)
                    
            else:
                await checking_msg.edit_text(
                    f"❌ **فشل التحقق من الكود**\n\n"
                    f"🔧 **السبب:** {result.get('error', 'كود خاطئ')}\n\n"
                    "🔄 **جرب مرة أخرى:**",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالجة الكود الحقيقي: {e}")
            await update.message.reply_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def handle_password_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة كلمة مرور التحقق بخطوتين الحقيقية"""
        try:
            user_id = update.effective_user.id
            password = update.message.text.strip()
            
            session_data = self.pending_sessions.get(user_id)
            if not session_data:
                await update.message.reply_text(
                    "❌ **انتهت جلسة التسجيل**\n\n"
                    "🔄 **الرجاء البدء من جديد:** /owner",
                    parse_mode='Markdown'
                )
                return
            
            session = session_data['session']
            
            # إرسال رسالة التحقق
            checking_msg = await update.message.reply_text(
                "⏳ **جاري التحقق من كلمة المرور...**",
                parse_mode='Markdown'
            )
            
            # التحقق من كلمة المرور
            result = await session.check_password(password)
            
            if result['success'] and result.get('authorized'):
                # تم تسجيل الدخول بنجاح
                await checking_msg.edit_text(
                    "✅ **تم التحقق من كلمة المرور بنجاح!**\n\n"
                    "🔄 **جاري حفظ الحساب...**",
                    parse_mode='Markdown'
                )
                await self._finalize_real_account_registration(update, session_data, user_id)
                
            else:
                await checking_msg.edit_text(
                    f"❌ **كلمة المرور غير صحيحة**\n\n"
                    f"🔧 **السبب:** {result.get('error', 'كلمة مرور خاطئة')}\n\n"
                    "🔄 **جرب مرة أخرى:**",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في معالجة كلمة المرور الحقيقية: {e}")
            await update.message.reply_text(
                f"❌ **حدث خطأ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def _finalize_real_account_registration(self, update: Update, session_data: dict, user_id: int):
        """إنهاء تسجيل الحساب الحقيقي وحفظه"""
        try:
            session = session_data['session']
            phone = session_data['phone']
            
            # الحصول على معلومات المستخدم
            if not session.user_info:
                await update.message.reply_text(
                    "❌ **فشل الحصول على معلومات المستخدم**",
                    parse_mode='Markdown'
                )
                return
            
            user_info = session.user_info
            
            # حفظ الحساب في قاعدة البيانات
            account_id = str(uuid.uuid4())
            
            with sqlite3.connect("real_assistant_accounts.db", timeout=20) as conn:
                # الحصول على الفئة الافتراضية
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM categories WHERE name = ? LIMIT 1", ("الحسابات المساعدة الحقيقية",))
                category_result = cursor.fetchone()
                category_id = category_result[0] if category_result else str(uuid.uuid4())
                
                # إدخال الحساب
                conn.execute("""
                    INSERT INTO real_assistant_accounts (
                        id, category_id, phone, username, user_id, 
                        first_name, last_name, session_path, 
                        created_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id,
                    category_id,
                    phone,
                    user_info.get('username'),
                    user_info['id'],
                    user_info.get('first_name', ''),
                    user_info.get('last_name', ''),
                    session.session_path,
                    datetime.now().isoformat(),
                    1
                ))
                conn.commit()
            
            # إرسال رسالة النجاح
            username_text = f"@{user_info.get('username')}" if user_info.get('username') else "غير محدد"
            
            await update.message.reply_text(
                f"🎉 **تم إضافة الحساب المساعد الحقيقي بنجاح!**\n\n"
                f"📱 **الهاتف:** {phone}\n"
                f"👤 **الاسم:** {user_info.get('first_name', '')} {user_info.get('last_name', '')}\n"
                f"🆔 **المعرف:** {user_info['id']}\n"
                f"👤 **اليوزر:** {username_text}\n"
                f"💾 **الجلسة:** {session.session_path}\n\n"
                f"🔥 **الحساب جاهز للاستخدام في البوت!**\n"
                f"⚡ **اتصال مباشر بخوادم تليجرام**",
                parse_mode='Markdown'
            )
            
            # تنظيف البيانات المؤقتة
            if user_id in self.pending_sessions:
                del self.pending_sessions[user_id]
            
            if user_id in self.user_states:
                del self.user_states[user_id]
            
            LOGGER(__name__).info(f"✅ تم إضافة حساب مساعد حقيقي جديد: {phone}")
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إنهاء التسجيل الحقيقي: {e}")
            await update.message.reply_text(
                f"❌ **فشل حفظ الحساب:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def cancel_add_assistant(self, query, user_id: int):
        """إلغاء عملية إضافة الحساب المساعد الحقيقي"""
        try:
            # تنظيف البيانات المؤقتة
            if user_id in self.pending_sessions:
                session = self.pending_sessions[user_id].get('session')
                if session:
                    await session.stop()
                del self.pending_sessions[user_id]
            
            if user_id in self.user_states:
                del self.user_states[user_id]
            
            await query.edit_message_text(
                "❌ **تم إلغاء عملية إضافة الحساب المساعد الحقيقي**",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في إلغاء إضافة المساعد الحقيقي: {e}")
    
    async def get_real_assistant_accounts(self) -> List[Dict]:
        """الحصول على قائمة الحسابات المساعدة الحقيقية"""
        try:
            with sqlite3.connect("real_assistant_accounts.db", timeout=20) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT phone, username, user_id, first_name, last_name, 
                           session_path, created_at, last_used
                    FROM real_assistant_accounts 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                """)
                
                accounts = []
                for row in cursor.fetchall():
                    phone, username, user_id, first_name, last_name, session_path, created_at, last_used = row
                    
                    accounts.append({
                        'phone': phone,
                        'username': username,
                        'user_id': user_id,
                        'first_name': first_name,
                        'last_name': last_name,
                        'session_path': session_path,
                        'created_at': created_at,
                        'last_used': last_used,
                        'type': 'real_tdlib'
                    })
                
                return accounts
                
        except Exception as e:
            LOGGER(__name__).error(f"❌ خطأ في الحصول على الحسابات المساعدة الحقيقية: {e}")
            return []

# إنشاء مثيل عام للمدير الحقيقي
real_tdlib_assistant_manager = RealTDLibAssistantManager()