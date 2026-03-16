from datetime import date, timedelta

from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, delete, func, case, update

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

    def get_habits_paginated(self, limit: int, offset: int) -> list[Habit]:
        return (
            self.db.query(Habit)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_habits(self):
        return self.db.query(Habit).count()

    def delete_habit(self, habit_id: int) -> bool:
        stmt = delete(Habit).where(Habit.id == habit_id)
        result = self.db.execute(stmt)
        self.db.commit()

        return result.rowcount > 0


    # LOGS

    def add_log(self, habit_id: int, log_date: date) -> HabitLog | None:
        log = HabitLog(habit_id=habit_id, date=log_date)

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    def get_logs_by_habit(self, habit_id: int) -> list[HabitLog]:
        stmt = (
            select(HabitLog)
            .where(HabitLog.habit_id == habit_id)
            .order_by(HabitLog.date.desc())
        )
        result = self.db.execute(stmt)

        return result.scalars().all()

    def get_all_logs(self) -> list[dict]:
        stmt = select(HabitLog.habit_id, HabitLog.date).order_by(HabitLog.date)

        return self.db.execute(stmt).scalars().all()

    def count_logs_between(self, habit_id: int, start: date, end: date):
        stmt = (
            select(func.count())
            .select_from(HabitLog)
            .where(
                HabitLog.habit_id == habit_id,
                HabitLog.date >= start,
                HabitLog.date <= end
            )
        )

        return self.db.execute(stmt).scalar()

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
                func.coalesce(
                    func.sum(
                        case(
                        (HabitLog.date >= week_ago, 1), else_=0)
                    ),
                    0
                ).label("last7"),
                (
                    func.coalesce(
                        func.sum(case(
                            (HabitLog.date >= week_ago, 1), else_=0)),
                            0
                    ) * 100.0 / 7
                ).label("completion_rate")
            )
            .where(HabitLog.habit_id == habit_id)
        )

        result = self.db.execute(stmt).one()

        total = result.total or 0
        last7 = result.last7 or 0

        completion_rate = round(result.completion_rate, 2)

        return {
            "total": total,
            "last7": last7,
            "completion_rate": completion_rate
        }

    def get_heatmap(self, habit_id: int):
        start = func.date(func.now(), "-29 days")
        end = func.date(func.now())

        #recursive CTE
        dates = select(start.label("date")).cte(name="dates", recursive=True)

        dates_alias = aliased(dates)

        dates = dates.union_all(
            select(func.date(dates_alias.c.date, "+1 day"))
            .where(dates_alias.c.date < end)
        )

        stmt = (
            select(
                dates.c.date,
                (HabitLog.id.is_not(None)).label("done")
            )
            .select_from(dates)
            .outerjoin(
                HabitLog,
                (HabitLog.date == dates.c.date) &
                (HabitLog.habit_id == habit_id)
            )
            .order_by(dates.c.date)
        )

        result = self.db.execute(stmt)

        return [
            {
                "date": row.date,
                "done": bool(row.done),
            }
            for row in result
        ]

    def count_completed_today(self):
        stmt = (
            select(func.count())
            .select_from(HabitLog)
            .where(HabitLog.date == date.today()))

        return self.db.execute(stmt).scalar()