from typing import Dict
from collections import OrderedDict

from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.util import AliasedClass


def get_model_from_rel(relation_name: str):
    """
    Given a name of column that contains a relationship field (ForeignKeyRel),
    Make an introspection ang get the model that hold the field.

    Example: tag_tuple.tupl_id will return the model TagTuple
    :param relation_name:
    :return:
    """
    import common.database.models as models
    
    table_name = relation_name.split(".")[0]
    
    found = [model
             for model in list(models.Base._decl_class_registry.values())
             if getattr(model, "__tablename__", None) == table_name
             ]
    
    if found:
        return found.pop()


def get_aliased_model_attrs(aliased_model: AliasedClass, only_fk=False, only_pk=False):
    """
    get attrs from aliased model as inspect does
    :param aliased_model:
    :return:
    """
    
    original_attrs = inspect(aliased_model._aliased_insp.class_).attrs
    aliased_model_attrs = [column for column in original_attrs]
    
    if only_fk:
        return [attr for attr in aliased_model_attrs if attr.foreign_keys]
    
    if only_pk:
        return [attr for attr in aliased_model_attrs if attr.primary_key]
        
    return aliased_model_attrs


def get_model_attrs(model) -> Dict:
    """
    get all attrs from a model sorted as follow: (Simple_column, Foreign, MTM)
    :param model:
    :return: Dict
    """
    
    inspection = inspect(model)
    current_all_fields = set(getattr(inspection, 'attrs', None) or get_aliased_model_attrs(model))
    many_to_many_rels = set(filter(lambda rel: getattr(rel, 'secondary', None) is not None, current_all_fields))
    
    fk_attrs = set(filter(
        lambda rel: getattr(rel, 'secondary', None) is None and isinstance(rel, RelationshipProperty)
                    or getattr(rel, 'foreign_keys', None),
        current_all_fields))
    
    # update current_available_field to remove many_to_many_rel field from it
    simple_attrs = current_all_fields.difference(fk_attrs).difference(many_to_many_rels)
    
    return OrderedDict({
        'simple_attrs': list(simple_attrs),
        'fk_attrs': list(fk_attrs),
        'many_to_many_rel': list(many_to_many_rels)
    })