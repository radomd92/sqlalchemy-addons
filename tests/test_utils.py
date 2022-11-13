from __future__ import annotations

import pytest
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import BinaryExpression

from sqlalchemy_wrapper.db.query import BaseQueryBuilder
from tests.models import User
from sqlalchemy_wrapper.utils import get_operator


# noinspection PyTypeChecker
class TestUtils:
    def test_get_model_from_rel(self):
        pass

    @pytest.mark.parametrize(
        "operator,expected",
        [
            ("ge", "__ge__"),
            ("le", "__le__"),
            ("lt", "__lt__"),
            ("ne", "__ne__"),
            ("not_in", "not_in"),
            ("between", "between"),
            ("like", "like"),
            ("ilike", "ilike"),
            ("not_like", "not_like"),
            ("endswith", "endswith"),
            ("startswith", "startswith"),
            ("is_not", "is_not"),
            ("isnot_distinct_from", "isnot_distinct_from"),
            ("is", "is_"),
            ("in", "in_"),
        ],
    )
    def test_get_operator_success(self, operator, expected):
        """
        test if a given operator at the end of a filter is supported by SQLAlchemy
        Eg: column1__exact=value -> operator is 'exact'
        """
        assert expected == get_operator(operator)

    @pytest.mark.parametrize(
        "model,field,operator_name,value",
        [
            (User, "first_name", "eq", "a first_name"),
            (User, "last_name", "is", None),
            (User, "id", "between", [1, 2]),
        ],
    )
    def test_build_expression_success(self, model, field, operator_name, value):
        expression = BaseQueryBuilder.build_expression(
            model, field, operator_name, value
        )
        assert isinstance(expression, BinaryExpression)

    @pytest.mark.parametrize(
        "model,field,operator_name,value",
        [(User, "last_name", "is", Query), (User, "id", "between", [1, 2, 7])],
    )
    def test_build_expression_fail(self, model, field, operator_name, value):
        with pytest.raises((ValueError, TypeError, AttributeError)):
            BaseQueryBuilder.build_expression(model, field, operator_name, value)
