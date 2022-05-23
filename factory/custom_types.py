from common.utils.protocol_utils import check_and_parse_service
from werkzeug.exceptions import BadRequest


class BaseCustomType:
    def __init__(self, v):
        self.value = v


class ClassicCustomType(BaseCustomType):
    """
    Base class for all custom type that can be managed as any other builtin types
    """
    def __init__(self, value):
        super().__init__(value)


class SpecialCustomType(BaseCustomType):
    """
    Base class for all custom type that can't be managed as other types. It can just be seen as a formatted raw type (str)
    For example field that can't use a specific converter syntax'
    """
    def __init__(self, value):
        super().__init__(value)


class ArService(SpecialCustomType):

    def __init__(self, value: str):
        value = value.strip().upper()

        if value not in ("UDP", "TCP"):
            try:
                proto, port, to_port = check_and_parse_service(value)
            except BadRequest as e:
                raise ValueError(e.description)
        super().__init__(value)
