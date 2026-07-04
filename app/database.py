from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bolao.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """
    Lightweight migration helper: adds new columns to existing tables when missing.
    Runs at startup so deploys without recreating the DB still pick up new fields.
    """
    inspector = inspect(engine)
    if not inspector.has_table("matches"):
        return

    existing_cols = {col["name"] for col in inspector.get_columns("matches")}

    pending = []
    if "prediction_deadline" not in existing_cols:
        pending.append("ALTER TABLE matches ADD COLUMN prediction_deadline DATETIME")

    if "penalty_winner" not in existing_cols:
        pending.append("ALTER TABLE matches ADD COLUMN penalty_winner VARCHAR")

    if not pending:
        return

    with engine.begin() as conn:
        for stmt in pending:
            try:
                conn.execute(text(stmt))
                print(f"[migration] OK: {stmt}")
            except Exception as e:
                print(f"[migration] FAIL: {stmt} -> {e}")

