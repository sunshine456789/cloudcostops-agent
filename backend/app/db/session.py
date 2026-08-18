from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# ============================================================
# Path
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_PATH = RUNTIME_DIR / "cloudcostops.db"


# ============================================================
# Database URL
# ============================================================

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


# ============================================================
# SQLAlchemy Engine
# ============================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    pool_pre_ping=True,
)


# ============================================================
# Session Factory
# ============================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ============================================================
# FastAPI Dependency
# ============================================================

def get_db():
    db: Session = SessionLocal()

    try:
        yield db
    finally:
        db.close()