import asyncio
import sqlite3
import re
from typing import Dict, Optional, Union
from urllib.parse import urlparse

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db

class ForceSubscribeHandler:
    """معالج الاشتراك الإجباري المتطور"""
    
    def __init__(self):
        self.is_enabled = False
        self.channel_id = None
        self.channel_username = None
        self.channel_link = None
        self.bot_is_admin = False
        self.cache_duration = 300  # 5 دقائق كاش للعضوية
        self.membership_cache = {}
        self.load_settings()
    
    def load_settings(self):
        """تحميل إعدادات الاشتراك الإجباري من قاعدة البيانات"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # إنشاء جدول الإعدادات إذا لم يكن موجوداً
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS force_subscribe_settings (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        is_enabled BOOLEAN DEFAULT FALSE,
                        channel_id TEXT,
                        channel_username TEXT,
                        channel_link TEXT,
                        bot_is_admin BOOLEAN DEFAULT FALSE,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # إدراج إعدادات افتراضية إذا لم توجد
                cursor.execute("INSERT OR IGNORE INTO force_subscribe_settings (id) VALUES (1)")
                
                # تحميل الإعدادات
                cursor.execute("SELECT * FROM force_subscribe_settings WHERE id = 1")
                row = cursor.fetchone()
                
                if row:
                    self.is_enabled = bool(row[1])
                    self.channel_id = row[2]
                    self.channel_username = row[3]
                    self.channel_link = row[4]
                    self.bot_is_admin = bool(row[5])
                    
                conn.commit()
                LOGGER(__name__).info(f"تم تحميل إعدادات الاشتراك الإجباري - مفعل: {self.is_enabled}")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في تحميل إعدادات الاشتراك الإجباري: {e}")
    
    def save_settings(self):
        """حفظ إعدادات الاشتراك الإجباري في قاعدة البيانات"""
        try:
            with sqlite3.connect(config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE force_subscribe_settings 
                    SET is_enabled = ?, channel_id = ?, channel_username = ?, 
                        channel_link = ?, bot_is_admin = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (
                    self.is_enabled, self.channel_id, self.channel_username,
                    self.channel_link, self.bot_is_admin
                ))
                conn.commit()
                LOGGER(__name__).info("تم حفظ إعدادات الاشتراك الإجباري")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في حفظ إعدادات الاشتراك الإجباري: {e}")
    
    async def show_force_subscribe_menu(self, user_id: int) -> Dict:
        """عرض قائمة الاشتراك الإجباري"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # الحصول على حالة النظام
        status_emoji = "🟢" if self.is_enabled else "🔴"
        status_text = "مُفعل" if self.is_enabled else "مُعطل"
        
        # معلومات القناة إذا كانت مضافة
        channel_info = ""
        if self.channel_id and self.channel_username:
            channel_info = (
                f"\n📢 **القناة المحددة:**\n"
                f"🆔 معرف القناة: `{self.channel_id}`\n"
                f"👤 اسم المستخدم: `@{self.channel_username}`\n"
                f"🔗 الرابط: {self.channel_link or 'غير محدد'}\n"
                f"🤖 البوت مدير: `{'نعم' if self.bot_is_admin else 'لا'}`\n"
            )
        
        keyboard = []
        
        if not self.is_enabled:
            keyboard.append([
                {'text': '🟢 تفعيل الاشتراك الإجباري', 'callback_data': 'fs_enable'}
            ])
        else:
            keyboard.append([
                {'text': '🔴 تعطيل الاشتراك الإجباري', 'callback_data': 'fs_disable'}
            ])
        
        keyboard.extend([
            [
                {'text': '⚙️ إعداد القناة', 'callback_data': 'fs_setup_channel'},
                {'text': '🧪 اختبار العضوية', 'callback_data': 'fs_test_membership'}
            ],
            [
                {'text': '📊 إحصائيات الاشتراك', 'callback_data': 'fs_stats'},
                {'text': '🔄 إعادة فحص البوت', 'callback_data': 'fs_check_bot'}
            ],
            [
                {'text': '📋 قائمة الاستثناءات', 'callback_data': 'fs_exceptions'},
                {'text': '🔧 إعدادات متقدمة', 'callback_data': 'fs_advanced'}
            ],
            [
                {'text': '🔙 العودة للوحة الرئيسية', 'callback_data': 'admin_main'}
            ]
        ])
        
        message = (
            f"🔐 **نظام الاشتراك الإجباري**\n\n"
            
            f"{status_emoji} **الحالة:** `{status_text}`\n"
            f"{channel_info}\n"
            
            f"📋 **آلية العمل:**\n"
            f"• عند التفعيل: يجب على جميع المستخدمين الاشتراك في القناة\n"
            f"• يتم فحص العضوية تلقائياً قبل تنفيذ أي أمر\n"
            f"• يشمل الفحص: المشتركين + طلبات الانضمام\n"
            f"• نظام كاش ذكي لتحسين الأداء\n\n"
            
            f"⚙️ **المتطلبات للتفعيل:**\n"
            f"✅ إضافة البوت كمدير في القناة\n"
            f"✅ تحديد رابط القناة\n"
            f"✅ التأكد من صحة الإعدادات\n\n"
            
            f"🎯 اختر الإجراء المطلوب:"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def enable_force_subscribe(self, user_id: int) -> Dict:
        """تفعيل الاشتراك الإجباري"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        # التحقق من الإعدادات المطلوبة
        if not self.channel_id or not self.channel_username:
            return {
                'success': False,
                'message': "❌ يجب إعداد القناة أولاً قبل التفعيل"
            }
        
        # التحقق من أن البوت مدير في القناة
        bot_status = await self._check_bot_admin_status()
        if not bot_status:
            return {
                'success': False,
                'message': "❌ البوت ليس مديراً في القناة، يرجى إضافته كمدير أولاً"
            }
        
        self.is_enabled = True
        self.save_settings()
        
        # مسح الكاش لبدء جديد
        self.membership_cache.clear()
        
        keyboard = [
            [
                {'text': '🔴 تعطيل الاشتراك الإجباري', 'callback_data': 'fs_disable'},
                {'text': '🧪 اختبار النظام', 'callback_data': 'fs_test_membership'}
            ],
            [
                {'text': '🔙 العودة لقائمة الاشتراك', 'callback_data': 'admin_force_subscribe'}
            ]
        ]
        
        message = (
            f"✅ **تم تفعيل الاشتراك الإجباري بنجاح!**\n\n"
            
            f"📢 **القناة:** @{self.channel_username}\n"
            f"🔗 **الرابط:** {self.channel_link}\n\n"
            
            f"🚀 **النظام نشط الآن:**\n"
            f"• جميع المستخدمين يجب أن يشتركوا في القناة\n"
            f"• يتم فحص العضوية تلقائياً\n"
            f"• المشتركون وطالبو الانضمام مقبولون\n\n"
            
            f"💡 **تلميح:** يمكنك اختبار النظام أو تعطيله في أي وقت"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def disable_force_subscribe(self, user_id: int) -> Dict:
        """تعطيل الاشتراك الإجباري"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        self.is_enabled = False
        self.save_settings()
        
        # مسح الكاش
        self.membership_cache.clear()
        
        keyboard = [
            [
                {'text': '🟢 تفعيل الاشتراك الإجباري', 'callback_data': 'fs_enable'},
                {'text': '⚙️ إعداد القناة', 'callback_data': 'fs_setup_channel'}
            ],
            [
                {'text': '🔙 العودة لقائمة الاشتراك', 'callback_data': 'admin_force_subscribe'}
            ]
        ]
        
        message = (
            f"🔴 **تم تعطيل الاشتراك الإجباري**\n\n"
            
            f"📋 **الحالة الحالية:**\n"
            f"• جميع المستخدمين يمكنهم استخدام البوت\n"
            f"• لا يتم فحص العضوية\n"
            f"• النظام في وضع المفتوح للجميع\n\n"
            
            f"💡 يمكنك إعادة التفعيل في أي وقت"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def setup_channel(self, user_id: int) -> Dict:
        """بدء إعداد القناة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        keyboard = [
            [
                {'text': '❌ إلغاء الإعداد', 'callback_data': 'admin_force_subscribe'}
            ]
        ]
        
        message = (
            f"⚙️ **إعداد قناة الاشتراك الإجباري**\n\n"
            
            f"📋 **الخطوات المطلوبة:**\n"
            f"1️⃣ إضافة البوت كمدير في القناة\n"
            f"2️⃣ إرسال رابط القناة\n\n"
            
            f"🔧 **صلاحيات مطلوبة للبوت:**\n"
            f"• إدارة القناة\n"
            f"• عرض قائمة الأعضاء\n"
            f"• عرض طلبات الانضمام\n\n"
            
            f"🔗 **أرسل الآن رابط القناة:**\n"
            f"• مثال: `https://t.me/channelname`\n"
            f"• أو: `@channelname`\n\n"
            
            f"⚠️ **تأكد من إضافة البوت كمدير قبل إرسال الرابط**"
        )
        
        return {
            'success': True,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown',
            'waiting_for_channel': True
        }
    
    async def process_channel_setup(self, user_id: int, channel_input: str) -> Dict:
        """معالجة إعداد القناة"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            # استخراج اسم المستخدم من الرابط أو النص
            channel_username = self._extract_channel_username(channel_input)
            if not channel_username:
                return {
                    'success': False,
                    'message': "❌ رابط أو اسم المستخدم غير صحيح\nيرجى إرسال رابط صحيح مثل: https://t.me/channelname أو @channelname"
                }
            
            # التحقق من وجود القناة والحصول على معلوماتها
            channel_info = await self._get_channel_info(channel_username)
            if not channel_info:
                return {
                    'success': False,
                    'message': f"❌ لم يتم العثور على القناة @{channel_username}\nتأكد من صحة الاسم وأن القناة عامة"
                }
            
            # التحقق من أن البوت مدير في القناة
            bot_admin_status = await self._check_bot_admin_status_in_channel(channel_info['id'])
            
            # حفظ إعدادات القناة
            self.channel_id = str(channel_info['id'])
            self.channel_username = channel_username
            self.channel_link = f"https://t.me/{channel_username}"
            self.bot_is_admin = bot_admin_status
            self.save_settings()
            
            keyboard = []
            
            if bot_admin_status:
                keyboard.extend([
                    [
                        {'text': '🟢 تفعيل الاشتراك الإجباري', 'callback_data': 'fs_enable'},
                        {'text': '🧪 اختبار العضوية', 'callback_data': 'fs_test_membership'}
                    ]
                ])
                status_message = "✅ البوت مدير في القناة - يمكن التفعيل الآن!"
            else:
                keyboard.extend([
                    [
                        {'text': '🔄 إعادة فحص البوت', 'callback_data': 'fs_check_bot'},
                        {'text': '📋 كيفية إضافة البوت', 'callback_data': 'fs_how_to_add_bot'}
                    ]
                ])
                status_message = "⚠️ البوت ليس مديراً - يجب إضافته كمدير أولاً"
            
            keyboard.append([
                {'text': '🔙 العودة لقائمة الاشتراك', 'callback_data': 'admin_force_subscribe'}
            ])
            
            message = (
                f"✅ **تم حفظ إعدادات القناة بنجاح!**\n\n"
                
                f"📢 **معلومات القناة:**\n"
                f"📛 الاسم: `{channel_info.get('title', 'غير متاح')}`\n"
                f"🆔 المعرف: `{self.channel_id}`\n"
                f"👤 اسم المستخدم: `@{self.channel_username}`\n"
                f"🔗 الرابط: {self.channel_link}\n"
                f"👥 عدد الأعضاء: `{channel_info.get('member_count', 'غير متاح')}`\n\n"
                
                f"🤖 **حالة البوت:** {status_message}\n\n"
                
                f"{'🎯 يمكنك الآن تفعيل النظام!' if bot_admin_status else '🔧 أضف البوت كمدير في القناة أولاً'}"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إعداد القناة: {e}")
            return {
                'success': False,
                'message': f"❌ حدث خطأ في إعداد القناة: {str(e)}"
            }
    
    async def check_user_subscription(self, user_id: int) -> bool:
        """فحص اشتراك المستخدم في القناة"""
        if not self.is_enabled or not self.channel_id:
            return True
        
        # التحقق من الكاش أولاً
        cache_key = f"user_{user_id}"
        if cache_key in self.membership_cache:
            cached_data = self.membership_cache[cache_key]
            if asyncio.get_event_loop().time() - cached_data['timestamp'] < self.cache_duration:
                return cached_data['is_member']
        
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected:
                return True  # السماح إذا كان البوت غير متصل
            
            # فحص عضوية المستخدم
            try:
                member_info = await bot_client.client.call_method('getChatMember', {
                    'chat_id': int(self.channel_id),
                    'member_id': {'@type': 'messageSenderUser', 'user_id': user_id}
                })
                
                # التحقق من حالة العضوية
                status = member_info.get('status', {}).get('@type', '')
                is_member = status in [
                    'chatMemberStatusMember',
                    'chatMemberStatusAdministrator',
                    'chatMemberStatusCreator',
                    'chatMemberStatusRestricted'  # عضو محدود لكن لا يزال عضو
                ]
                
                # فحص طلبات الانضمام إذا لم يكن عضو
                if not is_member:
                    is_member = await self._check_join_requests(user_id)
                
            except Exception:
                # إذا فشل الفحص، نفترض أنه غير عضو
                is_member = False
            
            # حفظ في الكاش
            self.membership_cache[cache_key] = {
                'is_member': is_member,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            return is_member
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في فحص اشتراك المستخدم {user_id}: {e}")
            return True  # السماح في حالة الخطأ
    
    async def get_subscription_message(self, user_name: str = "العزيز") -> Dict:
        """الحصول على رسالة طلب الاشتراك"""
        if not self.channel_username or not self.channel_link:
            return {
                'message': "❌ لم يتم إعداد قناة الاشتراك الإجباري بعد",
                'keyboard': []
            }
        
        keyboard = [
            [
                {'text': '📢 اشترك في القناة', 'url': self.channel_link},
                {'text': '🔄 تحقق من الاشتراك', 'callback_data': 'check_subscription'}
            ]
        ]
        
        message = (
            f"🔐 **الاشتراك مطلوب**\n\n"
            
            f"عذراً عزيزي **{user_name}** 👋\n\n"
            
            f"📢 للاستفادة من خدمات البوت، يجب عليك الاشتراك في قناتنا الرسمية أولاً:\n\n"
            
            f"🔗 **القناة:** @{self.channel_username}\n\n"
            
            f"✅ **خطوات الاشتراك:**\n"
            f"1️⃣ اضغط على زر \"📢 اشترك في القناة\"\n"
            f"2️⃣ اضغط على \"اشتراك\" أو \"Join\"\n"
            f"3️⃣ ارجع للبوت واضغط \"🔄 تحقق من الاشتراك\"\n\n"
            
            f"⚡ بعد الاشتراك ستتمكن من استخدام جميع ميزات البوت فوراً!"
        )
        
        return {
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    async def handle_subscription_check(self, user_id: int, user_name: str = "المستخدم") -> Dict:
        """معالجة فحص الاشتراك"""
        # مسح الكاش للمستخدم لفحص جديد
        cache_key = f"user_{user_id}"
        if cache_key in self.membership_cache:
            del self.membership_cache[cache_key]
        
        is_subscribed = await self.check_user_subscription(user_id)
        
        if is_subscribed:
            message = (
                f"✅ **تم التحقق من الاشتراك بنجاح!**\n\n"
                f"🎉 أهلاً وسهلاً **{user_name}**!\n\n"
                f"🚀 يمكنك الآن استخدام جميع ميزات البوت\n"
                f"📝 أرسل `/help` لمعرفة الأوامر المتاحة"
            )
            keyboard = []
        else:
            message = (
                f"❌ **لم يتم العثور على اشتراكك**\n\n"
                f"🔍 تأكد من أنك:\n"
                f"✅ اشتركت في القناة @{self.channel_username}\n"
                f"✅ لم تغادر القناة بعد الاشتراك\n"
                f"✅ انتظرت قليلاً بعد الاشتراك\n\n"
                f"🔄 جرب مرة أخرى بعد قليل"
            )
            keyboard = [
                [
                    {'text': '📢 اشترك في القناة', 'url': self.channel_link},
                    {'text': '🔄 تحقق مرة أخرى', 'callback_data': 'check_subscription'}
                ]
            ]
        
        return {
            'success': is_subscribed,
            'message': message,
            'keyboard': keyboard,
            'parse_mode': 'Markdown'
        }
    
    # الدوال المساعدة
    def _extract_channel_username(self, input_text: str) -> Optional[str]:
        """استخراج اسم المستخدم من الرابط أو النص"""
        input_text = input_text.strip()
        
        # إزالة @ إذا وجد
        if input_text.startswith('@'):
            return input_text[1:]
        
        # استخراج من رابط تليجرام
        if 't.me/' in input_text:
            try:
                parsed = urlparse(input_text)
                path = parsed.path.strip('/')
                if path:
                    return path
            except:
                pass
        
        # إذا كان نص عادي (اسم مستخدم مباشر)
        if re.match(r'^[a-zA-Z0-9_]+$', input_text):
            return input_text
        
        return None
    
    async def _get_channel_info(self, username: str) -> Optional[Dict]:
        """الحصول على معلومات القناة"""
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected:
                return None
            
            # البحث عن القناة بالاسم
            chat_info = await bot_client.client.call_method('searchPublicChat', {
                'username': username
            })
            
            if chat_info and chat_info.get('@type') == 'chat':
                return chat_info
            
            return None
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الحصول على معلومات القناة {username}: {e}")
            return None
    
    async def _check_bot_admin_status(self) -> bool:
        """فحص حالة البوت كمدير في القناة المحفوظة"""
        if not self.channel_id:
            return False
        
        return await self._check_bot_admin_status_in_channel(int(self.channel_id))
    
    async def _check_bot_admin_status_in_channel(self, channel_id: int) -> bool:
        """فحص حالة البوت كمدير في قناة محددة"""
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected:
                return False
            
            # الحصول على معلومات البوت في القناة
            bot_info = await bot_client.client.call_method('getChatMember', {
                'chat_id': channel_id,
                'member_id': {'@type': 'messageSenderUser', 'user_id': int(config.BOT_ID)}
            })
            
            # التحقق من صلاحيات الإدارة
            status = bot_info.get('status', {}).get('@type', '')
            return status in ['chatMemberStatusAdministrator', 'chatMemberStatusCreator']
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في فحص حالة البوت كمدير: {e}")
            return False
    
    async def _check_join_requests(self, user_id: int) -> bool:
        """فحص طلبات الانضمام للمستخدم"""
        try:
            bot_client = tdlib_manager.bot_client
            if not bot_client or not bot_client.is_connected or not self.channel_id:
                return False
            
            # الحصول على طلبات الانضمام
            join_requests = await bot_client.client.call_method('getChatJoinRequests', {
                'chat_id': int(self.channel_id),
                'invite_link': '',
                'query': '',
                'offset_request': None,
                'limit': 200
            })
            
            # البحث عن المستخدم في طلبات الانضمام
            requests = join_requests.get('requests', [])
            for request in requests:
                if request.get('user_id') == user_id:
                    return True
            
            return False
            
        except Exception as e:
            LOGGER(__name__).debug(f"خطأ في فحص طلبات الانضمام للمستخدم {user_id}: {e}")
            return False
    
    async def get_force_subscribe_stats(self, user_id: int) -> Dict:
        """الحصول على إحصائيات الاشتراك الإجباري"""
        if user_id != config.OWNER_ID:
            return {'success': False, 'message': "❌ غير مصرح"}
        
        try:
            # إحصائيات الكاش
            cache_stats = {
                'total_cached': len(self.membership_cache),
                'cache_hits': 0,
                'active_members': 0
            }
            
            current_time = asyncio.get_event_loop().time()
            for cache_data in self.membership_cache.values():
                if current_time - cache_data['timestamp'] < self.cache_duration:
                    cache_stats['cache_hits'] += 1
                    if cache_data['is_member']:
                        cache_stats['active_members'] += 1
            
            # معلومات القناة إن وجدت
            channel_stats = "غير متاح"
            if self.channel_id:
                try:
                    channel_info = await self._get_channel_info(self.channel_username)
                    if channel_info:
                        channel_stats = f"{channel_info.get('member_count', 0):,} عضو"
                except:
                    pass
            
            keyboard = [
                [
                    {'text': '🔄 تحديث الإحصائيات', 'callback_data': 'fs_stats'},
                    {'text': '🗑️ مسح الكاش', 'callback_data': 'fs_clear_cache'}
                ],
                [
                    {'text': '🔙 العودة لقائمة الاشتراك', 'callback_data': 'admin_force_subscribe'}
                ]
            ]
            
            message = (
                f"📊 **إحصائيات الاشتراك الإجباري**\n\n"
                
                f"📢 **معلومات القناة:**\n"
                f"📛 القناة: @{self.channel_username or 'غير محدد'}\n"
                f"👥 عدد الأعضاء: `{channel_stats}`\n"
                f"🤖 البوت مدير: `{'نعم' if self.bot_is_admin else 'لا'}`\n\n"
                
                f"💾 **إحصائيات الكاش:**\n"
                f"📦 إجمالي المحفوظ: `{cache_stats['total_cached']}`\n"
                f"✅ صالح للاستخدام: `{cache_stats['cache_hits']}`\n"
                f"👤 أعضاء نشطين: `{cache_stats['active_members']}`\n"
                f"⏱️ مدة الكاش: `{self.cache_duration // 60} دقائق`\n\n"
                
                f"🔧 **حالة النظام:**\n"
                f"{'🟢 مُفعل ويعمل' if self.is_enabled else '🔴 مُعطل'}\n"
            )
            
            return {
                'success': True,
                'message': message,
                'keyboard': keyboard,
                'parse_mode': 'Markdown'
            }
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إحصائيات الاشتراك الإجباري: {e}")
            return {
                'success': False,
                'message': "❌ حدث خطأ في جمع الإحصائيات"
            }

# إنشاء مثيل عام لمعالج الاشتراك الإجباري
force_subscribe_handler = ForceSubscribeHandler()