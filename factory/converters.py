import datetime
import re
from enum import Enum
from inspect import isclass

from common.database.factory.boolean_operators import BooleanOperator, BaseFilter
from common.database.factory.custom_types import ArService, BaseCustomType, SpecialCustomType
from flask_restx.reqparse import RequestParser, Argument


# ####################
#    Base classes    #
# ####################


class BaseRequestParser(RequestParser):
    """
    A RequestParser used to manage inner types hidden in argument type. ex a int contained in a str arg
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def endpoint_doc():
        """
        Get the doc of the Parser. This doc can be inserted in an endpoint docstring
        :return: str
        """
        return f""


class BaseConverter:
    """
    Base class to represent a Converter. The goal of a converter is to transform any form of input values for search into wrapper search values
    """

    def __init__(self, parser):
        self.parser = parser

    def convert_request(self, bool_clause):
        """
        Convert values in the bool_clause into wrapper friendly values
        :param bool_clause: BooleanOperator: the clause to convert
        :return: None
        """
        if not isinstance(bool_clause, BaseFilter):
            raise ValueError("Bad params")
        bool_clause.simple_operandes = self._convert_operande(**bool_clause.simple_operandes)
        for idx, bool_ope in enumerate(bool_clause.bool_operandes):
            bool_ope = bool_ope.filter_form()
            self.convert_request(bool_ope)
            bool_clause.bool_operandes[idx] = bool_ope

    def _convert_operande(self, **kwargs):
        """
        Convert operandes into wrapper friendly operandes
        :param kwargs: operandes to convert
        :return: dict: converted operandes
        """
        raise NotImplementedError

    @classmethod
    def extract_raw_values(cls, custom_value, operator=None):
        """
        Return the raw values contained in custom_value
        :param custom_value: a value that can contains operators
        :param operator: The operator
        :return: list(str) or str: The raw value without specifics operators
        """
        raise NotImplementedError

    @classmethod
    def extract_operator(cls, value):
        """
        Get the operator in value
        :param value: The value to parse
        :return: str
        """
        raise NotImplementedError

    @classmethod
    def check_type_is_managed(cls, type_):
        """
        Check if the type passed is managed by the converter. Used to avoid unexpected behaviours
        :param type_: The type to check
        :return: True or False
        """
        raise NotImplementedError

    @classmethod
    def check_value_type_compatibility(cls, value, type_):
        """
        Check if the value and its operator is managed by the converter this type. Used to avoid unexpected behaviours
        :param value: The value to check
        :param type_: The type to check
        :return: None or raise ValueError
        :raises: ValueError: If not compatible
        """
        raise NotImplementedError


# ##########################
#    NaturalSearchQuery    #
# ##########################

class NaturalSearchQueryParser(BaseRequestParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The converter used to transform custom filters from Arguments value to wrapper filters
        self.converter = NaturalSearchQueryConverter(self)
        self.extra_args = []

    @staticmethod
    def endpoint_doc():
        return f"All fields accept {'|'.join(['!', '<', '<=', '>', '>=', '~ (% is a wild card)'])}\n" \
               f"/!\ string field's ordering is made by alphabetically order (9 is not < than 123)\n" \
               f"Please contact administrators for any unwanted behaviours"

    def get_arg(self, name=None, dest_name=None, search_in_extra=False):
        """
        Get a named Argument attached to the Parser
        :param search_in_extra: bool if must search for the arg in extra_args only
        :param dest_name: the dest name of the arg to get
        :param name: The name of the Argument to get
        :return: Argument
        """
        for arg in self.args:
            if name is not None and arg.name == name \
                    or dest_name is not None and arg.dest == dest_name:
                return arg
        if search_in_extra:
            for arg in self.extra_args:
                if name is not None and arg.name == name \
                        or dest_name is not None and arg.dest == dest_name:
                    return arg

    def parse_args(self, *args, **kwargs):
        self.extra_args = []
        parsed = super().parse_args(*args, **kwargs)
        self.converter.case_sensitive = parsed.pop("case_sensitive")

        return parsed

    def add_argument(self, name, *args, **kwargs):
        inner_type = kwargs.pop("inner_type", None)
        if inner_type is not None:
            kwargs["type"] = lambda x: self.check_input_specific_even_with_operator(x, inner_type)

        parser = super().add_argument(name, *args, **kwargs)
        if kwargs.get("dest", None) is not None:
            arg = self.get_arg(dest_name=kwargs.get("dest"))
        else:
            arg = self.get_arg(name=name)
        if arg is None:
            raise Exception(f"Argument {name} not added to parser")
        if inner_type is not None:
            arg.inner_type = inner_type
        else:
            arg.inner_type = kwargs.get("type", str)

        return parser

    def add_custom_argument(self, *args, **kwargs):
        """
        Add custom args to be able to convert them. It concerns custom filters added manually
        :param args:
        :param kwargs:
        :return: self
        """
        inner_type = kwargs.pop("inner_type", None)
        arg = Argument(*args, **kwargs)

        if inner_type is not None:
            arg.inner_type = inner_type
        else:
            arg.inner_type = kwargs.get("type", str)

        self.extra_args.append(arg)
        return self

    def check_input_specific_even_with_operator(self, input_, expected_type):
        """
        Check the format of the value without the operators
        :param expected_type: The type which the value must conform
        :param input_: The value to check (ope + value)
        :return: the value passed in input_ param if correct
        """
        if isinstance(input_, str):

            self.converter.check_type_is_managed(expected_type)

            self.converter.check_value_type_compatibility(input_, expected_type)

            operandes = self.converter.extract_raw_values(input_, type_=expected_type)
            if isinstance(operandes, str):
                operandes = [operandes]

            for operande in operandes:

                try:
                    if expected_type == datetime.datetime:
                        datetime.datetime.strptime(operande, "%d-%m-%Y").date()
                    elif issubclass(expected_type, Enum):
                        expected_type(operande.upper())
                    elif issubclass(expected_type, BaseCustomType):
                        expected_type(operande)
                    else:
                        expected_type(operande)

                except ValueError as e:
                    if isclass(expected_type) and issubclass(expected_type, Enum):
                        e = type(e)(f"{str(e)}. Valid values are {str(expected_type.valueList())}")

                    raise e
        return input_


class NaturalSearchQueryConverter(BaseConverter):
    """
    A BaseConverter used to manage user friendly values
    """

    MANAGED_TYPES = [int, float, Enum, str, datetime.datetime, ArService]
    MANAGED_OPE = ["__ne", "__gt", "__lt", "__ge", "__le", "__between", "__like", "__eq"]

    def __init__(self, parser):
        self.case_sensitive = True
        super().__init__(parser)

    def _convert_operande(self, **kwargs):
        """
        Convert operandes into wrapper friendly operandes
        :param kwargs: operandes to convert
        :return: dict: converted operandes
        """
        filters = {}
        for column, v in kwargs.items():

            operator = self.extract_operator(v)
            val = self.extract_raw_values(v)
            type_ = self.parser.get_arg(name=column, dest_name=column, search_in_extra=True).inner_type
            if type_ == datetime.datetime:
                if isinstance(val, list):
                    val = [datetime.datetime.strptime(val[0], "%d-%m-%Y").date(),
                           datetime.datetime.strptime(val[1], "%d-%m-%Y").date()]
                else:
                    val = datetime.datetime.strptime(val, "%d-%m-%Y").date()

                if operator in ("__le", "__gt"):
                    val = datetime.datetime.combine(val, datetime.time(hour=23, minute=59, second=59))
                elif operator in ("__ge", "__lt"):
                    val = datetime.datetime.combine(val, datetime.time(hour=00, minute=00, second=00))
                elif operator in ("__eq", "__between"):
                    operator = "__between"
                    if isinstance(val, list):
                        tmp1, tmp2 = val[0], val[1]
                    else:
                        tmp1, tmp2 = val, val
                    val = [datetime.datetime.combine(tmp1, datetime.time(hour=00, minute=00, second=00)),
                           datetime.datetime.combine(tmp2, datetime.time(hour=23, minute=59, second=59))]

            elif type_ == str:

                if operator == "__ne":
                    if not self.case_sensitive:
                        val = val.replace("%", "\%").replace("_", "\_").replace("[", "\[")
                        operator = '__notilike'
                    else:
                        operator = "__ne"

                elif operator in ("__gt", "__ge"):
                    if not self.case_sensitive:
                        val = val.upper()
                elif operator in ("__lt", "__le"):
                    if not self.case_sensitive:
                        val = val.lower()

                elif operator == "__between":
                    # val = [min,max]
                    pass

                elif operator == "__like":
                    """ __like__ """
                    if not self.case_sensitive:
                        operator = "__ilike"
                else:
                    """ default __eq__ """
                    if not self.case_sensitive:
                        val = val.replace("%", "\%").replace("_", "\_").replace("[", "\[")
                        operator = '__ilike'
                    else:
                        operator = "__eq"
            else:
                if isinstance(val, list):
                    tmp1 = type_(val[0])
                    tmp2 = type_(val[1])
                    if isclass(type_) and issubclass(type_, Enum):
                        tmp1 = tmp1.value
                        tmp2 = tmp2.value
                    val = [tmp1, tmp2]
                else:
                    val = type_(val)
                    if isclass(type_) and issubclass(type_, Enum):
                        val = val.value
            filters.update({f"{column}{operator}": val})

        return filters

    @classmethod
    def extract_raw_values(cls, custom_value, operator=None, type_=None):
        """
        Return the raw values contained in custom_value
        :param custom_value: a value that can contains operators
        :param operator: The operator
        :return: list(str) or str: The raw value without specifics operators
        """
        if operator is None:
            operator = cls.extract_operator(custom_value)

        v = str(custom_value).strip()

        if operator == "__ne":
            val = re.sub(r"^!", "", v).strip()
            return val

        elif operator == "__gt":
            val = re.sub(r"^>(?!=)", "", v).strip()
            return val

        elif operator == "__lt":
            val = re.sub(r"^<(?!=)", "", v).strip()
            return val

        elif operator == "__ge":
            val = re.sub(r"^>=", "", v).strip()
            return val

        elif operator == "__le":
            val = re.sub(r"^<=", "", v).strip()
            return val

        elif operator == "__between":
            min_, max_ = map(str.strip, v.split(",", 1))
            min_value = min_[1:].strip()
            max_value = max_[:-1].strip()
            return [min_value, max_value]

        elif operator == "__like":
            val = re.sub(r"^~", "", v).strip()
            # if type_ is not None and issubclass(type_, BaseCustomType):
            #     val = val.replace("%", "")
            return val

        else:
            """ default __eq """
            return v.strip()

    @classmethod
    def extract_operator(cls, value):
        """
        Get the operator in value
        :param value: The value to parse
        :return: str
        """
        value = value.strip()
        if re.match(r"^!", value):
            """__ne__"""
            return "__ne"

        elif re.match(r"^>(?!=)", value):
            """__gt__"""
            return "__gt"

        elif re.match(r"^<(?!=)", value):
            """__lt__"""
            return "__lt"

        elif re.match(r"^>=", value):
            """__ge__"""
            return "__ge"

        elif re.match(r"^<=", value):
            """__le__"""
            return "__le"

        elif re.match(r"^\[(.*),(.*)\]$", value):
            """__between__"""
            return "__between"

        elif re.match(r"^~", value):
            """ __like__ """
            return "__like"

        else:
            """ default __eq__ """
            return "__eq"

    @classmethod
    def check_type_is_managed(cls, type_):
        """
        Check if the type passed is managed by the converter. Used to avoid unexpected behaviours
        :param type_: The type to check
        :return: True or False
        """
        is_managed = False
        for managed_type in cls.MANAGED_TYPES:
            if type(managed_type) == type:
                if type_ == managed_type:
                    is_managed = True
                    break
            elif isclass(type_) and issubclass(type_, managed_type):
                is_managed = True
                break
        if not is_managed:
            raise ValueError(f"The type {type_} is not managed by the converter")
        return True

    @classmethod
    def check_value_type_compatibility(cls, value, type_):
        """
        Check if the value and its operator is managed by the converter this type. Used to avoid unexpected behaviours
        :param value: The value to check
        :param type_: The type to check
        :return: None or raise ValueError
        :raises: ValueError: If not compatible
        """

        cls.check_type_is_managed(type_)
        ope = cls.extract_operator(value)
        if type_ == datetime.datetime:
            if ope == "__like":
                raise ValueError(f"You cant make 'like'(~) request on dates")
            if ope == "__ne":
                raise ValueError(f"You cant make 'not equals'(!) request on dates")
        elif type_ in (float, int):
            if ope == "__like":
                raise ValueError(f"You cant make 'like'(~) request on numeric types")
        elif type_ is not None and issubclass(type_, SpecialCustomType):
            if ope != "__eq":
                raise ValueError("This is a special type that don't accept special operators")
        return True
