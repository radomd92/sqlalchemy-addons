from __future__ import annotations

import pytest

from db.settings import DBSettings
from db.settings import DriverEnum
from tests.base_model import test_db_context
from tests.models import User

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)

# noinspection PyProtectedMember
User.__table__.create(User.db_context._engine)


@pytest.fixture(scope="class")
def test_context():
    yield test_db_context
