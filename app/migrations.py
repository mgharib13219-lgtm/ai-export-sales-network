import os
from .db import init_db

def migrate():
    # MVP schema is created idempotently. Keep this hook as the single pre-deploy
    # migration entrypoint until Alembic is introduced.
    init_db()

if __name__ == "__main__":
    migrate()
