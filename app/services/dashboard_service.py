from datetime import date

from app.repositories.habit_repository import HabitRepository
from app.services.helpers import calculate_best_streak

class DashboardService:
    def __init__(self, repo: HabitRepository):
        self.repo = repo

    def get_dashboard_stats(self, user_id: int) -> dict[str, int]:

        habits = self.repo.get_all_habits(user_id)
        logs = self.repo.get_all_logs(user_id)

        total_habits = len(habits)
        completed_today = self.repo.count_completed_today(user_id)

        logs_by_habit: dict[int, set[date]] = {}

        for log in logs:
            logs_by_habit.setdefault(log.habit_id, set()).add(log.date)

        best_streak = 0

        for habit in habits:
            log_dates = logs_by_habit.get(habit.id, set())

            streak = calculate_best_streak(log_dates)

            best_streak = max(best_streak, streak)

        return {
            "total_habits": total_habits,
            "completed_today": completed_today,
            "best_streak": best_streak,
        }