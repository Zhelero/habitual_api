import logging
from sqlalchemy import select, exists, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.models import TokenBlacklist

logger = logging.getLogger(__name__)

class TokenBlacklistRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, jti: str, expires_at: datetime):
        obj = TokenBlacklist(jti=jti, expires_at=expires_at)
        self.db.add(obj)
        try:
            self.db.flush()
            return obj
        except IntegrityError:
            self.db.rollback()
            logger.debug(f"Token already blacklisted: {jti}")
            return None

    def is_blacklisted(self, jti: str) -> bool:
        if not jti:
            return False

        stmt = select(exists().where(TokenBlacklist.jti == jti))
        return self.db.execute(stmt).scalar_one()

    def delete_expired_tokens(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)

        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount