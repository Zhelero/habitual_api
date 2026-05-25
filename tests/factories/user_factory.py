import factory

from app.core.security import hash_password
from app.db.models import User
from tests.factories.base import BaseFactory


class UserFactory(BaseFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password_hash = factory.LazyFunction(lambda: hash_password("123456"))
