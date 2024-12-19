import os

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}".format(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        name=DB_NAME,
    )
)
