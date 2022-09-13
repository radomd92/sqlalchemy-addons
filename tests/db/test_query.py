from __future__ import annotations

import unittest
from unittest import TestCase

import pytest
from sqlalchemy.orm import Query

from db.operators import And
from db.operators import Or
from db.query import BaseQueryBuilder
from tests.models import User


@pytest.mark.usefixtures("test_context")
class TestBaseQueryBuilder:
    def test_base_query_builder_init(self, test_context):
        query_with_and = BaseQueryBuilder(
            User,
            And(first_name__contains="test"),
            session=test_context.session,
        )
        query_with_or = BaseQueryBuilder(
            User,
            Or(first_name__contains="test"),
            session=test_context.session,
        )
        assert isinstance(query_with_and.complex_filter_clause, And)
        assert isinstance(query_with_or.complex_filter_clause, Or)
        assert isinstance(query_with_and.base_query, Query)

    @pytest.mark.parametrize(
        "operator,expected",
        [],
    )
    def test_get_operator_success(self, test_context):
        """
        test if a given operator at the end of a filter is supported by SQLAlchemy
        Eg: column1__exact=value -> operator is 'exact'
        """
        operator_list = ["like", "in", "between", "contains", "ilike"]
        result = list(map(BaseQueryBuilder.get_operator, operator_list))
        assert True == all(result)

    def test_make_filter(self):
        self.fail()

    def test_build_expression(self):
        self.fail()

    def test_run_search(self):
        self.fail()

    def test__run_search(self):
        self.fail()

    def test_updated_base_query(self):
        self.fail()

    def test_build_final_filter_expression(self):
        self.fail()

    def test_dive(self):
        self.fail()
