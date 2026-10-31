import asyncio
import copy
import logging
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pymongo import ASCENDING, IndexModel
from app.core.config import settings

logger = logging.getLogger("applyforme.database")


class MockAsyncCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs
        self._index = 0

    def sort(self, field: str, direction: int = 1):
        reverse = direction < 0
        self._docs.sort(key=lambda d: d.get(field, ""), reverse=reverse)
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index < len(self._docs):
            doc = copy.deepcopy(self._docs[self._index])
            self._index += 1
            return doc
        raise StopAsyncIteration


class InMemoryAsyncCollection:
    """High-performance async in-memory collection for test environments and offline dev."""
    def __init__(self, name: str):
        self.name = name
        self._docs: List[Dict[str, Any]] = []

    def _matches(self, doc: Dict[str, Any], filter_q: Dict[str, Any]) -> bool:
        if not filter_q:
            return True
        for k, v in filter_q.items():
            if k == "$or" and isinstance(v, list):
                if not any(self._matches(doc, cond) for cond in v):
                    return False
            elif k == "_id":
                doc_id = str(doc.get("_id"))
                filter_id = str(v)
                if doc_id != filter_id:
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def create_indexes(self, indexes: List[Any]) -> None:
        pass

    async def find_one(self, filter_q: Optional[Dict[str, Any]] = None, sort: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        filter_q = filter_q or {}
        matched = [doc for doc in self._docs if self._matches(doc, filter_q)]
        if sort and matched:
            sort_field, sort_dir = sort[0]
            matched.sort(key=lambda x: x.get(sort_field, ""), reverse=(sort_dir == -1))
        if matched:
            return copy.deepcopy(matched[0])
        return None

    def find(self, filter_q: Optional[Dict[str, Any]] = None) -> MockAsyncCursor:
        filter_q = filter_q or {}
        matched = [doc for doc in self._docs if self._matches(doc, filter_q)]
        return MockAsyncCursor(matched)

    async def insert_one(self, doc: Dict[str, Any]):
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id

        doc_copy = copy.deepcopy(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = ObjectId()
        self._docs.append(doc_copy)
        return InsertResult(doc_copy["_id"])

    async def update_one(self, filter_q: Dict[str, Any], update_q: Dict[str, Any], upsert: bool = False):
        class UpdateResult:
            def __init__(self, matched_count: int, modified_count: int):
                self.matched_count = matched_count
                self.modified_count = modified_count

        set_fields = update_q.get("$set", update_q)
        for i, doc in enumerate(self._docs):
            if self._matches(doc, filter_q):
                self._docs[i].update(copy.deepcopy(set_fields))
                return UpdateResult(1, 1)

        if upsert:
            new_doc = copy.deepcopy(filter_q)
            new_doc.update(copy.deepcopy(set_fields))
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self._docs.append(new_doc)
            return UpdateResult(0, 1)

        return UpdateResult(0, 0)

    async def delete_one(self, filter_q: Dict[str, Any]):
        class DeleteResult:
            def __init__(self, deleted_count: int):
                self.deleted_count = deleted_count

        for i, doc in enumerate(self._docs):
            if self._matches(doc, filter_q):
                del self._docs[i]
                return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, filter_q: Dict[str, Any]):
        class DeleteResult:
            def __init__(self, deleted_count: int):
                self.deleted_count = deleted_count

        initial_len = len(self._docs)
        self._docs = [d for d in self._docs if not self._matches(d, filter_q)]
        return DeleteResult(initial_len - len(self._docs))

    async def count_documents(self, filter_q: Dict[str, Any]) -> int:
        return len([d for d in self._docs if self._matches(d, filter_q)])

    async def update_many(self, filter_q: Dict[str, Any], update_q: Dict[str, Any]):
        class UpdateResult:
            def __init__(self, modified_count: int):
                self.modified_count = modified_count

        set_fields = update_q.get("$set", update_q)
        count = 0
        for i, doc in enumerate(self._docs):
            if self._matches(doc, filter_q):
                self._docs[i].update(copy.deepcopy(set_fields))
                count += 1
        return UpdateResult(count)

    async def find_one_and_update(self, filter_q: Dict[str, Any], update_q: Dict[str, Any], return_document: bool = True):
        set_fields = update_q.get("$set", update_q)
        for i, doc in enumerate(self._docs):
            if self._matches(doc, filter_q):
                self._docs[i].update(copy.deepcopy(set_fields))
                return copy.deepcopy(self._docs[i])
        return None


class InMemoryAsyncDatabase:
    """Mock async database container holding memory collections."""
    def __init__(self, name: str = "applyforme"):
        self.name = name
        self._collections: Dict[str, InMemoryAsyncCollection] = {}

    def __getattr__(self, name: str) -> InMemoryAsyncCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryAsyncCollection(name)
        return self._collections[name]

    def __getitem__(self, name: str) -> InMemoryAsyncCollection:
        return self.__getattr__(name)


class DatabaseManager:
    client: Optional[Any] = None
    db: Optional[Any] = None


db_manager = DatabaseManager()


async def connect_to_mongo() -> None:
    """Initialize connection to MongoDB (Atlas on Azure, local, or in-memory mock)."""
    import os
    import socket
    from urllib.parse import urlparse

    if settings.APP_ENV == "test" or os.environ.get("APP_ENV") == "test":
        logger.info("[DB] Using InMemoryAsyncDatabase for test environment.")
        db_manager.db = InMemoryAsyncDatabase(settings.MONGODB_DB_NAME)
        return

    # Check reachability for local MongoDB without blocking
    parsed = urlparse(settings.MONGODB_URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 27017
    
    is_reachable = False
    if "localhost" in host or "127.0.0.1" in host:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                is_reachable = True
        except Exception:
            is_reachable = False

        if not is_reachable:
            logger.info(f"[DB] Local MongoDB at {host}:{port} not listening. Using InMemoryAsyncDatabase.")
            db_manager.client = None
            db_manager.db = InMemoryAsyncDatabase(settings.MONGODB_DB_NAME)
            return

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=800,
            uuidRepresentation="standard"
        )
        await asyncio.wait_for(client.admin.command('ping'), timeout=0.8)
        db_manager.client = client
        db_manager.db = client[settings.MONGODB_DB_NAME]
        await init_db_indexes(db_manager.db)
        logger.info("[DB] Connected to live MongoDB.")
    except Exception as e:
        logger.info(f"[DB] Live MongoDB unreachable ({e}). Switching to InMemoryAsyncDatabase.")
        db_manager.client = None
        db_manager.db = InMemoryAsyncDatabase(settings.MONGODB_DB_NAME)


async def close_mongo_connection() -> None:
    """Close MongoDB connection pool."""
    if db_manager.client:
        try:
            db_manager.client.close()
        except Exception:
            pass
        logger.info("MongoDB connection pool closed.")


async def init_db_indexes(db: Any) -> None:
    """Create optimized indexes on all collections for performance & isolation."""
    try:
        if hasattr(db, "users") and hasattr(db.users, "create_indexes"):
            await db.users.create_indexes([
                IndexModel([("email", ASCENDING)], unique=True, name="idx_users_email"),
                IndexModel([("googleId", ASCENDING)], unique=True, sparse=True, name="idx_users_google_id")
            ])
            await db.profiles.create_indexes([
                IndexModel([("userId", ASCENDING)], unique=True, name="idx_profiles_user_id")
            ])
            await db.resumes.create_indexes([
                IndexModel([("userId", ASCENDING)], name="idx_resumes_user_id"),
                IndexModel([("uploadedAt", ASCENDING)], name="idx_resumes_uploaded_at")
            ])
            await db.applications.create_indexes([
                IndexModel([("userId", ASCENDING), ("status", ASCENDING)], name="idx_apps_user_status"),
                IndexModel([("userId", ASCENDING), ("appliedAt", ASCENDING)], name="idx_apps_user_applied")
            ])
            await db.generated_answers.create_indexes([
                IndexModel([("userId", ASCENDING)], name="idx_answers_user_id"),
                IndexModel([("userId", ASCENDING), ("company", ASCENDING)], name="idx_answers_user_company")
            ])
            await db.preferences.create_indexes([
                IndexModel([("userId", ASCENDING)], unique=True, name="idx_prefs_user_id")
            ])
    except Exception as err:
        logger.debug(f"Index creation note: {err}")


def get_database() -> Optional[Any]:
    """Retrieve database instance."""
    if db_manager.db is None:
        db_manager.db = InMemoryAsyncDatabase(settings.MONGODB_DB_NAME)
    return db_manager.db
