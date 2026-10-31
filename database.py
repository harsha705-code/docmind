
import sqlite3
from datetime import datetime
from pathlib import Path

# Database location
DB_NAME = Path(__file__).resolve().parent / "documind.db"


def get_connection():
    try:
        connection = sqlite3.connect(str(DB_NAME))
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as error:
        raise RuntimeError(f"Database connection failed: {error}")


def init_db():
    try:
        with get_connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_name TEXT NOT NULL,
                    document_type TEXT,
                    extracted_text TEXT,
                    ai_summary TEXT,
                    upload_timestamp TEXT NOT NULL
                )
            """)
        return True
    except sqlite3.Error as error:
        raise RuntimeError(f"Database initialization failed: {error}")


def save_document(document_name, document_type, extracted_text, ai_summary):
    if not isinstance(document_name, str) or not document_name.strip():
        raise ValueError("Document name cannot be empty.")

    try:
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO documents
                (document_name, document_type, extracted_text,
                 ai_summary, upload_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                document_name.strip(),
                document_type,
                extracted_text,
                ai_summary,
                timestamp
            ))

            return cursor.lastrowid

    except sqlite3.Error as error:
        raise RuntimeError(f"Unable to save document: {error}")


def get_all_documents():
    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                SELECT * FROM documents
                ORDER BY upload_timestamp DESC, id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as error:
        raise RuntimeError(f"Unable to retrieve documents: {error}")


def get_document_by_id(document_id):
    if not isinstance(document_id, int) or isinstance(document_id, bool):
        raise ValueError("Document ID must be an integer.")

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                SELECT * FROM documents WHERE id = ?
            """, (document_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    except sqlite3.Error as error:
        raise RuntimeError(f"Unable to retrieve document: {error}")


def delete_document(document_id):
    if not isinstance(document_id, int) or isinstance(document_id, bool):
        raise ValueError("Document ID must be an integer.")

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                DELETE FROM documents WHERE id = ?
            """, (document_id,))

            return cursor.rowcount > 0

    except sqlite3.Error as error:
        raise RuntimeError(f"Unable to delete document: {error}")


if __name__ == "__main__":
    init_db()
    print("DocuMind database initialized successfully!")
