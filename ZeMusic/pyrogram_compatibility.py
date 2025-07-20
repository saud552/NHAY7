"""
ملف التوافق الشامل لاستبدال pyrogram بـ TDLib
يتم استيراده بدلاً من pyrogram في جميع الملفات
"""

from .compatibility import (
    CompatibilityClient as Client, 
    TDLibFilters,
    enums,
    errors,
    app,
    __version__
)

# إنشاء كائن filters عام
filters = TDLibFilters()

# إضافة types للتوافق الكامل
class types:
    class Message:
        def __init__(self, **kwargs):
            self.text = kwargs.get('text', '')
            self.chat = kwargs.get('chat')
            self.from_user = kwargs.get('from_user')
            self.message_id = kwargs.get('message_id')
            self.reply_to_message = kwargs.get('reply_to_message')
    
    class CallbackQuery:
        def __init__(self, **kwargs):
            self.data = kwargs.get('data', '')
            self.from_user = kwargs.get('from_user')
            self.message = kwargs.get('message')
    
    class InlineQuery:
        def __init__(self, **kwargs):
            self.query = kwargs.get('query', '')
            self.from_user = kwargs.get('from_user')
    
    class User:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id')
            self.first_name = kwargs.get('first_name', '')
            self.username = kwargs.get('username')
    
    class Chat:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id')
            self.title = kwargs.get('title', '')
            self.type = kwargs.get('type', '')
    
    class InlineKeyboardMarkup:
        def __init__(self, inline_keyboard=None, **kwargs):
            self.inline_keyboard = inline_keyboard or []
    
    class InlineKeyboardButton:
        def __init__(self, text, **kwargs):
            self.text = text
            self.url = kwargs.get('url')
            self.callback_data = kwargs.get('callback_data')
            self.switch_inline_query = kwargs.get('switch_inline_query')
    
    class ReplyKeyboardMarkup:
        def __init__(self, keyboard=None, **kwargs):
            self.keyboard = keyboard or []
            self.resize_keyboard = kwargs.get('resize_keyboard', True)
            self.one_time_keyboard = kwargs.get('one_time_keyboard', False)
    
    class InlineQueryResultArticle:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id')
            self.title = kwargs.get('title', '')
            self.description = kwargs.get('description', '')
            self.input_message_content = kwargs.get('input_message_content')
    
    class InputTextMessageContent:
        def __init__(self, message_text, **kwargs):
            self.message_text = message_text
            self.parse_mode = kwargs.get('parse_mode')
    
    class InputMediaPhoto:
        def __init__(self, media, **kwargs):
            self.media = media
            self.caption = kwargs.get('caption', '')
    
    class Voice:
        def __init__(self, **kwargs):
            self.file_id = kwargs.get('file_id')
            self.duration = kwargs.get('duration', 0)

# متغير emoji للتوافق
emoji = "🎵"

# دالة decorator للتوافق
def on_message(filters_obj):
    """محاكاة @app.on_message decorator"""
    def decorator(func):
        return func
    return decorator

def on_callback_query(filters_obj=None):
    """محاكاة @app.on_callback_query decorator"""
    def decorator(func):
        return func
    return decorator

def on_inline_query():
    """محاكاة @app.on_inline_query decorator"""
    def decorator(func):
        return func
    return decorator

# إضافة app methods للتوافق
app.on_message = on_message
app.on_callback_query = on_callback_query
app.on_inline_query = on_inline_query