# تم تعطيل هذا الملف لأن النظام الجديد للاشتراك الإجباري متوفر
# استخدم: /admin ← الاشتراك الإجباري للوصول للنظام الجديد المتطور

# النظام الجديد يوفر:
# - إدارة كاملة من لوحة المطور
# - فحص المشتركين وطلبات الانضمام
# - نظام كاش محسن
# - إعدادات مرنة ومتقدمة
# - دعم TDLib كامل
# - تنبيهات ذكية

from ZeMusic.logging import LOGGER

LOGGER(__name__).info("⚠️ ملف الاشتراك الإجباري القديم معطل - استخدم النظام الجديد من /admin")

# ==========================
# الكود القديم معطل لتجنب التعارض
# ==========================

# from pyrogram import Client, filters
# from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
# from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
# from ZeMusic import app
# import config

# Muntazer = config.CHANNEL_ASHTRAK
# @app.on_message(filters.incoming & filters.private, group=-1)
# async def must_join_channel(app: Client, msg: Message):
#     if not Muntazer:
#         return
#     try:
#         try:
#             await app.get_chat_member(Muntazer, msg.from_user.id)
#         except UserNotParticipant:
#             if Muntazer.isalpha():
#                 link = "https://t.me/" + Muntazer
#             else:
#                 chat_info = await app.get_chat(Muntazer)
#                 link = chat_info.invite_link
#             try:
#                 await msg.reply(
#                     f"⟡ عزيزي {msg.from_user.mention} \n⟡ عليك الأشتراك في قناة البوت \n⟡ قناة البوت : @{Muntazer}.",
#                     disable_web_page_preview=True,
#                     reply_markup=InlineKeyboardMarkup([
#                         [InlineKeyboardButton(text="اضغط للإشتراك", url=link)]
#                     ])
#                 )
#                 await msg.stop_propagation()
#             except ChatWriteForbidden:
#                 pass
#     except ChatAdminRequired:
#         print(f"I m not admin in the MUST_JOIN chat {Muntazer}!")

