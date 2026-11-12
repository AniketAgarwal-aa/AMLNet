from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL

is_sqlite = DATABASE_URL.startswith('sqlite')
engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False} if is_sqlite else {},
    pool_pre_ping=True,
    pool_size=5 if not is_sqlite else 1,
    max_overflow=5 if not is_sqlite else 0,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
