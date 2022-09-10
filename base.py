from __future__ import annotations

from sqlalchemy.orm import declarative_base

from context import DBContext
from db.settings import DBSettings
from manager import Manager

db_setting = DBSettings()
context = DBContext(db_setting)
Manager.set_db_context(context)


base_model = declarative_base(cls=Manager)
