from __future__ import annotations

from context import DBContext
from db.settings import DBSettings
from manager import Manager

def get_base_declarative_model():
    db_setting = DBSettings()
    db_context = DBContext(db_setting)
    Manager.set_db_context(db_context)
