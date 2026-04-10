import pytest
from datetime import timedelta

from app.core.exceptions import HabitAlreadyMarkedError
from app.services.dashboard_service import DashboardService
from app.services.habit_service import HabitService
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository
from tests.utils.helpers import random_habit_name, random_email


@pytest.fixture
def user(db):
    repo = UserRepository(db)
    from app.core.security import hash_password
    return repo.create_user(random_email(), hash_password("123456"))

@pytest.fixture
def dashboard(db):
    return DashboardService(HabitRepository(db))

@pytest.fixture
def habits(db):
    return HabitService(HabitRepository(db))


class TestDashboardEmpty:
    def test_empty_returns_zeros(self, user, dashboard):
        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 0
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0

    def test_keys_present(self, user, dashboard):
        stats = dashboard.get_dashboard_stats(user.id)

        assert set(stats.keys()) == {"total_habits", "completed_today", "best_streak"}

    def test_deleted_habit_not_in_stats(self, user, dashboard, habits):
        habit = habits.create_habit(user.id, random_habit_name(), None)
        habits.mark_done(user.id, habit.id)

        habits.delete_habit(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 0
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0


class TestTotalHabits:
    def test_count_habits(self, user, dashboard, habits):
        for _ in range(3):
            habits.create_habit(user.id, random_habit_name(), None)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 3
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0

    def test_does_not_count_other_user_habits(self, db, dashboard, habits):
        repo = UserRepository(db)
        from app.core.security import hash_password

        user1 = repo.create_user(random_email(), hash_password("123456"))
        user2 = repo.create_user(random_email(), hash_password("123456"))

        habits.create_habit(user1.id, random_habit_name(), None)
        habits.create_habit(user1.id, random_habit_name(), None)
        habits.create_habit(user2.id, random_habit_name(), None)

        stats = dashboard.get_dashboard_stats(user1.id)

        assert stats["total_habits"] == 2

class TestCompletedToday:
    def test_completed_today_multiple(self, user, dashboard, habits):
        h1 = habits.create_habit(user.id, random_habit_name(), None)
        h2 = habits.create_habit(user.id, random_habit_name(), None)
        habits.create_habit(user.id, random_habit_name(), None)

        habits.mark_done(user.id, h1.id)
        habits.mark_done(user.id, h2.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 2
        assert stats["best_streak"] == 1
        assert stats["total_habits"] == 3

    def test_completed_today_none(self, user, dashboard, habits):
        habits.create_habit(user.id, random_habit_name(), None)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0
        assert stats["total_habits"] == 1

    def test_completed_today_duplicate_mark(self, user, dashboard, habits):
        habit = habits.create_habit(user.id, random_habit_name(), None)

        habits.mark_done(user.id, habit.id)

        with pytest.raises(HabitAlreadyMarkedError):
            habits.mark_done(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)
        assert stats["completed_today"] == 1

    def test_mark_done_after_duplicate_still_works(self, user, habits):
        habit = habits.create_habit(user.id, random_habit_name(), None)

        habits.mark_done(user.id, habit.id)

        with pytest.raises(HabitAlreadyMarkedError):
            habits.mark_done(user.id, habit.id)

            new_habit = habits.create_habit(user.id, random_habit_name(), None)

            assert new_habit.id is not None
            assert new_habit.id != habit.id

    def test_mark_done_midnight_boundary(self, user, habits, dashboard, freeze_time, base_time):
        habit = habits.create_habit(user.id, random_habit_name(), None)
        midnight = base_time.replace(hour=23, minute=59)
        with freeze_time(midnight):
            habits.mark_done(user.id, habit.id)

        with freeze_time(midnight + timedelta(minutes=5)):
            habits.mark_done(user.id, habit.id)
            stats = dashboard.get_dashboard_stats(user.id)

            assert stats["total_habits"] == 1
            assert stats["completed_today"] == 1
            assert stats["best_streak"] == 2

    def test_yesterday_completion_not_counted(self, user, dashboard, habits, freeze_time, base_time):
        habit = habits.create_habit(user.id, random_habit_name(), None)

        with freeze_time(base_time - timedelta(days=1)):
            habits.mark_done(user.id, habit.id)

        with freeze_time(base_time):
            stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 1


class TestBestStreak:
    def test_best_streak_single_habits(self, user, dashboard, habits, freeze_time, base_time):
        habit = habits.create_habit(user.id, random_habit_name(), None)

        with freeze_time(base_time - timedelta(days=2)):
            habits.mark_done(user.id, habit.id)

        with freeze_time(base_time - timedelta(days=1)):
            habits.mark_done(user.id, habit.id)

        with freeze_time(base_time):
            habits.mark_done(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["best_streak"] == 3

    def test_best_streak_across_habits(self, db, dashboard, freeze_time, base_time):
        repo = UserRepository(db)
        from app.core.security import hash_password
        user = repo.create_user(random_email(), hash_password("123456"))
        habit_svc = HabitService(HabitRepository(db))

        h1 = habit_svc.create_habit(user.id, random_habit_name(), None)
        h2 = habit_svc.create_habit(user.id, random_habit_name(), None)

        # h1: 2 days streak
        for i in range(3):
            with freeze_time(base_time - timedelta(days=i)):
                habit_svc.mark_done(user.id, h1.id)

        # h2: 5 days streak
        for i in range(5):
            with freeze_time(base_time - timedelta(days=i)):
                habit_svc.mark_done(user.id, h2.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["best_streak"] == 5

    def test_best_streak_with_gap(self, user, dashboard, habits, freeze_time, base_time):
        habit = habits.create_habit(user.id, random_habit_name(), None)

        with freeze_time(base_time - timedelta(days=3)):
            habits.mark_done(user.id, habit.id)
        with freeze_time(base_time - timedelta(days=1)):
            habits.mark_done(user.id, habit.id)
        with freeze_time(base_time):
            habits.mark_done(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["best_streak"] == 2

    def test_best_streak_no_logs(self, user, dashboard, habits):
        habits.create_habit(user.id, random_habit_name(), None)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0