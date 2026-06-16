import sqlite3
import os

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

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
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
                    catatan_id INTEGER NOT NULL,
                    attachment_name TEXT NOT NULL,
                    attachment_tipe_mime TEXT NOT NULL,
                    attachment_blob BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(catatan_id) REFERENCES notes(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def add_note(self, title, catatan, sumber_catatan=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (title, catatan, sumber_catatan) VALUES (?, ?, ?)",
                (title, catatan, sumber_catatan)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_notes(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, catatan, sumber_catatan, created_at FROM notes ORDER BY created_at DESC")
            return cursor.fetchall()

    def update_note(self, note_id, title, catatan, sumber_catatan=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET title = ?, catatan = ?, sumber_catatan = ? WHERE id = ?",
                (title, catatan, sumber_catatan, note_id)
            )
            conn.commit()

    def delete_note(self, note_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attachment_file WHERE catatan_id = ?", (note_id,))
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()

    def add_attachment(self, catatan_id, filename, mime_type, blob_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO attachment_file (catatan_id, attachment_name, attachment_tipe_mime, attachment_blob)
                   VALUES (?, ?, ?, ?)""",
                (catatan_id, filename, mime_type, blob_data)
            )
            conn.commit()
            return cursor.lastrowid

    def get_attachments_by_note_id(self, catatan_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, catatan_id, attachment_name, attachment_tipe_mime, attachment_blob, created_at FROM attachment_file WHERE catatan_id = ?",
                (catatan_id,)
            )
            return cursor.fetchall()

    def delete_attachment(self, attachment_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attachment_file WHERE id = ?", (attachment_id,))
            conn.commit()

    def search_notes(self, query):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT id, title, catatan, sumber_catatan, created_at 
                FROM notes 
                WHERE title LIKE ? OR catatan LIKE ? OR sumber_catatan LIKE ?
                ORDER BY created_at DESC
            """, (search_pattern,) * 3)
            return cursor.fetchall()

    def get_notes_paginated(self, offset=0, limit=20, search_query=None):
        """Fetch a page of notes with optional search filter."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if search_query:
                pattern = f"%{search_query}%"
                cursor.execute("""
                    SELECT id, title, catatan, sumber_catatan, created_at
                    FROM notes
                    WHERE title LIKE ? OR catatan LIKE ? OR sumber_catatan LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (pattern, pattern, pattern, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, title, catatan, sumber_catatan, created_at
                    FROM notes
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            return cursor.fetchall()

    def get_total_notes_count(self, search_query=None):
        """Return the total number of notes, with optional search filter."""
        with self.get_connection() as conn:
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
