from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseSettings
from pydantic import PyObject


class DriverEnum(str, Enum):
    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRES = "postgresql"


class DBSettings(BaseSettings):
    driver: DriverEnum
    host: str = None
    port: str = None
    name: str = None
    username: str = None
    password: str = None
    auto_commit: bool = True
    is_test: bool = False
    sqlite_db_path: str = "./db.sqlite3"
    error_handler: Optional[PyObject]

    class Config:
        env_prefix = "DB_"
        allow_mutation = False
