import factory
from datetime import date, timedelta

from app.db.models import HabitLog
from tests.factories.base import BaseFactory
from tests.factories.habit_factory import HabitFactory


class HabitLogFactory(BaseFactory):
    class Meta:
        model = HabitLog

    date = factory.Sequence(lambda n: date.today() - timedelta(days=n))

    habit = factory.SubFactory(HabitFactory)
