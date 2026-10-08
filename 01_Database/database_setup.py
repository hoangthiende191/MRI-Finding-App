import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

SCHEMA_FILE = BASE_DIR / "01_Database" / "database" / "schema.sql"
PROCEDURES_FILE = BASE_DIR / "01_Database" / "database" / "procedures.sql"

load_dotenv(BASE_DIR / ".env")


def get_server_connection():
    return mysql.connector.connect(
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT", 3306)),
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD")
    )


def get_database_connection():
    return mysql.connector.connect(
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT", 3306)),
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
        database=os.getenv("DATABASE_NAME")
    )


def setup_database():
    conn = get_server_connection()

    try:
        cursor = conn.cursor()

        database_name = os.getenv("DATABASE_NAME")

        cursor.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS `{database_name}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            """
        )

        conn.commit()

        print("Database is ready.")

    finally:
        cursor.close()
        conn.close()

def setup_schema():
    conn = get_database_connection()

    try:
        cursor = conn.cursor()

        sql = SCHEMA_FILE.read_text(encoding="utf-8")

        # Execute each SQL statement
        statements = sql.split(";")

        for statement in statements:
            statement = statement.strip()

            if statement:
                cursor.execute(statement)

        conn.commit()

        print("Database schema is ready.")

    finally:
        cursor.close()
        conn.close()

def setup_procedures():
    conn = get_database_connection()

    try:
        cursor = conn.cursor()

        sql = PROCEDURES_FILE.read_text(encoding="utf-8")

        delimiter = ";"
        statement_lines = []

        for line in sql.splitlines():

            stripped = line.strip()

            # Ignore empty lines before a statement
            if not stripped and not statement_lines:
                continue

            # Handle DELIMITER // or DELIMITER ;
            if stripped.upper().startswith("DELIMITER "):
                delimiter = stripped.split(None, 1)[1]
                continue

            statement_lines.append(line)

            statement = "\n".join(statement_lines).rstrip()

            if statement.endswith(delimiter):
                statement = statement[:-len(delimiter)].strip()

                if statement:
                    cursor.execute(statement)

                statement_lines = []

        # Execute remaining statement if any
        remaining = "\n".join(statement_lines).strip()

        if remaining:
            cursor.execute(remaining)

        conn.commit()

        print("Stored procedures are ready.")

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()