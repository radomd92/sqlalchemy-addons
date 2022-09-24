from __future__ import annotations

import logging
from collections import OrderedDict

from jsonformatter import JsonFormatter

RECORD_CUSTOM_FORMAT = OrderedDict(
    [
        ("name", "name"),
        ("level", "levelname"),
        ("filepath", "pathname"),
        ("module", "module"),
        ("linenumber", "lineno"),
        ("function", "funcName"),
        ("message", "message"),
    ],
)

logger = logging.getLogger("sqlalchemy_django_orm_like")
# noinspection PyTypeChecker
formatter = JsonFormatter(
    RECORD_CUSTOM_FORMAT, ensure_ascii=False, mix_extra=True, mix_extra_position="mix"
)

json_handler = logging.StreamHandler()
json_handler.setFormatter(formatter)

logger.addHandler(json_handler)
logger.setLevel(logging.INFO)
