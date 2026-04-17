import logging
from sqlalchemy import select, exists, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import TokenBlacklist

logger = logging.getLogger("app.blackist")


class TokenBlacklistRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, jti: str, expires_at: datetime):
        obj = TokenBlacklist(jti=jti, expires_at=expires_at)
        self.db.add(obj)
        try:
            self.db.flush()
            logger.info(
                "Token added to blacklist jti=%s, expires_at=%s",
                jti,
                expires_at,
            )
            return obj
        except IntegrityError:
            self.db.rollback()
            logger.debug("Token already blacklisted jti=%s", jti)
            return None

    def is_blacklisted(self, jti: str) -> bool:
        if not jti:
            return False

        stmt = select(exists().where(TokenBlacklist.jti == jti))
        result = bool(self.db.execute(stmt).scalar())

        logger.debug(
            "Check blacklist jti=%s, blacklisted=%s",
            jti,
            result,
        )

        return result

    def delete_expired_tokens(self, now: datetime) -> int:
        stmt = delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)

        result = self.db.execute(stmt)
        self.db.flush()
        deleted = result.rowcount or 0

        if deleted:
            logger.info("Deleted expired blacklist tokens count=%s", deleted)
        else:
            logger.debug("No expired blacklist tokens to delete")

        return deleted
