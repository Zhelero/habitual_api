import pytest
from datetime import timedelta, date

from app.core.exceptions import (
    HabitAlreadyMarkedError,
    NameCannotBeEmptyError,
    HabitAlreadyExistsError,
    HabitNameTooLongError,
    HabitNameTooShortError,
    NotFoundError,
    HabitNotMarkedError,
)
from app.repositories.habit_repository import HabitRepository
from app.services.habit_service import HabitService

from tests.factories.habit_factory import HabitFactory
from tests.factories.log_factory import HabitLogFactory
from tests.utils.helpers import random_habit_name
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def habit(db, user):
    habit = HabitFactory(user=user)
    db.commit()
    return habit


@pytest.fixture
def habit_service(db):
    return HabitService(HabitRepository(db))


class TestCreateHabit:
    def test_create_habit(self, user, habit_service):
        name = random_habit_name()
        description = "This is a test habit"

        habit = habit_service.create_habit(
            user.id,
            name,
            description,
        )

        assert habit is not None
        assert habit.user_id == user.id
        assert habit.name == name
        assert habit.description == description

    def test_create_habit_empty_name(self, user, habit_service):
        name = ""
        with pytest.raises(NameCannotBeEmptyError):
            habit_service.create_habit(user.id, name, "")

    def test_create_habit_short_name(self, user, habit_service):
        name = "a"
        with pytest.raises(HabitNameTooShortError):
            habit_service.create_habit(user.id, name, None)

    def test_create_habit_long_name(self, user, habit_service):
        name = "a" * 101
        with pytest.raises(HabitNameTooLongError):
            habit_service.create_habit(user.id, name, None)

    def test_create_habit_duplicate_name(self, user, habit_service):
        name = random_habit_name()

        HabitFactory(user=user, name=name)

        with pytest.raises(HabitAlreadyExistsError):
            habit_service.create_habit(user.id, name, None)

    def test_same_name_different_users_ok(self, habit_service, user, other_user):
        name = random_habit_name()

        HabitFactory(user=user, name=name)

        habit = habit_service.create_habit(other_user.id, name, None)

        assert habit.user_id == other_user.id
        assert habit.name == name


class TestGetHabit:
    def test_returns_habit(self, habit_service, user, habit):
        result = habit_service.get_habit(user.id, habit.id)

        assert result.id == habit.id

    def test_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.get_habit(other_user.id, habit.id)

    def test_missing_id_raises(self, habit_service, user):
        with pytest.raises(NotFoundError):
            habit_service.get_habit(user.id, 999999)


class TestGetHabits:
    def test_get_habit(self, user, habit_service):
        HabitFactory.create_batch(5, user=user)

        result = habit_service.get_habits(user.id, limit=2, offset=0)

        assert len(result["items"]) == 2
        assert result["total"] == 5
        assert result["limit"] == 2
        assert result["offset"] == 0

    def test_total_reflects_all_habit(self, habit_service, user):
        HabitFactory.create_batch(7, user=user)

        result = habit_service.get_habits(user.id, limit=3, offset=0)

        assert result["total"] == 7
        assert len(result["items"]) == 3

    def test_empty_for_new_user(self, habit_service, user):
        result = habit_service.get_habits(user.id, limit=10, offset=0)

        assert result["items"] == []
        assert result["total"] == 0


class TestUpdateHabit:
    def test_updates_name(self, habit_service, habit):
        updated = habit_service.update_habit(
            habit.user_id, habit.id, {"name": "New name"}
        )

        assert updated.name == "New name"

    def test_updates_description(self, habit_service, user, habit):
        updated = habit_service.update_habit(
            user.id, habit.id, {"description": "New description"}
        )

        assert updated.description == "New description"

    def test_ignores_unknown_fields(self, habit_service, user, habit):
        updated = habit_service.update_habit(
            user.id, habit.id, {"name": "Valid", "hacked": True}
        )

        assert updated.name == "Valid"

    def test_duplicate_name_raises(self, habit_service, user):
        HabitFactory(user=user, name="ABC")
        habit = HabitFactory(user=user, name="BCD")

        with pytest.raises(HabitAlreadyExistsError):
            habit_service.update_habit(user.id, habit.id, {"name": "ABC"})

    def test_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.update_habit(other_user.id, habit.id, {"name": "A"})

    def test_missing_habit_raises(self, habit_service, user):
        with pytest.raises(NotFoundError):
            habit_service.update_habit(user.id, 123, {"name": "A"})


class TestDeleteHabit:
    def test_deletes_habit(self, habit_service, habit):
        habit_service.delete_habit(habit.user_id, habit.id)

        with pytest.raises(NotFoundError):
            habit_service.get_habit(habit.user_id, habit.id)

    def test_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.delete_habit(other_user.id, habit.id)

    def test_missing_habit_raises(self, habit_service, user):
        with pytest.raises(NotFoundError):
            habit_service.delete_habit(user.id, 999999)


class TestMarkDone:
    def test_marks_done_creates_log(self, habit_service, habit):
        log = habit_service.mark_done(habit.user_id, habit.id)

        assert log is not None
        assert log.date == date.today()

    def test_mark_done_twice_raises(self, habit_service, habit):
        habit_service.mark_done(habit.user_id, habit.id)

        with pytest.raises(HabitAlreadyMarkedError):
            habit_service.mark_done(habit.user_id, habit.id)

    def test_mark_done_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.mark_done(other_user.id, habit.id)

    def test_mark_done_missing_habit_raises(self, habit_service, user):
        with pytest.raises(NotFoundError):
            habit_service.mark_done(user.id, 123)


class TestUndoDone:
    def test_undo_done(self, habit_service, habit):
        habit_service.mark_done(habit.user_id, habit.id)
        result = habit_service.undo_done(habit.user_id, habit.id)

        assert result is True

    def test_undo_without_mark_raises(self, habit_service, habit):
        with pytest.raises(HabitNotMarkedError):
            habit_service.undo_done(habit.user_id, habit.id)

    def test_undo_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.undo_done(other_user.id, habit.id)


class TestGetStats:
    def test_stats_empty(self, habit_service, user, habit):
        stats = habit_service.get_stats(user.id, habit.id)

        assert stats["current_streak"] == 0
        assert stats["best_streak"] == 0
        assert stats["completion_last_7_days"] == 0
        assert stats["completion_last_30_days"] == 0
        assert len(stats["last_7_days"]) == 7
        assert all(not d["done"] for d in stats["last_7_days"])

    def test_current_streak_one_day(self, habit_service, habit):
        HabitLogFactory(habit=habit, date=date.today())

        stats = habit_service.get_stats(habit.user_id, habit.id)

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1

    def test_current_streak_consecutive_days(self, habit_service, user, habit):
        now = date.today()
        for i in range(3):
            HabitLogFactory(
                habit=habit,
                date=now - timedelta(days=2 - i),
            )

        stats = habit_service.get_stats(user.id, habit.id)

        assert stats["current_streak"] == 3
        assert stats["best_streak"] == 3

    def test_streak_broken_by_gap(self, habit_service, habit):
        HabitLogFactory(
            habit=habit,
            date=date.today() - timedelta(days=3),
        )

        HabitLogFactory(
            habit=habit,
            date=date.today() - timedelta(days=2),
        )

        HabitLogFactory(
            habit=habit,
            date=date.today(),
        )

        stats = habit_service.get_stats(habit.user_id, habit.id)

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 2

    def test_completion_30_days(self, habit_service, habit):
        HabitLogFactory(
            habit=habit,
            date=date.today(),
        )

        stats = habit_service.get_stats(habit.user_id, habit.id)

        assert stats["completion_last_30_days"] == pytest.approx(1 / 30 * 100)

    def test_completion_excludes_out_of_window(self, habit_service, habit):
        HabitLogFactory(
            habit=habit,
            date=date.today() - timedelta(days=7),
        )

        HabitLogFactory(
            habit=habit,
            date=date.today() - timedelta(days=6),
        )

        stats = habit_service.get_stats(habit.user_id, habit.id)

        assert stats["completion_last_7_days"] == pytest.approx(1 / 7 * 100)

    def test_last_7_days_correct_dates(
        self, habit_service, user, habit, freeze_time, base_time
    ):
        with freeze_time(base_time):
            stats = habit_service.get_stats(user.id, habit.id)

        dates = [d["date"] for d in stats["last_7_days"]]
        expected = [(base_time - timedelta(days=i)).date() for i in range(6, -1, -1)]

        assert dates == expected

    def test_last_7_days_done_flag(
        self, habit_service, user, habit, freeze_time, base_time
    ):
        with freeze_time(base_time):
            habit_service.mark_done(user.id, habit.id)
            stats = habit_service.get_stats(user.id, habit.id)

        total_entry = stats["last_7_days"][-1]

        assert total_entry["date"] == base_time.date()
        assert total_entry["done"] is True

    def test_stats_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.get_stats(other_user.id, habit.id)

    def test_undo_resets_streak(self, habit_service, user, habit):
        habit_service.mark_done(user.id, habit.id)
        habit_service.undo_done(user.id, habit.id)

        stats = habit_service.get_stats(user.id, habit.id)

        assert stats["current_streak"] == 0
        assert stats["best_streak"] == 0
        assert stats["completion_last_7_days"] == 0


class TestGetHeatmap:
    def test_returns_30_entries(self, habit_service, habit):
        result = habit_service.get_heatmap(habit.user_id, habit.id)

        assert len(result) == 30

    def test_logged_day_is_done(self, habit_service, habit):
        today = date.today()
        HabitLogFactory(habit=habit, date=today)

        result = habit_service.get_heatmap(habit.user_id, habit.id)

        today_entry = next(r for r in result if r["date"] == today.isoformat())

        assert today_entry["done"] is True

    def test_empty_days_are_not_done(self, habit_service, habit):
        result = habit_service.get_heatmap(habit.user_id, habit.id)

        assert all(not r["done"] for r in result)

    def test_wrong_user_raises(self, habit_service, other_user, habit):
        with pytest.raises(NotFoundError):
            habit_service.get_heatmap(other_user.id, habit.id)
