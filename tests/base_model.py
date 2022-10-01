from __future__ import annotations
from sqlalchemy_wrapper.db.settings import DBSettings
from sqlalchemy_wrapper.db.settings import DriverEnum
from sqlalchemy_wrapper.manager import Manager

test_settings = DBSettings(
    driver=DriverEnum.SQLITE,
    is_test=True,
)

base_model = Manager.as_base_model(test_settings)
