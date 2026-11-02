from dayloom.config import Settings
from dayloom.db import build_engine
from dayloom.migrations import migrate


def main():
    engine = build_engine(Settings().database_url)
    migrate(engine)
    engine.dispose()


if __name__ == "__main__":
    main()
