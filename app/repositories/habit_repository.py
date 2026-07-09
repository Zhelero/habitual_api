import logging
from datetime import date, timezone, datetime, timedelta

from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select
from sqlalchemy import select, delete, func, update, literal, cast, Date

from app.db.models import Habit, HabitLog
from app.core.enums import HabitFilter

logger = logging.getLogger("app.habits.repo")


class HabitRepository:
    def __init__(self, db: Session):
        self.db = db

    # Habits

    def create_habit(
        self, user_id: int, name: str, description: str | None, color: str | None = None
    ) -> Habit:
        habit = Habit(user_id=user_id, name=name, description=description, color=color)

        self.db.add(habit)
        self.db.flush()
        self.db.refresh(habit)

        logger.info(
            "Create habit user_id=%s habit_id=%s name=%s",
            user_id,
            habit.id,
            name,
        )

        return habit

    def update_habit(self, user_id: int, habit_id: int, data: dict) -> Habit | None:
        stmt = (
            update(Habit)
            .where(Habit.id == habit_id, Habit.user_id == user_id)
            .values(**data)
            .returning(Habit)
        )
        result = self.db.execute(stmt)
        updated = result.scalar_one_or_none()
        self.db.flush()
        if updated:
            self.db.refresh(updated)
            logger.info(
                "Update habit user_id=%s habit_id=%s fields=%s",
                user_id,
                habit_id,
                list(data.keys()),
            )
        else:
            logger.debug(
                "Update habit not found user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )

        return updated

    def get_all_habits(
        self, user_id: int, filter: HabitFilter = HabitFilter.ACTIVE
    ) -> list[Habit]:
        conditions = self._apply_habit_filter([Habit.user_id == user_id], filter)

        stmt = select(Habit).where(*conditions).order_by(Habit.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def get_habit_by_id(self, user_id: int, habit_id: int) -> Habit | None:
        stmt = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
        result = self.db.execute(stmt)

        return result.scalar_one_or_none()

    def get_habits_paginated(
        self,
        user_id: int,
        limit: int,
        offset: int,
        filter: HabitFilter = HabitFilter.ACTIVE,
    ) -> list[Habit]:
        conditions = self._apply_habit_filter([Habit.user_id == user_id], filter)

        stmt = select(Habit).where(*conditions).offset(offset).limit(limit)

        return self.db.execute(stmt).scalars().all()

    def count_habits(
        self, user_id: int, filter: HabitFilter = HabitFilter.ACTIVE
    ) -> int:
        conditions = self._apply_habit_filter([Habit.user_id == user_id], filter)

        stmt = select(func.count()).select_from(Habit).where(*conditions)
        return self.db.execute(stmt).scalar()

    def archive_habit(self, habit: Habit) -> None:
        habit.is_archived = True
        self.db.flush()

    def restore_habit(self, habit: Habit) -> None:
        habit.is_archived = False
        self.db.flush()

    # LOGS

    def add_log(
        self,
        user_id: int,
        habit_id: int,
        log_date: date,
        note: str | None = None,
    ) -> HabitLog | None:
        stmt = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
        habit = self.db.execute(stmt).scalar_one_or_none()

        if not habit:
            logger.debug(
                "Mark habit done not found user_id=%s habit_id=%s",
                user_id,
                habit_id,
            )
            return None

        existing_stmt = select(HabitLog).where(
            HabitLog.habit_id == habit_id, HabitLog.date == log_date
        )

        existing = self.db.execute(existing_stmt).scalar_one_or_none()
        if existing:
            logger.debug(
                "Mark habit done duplicate user_id=%s habit_id=%s date=%s",
                user_id,
                habit_id,
                log_date,
            )
            return None

        note = note.strip() or None if note else None
        log = HabitLog(habit_id=habit_id, date=log_date, note=note)
        self.db.add(log)
        self.db.flush()

        logger.info(
            "Mark habit done user_id=%s habit_id=%s date=%s",
            user_id,
            habit_id,
            log_date,
        )

        return log

    def get_logs_by_habit(self, user_id: int, habit_id: int) -> list[HabitLog]:
        stmt = (
            select(HabitLog)
            .where(HabitLog.habit_id == habit_id, self._user_habit_filter(user_id))
            .order_by(HabitLog.date.desc())
        )
        result = self.db.execute(stmt)

        return result.scalars().all()

    def get_all_logs(self, user_id: int) -> list[HabitLog]:
        stmt = (
            select(HabitLog)
            .where(self._user_habit_filter(user_id))
            .order_by(HabitLog.date)
        )

        return self.db.execute(stmt).scalars().all()

    def count_logs_between(self, user_id: int, habit_id: int, start: date, end: date):
        stmt = (
            select(func.count())
            .select_from(HabitLog)
            .where(
                HabitLog.habit_id == habit_id,
                self._user_habit_filter(user_id),
                HabitLog.date >= start,
                HabitLog.date <= end,
            )
        )

        return self.db.execute(stmt).scalar() or 0

    def delete_log(self, user_id: int, habit_id: int, log_date: date):
        stmt = delete(HabitLog).where(
            HabitLog.habit_id == habit_id,
            HabitLog.date == log_date,
            self._user_habit_filter(user_id, habit_id),
        )

        result = self.db.execute(stmt)
        self.db.flush()

        deleted = result.rowcount > 0

        if deleted:
            logger.info(
                "Undo habit done user_id=%s habit_id=%s date=%s",
                user_id,
                habit_id,
                log_date,
            )

        return deleted

    def get_heatmap(self, user_id: int, habit_id: int):
        habit = self.get_habit_by_id(user_id, habit_id)
        if not habit:
            return []

        today = date.today()
        start_date = today - timedelta(days=29)

        # recursive CTE
        dates = select(literal(start_date).label("date")).cte(
            name="dates", recursive=True
        )
        dates_alias = aliased(dates)

        dates = dates.union_all(
            select(
                cast(dates_alias.c.date + timedelta(days=1), Date),
            ).where(dates_alias.c.date < today)
        )

        stmt = (
            select(dates.c.date, (HabitLog.id.is_not(None)).label("done"))
            .select_from(dates)
            .outerjoin(
                HabitLog,
                (HabitLog.date == dates.c.date) & (HabitLog.habit_id == habit_id),
            )
            .order_by(dates.c.date)
        )

        result = self.db.execute(stmt)

        return [
            {
                "date": str(row.date),
                "done": bool(row.done),
            }
            for row in result
        ]

    def count_completed_today(self, user_id: int):
        today = datetime.now(timezone.utc).date()
        stmt = (
            select(func.count())
            .select_from(HabitLog)
            .where(HabitLog.date == today, self._user_habit_filter(user_id))
        )

        return self.db.execute(stmt).scalar()

    # HELPERS

    def _habit_subquery(self, user_id: int) -> Select:
        return select(Habit.id).where(Habit.user_id == user_id)

    def _user_habit_filter(self, user_id: int, habit_id: int | None = None):
        condition = HabitLog.habit_id.in_(self._habit_subquery(user_id))

        if habit_id is not None:
            condition = condition & (HabitLog.habit_id == habit_id)
        return condition

    def _apply_habit_filter(self, conditions: list, filter: HabitFilter) -> list:
        if filter == HabitFilter.ACTIVE:
            conditions.append(Habit.is_archived.is_(False))
        elif filter == HabitFilter.ARCHIVED:
            conditions.append(Habit.is_archived.is_(True))
        # ALL — no additional condition
        return conditions
