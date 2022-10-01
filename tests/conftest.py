from __future__ import annotations

import pytest

from sqlalchemy_wrapper.db.settings import DBSettings
from sqlalchemy_wrapper.db.settings import DriverEnum
from sqlalchemy_wrapper.manager import Manager
from tests.models import User

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)

# noinspection PyProtectedMember
User.__table__.create(User.db_context._engine)


@pytest.fixture(scope="class")
def test_context():
    yield Manager.db_context
