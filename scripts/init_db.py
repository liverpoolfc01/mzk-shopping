"""Initialize database: create all tables and verify connection"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    print('Creating all tables...')
    db.create_all()
    print('All tables created successfully!')

    # List all tables
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'\nTables in database ({len(tables)}):')
    for t in sorted(tables):
        print(f'  - {t}')
    print('\nDatabase initialization complete!')
