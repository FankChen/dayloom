import pytest
from dayloom.config import Settings
from dayloom.db import Base, build_engine
from dayloom.registry import discover_plugins


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", _env_file=None)


@pytest.fixture
def engine(settings):
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    discover_plugins()
    yield engine
    engine.dispose()
