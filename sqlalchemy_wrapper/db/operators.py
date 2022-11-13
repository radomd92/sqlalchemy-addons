from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy import or_


class BaseFilter:
    """
    Parent class for any wrapper clause.
    """

    def __init__(self, *operators_expression, **simple_expression):
        self.simple_expression = simple_expression
        self.wrapped_expression = list(operators_expression)

    def _set_operation(self, operator, other):
        """
        Look for the operator within BooleanOperator then operate it on the elements
        :param operator:
        :param other:
        :return:
        """
        right_ope = other
        left_ope = self

        return operator(left_ope, right_ope)

    def __and__(self, other):
        return self._set_operation(And, other)

    def __or__(self, other):
        return self._set_operation(Or, other)

    def __eq__(self, other):
        return (
            isinstance(self, BooleanOperator)
            and isinstance(other, BooleanOperator)
            and self.simple_expression == other.simple_operandes
            and all(
                [
                    any([e == e2 for e2 in self.wrapped_expression])
                    for e in other.bool_operandes
                ],
            )
            and all(
                [
                    any([e == e2 for e2 in other.bool_operandes])
                    for e in self.wrapped_expression
                ],
            )
            and len(self.wrapped_expression) == len(other.bool_operandes)
        )


class BooleanOperator(BaseFilter):
    """
    Base class to represent boolean operation like and, or
    """

    def __init__(self, operator, *operators_operands, **simple_expression):
        self.sqlalchemy_operator = operator
        super().__init__(*operators_operands, **simple_expression)

    def __eq__(self, other):
        return (
            super().__eq__(other)
            and self.sqlalchemy_operator == other.sqlalchemy_operator
        )


class And(BooleanOperator):
    """
    BooleanOperator that represent the and operation
    """

    def __init__(self, *tmp, **fields):
        super().__init__(and_, *tmp, **fields)


class Or(BooleanOperator):
    """
    BooleanOperator that represent the or operation
    """

    def __init__(self, *tmp, **fields):
        super().__init__(or_, *tmp, **fields)
