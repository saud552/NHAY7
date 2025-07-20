"""
🎛️ لوحة تحكم إدارة الكوكيز والحلول المتقدمة
===========================================

لوحة تحكم شاملة لإدارة:
- نظام تدوير الكوكيز
- إدارة البروكسي
- التخزين المؤقت الذكي
- المراقبة والإحصائيات
"""

import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from ZeMusic import app, LOGGER
from ZeMusic.misc import SUDOERS
from ZeMusic.core.cookies_rotator import cookies_rotator
from ZeMusic.core.proxy_manager import proxy_manager
from ZeMusic.core.smart_cache import smart_cache

class CookiesManagementHandler:
    """معالج لوحة تحكم الكوكيز"""
    
    def __init__(self):
        self.setup_handlers()
    
    def setup_handlers(self):
        """تهيئة معالجات الأوامر والcallbacks"""
        
        @app.on_message(filters.command("cookies_panel") & filters.user(SUDOERS))
        async def cookies_panel_command(client, message: Message):
            """عرض لوحة تحكم الكوكيز"""
            await self.show_main_panel(message)
        
        @app.on_callback_query(filters.regex("^cookies_"))
        async def handle_cookies_callbacks(client, callback_query: CallbackQuery):
            """معالج callbacks لوحة الكوكيز"""
            if callback_query.from_user.id not in SUDOERS:
                await callback_query.answer("❌ غير مصرح لك بالوصول!", show_alert=True)
                return
            
            data = callback_query.data
            
            if data == "cookies_main":
                await self.show_main_panel(callback_query)
            elif data == "cookies_stats":
                await self.show_stats(callback_query)
            elif data == "cookies_manage":
                await self.show_cookies_management(callback_query)
            elif data == "cookies_add":
                await self.add_cookies_prompt(callback_query)
            elif data == "cookies_health":
                await self.health_check(callback_query)
            elif data == "proxy_main":
                await self.show_proxy_panel(callback_query)
            elif data == "proxy_stats":
                await self.show_proxy_stats(callback_query)
            elif data == "proxy_test":
                await self.test_all_proxies(callback_query)
            elif data == "cache_main":
                await self.show_cache_panel(callback_query)
            elif data == "cache_stats":
                await self.show_cache_stats(callback_query)
            elif data == "cache_cleanup":
                await self.cleanup_cache(callback_query)
            elif data == "system_overview":
                await self.show_system_overview(callback_query)
    
    async def show_main_panel(self, update):
        """عرض اللوحة الرئيسية"""
        text = """
🎛️ **لوحة تحكم الكوكيز والحلول المتقدمة**

اختر النظام الذي تريد إدارته:

🍪 **نظام الكوكيز:** إدارة وتدوير الكوكيز التلقائي
🌐 **نظام البروكسي:** إدارة واختبار البروكسي
💾 **التخزين المؤقت:** إدارة التخزين الذكي
📊 **نظرة عامة:** إحصائيات شاملة للنظام
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍪 إدارة الكوكيز", callback_data="cookies_manage"),
                InlineKeyboardButton("🌐 إدارة البروكسي", callback_data="proxy_main")
            ],
            [
                InlineKeyboardButton("💾 التخزين المؤقت", callback_data="cache_main"),
                InlineKeyboardButton("📊 نظرة عامة", callback_data="system_overview")
            ],
            [
                InlineKeyboardButton("📈 إحصائيات النظام", callback_data="cookies_stats"),
                InlineKeyboardButton("🔍 فحص الصحة", callback_data="cookies_health")
            ]
        ])
        
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(text, reply_markup=keyboard)
        else:
            await update.reply_text(text, reply_markup=keyboard)
    
    async def show_stats(self, callback_query: CallbackQuery):
        """عرض إحصائيات شاملة"""
        try:
            # إحصائيات الكوكيز
            cookies_stats = cookies_rotator.get_cookies_stats()
            
            # إحصائيات البروكسي
            proxy_stats = proxy_manager.get_proxy_stats()
            
            # إحصائيات التخزين المؤقت
            cache_stats = smart_cache.get_stats()
            
            text = f"""
📊 **إحصائيات النظام الشاملة**

🍪 **الكوكيز:**
• المجموع: {cookies_stats['total']}
• النشطة: {cookies_stats['active']}
• المحظورة: {cookies_stats['banned']}
• متوسط الصحة: {cookies_stats['health_avg']:.1f}%

🌐 **البروكسي:**
• المجموع: {proxy_stats['total']}
• العاملة: {proxy_stats['working']}
• المعطلة: {proxy_stats['failed']}
• متوسط زمن الاستجابة: {proxy_stats['avg_response_time']:.2f}s

💾 **التخزين المؤقت:**
• الطلبات الكلية: {cache_stats['total_requests']}
• معدل النجاح: {cache_stats['hit_rate_percent']}%
• الحجم المستخدم: {cache_stats['cache_size_mb']} MB
• عدد المدخلات: {cache_stats['entries_count']}

📈 **الأداء العام:**
• حالة النظام: {"🟢 ممتاز" if cache_stats['hit_rate_percent'] > 70 else "🟡 جيد" if cache_stats['hit_rate_percent'] > 50 else "🔴 يحتاج تحسين"}
• استقرار الكوكيز: {"🟢 مستقر" if cookies_stats['active'] > cookies_stats['total'] * 0.7 else "🟡 متوسط" if cookies_stats['active'] > cookies_stats['total'] * 0.5 else "🔴 غير مستقر"}
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 تحديث", callback_data="cookies_stats"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.answer(f"❌ خطأ في جلب الإحصائيات: {e}", show_alert=True)
    
    async def show_cookies_management(self, callback_query: CallbackQuery):
        """عرض لوحة إدارة الكوكيز"""
        try:
            stats = cookies_rotator.get_cookies_stats()
            
            text = f"""
🍪 **إدارة الكوكيز**

📊 **الحالة الحالية:**
• المجموع: {stats['total']} كوكيز
• النشطة: {stats['active']} كوكيز
• المحظورة: {stats['banned']} كوكيز
• متوسط الاستخدام: {stats['usage_avg']:.1f}

⚙️ **العمليات المتاحة:**
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ إضافة كوكيز", callback_data="cookies_add"),
                    InlineKeyboardButton("🔄 إعادة التدوير", callback_data="cookies_rotate")
                ],
                [
                    InlineKeyboardButton("🔍 فحص الصحة", callback_data="cookies_health"),
                    InlineKeyboardButton("📋 قائمة الكوكيز", callback_data="cookies_list")
                ],
                [
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.answer(f"❌ خطأ: {e}", show_alert=True)
    
    async def add_cookies_prompt(self, callback_query: CallbackQuery):
        """طلب إضافة كوكيز جديدة"""
        text = """
➕ **إضافة كوكيز جديدة**

📝 **التعليمات:**
1. قم بتصدير الكوكيز من المتصفح
2. أرسل محتوى ملف الكوكيز كرسالة
3. سيتم تشفيرها وإضافتها تلقائياً

**تنسيق الرسالة:**
```
/add_cookies اسم_الحساب
[محتوى الكوكيز هنا]
```

**مثال:**
```
/add_cookies youtube_account1
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1234567890	session_token	abc123...
```
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")]
        ])
        
        await callback_query.edit_message_text(text, reply_markup=keyboard)
    
    async def health_check(self, callback_query: CallbackQuery):
        """فحص صحة الكوكيز"""
        await callback_query.answer("🔍 جاري فحص صحة الكوكيز...")
        
        try:
            results = await cookies_rotator.health_check()
            
            text = f"""
🔍 **نتائج فحص صحة الكوكيز**

✅ **الكوكيز الصحية ({len(results['healthy'])}):**
{chr(10).join([f"• {name}" for name in results['healthy'][:5]])}
{"..." if len(results['healthy']) > 5 else ""}

⚠️ **الكوكيز المتدهورة ({len(results['degraded'])}):**
{chr(10).join([f"• {name}" for name in results['degraded'][:5]])}
{"..." if len(results['degraded']) > 5 else ""}

❌ **الكوكيز الفاشلة ({len(results['failed'])}):**
{chr(10).join([f"• {name}" for name in results['failed'][:5]])}
{"..." if len(results['failed']) > 5 else ""}

📋 **التوصيات:**
• استبدال الكوكيز الفاشلة
• مراقبة الكوكيز المتدهورة
• إضافة كوكيز جديدة عند الحاجة
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 إعادة الفحص", callback_data="cookies_health"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.edit_message_text(f"❌ خطأ في فحص الصحة: {e}")
    
    async def show_proxy_panel(self, callback_query: CallbackQuery):
        """عرض لوحة البروكسي"""
        try:
            stats = proxy_manager.get_proxy_stats()
            
            text = f"""
🌐 **إدارة البروكسي**

📊 **الحالة الحالية:**
• المجموع: {stats['total']} بروكسي
• العاملة: {stats['working']} بروكسي
• المعطلة: {stats['failed']} بروكسي
• متوسط زمن الاستجابة: {stats['avg_response_time']:.2f}s
• معدل النجاح: {stats['avg_success_rate']:.1f}%
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔍 اختبار الكل", callback_data="proxy_test"),
                    InlineKeyboardButton("📊 الإحصائيات", callback_data="proxy_stats")
                ],
                [
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.answer(f"❌ خطأ: {e}", show_alert=True)
    
    async def test_all_proxies(self, callback_query: CallbackQuery):
        """اختبار جميع البروكسي"""
        await callback_query.answer("🔍 جاري اختبار جميع البروكسي...")
        
        try:
            await proxy_manager._test_all_proxies()
            stats = proxy_manager.get_proxy_stats()
            
            text = f"""
✅ **اكتمل اختبار البروكسي**

📊 **النتائج:**
• تم اختبار: {stats['total']} بروكسي
• نجح: {stats['working']} بروكسي
• فشل: {stats['failed']} بروكسي
• معدل النجاح: {(stats['working']/max(1,stats['total'])*100):.1f}%
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="proxy_test"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.edit_message_text(f"❌ خطأ في اختبار البروكسي: {e}")
    
    async def show_cache_panel(self, callback_query: CallbackQuery):
        """عرض لوحة التخزين المؤقت"""
        try:
            stats = smart_cache.get_stats()
            
            text = f"""
💾 **إدارة التخزين المؤقت الذكي**

📊 **الحالة الحالية:**
• الطلبات الكلية: {stats['total_requests']}
• نسبة النجاح: {stats['hit_rate_percent']}%
• الحجم المستخدم: {stats['cache_size_mb']} MB
• الحد الأقصى: {stats['max_size_mb']} MB
• عدد المدخلات: {stats['entries_count']}

📈 **الأداء:** {"🟢 ممتاز" if stats['hit_rate_percent'] > 70 else "🟡 جيد" if stats['hit_rate_percent'] > 50 else "🔴 يحتاج تحسين"}
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🧹 تنظيف", callback_data="cache_cleanup"),
                    InlineKeyboardButton("📊 الإحصائيات", callback_data="cache_stats")
                ],
                [
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.answer(f"❌ خطأ: {e}", show_alert=True)
    
    async def cleanup_cache(self, callback_query: CallbackQuery):
        """تنظيف التخزين المؤقت"""
        await callback_query.answer("🧹 جاري تنظيف التخزين المؤقت...")
        
        try:
            await smart_cache._cleanup()
            stats = smart_cache.get_stats()
            
            text = f"""
✅ **اكتمل تنظيف التخزين المؤقت**

📊 **الحالة بعد التنظيف:**
• الحجم الحالي: {stats['cache_size_mb']} MB
• عدد المدخلات: {stats['entries_count']}
• نسبة النجاح: {stats['hit_rate_percent']}%
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 تنظيف مرة أخرى", callback_data="cache_cleanup"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.edit_message_text(f"❌ خطأ في التنظيف: {e}")
    
    async def show_system_overview(self, callback_query: CallbackQuery):
        """عرض نظرة عامة على النظام"""
        try:
            # جمع جميع الإحصائيات
            cookies_stats = cookies_rotator.get_cookies_stats()
            proxy_stats = proxy_manager.get_proxy_stats()
            cache_stats = smart_cache.get_stats()
            
            # تقييم الحالة العامة
            cookies_health = "🟢" if cookies_stats['active'] > cookies_stats['total'] * 0.7 else "🟡" if cookies_stats['active'] > cookies_stats['total'] * 0.5 else "🔴"
            proxy_health = "🟢" if proxy_stats['working'] > proxy_stats['total'] * 0.7 else "🟡" if proxy_stats['working'] > proxy_stats['total'] * 0.5 else "🔴"
            cache_health = "🟢" if cache_stats['hit_rate_percent'] > 70 else "🟡" if cache_stats['hit_rate_percent'] > 50 else "🔴"
            
            text = f"""
📊 **نظرة عامة على النظام**

🛡️ **حالة الأنظمة:**
• الكوكيز: {cookies_health} ({cookies_stats['active']}/{cookies_stats['total']})
• البروكسي: {proxy_health} ({proxy_stats['working']}/{proxy_stats['total']})
• التخزين المؤقت: {cache_health} ({cache_stats['hit_rate_percent']:.1f}% نجاح)

📈 **مؤشرات الأداء:**
• استقرار الكوكيز: {(cookies_stats['active']/max(1,cookies_stats['total'])*100):.1f}%
• موثوقية البروكسي: {proxy_stats['avg_success_rate']:.1f}%
• كفاءة التخزين المؤقت: {cache_stats['hit_rate_percent']:.1f}%

💡 **التوصيات:**
{"• ✅ النظام يعمل بكفاءة عالية" if all(h == "🟢" for h in [cookies_health, proxy_health, cache_health]) else "• ⚠️ بعض الأنظمة تحتاج مراجعة" if any(h == "🟡" for h in [cookies_health, proxy_health, cache_health]) else "• 🚨 النظام يحتاج اهتمام فوري"}
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 تحديث", callback_data="system_overview"),
                    InlineKeyboardButton("📈 إحصائيات تفصيلية", callback_data="cookies_stats")
                ],
                [
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="cookies_main")
                ]
            ])
            
            await callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.answer(f"❌ خطأ: {e}", show_alert=True)


# تهيئة معالج لوحة التحكم
cookies_management_handler = CookiesManagementHandler()


# أوامر إضافية لإدارة الكوكيز
@app.on_message(filters.command("add_cookies") & filters.user(SUDOERS))
async def add_cookies_command(client, message: Message):
    """إضافة كوكيز جديدة"""
    try:
        # تحليل الرسالة
        lines = message.text.split('\n')
        if len(lines) < 2:
            await message.reply_text("❌ تنسيق خاطئ!\n\nالاستخدام:\n/add_cookies اسم_الحساب\n[محتوى الكوكيز]")
            return
        
        # استخراج اسم الحساب
        command_line = lines[0].split()
        if len(command_line) < 2:
            await message.reply_text("❌ يجب تحديد اسم الحساب!")
            return
        
        account_name = command_line[1]
        cookies_content = '\n'.join(lines[1:])
        
        # إضافة الكوكيز
        success = await cookies_rotator.add_new_cookies(cookies_content, account_name)
        
        if success:
            await message.reply_text(f"✅ تم إضافة كوكيز الحساب: {account_name}")
        else:
            await message.reply_text("❌ فشل في إضافة الكوكيز!")
            
    except Exception as e:
        await message.reply_text(f"❌ خطأ: {e}")


@app.on_message(filters.command("cookies_status") & filters.user(SUDOERS))
async def cookies_status_command(client, message: Message):
    """عرض حالة الكوكيز السريعة"""
    try:
        stats = cookies_rotator.get_cookies_stats()
        
        text = f"""
🍪 **حالة الكوكيز السريعة**

📊 **الإحصائيات:**
• المجموع: {stats['total']}
• النشطة: {stats['active']}
• المحظورة: {stats['banned']}
• متوسط الصحة: {stats['health_avg']:.1f}%

🚨 **الحالة:** {"🟢 جيدة" if stats['active'] > stats['total'] * 0.7 else "🟡 تحتاج مراقبة" if stats['active'] > stats['total'] * 0.5 else "🔴 حرجة"}
        """
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ خطأ: {e}")