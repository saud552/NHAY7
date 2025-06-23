import logging

from ..logging import LOGGER

LOGGER(__name__).info("🔰 استخدام Stub بدلاً من MongoDB الحقيقي...")


class DummyCollection:
    """
    تمثيل زائف لمجموعة البيانات؛ كل الدوال تعيد None أو قائمة فارغة
    لتجنّب أي خطأ عند استدعائها في باقي الكود.
    """
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
    قاعدة بيانات زائفة: أي صفة تُطلب منها تُحوّل إلى DummyCollection.
    هذا يعني أنه مهما كانت أسماء المجمعات (collections) في كودك
    — sudoers, langs, adminauth, cmode, الخ — فإن Stub هنا
    سيوفّر dummy = DummyCollection() لأي منها تلقائيًا
    دون رفع أي خطأ.
    """
    def __init__(self):
        LOGGER(__name__).info("✔ MongoDB stub مُهيَّأ بنجاح")

    def __getattr__(self, name: str):
        # عند طلب أي صفة، رجّع DummyCollection
        col = DummyCollection()
        setattr(self, name, col)
        LOGGER(__name__).debug(f"🔹 MongoDB Stub: أنشأنا DummyCollection لِـ '{name}'")
        return col

    def __dir__(self):
        # لعرض أسماء الصفات عند استخدام dir(mongodb)
        return super().__dir__() + ["<any_collection_name>"]


# هذا هو الكائن الوحيد الذي سيُستورد في باقي التطبيق
mongodb = DummyDB()
