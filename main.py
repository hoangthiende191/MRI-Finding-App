import sys
from pathlib import Path


# ============================================================
# Project paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "01_Database"
ETL_DIR = DATABASE_DIR / "etl"
APP_DIR = BASE_DIR / "02_Application"


# Add project folders to Python path
sys.path.insert(0, str(DATABASE_DIR))
sys.path.insert(0, str(ETL_DIR))
sys.path.insert(0, str(APP_DIR))


# ============================================================
# Imports
# ============================================================

from database_setup import (
    setup_database,
    setup_schema,
    setup_procedures
)

from ETL import run_etl
from app import start_app


# ============================================================
# CONFIGURATION
# ============================================================

#Run first time
RUN_DATABASE_SETUP = True
RUN_SCHEMA_SETUP = True
RUN_PROCEDURE_SETUP = True
RUN_ETL = True
RUN_APP = True

#Run another time
# RUN_DATABASE_SETUP = False
# RUN_SCHEMA_SETUP = False
# RUN_PROCEDURE_SETUP = False
# RUN_ETL = False
# RUN_APP = True


# ============================================================
# MAIN
# ============================================================

def main():

    if RUN_DATABASE_SETUP:
        print("\n[1] Setting up database...")
        setup_database()

    if RUN_SCHEMA_SETUP:
        print("\n[2] Setting up schema...")
        setup_schema()

    if RUN_PROCEDURE_SETUP:
        print("\n[3] Setting up stored procedures...")
        setup_procedures()

    if RUN_ETL:
        print("\n[4] Running ETL...")
        run_etl()

    if RUN_APP:
        print("\n[5] Starting Flask application...")
        start_app()


if __name__ == "__main__":
    main()