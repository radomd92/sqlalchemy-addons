from __future__ import annotations

import pytest

from sqlalchemy_wrapper.db.settings import DBSettings
from sqlalchemy_wrapper.db.settings import DriverEnum
from sqlalchemy_wrapper.manager import Manager
from tests.base_model import base_model

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)

with open("." + test_settings.sqlite_db_path, "w") as f:
    pass

# noinspection PyProtectedMember
base_model.metadata.create_all(base_model.db_context._engine)


@pytest.fixture(scope="class")
def test_context():
    yield Manager.db_context
