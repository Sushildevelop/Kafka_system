from datetime import datetime, timezone

from beanie.operators import Set
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.user import User


class UserRepository:
    """Persistence boundary for user accounts."""

    def __init__(
        self,
        write_database: AsyncIOMotorDatabase,
        read_database: AsyncIOMotorDatabase,
    ) -> None:
        self._write_users = write_database[User.Settings.name]
        self._read_users = read_database[User.Settings.name]

    async def get_by_google_sub(
        self, google_sub: str, *, use_primary: bool = False
    ) -> User | None:
        collection = self._write_users if use_primary else self._read_users
        document = await collection.find_one({"google_sub": google_sub})
        return User.model_validate(document) if document else None

    async def get_by_user_id(
        self, user_id: str, *, use_primary: bool = True
    ) -> User | None:
        collection = self._write_users if use_primary else self._read_users
        document = await collection.find_one({"user_id": user_id})
        return User.model_validate(document) if document else None

    async def upsert_google_user(
        self,
        *,
        user_id: str,
        google_sub: str,
        email: str,
        name: str,
        picture: str | None,
        email_verified: bool,
    ) -> User:
        now = datetime.now(timezone.utc)
        document = await self._write_users.find_one_and_update(
            {"google_sub": google_sub},
            {
                "$set": {
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "email_verified": email_verified,
                    "is_active": True,
                    "updated_at": now,
                    "last_login_at": now,
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "google_sub": google_sub,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if not document:
            raise RuntimeError("Could not create or update the Google user")
        return User.model_validate(document)

    async def delete_by_user_id(self, user_id: str) -> bool:
        result = await self._write_users.delete_one({"user_id": user_id})
        return result.deleted_count == 1
