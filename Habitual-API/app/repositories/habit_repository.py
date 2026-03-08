from datetime import date, timedelta
from typing import Any, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func, case, text, update, Row, RowMapping

from app.db.models import Habit, HabitLog

class HabitRepository:
    def __init__(self, db: Session):
        self.db = db

    # Habits

    def create_habit(self, name: str, description: str | None) -> Habit:
        habit = Habit(name=name, description=description)

        self.db.add(habit)
        self.db.commit()
        self.db.refresh(habit)

        return habit

    def update_habit(self, habit_id: int, data: dict) -> Habit | None:
        stmt = (
            update(Habit)
            .where(Habit.id == habit_id)
            .values(**data)
            .returning(Habit)
        )
        result = self.db.execute(stmt)
        self.db.commit()

        return result.scalar_one_or_none()

    def get_all_habits(self) -> list[Habit]:
        stmt = select(Habit).order_by(Habit.created_at.desc())
        result = self.db.execute(stmt)

        return result.scalars().all()

    def get_habit_by_id(self, habit_id: int) -> Habit | None:
        stmt = select(Habit).where(Habit.id == habit_id)
        result = self.db.execute(stmt)

        return result.scalar_one_or_none()

    def delete_habit(self, habit_id: int) -> bool:
        stmt = delete(Habit).where(Habit.id == habit_id)
        result = self.db.execute(stmt)
        self.db.commit()

        return result.rowcount > 0


    # LOGS

    def add_log(self, habit_id: int, log_date: date) -> HabitLog | None:

        existing = self.db.execute(
            select(HabitLog)
            .where(
                HabitLog.habit_id == habit_id,
                HabitLog.date == log_date
            )
        ).scalar_one_or_none()

        if existing:
            return existing

        log = HabitLog(habit_id=habit_id, date=log_date)

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    def get_logs_by_habit(self, habit_id: int) -> list[HabitLog]:
        stmt = (
            select(HabitLog).
            where(HabitLog.habit_id == habit_id)
            .order_by(HabitLog.date.desc())
        )
        result = self.db.execute(stmt)

        return result.scalars().all()


    def delete_log(self, habit_id: int, log_date: date):

        stmt = (
            delete(HabitLog)
            .where(
                HabitLog.habit_id == habit_id,
                HabitLog.date == log_date
            )
        )

        result = self.db.execute(stmt)
        self.db.commit()

        return result.rowcount > 0


    def get_stats(self, habit_id: int):
        today = date.today()
        week_ago = today - timedelta(days=6)
        stmt = (
            select(
                func.count().label("total"),
                func.sum(
                    case(
                        (HabitLog.date >= week_ago, 1),
                        else_=0
                    )
                ).label("last7"),
                (
                    func.sum(
                        case(
                            (HabitLog.date >= week_ago, 1),
                            else_=0
                        )
                    ) * 100.0 / 7
                ).label("completion_rate")
            )
            .where(HabitLog.habit_id == habit_id)
        )

        result = self.db.execute(stmt).one()

        total = result.total or 0
        last7 = result.last7 or 0

        completion_rate = round(result.completion_rate or 2, 2)

        return {
            "total": total,
            "last7": last7,
            "completion_rate": completion_rate
        }

    def get_heatmap(self, habit_id: int):

        query = text("""
            WITH RECURSIVE dates(date) AS (
                SELECT DATE('now', '-29 days')
                UNION ALL
                SELECT DATE(date, '+1 day')
                FROM dates
                WHERE date < DATE('now')
            )
            
            SELECT
                dates.date as date,
                CASE
                    WHEN habit_logs.id IS NULL THEN 0
                    ELSE 1
                END as done
            FROM dates
            LEFT JOIN habit_logs
                ON habit_logs.date = dates.date
                AND habit_logs.habit_id = :habit_id
            ORDER BY dates.date
        """)

        result = self.db.execute(query, {"habit_id": habit_id})

        return [
            {
                "date": row.date,
                "done": bool(row.done),
            }
            for row in result
        ]