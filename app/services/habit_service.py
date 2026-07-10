import logging
from datetime import timedelta, timezone, datetime
from typing import Any
from sqlalchemy.exc import IntegrityError

from app.db.models import Habit, HabitLog
from app.repositories.habit_repository import HabitRepository
from app.services.helpers import calculate_best_streak
from app.core.enums import HabitFilter
from app.core.exceptions import (
    HabitAlreadyExistsError,
    HabitAlreadyMarkedError,
    HabitNotMarkedError,
    HabitArchivedError,
    NotFoundError,
    NameCannotBeEmptyError,
    HabitNameTooShortError,
    HabitNameTooLongError,
)

logger = logging.getLogger(__name__)


class HabitService:
    def __init__(self, repo: HabitRepository):
        self.repo = repo

    # Create habit

    def create_habit(
        self, user_id: int, name: str, description: str | None, color: str | None = None
    ) -> Habit:
        name = name.strip()

        if not name:
            logger.warning("Create habit failed: empty name user_id=%s", user_id)
            raise NameCannotBeEmptyError

        if len(name) < 2:
            logger.warning(
                "Create habit failed: name too short user_id=%s name=%s",
                user_id,
                name,
            )
            raise HabitNameTooShortError

        if len(name) > 100:
            logger.warning(
                "Create habit failed: name too long user_id=%s name=%s",
                user_id,
                name,
            )
            raise HabitNameTooLongError

        try:
            habit = self.repo.create_habit(user_id, name, description, color)
        except IntegrityError:
            logger.warning(
                "Create habit failed: already exists user_id=%s name=%s",
                user_id,
                name,
            )
            raise HabitAlreadyExistsError()

        logger.info("Habit created id=%s user_id=%s", habit.id, user_id)
        return habit

    # Update habit

    def update_habit(
        self, user_id: int, habit_id: int, data: dict[str, Any]
    ) -> Habit | None:
        self._get_habit_or_raise(user_id, habit_id)

        allowed_fields = {"name", "description", "color"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return self.repo.get_habit_by_id(user_id, habit_id)

        try:
            updated = self.repo.update_habit(user_id, habit_id, update_data)
        except IntegrityError:
            logger.warning(
                "Update habit failed: duplicate name user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            raise HabitAlreadyExistsError()

        logger.info("Habit updated id=%s user_id=%s", habit_id, user_id)
        return updated

    # Archive habit

    def archive_habit(self, user_id: int, habit_id: int):
        habit = self._get_habit_or_raise(user_id, habit_id)
        self.repo.archive_habit(habit)

        logger.info("Habit archived habit_id=%s user_id=%s", habit_id, user_id)
        return None

    # Restore habit

    def restore_habit(self, user_id: int, habit_id: int):
        habit = self._get_habit_or_raise(user_id, habit_id)
        self.repo.restore_habit(habit)

        logger.info("Habit restored habit_id=%s user_id=%s", habit_id, user_id)
        return None

    # Get habit by id

    def get_habit(self, user_id: int, habit_id: int) -> Habit:
        return self._get_habit_or_raise(user_id, habit_id)

    # Get all habits

    def get_habits(
        self,
        user_id: int,
        limit: int,
        offset: int,
        filter: HabitFilter = HabitFilter.ACTIVE,
    ) -> dict[str, Any]:
        habits = self.repo.get_habits_paginated(user_id, limit, offset, filter)
        total = self.repo.count_habits(user_id, filter)

        return {
            "items": habits,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # Mark done

    def mark_done(
        self, user_id: int, habit_id: int, note: str | None = None
    ) -> HabitLog:
        today = datetime.now(timezone.utc).date()

        habit = self._get_habit_or_raise(user_id, habit_id)
        if habit.is_archived:
            logger.warning(
                "Mark done failed: habit archived user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            raise HabitArchivedError()

        if note is not None:
            note = note.strip() or None

        log = self.repo.add_log(user_id, habit_id, today, note)
        if log is None:
            logger.warning(
                "Mark done failed: already marked user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            raise HabitAlreadyMarkedError()

        logger.info(
            "Habit marked done user_id=%s habit_id=%s",
            user_id,
            habit_id,
        )
        return log

    # Undo mark done

    def undo_done(self, user_id: int, habit_id: int) -> bool:
        today = datetime.now(timezone.utc).date()

        habit = self._get_habit_or_raise(user_id, habit_id)
        if habit.is_archived:
            logger.warning(
                "Undo failed: habit archived user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            raise HabitArchivedError()

        deleted = self.repo.delete_log(user_id, habit_id, today)
        if not deleted:
            logger.warning(
                "Undo failed: not marked user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            raise HabitNotMarkedError()

        logger.info(
            "Habit undone user_id=%s habit_id=%s",
            user_id,
            habit_id,
        )
        return True

    # Stats

    def get_stats(self, user_id: int, habit_id: int) -> dict[str, Any]:

        self._get_habit_or_raise(user_id, habit_id)

        logs = self.repo.get_logs_by_habit(user_id, habit_id)
        log_dates = {log.date for log in logs}

        today = datetime.now(timezone.utc).date()

        # Current streak
        streak = 0
        current_day = today

        if current_day not in log_dates:
            current_day -= timedelta(days=1)

        while current_day in log_dates:
            streak += 1
            current_day -= timedelta(days=1)

        # Best streak
        best_streak = calculate_best_streak(log_dates)

        count_7 = self.repo.count_logs_between(
            user_id, habit_id, today - timedelta(days=6), today
        )

        count_30 = self.repo.count_logs_between(
            user_id, habit_id, today - timedelta(days=29), today
        )

        completion_last_7_days = (count_7 / 7) * 100 if count_7 else 0
        completion_last_30_days = (count_30 / 30) * 100 if count_30 else 0

        last_7_days = [
            {
                "date": today - timedelta(days=i),
                "done": (today - timedelta(days=i)) in log_dates,
            }
            for i in range(6, -1, -1)
        ]

        logger.debug(
            "Stats calculated user_id=%s habit_id=%s",
            user_id,
            habit_id,
        )

        return {
            "current_streak": streak,
            "best_streak": best_streak,
            "completion_last_7_days": completion_last_7_days,
            "completion_last_30_days": completion_last_30_days,
            "last_7_days": last_7_days,
        }

    def get_heatmap(self, user_id: int, habit_id: int) -> list[dict[str, Any]]:

        self._get_habit_or_raise(user_id, habit_id)

        logger.debug(
            "Heatmap requested user_id=%s habit_id=%s",
            user_id,
            habit_id,
        )

        return self.repo.get_heatmap(user_id, habit_id)

    # Helper

    def _get_habit_or_raise(self, user_id: int, habit_id: int) -> Habit:
        habit = self.repo.get_habit_by_id(user_id, habit_id)

        if not habit:
            logger.warning(
                "Habit not found user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            raise NotFoundError("Habit not found")

        return habit
