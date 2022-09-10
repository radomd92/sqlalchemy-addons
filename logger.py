from __future__ import annotations

import logging
from collections import OrderedDict

from jsonformatter import JsonFormatter

RECORD_CUSTOM_FORMAT = OrderedDict([
    ('Name', 'name'),
    ('Levelno', 'levelno'),
    ('Levelname', 'levelname'),
    ('Pathname', 'pathname'),
    ('Module', 'module'),
    ('Lineno', 'lineno'),
    ('FuncName', 'funcName'),
    ('Message', 'message'),
])

logger = logging.getLogger('sqlalchemy_django_orm_like')
formatter = JsonFormatter(RECORD_CUSTOM_FORMAT)

json_handler = logging.StreamHandler()
json_handler.setFormatter(formatter)

logger.addHandler(json_handler)
logger.setLevel(logging.INFO)
