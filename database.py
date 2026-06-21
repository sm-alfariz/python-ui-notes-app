import sqlite3
import os
import contextlib

class DatabaseManager:
    def __init__(self, db_name="notes.db"):
        folder_name = ".catat-segala"
        # Create the folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        # Construct the full path to the database file
        database_path = os.path.join(folder_name, db_name)
        self.db_name = database_path
        self.init_db()

    @contextlib.contextmanager
    def _connect(self):
        """Context manager that opens a connection, commits on success, and always closes."""
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            # Create table only if it doesn't exist (preserves existing data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    catatan TEXT NOT NULL,
                    sumber_catatan TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachment_file (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notes_id INTEGER NOT NULL,
                    attachment_name TEXT NOT NULL,
                    attachment_tipe_mime TEXT NOT NULL,
                    attachment_blob BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(notes_id) REFERENCES notes(id) ON DELETE CASCADE
                )
            """)

            # Migrate existing database if it still uses catatan_id
            cursor.execute("PRAGMA table_info(attachment_file)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "catatan_id" in columns and "notes_id" not in columns:
                cursor.execute("ALTER TABLE attachment_file RENAME COLUMN catatan_id TO notes_id")

            # Add is_locked column if missing
            cursor.execute("PRAGMA table_info(notes)")
            note_columns = [row[1] for row in cursor.fetchall()]
            if "is_locked" not in note_columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN is_locked INTEGER DEFAULT 0")

    def add_note(self, title, catatan, sumber_catatan=None, is_locked=0):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (title, catatan, sumber_catatan, is_locked) VALUES (?, ?, ?, ?)",
                (title, catatan, sumber_catatan, is_locked)
            )
            return cursor.lastrowid

    def get_all_notes(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, catatan, sumber_catatan, created_at, is_locked FROM notes ORDER BY created_at DESC")
            return cursor.fetchall()

    def update_note(self, note_id, title, catatan, sumber_catatan=None, is_locked=0):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET title = ?, catatan = ?, sumber_catatan = ?, is_locked = ? WHERE id = ?",
                (title, catatan, sumber_catatan, is_locked, note_id)
            )

    def delete_note(self, note_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attachment_file WHERE notes_id = ?", (note_id,))
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    def add_attachment(self, notes_id, filename, mime_type, blob_data):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO attachment_file (notes_id, attachment_name, attachment_tipe_mime, attachment_blob)
                   VALUES (?, ?, ?, ?)""",
                (notes_id, filename, mime_type, blob_data)
            )
            return cursor.lastrowid

    def get_attachments_by_note_id(self, notes_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, notes_id, attachment_name, attachment_tipe_mime, attachment_blob, created_at FROM attachment_file WHERE notes_id = ?",
                (notes_id,)
            )
            return cursor.fetchall()

    def delete_attachment(self, attachment_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attachment_file WHERE id = ?", (attachment_id,))

    def get_attachment_counts(self, note_ids):
        """Return a dict mapping note_id -> attachment count for the given IDs."""
        if not note_ids:
            return {}
        with self._connect() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in note_ids)
            cursor.execute(
                f"SELECT notes_id, COUNT(*) FROM attachment_file WHERE notes_id IN ({placeholders}) GROUP BY notes_id",
                note_ids,
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def search_notes(self, query):
        with self._connect() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT id, title, catatan, sumber_catatan, created_at, is_locked
                FROM notes
                WHERE title LIKE ? OR catatan LIKE ? OR sumber_catatan LIKE ?
                ORDER BY created_at DESC
            """, (search_pattern,) * 3)
            return cursor.fetchall()

    def get_notes_paginated(self, offset=0, limit=20, search_query=None):
        """Fetch a page of notes with optional search filter."""
        with self._connect() as conn:
            cursor = conn.cursor()
            if search_query:
                pattern = f"%{search_query}%"
                cursor.execute("""
                    SELECT id, title, catatan, sumber_catatan, created_at, is_locked
                    FROM notes
                    WHERE title LIKE ? OR catatan LIKE ? OR sumber_catatan LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (pattern, pattern, pattern, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, title, catatan, sumber_catatan, created_at, is_locked
                    FROM notes
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            return cursor.fetchall()

    def get_total_notes_count(self, search_query=None):
        """Return the total number of notes, with optional search filter."""
        with self._connect() as conn:
            cursor = conn.cursor()
            if search_query:
                pattern = f"%{search_query}%"
                cursor.execute("""
                    SELECT COUNT(*) FROM notes
                    WHERE title LIKE ? OR catatan LIKE ? OR sumber_catatan LIKE ?
                """, (pattern, pattern, pattern))
            else:
                cursor.execute("SELECT COUNT(*) FROM notes")
            return cursor.fetchone()[0]
