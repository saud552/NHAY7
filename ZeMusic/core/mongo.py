import logging

# لو كان الملف يحتوي على منطق Mongo حقيقي، نعلّقه أو نحذفه
# import motor.motor_asyncio

# منسِّق لرسائل اللوج
LOGGER = logging.getLogger(__name__)

class DummyCollection:
    """مجموعة زائفة تتجاهل كل العمليات."""
    async def find_one(self, *args, **kwargs):
        return None

    async def update_one(self, *args, **kwargs):
        return None

    async def insert_one(self, *args, **kwargs):
        return None

    async def delete_one(self, *args, **kwargs):
        return None

class DummyDB:
    """قاعدة بيانات زائفة بمجموعات sudoers و langs وغيرها."""
    def __init__(self):
        self.sudoers = DummyCollection()
        self.langs = DummyCollection()
        # إذا كانت هناك مجموعات أخرى يستخدمها كودك فـ أعرضها هنا:
        # self.some_other_collection = DummyCollection()
        LOGGER.info("🔰 تم تهيئة MongoDB stub (DummyDB)")

# اصدار كائن mongodb المستخدم عبر التطبيق
mongodb = DummyDB()
