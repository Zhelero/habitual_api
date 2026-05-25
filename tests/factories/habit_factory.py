import factory

from app.db.models import Habit
from tests.factories.base import BaseFactory
from tests.factories.user_factory import UserFactory


class HabitFactory(BaseFactory):
    class Meta:
        model = Habit

    user = factory.SubFactory(UserFactory)

    name = factory.Sequence(lambda n: f"Habit {n}")

    description = None
