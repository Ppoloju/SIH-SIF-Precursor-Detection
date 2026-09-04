"""Database clearing script.

Removes all data from the database while preserving the schema.
Use this to clear test data, demo data, or start fresh.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.models.db import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_database() -> None:
    """Clear all data from all tables while preserving schema."""
    
    # Get all table names
    with engine.begin() as conn:
        # Get table names for SQLite
        if engine.dialect.name == "sqlite":
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ))
        else:
            # For PostgreSQL
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ))
        
        tables = [row[0] for row in result]
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
    
    # Clear data from each table in correct order (respecting foreign keys)
    # Order matters: delete from child tables before parent tables
    table_order = [
        "feedback",           # Child of reports
        "reviews",           # Child of reports  
        "training_runs",     # Independent
        "analyses",          # Child of reports
        "reports",           # Parent
        "life_saving_rules", # Independent
    ]
    
    # Filter to only existing tables
    tables_to_clear = [t for t in table_order if t in tables]
    
    # Add any remaining tables not in our predefined order
    for table in tables:
        if table not in tables_to_clear:
            tables_to_clear.append(table)
    
    db = SessionLocal()
    try:
        for table in tables_to_clear:
            try:
                # Get row count before deletion
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                
                if count > 0:
                    db.execute(text(f"DELETE FROM {table}"))
                    db.commit()
                    logger.info(f"Cleared {count} rows from table '{table}'")
                else:
                    logger.info(f"Table '{table}' was already empty")
                    
            except Exception as e:
                logger.warning(f"Could not clear table '{table}': {e}")
                db.rollback()
        
        logger.info("Database clearing completed successfully")
        
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting database clear...")
    clear_database()
    logger.info("Database clear complete - schema preserved, all data removed")
