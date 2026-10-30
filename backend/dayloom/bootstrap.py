from dayloom.config import Settings
from dayloom.db import Base, build_engine


def main():
    engine = build_engine(Settings().database_url)
    Base.metadata.create_all(engine)
    engine.dispose()


if __name__ == "__main__":
    main()
