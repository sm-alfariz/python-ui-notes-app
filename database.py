import sqlite3
from datetime import datetime
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
        return sqlite3.connect(self.db_name)

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
            conn.commit()

    def add_note(self, title, catatan, sumber_catatan=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (title, catatan, sumber_catatan) VALUES (?, ?, ?)",
                (title, catatan, sumber_catatan)
            )
            conn.commit()

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
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
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
