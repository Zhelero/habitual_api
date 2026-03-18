from datetime import date, timedelta
from typing import Any
from sqlalchemy.exc import IntegrityError

from app.repositories.habit_repository import HabitRepository
from app.services.helpers import calculate_best_streak
from app.core.exceptions import (
    HabitAlreadyMarkedError,
    HabitAlreadyExistsError,
    HabitNotMarkedError,
    NotFoundError,
)

class HabitService:
    def __init__(self, repo: HabitRepository):
        self.repo = repo

    # Create habit

    def create_habit(self, name: str, description: str | None):
        try:
            return self.repo.create_habit(name, description)
        except IntegrityError as e:
            print(e)
            raise


    # Update habit

    def update_habit(self, habit_id: int, data: dict[str, Any]):
        self._get_habit_or_raise(habit_id)

        allowed_fields = {"name", "description"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return self.repo.get_habit_by_id(habit_id)

        try:
            updated = self.repo.update_habit(habit_id, update_data)
        except IntegrityError:
            raise HabitAlreadyExistsError()

        return updated


    # Get all habits

    def get_habits(self):
        return self.repo.get_all_habits()

    def get_habits_paginated(self, limit: int, offset: int):
        habits = self.repo.get_habits_paginated(limit, offset)
        total = self.repo.count_habits()

        return {
            "items": habits,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


    # Delete habit

    def delete_habit(self, habit_id: int):
        self._get_habit_or_raise(habit_id)
        return self.repo.delete_habit(habit_id)


    # Mark done

    def mark_done(self, habit_id: int):
        today = date.today()

        self._get_habit_or_raise(habit_id)

        try:
            return self.repo.add_log(habit_id, today)
        except IntegrityError:
            raise HabitAlreadyMarkedError()


    # Undo mark done

    def undo_done(self, habit_id: int):
        today = date.today()

        self._get_habit_or_raise(habit_id)

        deleted = self.repo.delete_log(habit_id, today)
        if not deleted:
            raise HabitNotMarkedError()

        return True


    # Stats

    def get_stats(self, habit_id: int):

        self._get_habit_or_raise(habit_id)

        logs = self.repo.get_logs_by_habit(habit_id)
        log_dates = {log.date for log in logs}

        today = date.today()

        # Current streak
        streak = 0
        current_day = today

        while current_day in log_dates:
            streak += 1
            current_day -= timedelta(days=1)

        # Best streak
        best_streak = calculate_best_streak(log_dates)

        count_7 = self.repo.count_logs_between(
            habit_id,
            today - timedelta(days=6),
            today
        )

        count_30 = self.repo.count_logs_between(
            habit_id,
            today - timedelta(days=29),
            today
        )

        completion_last_7_days = round((count_7 / 7) * 100, 2)
        completion_last_30_days = round((count_30 / 30) * 100, 2)

        last_7_days = [
            {
                "date": today - timedelta(days=i),
                "done": (today - timedelta(days=i)) in log_dates,
            }
            for i in range(6, -1, -1)
        ]

        return {
            "current_streak": streak,
            "best_streak": best_streak,
            "completion_last_7_days": completion_last_7_days,
            "completion_last_30_days": completion_last_30_days,
            "last_7_days": last_7_days,
        }


    def get_heatmap(self, habit_id: int):

        self._get_habit_or_raise(habit_id)

        return self.repo.get_heatmap(habit_id)


    # Helper

    def _get_habit_or_raise(self, habit_id: int):
        habit = self.repo.get_habit_by_id(habit_id)

        if not habit:
            raise NotFoundError("Habit not found")

        return habit

