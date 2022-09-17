from __future__ import annotations

import pytest
from sqlalchemy.orm import declarative_base

from context import DBContext
from db.operators import And
from db.query import BaseQueryBuilder
from db.settings import DBSettings
from db.settings import DriverEnum
from manager import Manager
from tests.models import User

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)

test_db_context = DBContext(test_settings)
Manager.set_db_context(test_db_context)
base_model = declarative_base(cls=Manager)


@pytest.fixture(scope="class")
def test_context(request):
    request.cls.test_context = test_db_context


@pytest.fixture(scope="class")
def query_with_join(request):
    query_builder_instance = BaseQueryBuilder(
        User, And(addresses__email_adress__contains="@"), test_context.session
    )
    request.cls.query_with_join = query_builder_instance
