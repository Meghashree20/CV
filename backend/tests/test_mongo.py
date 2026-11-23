"""MongoDB connection handling without a live server."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import get_settings
from app.db.mongo import MongoManager


def test_ping_without_client_is_unavailable():
    manager = MongoManager()

    assert asyncio.run(manager.ping()) is False


def test_ping_success():
    manager = MongoManager()
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    manager.client = client

    assert asyncio.run(manager.ping()) is True


def test_ping_failure_is_contained():
    manager = MongoManager()
    client = MagicMock()
    client.admin.command = AsyncMock(side_effect=ServerSelectionTimeoutError("timed out"))
    manager.client = client

    assert asyncio.run(manager.ping()) is False


def test_connect_failure_leaves_database_unset(monkeypatch):
    class FailingClient:
        def __init__(self, uri, **kwargs):
            assert uri.startswith("mongodb://")
            self.admin = MagicMock()
            self.admin.command = AsyncMock(side_effect=ServerSelectionTimeoutError("down"))

        def close(self):
            return None

    monkeypatch.setattr("app.db.mongo.AsyncIOMotorClient", FailingClient)
    manager = MongoManager()

    assert asyncio.run(manager.connect()) is False
    assert manager.database is None
    assert manager.client is not None


def test_connect_success_selects_configured_database(monkeypatch):
    class WorkingClient:
        def __init__(self, uri, **kwargs):
            self.uri = uri
            self.admin = MagicMock()
            self.admin.command = AsyncMock(return_value={"ok": 1})
            self.closed = False

        def close(self):
            self.closed = True

        def __getitem__(self, name):
            return {"name": name}

    monkeypatch.setattr("app.db.mongo.AsyncIOMotorClient", WorkingClient)
    manager = MongoManager()

    assert asyncio.run(manager.connect()) is True
    assert manager.database["name"] == get_settings().mongodb_db_name
    asyncio.run(manager.disconnect())
    assert manager.client is None
    assert manager.database is None
