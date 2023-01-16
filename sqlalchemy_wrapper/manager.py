from __future__ import annotations

from typing import Dict, Type
from typing import List
from typing import Tuple
from typing import Union

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import declarative_base, DeclarativeMeta

from easy_sqla.context import DBContext
from easy_sqla.db.operators import And
from easy_sqla.db.operators import Or
from easy_sqla.db.query import BaseQueryBuilder
from easy_sqla.db.selector import CompositePK
from easy_sqla.db.settings import DBSettings
from easy_sqla.logger import logger as logging
from easy_sqla.utils import _lookup_model_foreign_key
from easy_sqla.utils import get_primary_key


class Manager:
    db_context: DBContext

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def pks(self):
        """
        We'll assume that there is just one primary key column inside a table.
        """
        pk_attrs = get_primary_key(self.__class__)
        return {v: getattr(self, v) for v in pk_attrs}

    @classmethod
    def set_db_context(cls, context: DBContext):
        cls.db_context = context

    @classmethod
    def get_simple_column(cls):
        """
        Simple mapper that return field of the model without relationship
        :return:
        """
        return [col.key for col in inspect(cls).mapper.column_attrs]

    @classmethod
    def as_base_model(cls, settings: DBSettings):
        cls.set_db_context(DBContext(settings))
        return declarative_base(cls=cls)

    def as_json(self, include_rel: bool):
        """
        Convert primary field of the object to json, that can be sent back to a request
        :return: dict
        """
        result = {}
        [
            result.update({col: getattr(self, col)})
            for col in self.get_class().get_simple_column()
        ]
        if include_rel:
            # TODO: Implement the method in the next release
            pass
        return result

    @classmethod
    def create(cls, **values):
        """
        A helper to create an object given some value
        :param values:
        :return: The instance of the cls
        """
        logging.info(
            f"Adding object {cls} to db",
            extra={
                "data": values,
            },
        )
        values = cls.get_foreign_model_creation_data(values)
        obj = cls(**values)
        logging.info(f"{cls} is being add to the DB", extra={"objects": [str(obj)]})
        cls.db_context.session.add(obj)

        if cls.db_context.settings.get("auto_commit"):
            cls.db_context.session.commit()

        logging.info(f"{obj} added with success")

        return obj

    @classmethod
    def get_foreign_model_creation_data(cls, data: dict):
        """
        Detect in a creation payload, which field are for the creation for a related model
        Ex:
            class Child(Base):
                first_name = ...

            class Parent(Base):
                name = ...
                birth = ...
                child = Column(INTEGER, ForeignKey(Child.id), ....)

            Parent.create(name=..., birth=..., child={'first_name': 'Jon Doe'})

        Should save object as it is if the field is a JSONField
        """

        for field_name, field_value in data.items():
            remote_field_model: Type[DeclarativeMeta] = _lookup_model_foreign_key(
                getattr(cls, field_name, None)
            )
            if remote_field_model:
                logging.info(
                    f"Remote field detected: {remote_field_model.__name__}. Creating a new {remote_field_model.__name__} object"
                )
                if isinstance(field_value, dict):
                    objekt = remote_field_model.create(**field_value)

                elif isinstance(field_value, CompositePK):
                    objekt = remote_field_model.get_by_pks(**field_value)

                elif isinstance(field_value, (str, int)):
                    objekt = remote_field_model.get_by_pks(int(field_value))

                if len(objekt.pks) > 1:
                    raise NotImplemented("Multiple primary key relation object creation not supported yet.")

                data.update({field_name: list(objekt.pks.values())[0]})

        return data

    @classmethod
    def create_multiple(cls, data_collections: Union[List[Dict], Tuple[Dict]]) -> None:
        """
        Add the same time, multiple instance of the current model
        :param data_collections:
        :return:
        """
        if data_collections:
            obj_collections = list(map(lambda data: cls(**data), data_collections))
            cls.db_context.session.bulk_save_objects(obj_collections)
        else:
            logging.info("No data to add")

    @classmethod
    def all(cls):
        return cls.db_context.session.query(cls).all()

    @classmethod
    def get_by_pks(cls, *args, **kwargs):
        """
        Used to get unique row by name:value or only by value
        """
        pks = get_primary_key(cls)
        undefined_pks = set(pks.keys()).difference(kwargs.keys())

        if len(pks) > 1:
            if undefined_pks:
                raise ValueError(f'While using this method, you should specify all pks to be sure at 100% to return only '
                                 f'one row. Not defined {list(undefined_pks)}')
        else:
            # update the kwargs to set the value of the pk field
            kwargs = dict(zip(pks.keys(), args))
        return cls.get_one(**kwargs)



    @classmethod
    def get_one(cls, **conditions):
        """
        Return a single object from the db.
        Be aware. You'd better use this one to fetch data by only the primary key in order to be sure
        that the object is unique in database. Otherwise, an error will be thrown back
        :param conditions: dict with condition
        :return:
        """
        data = cls.filter(**conditions)
        if data:
            if len(data) > 1:
                raise ValueError(
                    "The conditions provided has returned multiple result. It's not allowed",
                )

            logging.debug(f"Found : {data[0]}")
            return data[0]

    @classmethod
    def _filter(cls, bool_clause=None, **conditions):
        """
        Fire the filtering of query.py in db
        :param operator: the operator used for filtering
        :param conditions: Clause expression
        :return: SQLAlchemy query.py object
        """

        if not bool_clause or not isinstance(bool_clause, (Or, And)):
            bool_clause = And(**conditions)

        query_build = BaseQueryBuilder(cls, bool_clause, cls.db_context.session)
        query = query_build.make_filter()

        return query

    @classmethod
    def filter(cls, bool_clause=And, **conditions):
        """
        Dummy wrapper for filtering. For now use the default session of SQLAlchemy.
        :param bool_clause: operator to use by default when multiple kwargs are passed
        :param conditions:
        :return:
        """

        data = cls._filter(bool_clause, **conditions).all()
        logging.debug(
            f"{len(data)} {str(cls)} retrieved from database.",
            extra={
                "data_retrieved": list(map(str, data)),
            },
        )
        return data

    def get_class(self):
        """
        Return the class of the calling model
        :return:
        """
        return self.__class__

    def delete(self) -> None:
        """
        Delete the current object from the database
        :return: None
        """
        self.db_context.session.delete(self)

    def update(self, filter_none=True, **field_to_update):
        """
        Update current instance.
        :param filter_none: Remove None from field_to_update if true
        :param field_to_update: all fields that you want update in target model
        :return:
        """
        if filter_none:
            logging.debug(
                f"Filtering None values in filter to get {self.__str__()} object",
            )
            field_to_update = {
                k: v for k, v in field_to_update.items() if v is not None
            }

        for field, value in field_to_update.items():
            if not hasattr(self, field):
                logging.warning(
                    f"The current object has not field named {field}. Skipping..."
                )
                continue

            logging.debug(f"Setting attribute {field}:{value}")
            setattr(self, field, value)

        self.db_context.session.flush()
