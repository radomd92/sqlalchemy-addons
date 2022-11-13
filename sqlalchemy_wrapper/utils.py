from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Dict
from typing import Type

from sqlalchemy import Column
from sqlalchemy import inspect
from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.operators import ColumnOperators


def get_model_from_rel(relation_name: str):
    """
    Given a name of column that contains a relationship field (ForeignKeyRel),
    Make an introspection ang get the model that hold the field.

    :param relation_name:
    :return: List of model
    """

    from sqlalchemy_wrapper.manager import Manager

    all_models = Manager.__subclasses__()[0].__subclasses__()

    table_name = relation_name.split(".")[0]
    found = [
        model
        for model in all_models
        if getattr(model, "__tablename__", None) == table_name
    ]

    if found:
        return found.pop()

    return


def get_aliased_model_attrs(aliased_model: AliasedClass, only_fk=False, only_pk=False):
    """
    Get attrs from aliased model as inspect does
    :param only_pk: get only primary key from the aliased model
    :param only_fk: get only foreign key from the aliased model
    :param aliased_model: the model that has been aliased
    :return:
    """

    # noinspection PyProtectedMember
    original_attrs = inspect(aliased_model._aliased_insp.class_).attrs
    aliased_model_attrs = [column for column in original_attrs]

    if only_fk:
        return [attr for attr in aliased_model_attrs if attr.foreign_keys]

    if only_pk:
        return [attr for attr in aliased_model_attrs if attr.primary_key]

    return aliased_model_attrs


def get_model_attrs(model) -> Dict:
    """
    get all attrs from a model sorted as follows: (Simple_column, Foreign, MTM)
    :param model:
    :return: Dict
    """

    inspection = inspect(model)
    current_all_fields = set(
        getattr(inspection, "attrs", None) or get_aliased_model_attrs(model),
    )
    many_to_many_rels = set(
        filter(
            lambda rel: getattr(rel, "secondary", None) is not None,
            current_all_fields,
        ),
    )

    fk_attrs = set(
        filter(
            lambda rel: getattr(rel, "secondary", None) is None
            and isinstance(rel, RelationshipProperty)
            or getattr(rel, "foreign_keys", None),
            current_all_fields,
        ),
    )

    # update current_available_field to remove many_to_many_rel field from it
    simple_attrs = current_all_fields.difference(fk_attrs).difference(many_to_many_rels)

    return OrderedDict(
        {
            "simple_attrs": list(simple_attrs),
            "fk_attrs": list(fk_attrs),
            "many_to_many_rel": list(many_to_many_rels),
        },
    )


def _lookup_model_manytomany_rel(ref_key: Column) -> Dict[str, Table]:
    """
    Retrieve all remote model we found while diving through MTM relationship
    :param ref_key:
    :return: Dict
    """
    return {
        "target": get_model_from_rel(ref_key.target.name),
        "secondary": ref_key.secondary,  # Association table are not derived from Base. So use them as they are
    }


def _lookup_model_foreign_key(column: Column) -> Table | Type[DeclarativeMeta] | None:
    """
    Retrieve remote model of a foreign key column
    """

    if getattr(column, "foreign_keys", None):
        field = list(column.foreign_keys).pop()
        field_name = field.column.table.name
    else:
        try:
            field_name = column.prop.target.name
        except AttributeError:
            logging.debug(f"Column {column} has no remote field")
            return None

    return get_model_from_rel(field_name)


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
