import pytest
from datetime import date, timedelta

from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password
from tests.utils.helpers import random_habit_name, random_email

# Fixtures


@pytest.fixture
def repo(db):
    return HabitRepository(db)


@pytest.fixture
def user(db):
    return UserRepository(db).create_user(random_email(), hash_password("123456"))


@pytest.fixture
def other_user(db):
    return UserRepository(db).create_user(random_email(), hash_password("123456"))


@pytest.fixture
def habit(db, repo, user):
    return repo.create_habit(user.id, random_habit_name(), None)


class TestCreateHabit:
    def test_returns_habit_with_id(self, user, repo):
        h = repo.create_habit(user.id, "Habit name", None)

        assert h.id is not None
        assert h.name == "Habit name"
        assert h.description is None
        assert h.user_id == user.id

    def test_with_description(self, user, repo):
        h = repo.create_habit(user.id, "Habit name", "It's a description")

        assert h.description == "It's a description"

    def test_duplicate_habit_name_same_user_raises(self, user, repo):
        from sqlalchemy.exc import IntegrityError

        repo.create_habit(user.id, "Habit name", "It's a description")

        with pytest.raises(IntegrityError):
            repo.create_habit(user.id, "Habit name", None)

    def test_same_name_different_users_ok(self, user, other_user, repo):
        h1 = repo.create_habit(user.id, "Habit name", None)
        h2 = repo.create_habit(other_user.id, "Habit name", "Description")

        assert h1.id != h2.id


class TestGetHabitById:
    def test_returns_habit(self, user, habit, repo):
        result = repo.get_habit_by_id(user.id, habit.id)

        assert result is not None
        assert result.id == habit.id

    def test_returns_none_for_wrong_user(self, other_user, habit, repo):
        result = repo.get_habit_by_id(other_user.id, habit.id)

        assert result is None

    def test_returns_none_for_missing_id(self, user, repo):
        result = repo.get_habit_by_id(user.id, 123)

        assert result is None


class TestGetAllHabits:
    def test_returns_all_habits(self, user, repo):
        for _ in range(5):
            repo.create_habit(user.id, random_habit_name(), None)

        result = repo.get_all_habits(user.id)

        assert len(result) == 5

    def test_does_not_return_other_user_habits(self, user, other_user, repo):
        repo.create_habit(user.id, random_habit_name(), None)
        repo.create_habit(other_user.id, random_habit_name(), None)
        repo.create_habit(other_user.id, random_habit_name(), None)

        result1 = repo.get_all_habits(user.id)

        assert len(result1) == 1

        result2 = repo.get_all_habits(other_user.id)

        assert len(result2) == 2

    def test_empty_for_new_user(self, user, repo):
        assert repo.get_all_habits(user.id) == []


class TestPagination:
    def test_limit(self, user, repo):
        for _ in range(5):
            repo.create_habit(user.id, random_habit_name(), None)

        result = repo.get_habits_paginated(user.id, limit=2, offset=0)

        assert len(result) == 2

    def test_offset(self, user, repo):
        for _ in range(5):
            repo.create_habit(user.id, random_habit_name(), None)

        page1 = repo.get_habits_paginated(user.id, limit=2, offset=0)
        page2 = repo.get_habits_paginated(user.id, limit=2, offset=2)

        ids1 = {h.id for h in page1}
        ids2 = {h.id for h in page2}
        assert ids1.isdisjoint(ids2)

    def test_pagination_stable_order(self, user, repo):
        for i in range(5):
            repo.create_habit(user.id, f"h{i}", None)

        page1 = repo.get_habits_paginated(user.id, limit=5, offset=0)
        page2 = repo.get_habits_paginated(user.id, limit=5, offset=0)

        assert [h.id for h in page1] == [h.id for h in page2]

    def test_offset_beyond_total_returns_empty(self, user, repo):
        repo.create_habit(user.id, random_habit_name(), None)

        result = repo.get_habits_paginated(user.id, limit=10, offset=100)

        assert result == []

    def test_count_habits(self, user, repo):
        for _ in range(5):
            repo.create_habit(user.id, random_habit_name(), None)

        assert repo.count_habits(user.id) == 5

    def test_count_habits_isolated(self, user, other_user, repo):
        repo.create_habit(user.id, random_habit_name(), None)
        repo.create_habit(other_user.id, random_habit_name(), None)
        repo.create_habit(other_user.id, random_habit_name(), None)

        assert repo.count_habits(user.id) == 1
        assert repo.count_habits(other_user.id) == 2


class TestUpdateHabit:
    def test_updates_name(self, user, habit, repo):
        updated = repo.update_habit(user.id, habit.id, {"name": "New Name"})

        assert updated is not None
        assert updated.name == "New Name"

    def test_updates_description(self, user, habit, repo):
        updated = repo.update_habit(
            user.id, habit.id, {"description": "New Description"}
        )

        assert updated.description == "New Description"

    def test_wrong_user_returns_none(self, other_user, habit, repo):
        result = repo.update_habit(other_user.id, habit.id, {"name": "Hack"})

        assert result is None

    def test_missing_habit_returns_none(self, user, repo):
        result = repo.update_habit(user.id, 123, {"name": "Hack"})

        assert result is None

    def test_update_to_duplicate_name_raises(self, user, repo):
        repo.create_habit(user.id, "A", None)
        h2 = repo.create_habit(user.id, "B", None)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            repo.update_habit(user.id, h2.id, {"name": "A"})

    def test_update_empty_dict(self, user, habit, repo):
        result = repo.update_habit(user.id, habit.id, {})

        assert result is not None


class TestDeleteHabit:
    def test_deletes_and_return_true(self, user, habit, repo):
        result = repo.delete_habit(user.id, habit.id)

        assert result is True
        assert repo.get_habit_by_id(user.id, habit.id) is None

    def test_wrong_user_returns_false(self, other_user, habit, repo):
        result = repo.delete_habit(other_user.id, habit.id)

        assert result is False

    def test_missing_habit_returns_false(self, user, repo):
        result = repo.delete_habit(user.id, 123)

        assert result is False

    def test_delete_cascades_to_logs(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today)

        repo.delete_habit(user.id, habit.id)

        habit = repo.get_habit_by_id(user.id, habit.id)
        assert habit is None

        logs = repo.get_all_logs(user.id)
        assert logs == []


class TestAddLog:
    def test_returns_log(self, user, habit, repo):
        today = date.today()
        log = repo.add_log(user.id, habit.id, today)

        assert log is not None
        assert log.habit_id == habit.id
        assert log.date == today

    def test_duplicate_date_returns_none(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today)

        result = repo.add_log(user.id, habit.id, today)

        assert result is None

    def test_wrong_user_returns_none(self, other_user, habit, repo):
        result = repo.add_log(other_user.id, habit.id, date.today())

        assert result is None

    def test_different_dates_allowed(self, user, habit, repo):
        today = date.today()
        yesterday = today - timedelta(days=1)

        log1 = repo.add_log(user.id, habit.id, today)
        log2 = repo.add_log(user.id, habit.id, yesterday)

        assert log1 is not None
        assert log2 is not None


class TestDeleteLog:
    def test_deletes_and_returns_true(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today)

        result = repo.delete_log(user.id, habit.id, today)

        assert result is True

        logs = repo.get_all_logs(user.id)
        assert logs == []

    def test_missing_log_returns_false(self, user, habit, repo):
        result = repo.delete_log(user.id, habit.id, date.today())

        assert result is False

    def test_wrong_user_returns_false(self, other_user, habit, repo):
        today = date.today()
        repo.add_log(habit.user_id, habit.id, today)

        result = repo.delete_log(other_user.id, habit.id, today)

        assert result is False


class TestGetLogs:
    def test_get_logs_by_habit_ordered_desc(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today - timedelta(days=2))
        repo.add_log(user.id, habit.id, today - timedelta(days=1))
        repo.add_log(user.id, habit.id, today)

        logs = repo.get_logs_by_habit(user.id, habit.id)

        assert logs[0].date == today
        assert logs[-1].date == today - timedelta(days=2)

    def test_get_logs_by_habit_isolates_user(self, user, other_user, habit, repo):
        h_other = repo.create_habit(other_user.id, random_habit_name(), None)
        repo.add_log(other_user.id, h_other.id, date.today())

        logs = repo.get_logs_by_habit(user.id, h_other.id)

        assert logs == []

    def test_get_all_logs_returns_only_own(self, user, other_user, habit, repo):
        h_other = repo.create_habit(other_user.id, random_habit_name(), None)
        today = date.today()

        repo.add_log(user.id, habit.id, today)
        repo.add_log(other_user.id, h_other.id, today)

        logs = repo.get_all_logs(user.id)

        assert all(log.habit_id == habit.id for log in logs)
        assert len(logs) == 1


class TestCountLogsBetween:
    def test_counts_within_range(self, user, habit, repo):
        today = date.today()
        for i in range(3):
            repo.add_log(user.id, habit.id, today - timedelta(days=i))

        count = repo.count_logs_between(
            user.id,
            habit.id,
            today - timedelta(days=6),
            today,
        )

        assert count == 3

    def test_start_and_end_inclusive(self, user, habit, repo):
        today = date.today()
        start = today - timedelta(days=6)

        repo.add_log(user.id, habit.id, start)
        repo.add_log(user.id, habit.id, today)

        count = repo.count_logs_between(user.id, habit.id, start, today)

        assert count == 2

    def test_excludes_out_of_range(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today - timedelta(days=8))

        count = repo.count_logs_between(
            user.id,
            habit.id,
            today - timedelta(days=6),
            today,
        )

        assert count == 0

    def test_returns_zero_no_logs(self, user, habit, repo):
        today = date.today()
        count = repo.count_logs_between(
            user.id,
            habit.id,
            today - timedelta(days=6),
            today,
        )

        assert count == 0

    def test_count_logs_between_isolated(self, user, other_user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today)

        count = repo.count_logs_between(
            other_user.id, habit.id, today - timedelta(days=10), today
        )

        assert count == 0


class TestGetHeatmap:
    def test_returns_30_days(self, user, habit, repo):
        result = repo.get_heatmap(user.id, habit.id)

        assert len(result) == 30

    def test_key_present(self, user, habit, repo):
        result = repo.get_heatmap(user.id, habit.id)

        assert "date" in result[0]
        assert "done" in result[0]

    def test_done_true_for_logged_day(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today)

        result = repo.get_heatmap(user.id, habit.id)
        today_entry = next(r for r in result if r["date"] == str(today))

        assert today_entry["done"] is True

    def test_done_false_for_empty_day(self, user, habit, repo):
        result = repo.get_heatmap(user.id, habit.id)

        assert all(r["done"] is False for r in result)

    def test_ordered_ascending(self, user, habit, repo):
        today = date.today()
        then = today - timedelta(days=29)
        result = repo.get_heatmap(user.id, habit.id)

        assert result[0]["date"] == str(then)
        assert result[-1]["date"] == str(today)

    def test_heatmap_wrong_user(self, other_user, habit, repo):
        result = repo.get_heatmap(other_user.id, habit.id)

        assert result == []


class TestCountCompletedToday:
    def test_counts_today(self, user, repo):
        h1 = repo.create_habit(user.id, random_habit_name(), None)
        h2 = repo.create_habit(user.id, random_habit_name(), None)

        repo.add_log(user.id, h1.id, date.today())
        repo.add_log(user.id, h2.id, date.today())

        assert repo.count_completed_today(user.id) == 2

    def test_does_not_count_yesterday(self, user, habit, repo):
        today = date.today()
        repo.add_log(user.id, habit.id, today - timedelta(days=1))

        assert repo.count_completed_today(user.id) == 0

    def test_isolated_from_other_user(self, user, other_user, habit, repo):
        h_other = repo.create_habit(other_user.id, random_habit_name(), None)
        repo.add_log(other_user.id, h_other.id, date.today())

        assert repo.count_completed_today(user.id) == 0
