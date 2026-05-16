import hashlib
import hmac
import os
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import AdminRole, AdminUser


@dataclass
class AdminIdentity:
    id: int
    login: str
    role: str


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, digest_hex = password_hash.split(":", 1)
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            120_000,
        ).hex()
        return hmac.compare_digest(expected, digest_hex)
    except Exception:
        return False


async def authenticate_admin(
    session: AsyncSession,
    settings: Settings,
    *,
    login: str,
    password: str,
) -> AdminUser | None:
    result = await session.execute(select(AdminUser).where(AdminUser.login == login))
    admin = result.scalar_one_or_none()
    if admin and verify_password(password, admin.password_hash):
        return admin
    if not admin and login == settings.admin_login and password == settings.admin_password:
        admin = AdminUser(login=login, password_hash=hash_password(password), role=AdminRole.OWNER)
        session.add(admin)
        await session.flush()
        return admin
    return None


def current_admin(request: Request) -> AdminIdentity | None:
    admin = request.session.get("admin")
    if not admin:
        return None
    return AdminIdentity(**admin)

