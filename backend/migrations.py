"""
Database migrations for ERIK ERP.

This module ensures database schema is up-to-date on application startup.
Uses SQLAlchemy inspector to check column existence for database portability.
"""

import logging
from sqlalchemy import inspect, text, Column, String
from sqlalchemy.exc import OperationalError
from database import engine

logger = logging.getLogger(__name__)

def column_exists(table_name, column_name):
    """
    Check if a column exists in a table using SQLAlchemy inspector.
    Works across all database backends (SQLite, PostgreSQL, MySQL, etc.)
    """
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def run_migrations():
    """
    Run all database migrations in order.
    Each migration checks if changes are needed before executing.
    Safe to run multiple times (idempotent).
    """
    logger.info("Running database migrations...")
    
    with engine.connect() as conn:
        # Migration 001: Add phone column to users table
        try:
            if not column_exists('users', 'phone'):
                logger.info("Running migration 001: Adding phone column to users table")
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR"))
                conn.commit()
                logger.info("✓ Migration 001 completed: phone column added")
            else:
                logger.info("⊘ Migration 001 skipped: phone column already exists")
        except OperationalError as e:
            logger.error(f"✗ Migration 001 failed: {str(e)}")
            logger.warning("Continuing startup despite migration failure...")
        except Exception as e:
            logger.error(f"✗ Migration 001 failed with unexpected error: {str(e)}")
            logger.warning("Continuing startup despite migration failure...")
        
        # Add future migrations here following the same pattern:
        # if not column_exists('table_name', 'column_name'):
        #     conn.execute(text("ALTER TABLE ..."))
    
    logger.info("All migrations completed")

if __name__ == "__main__":
    run_migrations()
