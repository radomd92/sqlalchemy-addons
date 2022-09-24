from __future__ import annotations

import re
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from sqlalchemy.exc import InvalidRequestError

from sqlalchemy_wrapper.db.operators import And
from sqlalchemy_wrapper.db.operators import Or
from sqlalchemy_wrapper.db.query import BaseQueryBuilder
from tests.models import User


@pytest.mark.usefixtures("test_context")
class TestBaseQueryBuilder:
    def test_make_filter_with_join_success_args(self, test_context):
        """
        Test one join
        """
        query = BaseQueryBuilder(
            User, And(addresses__address__contains="@"), test_context.session
        ).make_filter()
        assert len(re.findall("JOIN", str(query))) <= 1

    def test_make_filter_with_join_success_complex_args(self, test_context):
        """
        Test one join
        """
        query = BaseQueryBuilder(
            User,
            And(
                Or(last_name="test", first_name__contains="tester"),
                addresses__address__contains="@",
            ),
            test_context.session,
        ).make_filter()
        assert len(re.findall("JOIN", str(query))) <= 1
        assert len(re.findall("OR", str(query)))

    def test_make_filter_with_join_fail_fake_field(self, test_context):
        """
        Test one join - fail with a remote field that not exists
        """
        with pytest.raises(AttributeError):
            BaseQueryBuilder(
                User, And(addresses__fake_field="@"), test_context.session
            ).make_filter()

    def test_make_filter_with_join_success_empty_args(self, test_context):
        """
        Test empty arguments return all result
        """
        query_builder = BaseQueryBuilder(User, And(), test_context.session)
        query = query_builder.make_filter()
        assert str(query).endswith("FROM user_account")

    @patch("sqlalchemy_wrapper.db.query.BaseQueryBuilder._run_search")
    def test_run_search_success(self, run_search, test_context):
        query_builder = BaseQueryBuilder(
            User, And(Or(last_name="hello", first_name="owner")), test_context.session
        )
        query_builder.run_search(query_builder.complex_filter_clause)
        expected_calls = [
            run_search({"last_name": "hello", "first_name": "owner"}),
            run_search({}),
        ]
        run_search.has_calls(expected_calls)

    def test__run_search_success(self, test_context):
        query_builder = BaseQueryBuilder(
            User, And(Or(last_name="hello", first_name="owner")), test_context.session
        )
        result = query_builder._run_search(
            {"first_name": "an example", "last_name": "hello world"}
        )
        assert 2 == len(result)

        assert User == result[0].get("first_name").get("model")
        assert "__eq__" == result[0].get("first_name").get("operator_name")

        assert User == result[1].get("last_name").get("model")
        assert "__eq__" == result[1].get("last_name").get("operator_name")

    @patch("sqlalchemy_wrapper.db.query.BaseQueryBuilder.dive")
    def test__run_search_fail(self, dive: MagicMock, test_context):
        dive.side_effect = InvalidRequestError
        query_builder = BaseQueryBuilder(User, And(), test_context.session)

        with pytest.raises(InvalidRequestError):
            query_builder._run_search(
                {"addresses__address": "an example", "last_name": "hello world"}
            )

    def test_updated_base_query(self):
        pass

    def test_build_final_filter_expression(self):
        pass

    def test_dive(self):
        pass
