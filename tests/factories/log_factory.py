import factory
from datetime import timedelta, datetime, timezone

from app.db.models import HabitLog
from tests.factories.base import BaseFactory
from tests.factories.habit_factory import HabitFactory


class HabitLogFactory(BaseFactory):
    class Meta:
        model = HabitLog

    date = factory.Sequence(
        lambda n: datetime.now(timezone.utc).date() - timedelta(days=n)
    )

    habit = factory.SubFactory(HabitFactory)

    note = None
