from __future__ import annotations

import copy
import logging
from typing import Dict
from typing import Tuple
from typing import Union

from sqlalchemy import Column
from sqlalchemy import inspect
from sqlalchemy import Table
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import aliased
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm import Session
from sqlalchemy.sql.operators import ColumnOperators

from db.operators import And
from db.operators import Or
from utils import _lookup_model_foreign_key
from utils import _lookup_model_manytomany_rel
from utils import get_model_attrs
from utils import get_model_from_rel


class BaseQueryBuilder(object):
    def __init__(self, base_model, bool_clause: Union[And, Or], session: Session):
        if not bool_clause:
            raise ValueError("Resolving path cannot be None")

        self.current = None
        self.discovered = []
        self.visited = []
        self.base_model = base_model
        self.base_query = session.query(base_model)
        self.complex_filter_clause = bool_clause

    @staticmethod
    def get_operator(operator):
        """
        Given a filtering_path, return the intended operator
        :param operator:
        :return:
        """

        ope_attr = list(
            filter(
                lambda e: hasattr(ColumnOperators, e.format(operator)),
                ["{}", "{}_", "__{}__"],
            ),
        )
        if ope_attr:
            return ope_attr[0].format(operator)

    def make_filter(self):
        """
        Put all together (make in one shot the filter)
        :return: SQLAlchemy Expression
        """
        expressions = self.build_final_filter_expression()
        logging.info(expressions)

        return self.base_query.filter(expressions)

    def build_expression(self, model, field, operator_name, value):
        """
        Build the expression for the current field_path that will be used in the filter() of baseQuery
        :param operator_name:
        :param model:
        :param field:
        :param value:
        :return:
        """
        model = list(model)[-1] if isinstance(model, tuple) else model
        column = getattr(model, field)

        if not column:
            raise Exception("Invalid filter column")

        operator = self.get_operator(operator_name)

        if operator in ["in_", "notin_", "between"]:
            if not isinstance(value, (list, set, tuple)):
                raise ValueError(
                    f"Iterable object expected when using {operator} operator",
                )

            if operator == "between" and len(value) != 2:
                raise ValueError("Between comparison need exactly two in the list.")

        if operator in ("like", "ilike"):
            filter_ = getattr(column, operator)(value, escape="\\")
        else:
            filter_ = (
                getattr(column, operator)(value)
                if operator != "between"
                else getattr(column, operator)(*value)
            )

        return filter_

    def run_search(self, operand: Union[And, Or]):
        """
        Complex expression are which are wrapped into And or Or operator such as: And(column1__like=value, column2__...)
        :return:
        """
        for complex_expression in operand.wrapped_expression:
            self.run_search(complex_expression)

        operand.simple_expression = self._run_search(operand.simple_expression)

    def _run_search(self, args):
        """
        For each argument passed in the filter eg: column1__remote__column2__operator
        found the models related to it and make in order to reuse them while building base query
        :return:
        """
        data = []

        for filter_request, value in args.items():
            self.current = copy.deepcopy(filter_request)
            filter_request = filter_request.split("__")
            operator = self.get_operator(filter_request[-1])

            if operator:
                filter_request.pop(-1)
            try:
                collected_rel_object, lookup_field = self.dive(
                    self.base_model,
                    filter_request,
                )
                for rel_info in collected_rel_object:
                    self.updated_base_query(**rel_info)

                models = [obj.get("model") for obj in collected_rel_object]

                data.append(
                    {
                        self.current: {
                            "model": models[-1] if models else self.base_model,
                            "operator_name": operator or "__eq__",
                            "field": lookup_field,
                            "value": value,
                        },
                    },
                )
            except InvalidRequestError as e:
                logging.error("An error occurred while trying to find field in model")
                logging.exception(e)
                raise e

        return data

    def updated_base_query(
        self,
        model,
        local_join_column=None,
        remote_join_column=None,
    ):
        """
        After fetch concerned model, we build the base query which will be used to filter data
        :return:
        """
        if model not in self.visited:
            if local_join_column is not None and remote_join_column is not None:
                if isinstance(local_join_column, RelationshipProperty):
                    local_join_column = list(local_join_column.local_columns)[0]
                elif isinstance(local_join_column, InstrumentedAttribute):
                    local_join_column = list(
                        getattr(local_join_column.prop, "local_columns", None)
                        or getattr(local_join_column.prop, "columns", None),
                    )[0]

                self.base_query = self.base_query.join(
                    model,
                    local_join_column == remote_join_column,
                )
            else:
                self.base_query = self.base_query.join(model)

        self.visited.append(model)

    def build_final_filter_expression(self):
        """
        Build expression which will be used in the filter.
        :return:
        """

        def _build_expression(operand):
            expression_list = []

            for expression_argument in operand.simple_expression:
                for filter_, content in expression_argument.items():
                    expression_list.append(self.build_expression(**content))

            for arg in operand.wrapped_expression:
                expression_list.append(_build_expression(arg))

            return operand.sqlalchemy_operator(*expression_list)

        complex_filter_clause = self.complex_filter_clause
        self.run_search(complex_filter_clause)
        final_expression = _build_expression(complex_filter_clause)
        return final_expression

    def dive(self, model, path, result: list = None):
        """
        Given a path, dive in model which through we can reach the final column
        :param path:
        :param model: model where we start diving
        :param result: all resolved model
        :return: Tuple
        """
        next_model = None
        is_many_to_many = False
        through_table = None

        if not result:
            result = []

        simple_attrs, fk_attrs, many_to_many_rels = get_model_attrs(model).values()
        field = path.pop(0) if path else ""
        column = getattr(model, field)

        if not column:
            raise RuntimeError(f"No column named {field}")

        if field in list(map(lambda col: col.key, simple_attrs + fk_attrs)):
            next_model = _lookup_model_foreign_key(column)
        else:
            for relation_object in many_to_many_rels:
                if field == relation_object.key:
                    next_model, through_table = _lookup_model_manytomany_rel(
                        relation_object,
                    ).values()
                    is_many_to_many = True
                    break

        if next_model is None or next_model == []:
            if (
                path
            ):  # If we didn't reached the last element of the path without any model, it's an error
                raise InvalidRequestError(f"Unable to find {field} field in {model}")
            else:
                return result, field

        # When there's more than one foreign key in the model, we have to choose the correct one between them
        _, remote_fk_attrs, __ = get_model_attrs(next_model).values()
        remote_explicit_join_column = list(inspect(next_model).primary_key)[0]

        if remote_fk_attrs:
            valid_fk = list(
                filter(
                    lambda fk: get_model_from_rel(fk.target.name) == model,
                    remote_fk_attrs,
                ),
            )
            if valid_fk:
                remote_explicit_join_column = (
                    list(valid_fk[0].local_columns)[0]
                    if isinstance(valid_fk[0], RelationshipProperty)
                    else valid_fk[0]
                )

        local_explicit_join_column = list(
            filter(
                lambda fk: getattr(fk, "name", None)
                or getattr(fk, "key", None) == field,
                fk_attrs + many_to_many_rels + simple_attrs,
            ),
        )[0]

        if next_model in self.discovered:
            aliased_model = aliased(next_model)
            local_explicit_join_column = getattr(model, local_explicit_join_column.key)
            remote_explicit_join_column = getattr(
                aliased_model,
                remote_explicit_join_column.key,
            )
            next_model = aliased_model

        if is_many_to_many:
            result.extend(
                [
                    {
                        "model": model,
                        "local_join_column": None,
                        "remote_join_column": None,
                    }
                    for model in [through_table, next_model]
                ],
            )
            self.discovered.extend([through_table, next_model])
        else:
            result.append(
                {
                    "model": next_model,
                    "local_join_column": local_explicit_join_column,
                    "remote_join_column": remote_explicit_join_column,
                },
            )
            self.discovered.append(next_model)

        if path:
            return self.dive(next_model, path, result)

        return result, field
