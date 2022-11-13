from __future__ import annotations

from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import declarative_base

from sqlalchemy_wrapper.context import DBContext
from sqlalchemy_wrapper.db.operators import And
from sqlalchemy_wrapper.db.operators import Or
from sqlalchemy_wrapper.db.query import BaseQueryBuilder
from sqlalchemy_wrapper.db.settings import DBSettings
from sqlalchemy_wrapper.logger import logger as logging


class Manager:
    db_context: DBContext

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        obj = cls(**values)
        cls.db_context.session.add(obj)  # ID is not commit without dbService
        logging.info(f"{cls} is being add to the DB", extra={"objects": [str(obj)]})
        return obj

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
