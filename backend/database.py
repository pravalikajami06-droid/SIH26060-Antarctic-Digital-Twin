import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load .env from the backend folder
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# PostgreSQL connection
engine = create_engine(DATABASE_URL)

print("Database engine created successfully")