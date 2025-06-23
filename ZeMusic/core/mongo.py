from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB_URI
from ..logging import LOGGER

LOGGER(__name__).info("🔄 initializing MongoDB connection...")

mongodb = None

if MONGO_DB_URI:
    try:
        client = AsyncIOMotorClient(MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        # اختبار الاتصال:
        client.admin.command("ping")
        mongodb = client.Elhyba
        LOGGER(__name__).info("✅ connected to MongoDB.")
    except Exception as e:
        LOGGER(__name__).warning(
            f"⚠️ failed to connect to MongoDB, falling back to stub: {e}"
        )

if not mongodb:
    # dummy stub for all collections used in the code:
    class DummyCollection:
        def __init__(self, name): self.name = name
        async def find_one(self, *a, **k): return None
        async def update_one(self, *a, **k): pass
        def find(self, *a, **k): return self
        async def __aiter__(self): return
        async def next(self): raise StopAsyncIteration

    class DummyDB:
        def __getattr__(self, name):
            return DummyCollection(name)

    mongodb = DummyDB()
    LOGGER(__name__).info("🔰 using MongoDB stub (DummyDB).")
