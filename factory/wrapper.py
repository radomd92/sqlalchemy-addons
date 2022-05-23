import copy
import re
import warnings
from itertools import chain
from typing import Dict, Tuple

from sqlalchemy import Column, Table
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import RelationshipProperty, aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.operators import ColumnOperators

from common.database import dbService
from common.database.factory.boolean_operators import BooleanOperator, and__, BaseFilter
from common.database.factory.converters import BaseConverter
from common.exception import db
from common.exception.db.exceptions import ObjectCreationException
from common.utils.db import get_model_from_rel, get_aliased_model_attrs, get_model_attrs
from common.utils.logging import get_log

session = dbService.session
logger = get_log(__name__)


def get_permissive_clause(input_):
    """
    Pop out of the initial request of the user in order to fetch fields that are not stricts
    :param input_: dict of requested filter
    :return:
    """
    logger.warn(input_)
    return {k: v for k, v in input_.items() if re.match(r'%', str(v)) and isinstance(v, str)}


class BaseQueryBuilder(object):
    
    def __init__(self, base_model, bool_clause):
        self.discovered = []
        self.base_query = session.query(base_model)
        self.visited = []
        if not bool_clause:
            raise ValueError("Resolving path cannot be None")
        
        # self.path_list = argument
        
        if not isinstance(bool_clause, BooleanOperator):
            raise ValueError("Invalids arguments")
        
        self.boolean_filter_clause = bool_clause
        self.current = None
        self.base_model = base_model
    
    def get_operator(self, operator):
        """
        Given a filtering_path, return the intended operator
        :param field:
        :return:
        """
        
        ope_attr = list(filter(lambda e: hasattr(ColumnOperators, e.format(operator)), ['{}', '{}_', '__{}__']))
        if ope_attr:
            return ope_attr[0].format(operator)
    
    def make_filter(self):
        """
        Put all together (make in one shot the filter)
        :return: SQLalchemy Expression
        """
        expressions = self.build_final_filter_expression()
        logger.info(expressions)
        
        return self.base_query.filter(expressions)
    
    def build_expression(self, model, field, operator_name, value, ):
        """
        Build the expression for the current field_path that will be used in the filter() of baseQuery
        :param model:
        :param field:
        :param value:
        :return:
        """
        model = list(model)[-1] if isinstance(model, tuple) else model
        column = getattr(model, field)
        
        if not column:
            raise Exception('Invalid filter column')
        
        operator = self.get_operator(operator_name)
        
        if operator in ['in_', 'notin_', "between"]:
            if not isinstance(value, (list, set, tuple)):
                raise ValueError(f"Iterable object expected when using {operator} operator")
            
            if operator == "between" and len(value) != 2:
                raise ValueError("Between comparison need exactly two in the list.")
        if operator in ("like", "ilike"):
            filter_ = getattr(column, operator)(value, escape='\\')
        else:
            filter_ = getattr(column, operator)(value) if operator != "between" else getattr(column, operator)(*value)
        
        return filter_
    
    def run_search(self, operande):
        """
        For each element in the clause (including booleanOperators operandes  and simpleoperandes
        found the models related to it and make in order to reuse them while building base query
        :return:
        """
        for operator_operande in operande.bool_operandes:
            self.run_search(operator_operande)
        operande.simple_operandes = self._run_search(operande.simple_operandes)
    
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
                collected_rel_object, lookup_field = self.dive(self.base_model, filter_request)
                for rel_info in collected_rel_object:
                    self.updated_base_query(**rel_info)
                
                models = [obj.get("model") for obj in collected_rel_object]
                
                data.append({self.current: {
                    "model": models[-1] if models else self.base_model,
                    "operator_name": operator or "__eq__",
                    "field": lookup_field,
                    "value": value
                }})
            except InvalidRequestError as e:
                logger.error("An error occurred while trying to find field in model")
                logger.exception(e)
                raise e
        
        return data
    
    def updated_base_query(self, model, local_join_column=None, remote_join_column=None):
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
                        getattr(local_join_column.prop, "local_columns", None) or
                        getattr(local_join_column.prop, "columns", None)
                    )[0]
                
                self.base_query = self.base_query.join(model, local_join_column == remote_join_column)
            else:
                self.base_query = self.base_query.join(model)
        
        self.visited.append(model)
    
    def build_final_filter_expression(self):
        """
        Build expression which will be used in the filter clause.
        :return:
        """
        
        def _build_expression(operande):
            ope = operande.sqlalchemy_operator
            expression_list = []
            for expression_argument in operande.simple_operandes:
                for filter_, content in expression_argument.items():
                    expression_list.append(self.build_expression(**content))
            for arg in operande.bool_operandes:
                expression_list.append(_build_expression(arg))
            return ope(*expression_list)
        
        boolean_filter_clause = self.boolean_filter_clause
        self.run_search(boolean_filter_clause)
        final_expression = _build_expression(boolean_filter_clause)
        return final_expression
    
    def dive(self, model, path, result: list = None):
        """
        Given a path, dive in model which through we can reach the final column
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
            next_model = self._lookup_model_foreign_key(column)
        else:
            for relation_object in many_to_many_rels:
                if field == relation_object.key:
                    next_model, through_table = self._lookup_model_manytomany_rel(relation_object).values()
                    is_many_to_many = True
                    break
        
        if next_model is None or next_model == []:
            if path:  # If we didn't reached the last element of the path without any model, it's error
                raise InvalidRequestError(f"Unable to find {field} field in {model}")
            else:
                return result, field
        
        # When there's more than one foreign key in the model, we have to choose the correct one between them
        _, remote_fk_attrs, __ = get_model_attrs(next_model).values()
        remote_explicit_join_column = list(inspect(next_model).primary_key)[0]
        
        if remote_fk_attrs:
            valid_fk = list(
                filter(lambda fk: get_model_from_rel(fk.target.name) == model, remote_fk_attrs)
            )
            if valid_fk:
                remote_explicit_join_column = list(valid_fk[0].local_columns)[0] \
                if isinstance(valid_fk[0], RelationshipProperty) else valid_fk[0]
        
        local_explicit_join_column = list(
            filter(lambda fk: getattr(fk, 'name', None) or getattr(fk, 'key', None) == field,
                   fk_attrs + many_to_many_rels + simple_attrs)
        )[0]
        
        if next_model in self.discovered:
            aliased_model = aliased(next_model)
            local_explicit_join_column = getattr(model, local_explicit_join_column.key)
            remote_explicit_join_column = getattr(aliased_model, remote_explicit_join_column.key)
            next_model = aliased_model
        
        if is_many_to_many:
            result.extend([{'model': model, 'local_join_column': None, 'remote_join_column': None}
                           for model in [through_table, next_model]
                           ])
            self.discovered.extend([through_table, next_model])
        else:
            result.append({
                'model': next_model,
                'local_join_column': local_explicit_join_column,
                'remote_join_column': remote_explicit_join_column
            })
            self.discovered.append(next_model)
        
        if path:
            return self.dive(next_model, path, result)
        
        return result, field
    
    def _lookup_model_manytomany_rel(self, ref_key: Column) -> Dict[str, Table]:
        """
        Retrieve all remote model we found while diving through MTM relationship
        :param ref_key:
        :return: Dict
        """
        return {
            "target": get_model_from_rel(ref_key.target.name),
            "secondary": ref_key.secondary  # Association table are not derived from Base. So use them as they are
        }
    
    def _lookup_model_foreign_key(self, column: Column) -> Tuple[Table, InstrumentedAttribute] or None:
        """
        Retrieve remote model of a foreign key column
        :param column:
        :return: Models
        """
        
        if getattr(column, "foreign_keys", None):
            field = list(column.foreign_keys).pop()
            field_name = field.column.table.name
        else:
            try:
                field_name = column.prop.target.name
            except AttributeError as e:
                return
        
        return get_model_from_rel(field_name)


class ManagerMixin(object):
    
    @classmethod
    def get_simple_column(cls):
        """
        Simple mapper that return field of the model without relationship
        :return:
        """
        return [col.key for col in inspect(cls).mapper.column_attrs]
    
    def describe(self, include_rel=False, format_="json"):
        pass
    
    def as_json(self, include_relformat_="json"):
        """
        Convert primary field of the object to json, that can be send back to a request
        :return: dict
        """
        result = {}
        [result.update({col: getattr(self, col)}) for col in self.getClass().get_simple_column()]
        if include_relformat_:
            pass
        return result
    
    @classmethod
    def add(cls, **values):
        """
        An helper to create an object given some value
        :param values:
        :return: The instance of the cls
        """
        try:
            logger.debug(f"Adding object {str(cls)} to db")
            obj = cls(**values)
            dbService.add_object(obj)  # Id is not commit without dbService
            logger.debug(f'{cls} has been added to DB. Object is {str(obj)}')
            return obj
        except Exception as e:
            logger.debug("An error occured while creating or adding object into database", extra={
                "object": values
            })
            logger.exception(e)
            raise db.exceptions.ObjectCreationException
    
    @classmethod
    def all(cls):
        return dbService.session.query(cls).all()
    
    @classmethod
    def get(cls, filter_none=True, **conditions):
        """
        Return a single object from the db.
        /!\ Be aware. You'd better use this one to fetch data by only the primary key in order to be sure
        that the object is unique in database. Otherwise an error will be thrown back
        :param filter_none:
        :param conditions: dict with condition
        :return:
        """
        data = cls.filter(**conditions)
        if len(data) > 1:
            warnings.warn("The conditions provided has returned multiple result. Be careful of what you're doing")
        
        logger.debug(f'Retrieved : {list(map(str, data))}')
        return data
    
    @classmethod
    def get_one(cls, **conditions):
        """
        Return a single object from the db.
        /!\ Be aware. You'd better use this one to fetch data by only the primary key in order to be sure
        that the object is unique in database. Otherwise an error will be thrown back
        :param filter_none:
        :param conditions: dict with condition
        :return:
        """
        data = cls.filter(**conditions)
        if data:
            if len(data) > 1:
                raise ValueError("The conditions provided has returned multiple result. It's not allowed here")
            
            logger.debug(f'Retrieved : {data[0]}')
            return data[0]
    
    @classmethod
    def _filter(cls, bool_clause=None, **conditions):
        """
        Fire the filtering of query in db
        :param operator: the operator used for filtering
        :param conditions: Clause
        :return: sqlachemy query object
        """
        if bool_clause is None:
            bool_clause = and__(**conditions)
        else:
            if not isinstance(bool_clause, BaseFilter):
                raise ValueError("filter clause must bo of type BaseFilter")
            bool_clause = bool_clause.filter_form()
        
        logger.info(f"filter clause = \n{str(bool_clause)}")
        query_build = BaseQueryBuilder(cls, bool_clause)
        query = query_build.make_filter()
        logger.info(str(query))
        return query
    
    @classmethod
    def filter(cls, bool_clause=None, **conditions):
        """
        Dummy wrapper for filtering. For now use the default
        :param operator:
        :param conditions:
        :return:
        """
        if bool_clause is None:
            bool_clause = and__(**conditions)
        else:
            if not isinstance(bool_clause, BaseFilter):
                raise ValueError("filter clause must bo of type BaseFilter")
            bool_clause = bool_clause.filter_form()
        
        data = cls._filter(bool_clause).all()
        logger.debug(f'{len(data)} {str(cls)} retrieved from database.', extra={
            'data_retrieved': list(map(str, data))
        })
        return data
    
    @classmethod
    def custom_filter(cls, bool_clause=None, converter=None, **conditions):
        """
        Filter that accept any king of filter value that will be converted by converter
        :param bool_clause:
        :param converter:
        :param conditions:
        :return:
        """
        if not isinstance(converter, BaseConverter):
            raise ValueError("invalid converter")
        if bool_clause and not isinstance(bool_clause, BaseFilter):  # BooleanOperator):
            # raise ValueError("Only BooleanOperators are implemented for now in custom filter")
            raise ValueError("invalid Basefilter for bool_clause")
        if bool_clause is None:
            bool_clause = and__(**conditions)
        converter.convert_request(bool_clause)
        return cls.filter(bool_clause)
    
    def getClass(self):
        """
        Return the class of the calling model
        :return:
        """
        return self.__class__
    
    def delete(self):
        """
        Delete the current object from the databa
        :return: None
        """
        try:
            dbService.delete_object(self)
        except Exception as e:
            logger.error("An error occured while deleting ")
            logger.exception(e)
    
    def update(self, filter_none=True, **field_to_update, ):
        """
        Update current instance.
        :param filter_none: Remove None value from field_to_update if true
        :param field_to_update: all fields that you want update in target model
        :return:
        """
        if filter_none:
            logger.debug(f"Filtering None values in filter to get {self.__str__()} object")
            field_to_update = {k: v for k, v in field_to_update.items() if v is not None}
        
        for field, value in field_to_update.items():
            if not hasattr(self, field):
                logger.debug("The current object has not this fields")
                continue
            logger.debug(f'Setting attribute {field}:{value}')
            setattr(self, field, value)
        
        dbService.flush_session()
