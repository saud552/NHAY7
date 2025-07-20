import random
from typing import Dict, List, Union

# استخدام TDLib manager بدلاً من userbot
from ZeMusic.core.tdlib_client import tdlib_manager
from ZeMusic.core.database import db

# متغيرات الذاكرة للحالات المؤقتة (كما في الكود الأصلي)
active = []
activevideo = []
assistantdict = {}
autoend = {}
count = {}
channelconnect = {}
langm = {}
loop = {}
maintenance = []
nonadmin = {}
pause = {}
playmode = {}
playtype = {}
skipmode = {}

###############&&&&&&&&&&&&############

async def is_loge_enabled(chat_id):
    """التحقق من تفعيل السجلات"""
    settings = await db.get_chat_settings(chat_id)
    return settings.log_enabled

async def enable_loge(chat_id):
    """تفعيل السجلات"""
    await db.update_chat_setting(chat_id, log_enabled=True)

async def disable_loge(chat_id):
    """إلغاء تفعيل السجلات"""
    await db.update_chat_setting(chat_id, log_enabled=False)

###############&&&&&&&&&&&&############

async def is_welcome_enabled(chat_id):
    """التحقق من تفعيل الترحيب"""
    settings = await db.get_chat_settings(chat_id)
    return settings.welcome_enabled

async def enable_welcome(chat_id):
    """تفعيل الترحيب"""
    await db.update_chat_setting(chat_id, welcome_enabled=True)

async def disable_welcome(chat_id):
    """إلغاء تفعيل الترحيب"""
    await db.update_chat_setting(chat_id, welcome_enabled=False)
    
#####################################################
async def is_search_enabled1():
    """التحقق من تفعيل البحث العام"""
    return await db.get_temp_state("global_search_enabled", False)

async def enable_search1():
    """تفعيل البحث العام"""
    await db.set_temp_state("global_search_enabled", True)

async def disable_search1():
    """إلغاء تفعيل البحث العام"""
    await db.set_temp_state("global_search_enabled", False)

async def is_search_enabled(chat_id):
    """التحقق من تفعيل البحث في المجموعة"""
    settings = await db.get_chat_settings(chat_id)
    return settings.search_enabled

async def enable_search(chat_id):
    """تفعيل البحث في المجموعة"""
    await db.update_chat_setting(chat_id, search_enabled=True)

async def disable_search(chat_id):
    """إلغاء تفعيل البحث في المجموعة"""
    await db.update_chat_setting(chat_id, search_enabled=False)

########################################################

async def get_assistant_number(chat_id: int) -> str:
    """الحصول على رقم المساعد"""
    assistant = assistantdict.get(chat_id)
    if assistant:
        return str(assistant)
    
    # الحصول من قاعدة البيانات
    settings = await db.get_chat_settings(chat_id)
    assistantdict[chat_id] = settings.assistant_id
    return str(settings.assistant_id)

async def get_client(assistant: int):
    """الحصول على عميل المساعد - TDLib version"""
    try:
        # الحصول على المساعد من TDLib manager
        for tdlib_assistant in tdlib_manager.assistants:
            if tdlib_assistant.assistant_id == assistant:
                return tdlib_assistant
        
        # إذا لم يتم العثور على المساعد، إرجاع أول مساعد متاح
        if tdlib_manager.assistants:
            return tdlib_manager.assistants[0]
        
        return None
    except Exception:
        return None

async def set_assistant_new(chat_id, number):
    """تعيين مساعد جديد"""
    number = int(number)
    assistantdict[chat_id] = number
    await db.update_chat_setting(chat_id, assistant_id=number)

async def set_assistant(chat_id):
    """تعيين مساعد عشوائي - TDLib version"""
    try:
        # الحصول على قائمة المساعدين المتصلين
        connected_assistants = [
            assistant for assistant in tdlib_manager.assistants 
            if assistant.is_connected
        ]
        
        if not connected_assistants:
            return None
        
        # اختيار مساعد عشوائي
        selected_assistant = random.choice(connected_assistants)
        
        assistantdict[chat_id] = selected_assistant.assistant_id
        await db.update_chat_setting(chat_id, assistant_id=selected_assistant.assistant_id)
        
        return selected_assistant
    except Exception:
        return None

async def get_assistant(chat_id: int) -> str:
    """الحصول على المساعد - TDLib version"""
    try:
        assistant = assistantdict.get(chat_id)
        if assistant:
            return assistant
        
        settings = await db.get_chat_settings(chat_id)
        got_assis = settings.assistant_id
        if got_assis:
            assistantdict[chat_id] = got_assis
            return got_assis
        else:
            # اختيار مساعد متاح من TDLib
            available_assistants = [
                assistant.assistant_id for assistant in tdlib_manager.assistants 
                if assistant.is_connected
            ]
            
            if available_assistants:
                ran_assistant = random.choice(available_assistants)
                assistantdict[chat_id] = ran_assistant
                await db.update_chat_setting(chat_id, assistant_id=ran_assistant)
                return ran_assistant
            else:
                return None
    except Exception:
        return None

async def get_assistant_details(chat_id: int) -> str:
    """الحصول على تفاصيل المساعد - TDLib version"""
    try:
        assistant = assistantdict.get(chat_id)
        if assistant:
            return assistant
        
        settings = await db.get_chat_settings(chat_id)
        got_assis = settings.assistant_id
        if got_assis:
            assistantdict[chat_id] = got_assis
            return got_assis
        else:
            # اختيار مساعد متاح من TDLib
            available_assistants = [
                assistant.assistant_id for assistant in tdlib_manager.assistants 
                if assistant.is_connected
            ]
            
            if available_assistants:
                ran_assistant = random.choice(available_assistants)
                assistantdict[chat_id] = ran_assistant
                await db.update_chat_setting(chat_id, assistant_id=ran_assistant)
                return ran_assistant
            else:
                return None
    except Exception:
        return None

# وظائف Skip Mode
async def is_skipmode(chat_id: int) -> bool:
    """التحقق من وضع التخطي"""
    mode = skipmode.get(chat_id)
    if mode is not None:
        return mode
    return await db.get_temp_state(f"skipmode_{chat_id}", False)

async def skip_on(chat_id: int):
    """تفعيل وضع التخطي"""
    skipmode[chat_id] = True
    await db.set_temp_state(f"skipmode_{chat_id}", True)

async def skip_off(chat_id: int):
    """إلغاء تفعيل وضع التخطي"""
    skipmode[chat_id] = False
    await db.set_temp_state(f"skipmode_{chat_id}", False)

# وظائف عدد الأصوات
async def get_upvote_count(chat_id: int) -> int:
    """الحصول على عدد الأصوات المطلوبة"""
    mode = count.get(chat_id)
    if mode is not None:
        return mode
    
    settings = await db.get_chat_settings(chat_id)
    count[chat_id] = settings.upvote_count
    return settings.upvote_count

async def set_upvotes(chat_id: int, mode: int):
    """تعيين عدد الأصوات المطلوبة"""
    count[chat_id] = mode
    await db.update_chat_setting(chat_id, upvote_count=mode)

# وظائف الإنهاء التلقائي
async def is_autoend() -> bool:
    """التحقق من الإنهاء التلقائي العام"""
    return await db.get_temp_state("global_auto_end", False)

async def autoend_on():
    """تفعيل الإنهاء التلقائي العام"""
    await db.set_temp_state("global_auto_end", True)

async def autoend_off():
    """إلغاء تفعيل الإنهاء التلقائي العام"""
    await db.set_temp_state("global_auto_end", False)

# وظائف التكرار
async def get_loop(chat_id: int) -> int:
    """الحصول على وضع التكرار"""
    lop = loop.get(chat_id)
    if lop is not None:
        return lop
    return await db.get_temp_state(f"loop_{chat_id}", 0)

async def set_loop(chat_id: int, mode: int):
    """تعيين وضع التكرار"""
    loop[chat_id] = mode
    await db.set_temp_state(f"loop_{chat_id}", mode)

# وظائف الاتصال بالقناة
async def get_cmode(chat_id: int) -> str:
    """الحصول على وضع الاتصال بالقناة"""
    mode = channelconnect.get(chat_id)
    if mode is not None:
        return mode["mode"]
    return await db.get_temp_state(f"channelconnect_{chat_id}", "Direct")

async def set_cmode(chat_id: int, mode: str):
    """تعيين وضع الاتصال بالقناة"""
    channelconnect[chat_id] = {"mode": mode}
    await db.set_temp_state(f"channelconnect_{chat_id}", mode)

# وظائف نوع التشغيل
async def get_playtype(chat_id: int) -> str:
    """الحصول على نوع التشغيل"""
    mode = playtype.get(chat_id)
    if mode is not None:
        return mode
    
    settings = await db.get_chat_settings(chat_id)
    playtype[chat_id] = settings.play_type
    return settings.play_type

async def set_playtype(chat_id: int, ptype: str):
    """تعيين نوع التشغيل"""
    playtype[chat_id] = ptype
    await db.update_chat_setting(chat_id, play_type=ptype)

# وظائف وضع التشغيل
async def get_playmode(chat_id: int) -> str:
    """الحصول على وضع التشغيل"""
    mode = playmode.get(chat_id)
    if mode is not None:
        return mode
    
    settings = await db.get_chat_settings(chat_id)
    playmode[chat_id] = settings.play_mode
    return settings.play_mode

async def set_playmode(chat_id: int, mode: str):
    """تعيين وضع التشغيل"""
    playmode[chat_id] = mode
    await db.update_chat_setting(chat_id, play_mode=mode)

# وظائف اللغة
async def get_lang(chat_id: int) -> str:
    """الحصول على اللغة"""
    mode = langm.get(chat_id)
    if mode is not None:
        return mode
    
    settings = await db.get_chat_settings(chat_id)
    langm[chat_id] = settings.language
    return settings.language

async def set_lang(chat_id: int, lang: str):
    """تعيين اللغة"""
    langm[chat_id] = lang
    await db.update_chat_setting(chat_id, language=lang)

# وظائف الإيقاف المؤقت
async def is_music_playing(chat_id: int) -> bool:
    """التحقق من تشغيل الموسيقى"""
    mode = pause.get(chat_id)
    if mode is not None:
        return not mode  # إذا كان مُوقف مؤقتاً = False، إذا كان يعمل = True
    return True  # افتراضياً يعمل

async def music_on(chat_id: int):
    """تشغيل الموسيقى"""
    pause[chat_id] = False

async def music_off(chat_id: int):
    """إيقاف الموسيقى مؤقتاً"""
    pause[chat_id] = True

# وظائف المستخدمين والمديرين
async def get_userss(user_id: int) -> bool:
    """التحقق من وجود المستخدم"""
    # إضافة المستخدم تلقائياً إذا لم يكن موجوداً
    await db.add_user(user_id)
    return True

async def is_served_user(user_id: int) -> bool:
    """التحقق من خدمة المستخدم"""
    return await get_userss(user_id)

async def add_served_user(user_id: int):
    """إضافة مستخدم مخدوم"""
    await db.add_user(user_id)

async def get_served_chats() -> list:
    """الحصول على المجموعات المخدومة"""
    stats = await db.get_stats()
    return list(range(1, stats['chats'] + 1))  # مؤقت

async def is_served_chat(chat_id: int) -> bool:
    """التحقق من خدمة المجموعة"""
    await db.add_chat(chat_id)
    return True

async def add_served_chat(chat_id: int):
    """إضافة مجموعة مخدومة"""
    await db.add_chat(chat_id)

# وظائف القائمة السوداء
async def blacklisted_chats() -> list:
    """الحصول على المجموعات المحظورة"""
    # TODO: تنفيذ هذه الوظيفة
    return []

async def blacklist_chat(chat_id: int):
    """إضافة مجموعة للقائمة السوداء"""
    await db.blacklist_chat(chat_id)

async def whitelist_chat(chat_id: int):
    """إزالة مجموعة من القائمة السوداء"""
    await db.whitelist_chat(chat_id)

async def is_blacklisted_chat(chat_id: int) -> bool:
    """التحقق من وجود المجموعة في القائمة السوداء"""
    return await db.is_blacklisted_chat(chat_id)

# وظائف المصرح لهم
async def get_authuser_names(chat_id: int):
    """الحصول على أسماء المصرح لهم"""
    users = await db.get_auth_users(chat_id)
    return {"notes": users}

async def get_authuser(chat_id: int, user_id: int) -> bool:
    """التحقق من تصريح المستخدم"""
    return await db.is_auth_user(chat_id, user_id)

async def save_authuser(chat_id: int, user_id: int):
    """حفظ مستخدم مصرح"""
    await db.add_auth_user(chat_id, user_id)

async def delete_authuser(chat_id: int, user_id: int) -> bool:
    """حذف مستخدم مصرح"""
    await db.remove_auth_user(chat_id, user_id)
    return True

# وظائف الحظر العام
async def get_gbanned_users() -> list:
    """الحصول على المستخدمين المحظورين عالمياً"""
    # TODO: تنفيذ هذه الوظيفة
    return []

async def is_gbanned_user(user_id: int) -> bool:
    """التحقق من الحظر العالمي"""
    return await db.is_banned(user_id)

async def add_gban_user(user_id: int):
    """إضافة حظر عالمي"""
    await db.ban_user(user_id)

async def remove_gban_user(user_id: int):
    """إزالة الحظر العالمي"""
    await db.unban_user(user_id)

# وظائف المديرين
async def get_sudoers() -> list:
    """الحصول على قائمة المديرين"""
    return await db.get_sudoers()

async def add_sudo(user_id: int) -> bool:
    """إضافة مدير"""
    await db.add_sudo(user_id)
    return True

async def remove_sudo(user_id: int) -> bool:
    """إزالة مدير"""
    await db.remove_sudo(user_id)
    return True

# وظائف عدم الإدارة
async def check_nonadmin_chat(chat_id: int) -> bool:
    """التحقق من إعدادات عدم الإدارة"""
    return await db.get_temp_state(f"nonadmin_{chat_id}", False)

async def is_nonadmin_chat(chat_id: int) -> bool:
    """التحقق من وضع عدم الإدارة"""
    mode = nonadmin.get(chat_id)
    if mode is not None:
        return mode
    
    stored = await check_nonadmin_chat(chat_id)
    nonadmin[chat_id] = stored
    return stored

async def add_nonadmin_chat(chat_id: int):
    """إضافة مجموعة لوضع عدم الإدارة"""
    nonadmin[chat_id] = True
    await db.set_temp_state(f"nonadmin_{chat_id}", True)

async def remove_nonadmin_chat(chat_id: int):
    """إزالة مجموعة من وضع عدم الإدارة"""
    nonadmin[chat_id] = False
    await db.set_temp_state(f"nonadmin_{chat_id}", False)

# وظائف الصيانة
async def is_maintenance():
    """التحقق من وضع الصيانة"""
    if not maintenance:
        return await db.get_temp_state("maintenance_mode", False)
    return True

async def maintenance_off():
    """إلغاء وضع الصيانة"""
    maintenance.clear()
    await db.set_temp_state("maintenance_mode", False)

async def maintenance_on():
    """تفعيل وضع الصيانة"""
    maintenance.clear()
    maintenance.append(1)
    await db.set_temp_state("maintenance_mode", True)

async def is_on_off(on_off: int) -> bool:
    """التحقق من حالة التشغيل/الإيقاف"""
    return await db.get_temp_state(f"on_off_{on_off}", True)

async def add_on(on_off: int):
    """إضافة حالة تشغيل"""
    await db.set_temp_state(f"on_off_{on_off}", True)

async def add_off(on_off: int):
    """إضافة حالة إيقاف"""
    await db.set_temp_state(f"on_off_{on_off}", False)

# وظائف المحظورين محلياً
async def get_banned_users() -> list:
    """الحصول على المستخدمين المحظورين محلياً"""
    # TODO: تنفيذ هذه الوظيفة
    return []

async def is_banned_user(user_id: int) -> bool:
    """التحقق من الحظر المحلي"""
    return await db.is_banned(user_id)

async def add_banned_user(user_id: int):
    """إضافة حظر محلي"""
    await db.ban_user(user_id)

async def remove_banned_user(user_id: int):
    """إزالة الحظر المحلي"""
    await db.unban_user(user_id)
