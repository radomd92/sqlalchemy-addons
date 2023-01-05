from __future__ import annotations

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from tests.base_model import base_model


class Item(base_model):
    __tablename__ = "item"
    item_id = Column(Integer, primary_key=True)
    content = Column(String)

    file = relationship("File")


class File(base_model):
    __tablename__ = "file"

    id = Column(Integer, primary_key=True)
    path = Column(String)
    item = Column(ForeignKey(Item.item_id))

    user = relationship("User")


class User(base_model):
    __tablename__ = "user_account"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    file = Column(ForeignKey(File.id))

    addresses = relationship(
        "Email",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    houses = relationship("HouseAssociation", back_populates="user")

    def __repr__(self):
        return f"User(id={self.id!r}, first_name={self.first_name!r}, last_name={self.last_name!r}, address={self.addresses})"


class Email(base_model):
    __tablename__ = "email_address"

    card_number = Column(Integer, primary_key=True)
    address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)

    user = relationship("User", back_populates="addresses")

    def __repr__(self):
        return f"Email(id={self.id!r}, address={self.email_address!r})"


class House(base_model):
    __tablename__ = "house"
    label = Column(String, primary_key=True)
    address = Column(String, nullable=True)

    users = relationship("HouseAssociation", back_populates="house")


class HouseAssociation(base_model):
    __tablename__ = "house_association"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_account.id"))
    house_id = Column(String, ForeignKey("house.label"))

    user = relationship("User", back_populates="houses")
    house = relationship("House", back_populates="users")
    extra = Column(String, nullable=True)
