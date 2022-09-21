from __future__ import annotations

from sqlalchemy.orm import declarative_base

from context import DBContext
from db.settings import DBSettings
from db.settings import DriverEnum
from manager import Manager

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)


test_db_context = DBContext(test_settings)
Manager.set_db_context(test_db_context)
base_model = declarative_base(cls=Manager)
