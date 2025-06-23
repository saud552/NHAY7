from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB_URI
from ..logging import LOGGER

# Dummy classes for fallback when real MongoDB is unavailable
class DummyCollection:
    def __init__(self):
        self._data = []

    async def find_one(self, *args, **kwargs):
        return None

    async def update_one(self, *args, **kwargs):
        return None

    def find(self, *args, **kwargs):
        return self

    def insert_one(self, *args, **kwargs):
        return None

    async def delete_one(self, *args, **kwargs):
        return None

    def __aiter__(self):
        self._iter = iter(self._data)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

class DummyDB:
    def __init__(self):
        # استبانات لمجموعات قاعدة البيانات التي يستخدمها المشروع
        self.sudoers = DummyCollection()
        self.adminauth = DummyCollection()
        self.gbans = DummyCollection()
        self.lyrics = DummyCollection()
        # يمكنك إضافة المزيد هنا حسب الحاجة

    def __getattr__(self, name):
        # أي اسم مجموعة غير معرّف سيعود باستبانة وهمية تلقائيًّا
        return DummyCollection()

# محاولة الاتصال بـ MongoDB الحقيقي
LOGGER(__name__).info("🔰 Attempting MongoDB connection...")
try:
    _mongo_async_ = AsyncIOMotorClient(MONGO_DB_URI, serverSelectionTimeoutMS=5000)
    # نختار قاعدة البيانات باسم Elhyba
    mongodb = _mongo_async_["Elhyba"]
    # نتحقق من الاتصال فعليًّا
    _mongo_async_.server_info()
    LOGGER(__name__).info("✔ Connected to MongoDB.")
except Exception as e:
    LOGGER(__name__).warning(f"MongoDB unavailable, using stub: {e}")
    mongodb = DummyDB()
    LOGGER(__name__).info("✔ MongoDB stub initialized.")
