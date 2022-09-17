from __future__ import annotations

import pytest
from sqlalchemy.orm import Query

from db.operators import And
from db.operators import Or
from db.query import BaseQueryBuilder
from tests.models import User


@pytest.mark.usefixtures("test_context")
@pytest.mark.usefixtures("query_with_join")
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
    def test_get_operator_success(self, operator, expected, test_context):
        """
        test if a given operator at the end of a filter is supported by SQLAlchemy
        Eg: column1__exact=value -> operator is 'exact'
        """
        assert expected == BaseQueryBuilder.get_operator(operator)

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
