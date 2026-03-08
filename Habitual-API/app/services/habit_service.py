from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError

from app.repositories.habit_repository import HabitRepository

class HabitService:
    def __init__(self, repo: HabitRepository):
        self.repo = repo

    # Create habit

    def create_habit(self, name: str, description: str | None):
        try:
            return self.repo.create_habit(name, description)
        except IntegrityError:
            raise ValueError("Habit with this name already exists")


    # Update habit

    def update_habit(self, habit_id: int, data: dict):
        self._get_habit_or_raise(habit_id)

        allowed_fields = {"name", "description"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return self.repo.get_habit_by_id(habit_id)

        try:
            self.repo.update_habit(habit_id, update_data)
        except IntegrityError:
            raise ValueError("Habit with this name already exists")

        return self.repo.get_habit_by_id(habit_id)


    # Get all habits

    def get_habits(self):
        return self.repo.get_all_habits()


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
            raise ValueError("Habit already marked as done today")


    # Undo mark done

    def undo_done(self, habit_id: int):
        today = date.today()

        self._get_habit_or_raise(habit_id)

        deleted = self.repo.delete_log(habit_id, today)
        if not deleted:
            raise ValueError("Habit was not marked as done today")

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
        best_streak = self._calculate_best_streak(log_dates)

        # Completion rate (last 30 days)
        completion_last_7_days = self._calculate_completion_percentage(log_dates, 7)
        completion_last_30_days = self._calculate_completion_percentage(log_dates, 30)

        # Last 7 days stats
        last_7_days = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            last_7_days.append({
                "date": day,
                "done": day in log_dates,
            })

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
            raise ValueError("Habit not found")

        return habit

    def _calculate_completion_percentage(self, log_dates: set[date], days: int):
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        count = sum(
            1
            for single_date in log_dates
            if start_date <= single_date <= today
        )

        return round((count / days) * 100, 2)

    def _calculate_best_streak(self, log_dates: set[date]) -> int:

        if not log_dates:
            return 0

        sorted_dates = sorted(log_dates)

        best = 1
        current = 1

        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] == sorted_dates[i-1] + timedelta(days=1):
                current += 1
                best = max(best, current)
            else:
                current = 1

        return best