from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def init_db() -> None:
    global engine, SessionLocal
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=settings.debug,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from app.models.orm import Base as _  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Automatically ensure SQLite tables have newly added columns
    if settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                cursor = conn.connection.cursor()
                cursor.execute("PRAGMA table_info(detections)")
                cols = {r[1] for r in cursor.fetchall()}
                if cols:
                    if "image_url" not in cols:
                        cursor.execute("ALTER TABLE detections ADD COLUMN image_url VARCHAR(512)")
                    if "mask_url" not in cols:
                        cursor.execute("ALTER TABLE detections ADD COLUMN mask_url VARCHAR(512)")
                    if "sadh_height_m" not in cols:
                        cursor.execute("ALTER TABLE detections ADD COLUMN sadh_height_m FLOAT")
                    if "physics_confidence" not in cols:
                        cursor.execute("ALTER TABLE detections ADD COLUMN physics_confidence FLOAT")
                    conn.connection.commit()
        except Exception:
            pass


def get_session() -> Session:
    if SessionLocal is None:
        init_db()
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    db = get_session()
    try:
        yield db
    finally:
        db.close()

