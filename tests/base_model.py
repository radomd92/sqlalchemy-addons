from __future__ import annotations

from sqlalchemy.orm import declarative_base

from sqlalchemy_wrapper.context import DBContext
from sqlalchemy_wrapper.db.settings import DBSettings
from sqlalchemy_wrapper.db.settings import DriverEnum
from sqlalchemy_wrapper.manager import Manager

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)


test_db_context = DBContext(test_settings)
Manager.set_db_context(test_db_context)
base_model = declarative_base(cls=Manager)
