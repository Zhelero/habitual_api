import pytest
from datetime import timedelta, date

from app.core.exceptions import HabitAlreadyMarkedError
from app.services.dashboard_service import DashboardService
from app.services.habit_service import HabitService
from app.repositories.habit_repository import HabitRepository
from tests.factories.habit_factory import HabitFactory
from tests.factories.log_factory import HabitLogFactory
from tests.factories.user_factory import UserFactory
from tests.utils.helpers import random_habit_name


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def other_user():
    return UserFactory()


@pytest.fixture
def habits(db):
    return HabitService(HabitRepository(db))


@pytest.fixture
def dashboard(db):
    return DashboardService(HabitRepository(db))


class TestDashboardEmpty:
    def test_empty_returns_zeros(self, user, dashboard):
        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 0
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0

    def test_keys_present(self, user, dashboard):
        stats = dashboard.get_dashboard_stats(user.id)

        assert set(stats.keys()) == {"total_habits", "completed_today", "best_streak"}

    def test_deleted_habit_not_in_stats(self, user, dashboard, db):
        habit = HabitFactory(user=user)

        HabitLogFactory(habit=habit, date=date.today())

        db.delete(habit)
        db.commit()

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 0
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0


class TestTotalHabits:
    def test_count_habits(self, user, dashboard):
        HabitFactory.create_batch(3, user=user)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 3
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0

    def test_does_not_count_other_user_habits(self, user, other_user, dashboard):
        HabitFactory.create_batch(2, user=user)

        HabitFactory(user=other_user)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 2


class TestCompletedToday:
    def test_count_habits(self, user, dashboard):
        HabitFactory.create_batch(3, user=user)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["total_habits"] == 3
        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0

    def test_completed_today_multiple(self, user, dashboard):
        habits = HabitFactory.create_batch(3, user=user)

        HabitLogFactory(habit=habits[0], date=date.today())
        HabitLogFactory(habit=habits[1], date=date.today())

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 2
        assert stats["best_streak"] == 1
        assert stats["total_habits"] == 3

    def test_completed_today_none(self, user, dashboard):
        HabitFactory(user=user)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0
        assert stats["total_habits"] == 1

    def test_completed_today_duplicate_mark(self, user, habits, dashboard):
        habit = HabitFactory(user=user)

        habits.mark_done(user.id, habit.id)

        with pytest.raises(HabitAlreadyMarkedError):
            habits.mark_done(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 1

    def test_mark_done_after_duplicate_still_works(self, user, habits):
        habit = HabitFactory(user=user)

        habits.mark_done(user.id, habit.id)

        with pytest.raises(HabitAlreadyMarkedError):
            habits.mark_done(user.id, habit.id)

        new_habit = HabitFactory(user=user)

        assert new_habit.id is not None
        assert new_habit.id != habit.id

    def test_mark_done_midnight_boundary(
        self, user, habits, dashboard, freeze_time, base_time
    ):
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

    def test_yesterday_completion_not_counted(
        self, user, dashboard, habits, freeze_time, base_time
    ):
        habit = HabitFactory(user=user)

        with freeze_time(base_time - timedelta(days=1)):
            habits.mark_done(user.id, habit.id)

        with freeze_time(base_time):
            stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 1


class TestBestStreak:
    def test_best_streak_single_habit(
        self, user, dashboard, habits, freeze_time, base_time
    ):
        habit = HabitFactory(user=user)

        with freeze_time(base_time - timedelta(days=2)):
            habits.mark_done(user.id, habit.id)

        with freeze_time(base_time - timedelta(days=1)):
            habits.mark_done(user.id, habit.id)

        with freeze_time(base_time):
            habits.mark_done(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["best_streak"] == 3

    def test_best_streak_across_habits(
        self, user, dashboard, habits, freeze_time, base_time
    ):
        h1 = HabitFactory(user=user)
        h2 = HabitFactory(user=user)

        # h1: 3 days streak
        for i in range(3):
            with freeze_time(base_time - timedelta(days=i)):
                habits.mark_done(user.id, h1.id)

        # h2: 5 days streak
        for i in range(5):
            with freeze_time(base_time - timedelta(days=i)):
                habits.mark_done(user.id, h2.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["best_streak"] == 5

    def test_best_streak_with_gap(
        self, user, dashboard, habits, freeze_time, base_time
    ):
        habit = HabitFactory(user=user)

        with freeze_time(base_time - timedelta(days=3)):
            habits.mark_done(user.id, habit.id)
        with freeze_time(base_time - timedelta(days=1)):
            habits.mark_done(user.id, habit.id)
        with freeze_time(base_time):
            habits.mark_done(user.id, habit.id)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["best_streak"] == 2

    def test_best_streak_no_logs(self, user, dashboard):
        HabitFactory(user=user)

        stats = dashboard.get_dashboard_stats(user.id)

        assert stats["completed_today"] == 0
        assert stats["best_streak"] == 0
