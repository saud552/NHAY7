# ZeMusic/core/mongo.py

import os
import logging
from config import MONGO_DB_URI
from ..logging import LOGGER

LOGGER(__name__).info("🔄 تهيئة اتصال MongoDB...")

# إذا لم يُحدّد URI أو كان فارغاً، ننشئ DummyDB
if not MONGO_DB_URI:
    LOGGER(__name__).warning("⚠️ لم يُحدّد MONGO_DB_URI، استخدام قاعدة بيانات وهميّة (DummyDB).")

    class DummyCollection:
        """مجسّم لمجموعة MongoDB يقبل find_one و update_one و غيرها من العمليات البسيطة."""
        async def find_one(self, *args, **kwargs):
            return None

        async def update_one(self, *args, **kwargs):
            return None

        async def find(self, *args, **kwargs):
            # للإستخدام في تجاويد async for
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class DummyDB:
        """مجسّم لقاعدة بيانات: أي خاصيّة تطلبها تعود DummyCollection."""
        def __getattr__(self, name):
            return DummyCollection()

    mongodb = DummyDB()
    LOGGER(__name__).info("✔ DummyDB جاهزة للاستخدام.")

else:
    # إذا وُجد URI، نحاول الاتصال فعلياً
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        _mongo_async_ = AsyncIOMotorClient(MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        # نجرب طلب معلومات السيرفر لنتأكد من الاتصال
        _mongo_async_.server_info()
        mongodb = _mongo_async_.Elhyba
        LOGGER(__name__).info("✅ تمّ الاتصال بـ MongoDB بنجاح.")
    except Exception as e:
        # لو فشل الاتصال، نتحول إلى DummyDB أيضاً
        LOGGER(__name__).error(f"❌ فشل الاتصال بـ MongoDB: {e}")
        LOGGER(__name__).warning("⚠️ سنستخدم DummyDB بدلّاً عنها.")

        class DummyCollection:
            async def find_one(self, *args, **kwargs):
                return None
            async def update_one(self, *args, **kwargs):
                return None
            async def find(self, *args, **kwargs):
                return self
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise StopAsyncIteration

        class DummyDB:
            def __getattr__(self, name):
                return DummyCollection()

        mongodb = DummyDB()
        LOGGER(__name__).info("✔ DummyDB جاهزة للاستخدام.")
