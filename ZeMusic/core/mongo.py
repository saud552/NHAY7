import logging

LOGGER = logging.getLogger(__name__)

class DummyCollection:
    """مجموعة بيانات زائفة تتجاهل كل العمليات وتعيد None أو قيم فارغة."""
    async def find_one(self, *args, **kwargs):
        return None

    async def find(self, *args, **kwargs):
        return []

    async def update_one(self, *args, **kwargs):
        return None

    async def insert_one(self, *args, **kwargs):
        return None

    async def delete_one(self, *args, **kwargs):
        return None

class DummyDB:
    """
    قاعدة بيانات زائفة بمجموعات:
      - sudoers    (لـ sudo)
      - langs      (لـ تخزين لغات الشات)
      - adminauth  (لـ كائن authdb في database.py)
      - ... يمكنك إضافة أي مجموعة أخرى يستخدمها كودك هنا
    """
    def __init__(self):
        self.sudoers = DummyCollection()
        self.langs = DummyCollection()
        self.adminauth = DummyCollection()
        # إذا كان لديك مجموعات أخرى تستوردها utils/database.py،
        # كرّر السطر أعلاه مع اسم المجموعة.
        LOGGER.info("🔰 تم تهيئة MongoDB stub (DummyDB)")

# كائن mongodb الذي يستورده الكود في بقية التطبيق
mongodb = DummyDB()
