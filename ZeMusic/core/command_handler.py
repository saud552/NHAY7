import asyncio
import json
from typing import Dict, Any, Callable, Optional

import config
from ZeMusic.logging import LOGGER
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.plugins.bot.basic_commands import command_handler as basic_commands
from ZeMusic.plugins.owner.admin_panel import admin_panel
from ZeMusic.plugins.owner.stats_handler import stats_handler
from ZeMusic.plugins.owner.broadcast_handler import broadcast_handler
from ZeMusic.plugins.owner.owner_panel import owner_panel

class TDLibCommandHandler:
    """معالج الأوامر والcallbacks مع TDLib"""
    
    def __init__(self):
        self.commands = {}
        self.callback_handlers = {}
        self.message_handlers = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        """إعداد معالجات الأوامر والcallbacks"""
        # تسجيل الأوامر الأساسية
        self.commands = {
            '/start': self.handle_start,
            '/help': self.handle_help,
            '/play': self.handle_play,
            '/pause': self.handle_pause,
            '/resume': self.handle_resume,
            '/stop': self.handle_stop,
            '/skip': self.handle_skip,
            '/current': self.handle_current,
            '/queue': self.handle_queue,
            '/owner': self.handle_owner,
            '/stats': self.handle_stats,
            '/admin': self.handle_admin,  # أمر لوحة المطور الجديد
        }
        
        # تسجيل معالجات الcallbacks
        self.callback_handlers = {
            'admin_': self.handle_admin_callback,
            'broadcast_': self.handle_broadcast_callback,
            'owner_': self.handle_owner_callback,
            'stats_': self.handle_stats_callback,
        }
    
    async def handle_message(self, update: Dict[str, Any]):
        """معالج الرسائل الواردة"""
        try:
            message = update.get('message', {})
            message_content = message.get('content', {})
            
            # معالجة الرسائل النصية
            if message_content.get('@type') == 'messageText':
                text = message_content.get('text', {}).get('text', '')
                chat_id = message.get('chat_id')
                sender_id = message.get('sender_id', {}).get('user_id')
                message_id = message.get('id')
                
                # تحويل للتنسيق المتوافق مع الأوامر الموجودة
                mock_update = self._create_mock_update(text, chat_id, sender_id, message_id, message)
                
                # فحص الاشتراك الإجباري بناءً على نوع المحادثة
                should_check_subscription = False
                
                # الحصول على نوع المحادثة
                chat_type = message.get('chat_id', 0)
                is_private_chat = chat_id > 0  # المحادثات الخاصة لها معرف موجب
                is_group_or_channel = chat_id < 0  # المجموعات والقنوات لها معرف سالب
                
                # قواعد فحص الاشتراك:
                if sender_id == config.OWNER_ID:
                    # المطور معفي دائماً
                    should_check_subscription = False
                elif text.startswith('/admin') or text.startswith('/owner'):
                    # أوامر الإدارة معفية دائماً
                    should_check_subscription = False
                elif text == '/start':
                    # أمر البدء معفي دائماً للترحيب
                    should_check_subscription = False
                elif is_private_chat:
                    # في المحادثات الخاصة: فحص جميع الرسائل
                    should_check_subscription = True
                elif is_group_or_channel:
                    # في المجموعات والقنوات: فحص فقط عند استخدام البوت
                    is_bot_command = text.startswith('/')
                    is_bot_mention = f"@{tdlib_manager.bot_client.username}" in text if tdlib_manager.bot_client and hasattr(tdlib_manager.bot_client, 'username') else False
                    is_reply_to_bot = message.get('reply_to_message_id') and message.get('reply_to_message', {}).get('sender_id', {}).get('user_id') == int(config.BOT_ID)
                    
                    # كلمات مفتاحية تدل على استخدام البوت
                    bot_keywords = [
                        'شغل', 'تشغيل', 'play', 'ايقاف', 'وقف', 'stop', 'pause', 'resume',
                        'تخطي', 'skip', 'next', 'تالي', 'قائمة', 'queue', 'موسيقى', 'music',
                        'صوت', 'audio', 'video', 'فيديو', 'بحث', 'search'
                    ]
                    is_using_bot_keywords = any(keyword in text.lower() for keyword in bot_keywords)
                    
                    # فحص الاشتراك فقط إذا كان المستخدم يتفاعل مع البوت
                    should_check_subscription = is_bot_command or is_bot_mention or is_reply_to_bot or is_using_bot_keywords
                
                # تنفيذ فحص الاشتراك إذا كان مطلوباً
                if should_check_subscription:
                    from ZeMusic.plugins.owner.force_subscribe_handler import force_subscribe_handler
                    is_subscribed = await force_subscribe_handler.check_user_subscription(sender_id)
                    
                    if not is_subscribed:
                        # الحصول على اسم المستخدم من الرسالة
                        user_name = message.get('sender_id', {}).get('user_id', 'المستخدم')
                        try:
                            # محاولة الحصول على الاسم الحقيقي
                            bot_client = tdlib_manager.bot_client
                            if bot_client and bot_client.is_connected:
                                user_info = await bot_client.client.call_method('getUser', {'user_id': sender_id})
                                user_name = user_info.get('first_name', 'المستخدم')
                        except:
                            user_name = "المستخدم"
                        
                        # إرسال رسالة طلب الاشتراك
                        subscription_msg = await force_subscribe_handler.get_subscription_message(user_name)
                        
                        # إرسال الرسالة مع الأزرار
                        bot_client = tdlib_manager.bot_client
                        if bot_client and bot_client.is_connected:
                            # تحويل keyboard للتنسيق المناسب
                            keyboard = self._convert_keyboard_for_subscription(subscription_msg['keyboard'])
                            await bot_client.client.call_method('sendMessage', {
                                'chat_id': chat_id,
                                'input_message_content': {
                                    '@type': 'inputMessageText',
                                    'text': {
                                        '@type': 'formattedText',
                                        'text': subscription_msg['message']
                                    }
                                },
                                'reply_markup': keyboard
                            })
                        return  # منع معالجة الرسالة إذا لم يكن مشتركاً
                
                # التحقق من الأوامر
                if text.startswith('/'):
                    command = text.split()[0].lower()
                    if command in self.commands:
                        await self.commands[command](mock_update, None)
                        return
                
                # معالجة session strings والأسماء للحسابات المساعدة
                elif sender_id == config.OWNER_ID:
                    from ZeMusic.plugins.owner.assistants_handler import assistants_handler
                    
                    # فحص إذا كان المطور في جلسة إضافة حساب مساعد
                    if sender_id in assistants_handler.pending_sessions:
                        session = assistants_handler.pending_sessions[sender_id]
                        
                        if session['step'] == 'waiting_session_string':
                            # معالجة session string
                            result = await assistants_handler.process_session_string(sender_id, text)
                            
                            # إرسال الرد
                            bot_client = tdlib_manager.bot_client
                            if bot_client and bot_client.is_connected and result:
                                keyboard = None
                                if result.get('keyboard'):
                                    keyboard = self._convert_keyboard_for_tdlib(result['keyboard'])
                                
                                await bot_client.client.call_method('sendMessage', {
                                    'chat_id': chat_id,
                                    'input_message_content': {
                                        '@type': 'inputMessageText',
                                        'text': {
                                            '@type': 'formattedText',
                                            'text': result['message']
                                        }
                                    },
                                    'reply_markup': keyboard
                                })
                            return
                        
                        elif session['step'] == 'waiting_name':
                            # معالجة اسم الحساب المساعد
                            result = await assistants_handler.process_assistant_name(sender_id, text)
                            
                            # إرسال الرد
                            bot_client = tdlib_manager.bot_client
                            if bot_client and bot_client.is_connected and result:
                                keyboard = None
                                if result.get('keyboard'):
                                    keyboard = self._convert_keyboard_for_tdlib(result['keyboard'])
                                
                                await bot_client.client.call_method('sendMessage', {
                                    'chat_id': chat_id,
                                    'input_message_content': {
                                        '@type': 'inputMessageText',
                                        'text': {
                                            '@type': 'formattedText',
                                            'text': result['message']
                                        }
                                    },
                                    'reply_markup': keyboard
                                })
                            return
                
                # معالجة الرسائل العادية (للإذاعة مثلاً)
                await self.handle_regular_message(mock_update, message)
            
            # معالجة callbackQuery
            elif update.get('@type') == 'updateNewCallbackQuery':
                await self.handle_callback_query(update)
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالجة الرسالة: {e}")
    
    async def handle_callback_query(self, update: Dict[str, Any]):
        """معالج الcallback queries"""
        try:
            callback_query = update.get('callback_query', {})
            data = callback_query.get('data', '')
            sender_id = callback_query.get('sender_user_id')
            message_id = callback_query.get('message', {}).get('id')
            chat_id = callback_query.get('message', {}).get('chat_id')
            callback_query_id = callback_query.get('id')
            
            # فحص الاشتراك الإجباري للcallback queries
            should_check_subscription = True
            
            # استثناءات فحص الاشتراك
            if sender_id == config.OWNER_ID:
                should_check_subscription = False
            elif data.startswith('admin_') or data.startswith('owner_'):
                should_check_subscription = False
            elif data == 'check_subscription':  # زر التحقق من الاشتراك نفسه
                should_check_subscription = False
            
            # تنفيذ فحص الاشتراك إذا كان مطلوباً
            if should_check_subscription:
                from ZeMusic.plugins.owner.force_subscribe_handler import force_subscribe_handler
                is_subscribed = await force_subscribe_handler.check_user_subscription(sender_id)
                
                if not is_subscribed:
                    # الرد السريع بالاشتراك المطلوب
                    await self._answer_callback_query(callback_query_id, "🔐 يجب الاشتراك في القناة أولاً!", True)
                    
                    # إرسال رسالة الاشتراك
                    try:
                        bot_client = tdlib_manager.bot_client
                        if bot_client and bot_client.is_connected:
                            user_info = await bot_client.client.call_method('getUser', {'user_id': sender_id})
                            user_name = user_info.get('first_name', 'المستخدم')
                    except:
                        user_name = "المستخدم"
                    
                    subscription_msg = await force_subscribe_handler.get_subscription_message(user_name)
                    
                    # إرسال رسالة الاشتراك
                    bot_client = tdlib_manager.bot_client
                    if bot_client and bot_client.is_connected:
                        keyboard = self._convert_keyboard_for_subscription(subscription_msg['keyboard'])
                        await bot_client.client.call_method('sendMessage', {
                            'chat_id': chat_id,
                            'input_message_content': {
                                '@type': 'inputMessageText',
                                'text': {
                                    '@type': 'formattedText',
                                    'text': subscription_msg['message']
                                }
                            },
                            'reply_markup': keyboard
                        })
                    return
            
            # الرد السريع على الcallback
            await self._answer_callback_query(callback_query_id)
            
            # تحويل للتنسيق المتوافق
            mock_query = self._create_mock_callback_query(data, sender_id, message_id, chat_id, callback_query)
            
            # توجيه إلى المعالج المناسب
            handled = False
            for prefix, handler in self.callback_handlers.items():
                if data.startswith(prefix):
                    await handler(mock_query)
                    handled = True
                    break
            
            if not handled:
                LOGGER(__name__).warning(f"لم يتم العثور على معالج للcallback: {data}")
                
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالجة callback query: {e}")
    
    async def handle_regular_message(self, mock_update, original_message):
        """معالجة الرسائل العادية (غير الأوامر)"""
        try:
            user_id = mock_update.effective_user.id
            
            # التحقق من جلسات الإذاعة المعلقة
            if user_id in broadcast_handler.pending_sessions:
                session = broadcast_handler.pending_sessions[user_id]
                if session.get('step') == 'waiting_message':
                    # تحويل الرسالة لتنسيق مناسب للإذاعة
                    message_data = self._convert_message_for_broadcast(original_message)
                    result = await broadcast_handler.handle_message_content(user_id, message_data)
                    
                    if result.get('success'):
                        await self._send_reply(mock_update, result)
                    return
            
            # التحقق من جلسات إعداد الاشتراك الإجباري
            from ZeMusic.plugins.owner.force_subscribe_handler import force_subscribe_handler
            # (يمكن إضافة آلية لحفظ حالة الانتظار لإعداد القناة)
            # في هذا المثال، سنفترض أن النص هو رابط قناة إذا بدأ بـ https://t.me أو @
            text = mock_update.message.text
            if (user_id == config.OWNER_ID and 
                (text.startswith('https://t.me/') or text.startswith('@') or 
                 ('t.me/' in text and len(text.strip()) > 5))):
                
                # محاولة معالجة كإعداد قناة
                result = await force_subscribe_handler.process_channel_setup(user_id, text)
                if result.get('success'):
                    await self._send_reply(mock_update, result)
                    return
            
            # يمكن إضافة معالجات أخرى للرسائل العادية هنا
            
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في معالجة الرسالة العادية: {e}")
    
    # معالجات الأوامر
    async def handle_start(self, update, context):
        """معالج أمر /start"""
        await basic_commands.start_command(update, context)
    
    async def handle_help(self, update, context):
        """معالج أمر /help"""
        await basic_commands.help_command(update, context)
    
    async def handle_play(self, update, context):
        """معالج أمر /play"""
        await basic_commands.play_command(update, context)
    
    async def handle_pause(self, update, context):
        """معالج أمر /pause"""
        await basic_commands.pause_command(update, context)
    
    async def handle_resume(self, update, context):
        """معالج أمر /resume"""
        await basic_commands.resume_command(update, context)
    
    async def handle_stop(self, update, context):
        """معالج أمر /stop"""
        await basic_commands.stop_command(update, context)
    
    async def handle_skip(self, update, context):
        """معالج أمر /skip"""
        await basic_commands.skip_command(update, context)
    
    async def handle_current(self, update, context):
        """معالج أمر /current"""
        await basic_commands.current_command(update, context)
    
    async def handle_queue(self, update, context):
        """معالج أمر /queue"""
        await basic_commands.queue_command(update, context)
    
    async def handle_owner(self, update, context):
        """معالج أمر /owner"""
        await basic_commands.owner_command(update, context)
    
    async def handle_stats(self, update, context):
        """معالج أمر /stats"""
        await basic_commands.stats_command(update, context)
    
    async def handle_admin(self, update, context):
        """معالج أمر /admin - لوحة المطور"""
        await basic_commands.admin_command(update, context)
    
    # معالجات الcallbacks
    async def handle_admin_callback(self, query):
        """معالج callbacks لوحة المطور"""
        await basic_commands.handle_callback_query(query, None)
    
    async def handle_broadcast_callback(self, query):
        """معالج callbacks الإذاعة"""
        await basic_commands.handle_callback_query(query, None)
    
    async def handle_owner_callback(self, query):
        """معالج callbacks إدارة الحسابات المساعدة"""
        await basic_commands.handle_callback_query(query, None)
    
    async def handle_stats_callback(self, query):
        """معالج callbacks الإحصائيات"""
        await basic_commands.handle_callback_query(query, None)
    
    # الدوال المساعدة
    def _create_mock_update(self, text: str, chat_id: int, sender_id: int, message_id: int, original_message: Dict):
        """إنشاء كائن update وهمي متوافق مع الأوامر الموجودة"""
        class MockMessage:
            def __init__(self, text, chat_id, user_id, message_id, original):
                self.text = text
                self.message_id = message_id
                self.original = original
                
                # Mock chat
                class MockChat:
                    def __init__(self, chat_id):
                        self.id = chat_id
                self.chat = MockChat(chat_id)
                
                # Mock user
                class MockUser:
                    def __init__(self, user_id):
                        self.id = user_id
                        self.first_name = "User"
                self.from_user = MockUser(user_id)
                
            async def reply_text(self, text, **kwargs):
                """إرسال رد"""
                bot_client = tdlib_manager.bot_client
                if bot_client and bot_client.is_connected:
                    await bot_client.send_message(self.chat.id, text)
        
        class MockUpdate:
            def __init__(self, message):
                self.message = message
                self.effective_user = message.from_user
                self.effective_chat = message.chat
        
        mock_message = MockMessage(text, chat_id, sender_id, message_id, original_message)
        return MockUpdate(mock_message)
    
    def _create_mock_callback_query(self, data: str, user_id: int, message_id: int, chat_id: int, original_query: Dict):
        """إنشاء كائن callback query وهمي"""
        class MockMessage:
            def __init__(self, message_id, chat_id):
                self.message_id = message_id
                self.chat_id = chat_id
                
            async def reply_text(self, text, **kwargs):
                """إرسال رد"""
                bot_client = tdlib_manager.bot_client
                if bot_client and bot_client.is_connected:
                    await bot_client.send_message(self.chat_id, text)
        
        class MockUser:
            def __init__(self, user_id):
                self.id = user_id
        
        class MockCallbackQuery:
            def __init__(self, data, user_id, message_id, chat_id, original):
                self.data = data
                self.from_user = MockUser(user_id)
                self.message = MockMessage(message_id, chat_id)
                self.original = original
                
            async def answer(self, text=None, show_alert=False):
                """الرد على الcallback query"""
                await tdlib_manager.bot_client.client.call_method('answerCallbackQuery', {
                    'callback_query_id': self.original.get('id'),
                    'text': text or '',
                    'show_alert': show_alert
                })
                
            async def edit_message_text(self, text, **kwargs):
                """تعديل نص الرسالة"""
                bot_client = tdlib_manager.bot_client
                if bot_client and bot_client.is_connected:
                    # تحويل keyboard إذا وجد
                    reply_markup = kwargs.get('reply_markup')
                    keyboard = None
                    if reply_markup:
                        keyboard = self._convert_keyboard_to_tdlib(reply_markup)
                    
                    await bot_client.client.call_method('editMessageText', {
                        'chat_id': self.message.chat_id,
                        'message_id': self.message.message_id,
                        'input_message_content': {
                            '@type': 'inputMessageText',
                            'text': {
                                '@type': 'formattedText',
                                'text': text
                            }
                        },
                        'reply_markup': keyboard
                    })
            
            def _convert_keyboard_to_tdlib(self, keyboard):
                """تحويل keyboard للتنسيق المناسب لـ TDLib"""
                if not keyboard:
                    return None
                
                rows = []
                for row in keyboard:
                    buttons = []
                    for button in row:
                        if len(button) >= 2:
                            buttons.append({
                                '@type': 'inlineKeyboardButton',
                                'text': button[0],
                                'type': {
                                    '@type': 'inlineKeyboardButtonTypeCallback',
                                    'data': button[1]
                                }
                            })
                    if buttons:
                        rows.append(buttons)
                
                return {
                    '@type': 'replyMarkupInlineKeyboard',
                    'rows': rows
                } if rows else None
        
        return MockCallbackQuery(data, user_id, message_id, chat_id, original_query)
    
    def _convert_message_for_broadcast(self, message: Dict) -> Dict:
        """تحويل الرسالة لتنسيق مناسب للإذاعة"""
        content = message.get('content', {})
        message_data = {
            'chat_id': message.get('chat_id'),
            'message_id': message.get('id')
        }
        
        if content.get('@type') == 'messageText':
            message_data['text'] = content.get('text', {}).get('text', '')
        elif content.get('@type') == 'messagePhoto':
            message_data['photo'] = content.get('photo')
            caption = content.get('caption', {}).get('text', '')
            if caption:
                message_data['caption'] = caption
        elif content.get('@type') == 'messageVideo':
            message_data['video'] = content.get('video')
            caption = content.get('caption', {}).get('text', '')
            if caption:
                message_data['caption'] = caption
        # يمكن إضافة المزيد من أنواع المحتوى
        
        return message_data
    
    async def _answer_callback_query(self, callback_query_id: str, text: str = "", show_alert: bool = False):
        """الرد على callback query"""
        try:
            bot_client = tdlib_manager.bot_client
            if bot_client and bot_client.is_connected:
                await bot_client.client.call_method('answerCallbackQuery', {
                    'callback_query_id': callback_query_id,
                    'text': text,
                    'show_alert': show_alert
                })
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في الرد على callback query: {e}")
    
    async def _send_reply(self, update, result: Dict):
        """إرسال رد للمستخدم"""
        try:
            if result.get('success') and result.get('message'):
                await update.message.reply_text(
                                          result['message'],
                      parse_mode=result.get('parse_mode', 'Markdown')
                  )
        except Exception as e:
            LOGGER(__name__).error(f"خطأ في إرسال الرد: {e}")
    
    def _convert_keyboard_for_subscription(self, keyboard_data):
        """تحويل keyboard للتنسيق المناسب لرسالة الاشتراك"""
        if not keyboard_data:
            return None
        
        rows = []
        for row in keyboard_data:
            buttons = []
            for button in row:
                if button.get('url'):
                    # زر رابط
                    buttons.append({
                        '@type': 'inlineKeyboardButton',
                        'text': button['text'],
                        'type': {
                            '@type': 'inlineKeyboardButtonTypeUrl',
                            'url': button['url']
                        }
                    })
                elif button.get('callback_data'):
                    # زر callback
                    buttons.append({
                        '@type': 'inlineKeyboardButton',
                        'text': button['text'],
                        'type': {
                            '@type': 'inlineKeyboardButtonTypeCallback',
                            'data': button['callback_data']
                        }
                    })
            if buttons:
                rows.append(buttons)
        
        return {
            '@type': 'replyMarkupInlineKeyboard',
            'rows': rows
        } if rows else None

# إنشاء مثيل عام لمعالج الأوامر
tdlib_command_handler = TDLibCommandHandler()