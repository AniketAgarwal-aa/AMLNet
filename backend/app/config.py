import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
ARTIFACT_DIR = BASE_DIR / 'artifacts'
DB_PATH = DATA_DIR / 'amlnet.db'
SEED = 42
APP_ENV = os.getenv('APP_ENV', 'development').lower()
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DB_PATH}')
# Neon commonly supplies postgres://; SQLAlchemy 2 uses the psycopg driver URL.
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
CORS_ORIGINS = [x.strip().rstrip('/') for x in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',') if x.strip()]
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '')
for path in (DATA_DIR, ARTIFACT_DIR): path.mkdir(parents=True, exist_ok=True)
