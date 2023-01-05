from __future__ import annotations

from unittest import TestCase

from tests.models import File
from tests.models import Item
from tests.models import User


class TestManager(TestCase):
    def test_create_simple_object(self):
        create_payload = {"first_name": "soumaila", "last_name": "kouriba"}
        user = User.create(**create_payload)
        assert user.pk

    def test_create_nested_object(self):
        create_payload = {
            "first_name": "soumaila",
            "last_name": "kouriba",
            "file": {"path": "/c/mnt", "item": {"content": "a content"}},
        }

        user = User.create(**create_payload)
        assert File.all()
        assert Item.all()
        assert user.file
        assert File.get_one(id=user.file).pk == user.file
