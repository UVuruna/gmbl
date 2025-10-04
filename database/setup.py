# database_setup.py

"""
Database setup script.
Run this to create the database and tables for the first time.
"""

from database.models import DatabaseCreator
from root.logger import AviatorLogger


def setup_database():
    """Setup database with all necessary tables."""
    logger = AviatorLogger.get_logger("DatabaseSetup")
    
    try:
        with DatabaseCreator() as db_creator:
            logger.info("Creating database tables...")
            db_creator.create_tables()
            
            for table_name in DatabaseCreator.TABLE_SCHEMAS.keys():
                if db_creator.table_exists(table_name):
                    logger.info(f"✓ Table '{table_name}' created successfully")
                else:
                    logger.error(f"✗ Failed to create table '{table_name}'")
        
        logger.info("Database setup completed!")
        
    except Exception as e:
        logger.critical(f"Database setup failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    from root.logger import init_logging
    from config import AppConstants
    
    init_logging(debug=AppConstants.debug)
    setup_database()