import sys
import unittest
import os
import tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

# Ensure app modules can be loaded from the current directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database import DatabaseManager
from src.config import t
from src.dialogs.note_dialogs import NoteDialog, NoteDetailDialog
from src.ui.main_window import MainWindow

# Initialize QApplication once for the entire test suite run (mandatory for Qt widgets)
app = QApplication.instance() or QApplication(sys.argv)

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_run.db"
        self.db = DatabaseManager(self.db_name)

    def tearDown(self):
        # Close connection and cleanup db file
        if os.path.exists(f".catat-segala/{self.db_name}"):
            os.remove(f".catat-segala/{self.db_name}")

    def test_notes_crud(self):
        # Create
        note_id = self.db.add_note("Unit Test Note", "<p>Content</p>", "Unit Test Source")
        self.assertIsNotNone(note_id)

        # Read
        notes = self.db.get_all_notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0][1], "Unit Test Note")

        # Update
        self.db.update_note(note_id, "Updated Unit Test Note", "<p>Updated Content</p>", "Updated Source")
        notes = self.db.get_all_notes()
        self.assertEqual(notes[0][1], "Updated Unit Test Note")

        # Delete
        self.db.delete_note(note_id)
        notes = self.db.get_all_notes()
        self.assertEqual(len(notes), 0)

    def test_attachments(self):
        note_id = self.db.add_note("Note with Attachments", "<p>Content</p>")
        
        # Add attachment
        att_id = self.db.add_attachment(note_id, "doc.pdf", "application/pdf", b"%PDF-1.4...")
        self.assertIsNotNone(att_id)

        # Get attachments
        atts = self.db.get_attachments_by_note_id(note_id)
        self.assertEqual(len(atts), 1)
        self.assertEqual(atts[0][2], "doc.pdf")
        self.assertEqual(atts[0][3], "application/pdf")
        self.assertEqual(atts[0][4], b"%PDF-1.4...")

        # Delete attachment
        self.db.delete_attachment(att_id)
        atts = self.db.get_attachments_by_note_id(note_id)
        self.assertEqual(len(atts), 0)


class TestConfigTranslations(unittest.TestCase):
    def test_translation_en(self):
        self.assertEqual(t("en", "add_note"), "Add Note")
        self.assertEqual(t("en", "attachments"), "Attachments:")

    def test_translation_id(self):
        self.assertEqual(t("id", "add_note"), "Tambah Catatan")
        self.assertEqual(t("id", "attachments"), "Lampiran:")

    def test_translation_restore_en(self):
        self.assertEqual(t("en", "restore_db"), "Restore Database")
        self.assertIn("replace", t("en", "restore_confirm"))
        self.assertIn("restored", t("en", "restore_success"))
        self.assertIn("valid", t("en", "restore_invalid_db"))

    def test_translation_restore_id(self):
        self.assertEqual(t("id", "restore_db"), "Restore Database")
        self.assertIn("menggantikan", t("id", "restore_confirm"))
        self.assertIn("direstore", t("id", "restore_success"))
        self.assertIn("valid", t("id", "restore_invalid_db"))

    def test_translation_export_html(self):
        self.assertEqual(t("en", "export_html"), "Export as HTML")
        self.assertEqual(t("en", "save_html"), "Save as HTML")
        self.assertIn("HTML", t("en", "export_html_success"))
        self.assertIn("HTML", t("en", "export_html_error"))

    def test_translation_export_pdf(self):
        self.assertEqual(t("en", "export_pdf"), "Export as PDF")
        self.assertEqual(t("en", "save_pdf"), "Save as PDF")
        self.assertIn("PDF", t("en", "export_pdf_success"))
        self.assertIn("PDF", t("en", "export_pdf_error"))


class TestNoteDialog(unittest.TestCase):
    def test_note_dialog_creation(self):
        dialog = NoteDialog(lang="en")
        self.assertEqual(dialog.windowTitle(), "Add Note")
        self.assertEqual(dialog.title_input.text(), "")
        self.assertEqual(dialog.current_attachments, [])

    def test_note_dialog_edit_load(self):
        # Mock note_data: (id, title, catatan_html, sumber)
        note_data = (1, "Loaded Note Title", "<p>Loaded Content</p>", "Loaded Source")
        dialog = NoteDialog(note_data=note_data, lang="en")
        
        self.assertEqual(dialog.windowTitle(), "Edit")
        self.assertEqual(dialog.title_input.text(), "Loaded Note Title")
        self.assertEqual(dialog.sumber_input.text(), "Loaded Source")

    def test_note_dialog_get_data(self):
        dialog = NoteDialog(lang="en")
        dialog.title_input.setText("New Title")
        dialog.catatan_input.setHtml("<p>New Content</p>")
        dialog.sumber_input.setText("New Source")
        
        data = dialog.get_data()
        self.assertEqual(data["title"], "New Title")
        self.assertIn("New Content", data["catatan"])
        self.assertEqual(data["sumber"], "New Source")


class TestMainWindow(unittest.TestCase):
    def setUp(self):
        """Reset QSettings to avoid persisted language affecting assertions."""
        from PySide6.QtCore import QSettings
        settings = QSettings("CatatSegala", "python-ui-notes-app")
        settings.clear()

    def test_main_window_init(self):
        window = MainWindow()
        self.assertEqual(window.windowTitle(), t("en", "app_title"))
        self.assertEqual(window.tableWidget.columnCount(), 6)
        self.assertGreaterEqual(window.tableWidget.rowCount(), 0)

    def test_main_window_has_restore_and_export_methods(self):
        """Verify new methods exist on MainWindow."""
        self.assertTrue(callable(getattr(MainWindow, "restore_database", None)))
        self.assertTrue(callable(getattr(MainWindow, "_validate_sqlite_file", None)))
        self.assertTrue(callable(getattr(MainWindow, "export_note_as_html", None)))
        self.assertTrue(callable(getattr(MainWindow, "export_note_as_pdf", None)))
        self.assertTrue(callable(getattr(MainWindow, "_get_selected_note_data", None)))

    def test_validate_sqlite_file_valid(self):
        """Test _validate_sqlite_file with a real SQLite database."""
        import tempfile
        import sqlite3 as sq

        # Create a valid temp SQLite file
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sq.connect(path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        window = MainWindow.__new__(MainWindow)
        self.assertTrue(window._validate_sqlite_file(path))
        os.unlink(path)

    def test_validate_sqlite_file_invalid(self):
        """Test _validate_sqlite_file with non-SQLite files."""
        window = MainWindow.__new__(MainWindow)

        # Text file
        fd, txt = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        with open(txt, "w") as f:
            f.write("not a database")
        self.assertFalse(window._validate_sqlite_file(txt))
        os.unlink(txt)

        # Empty file
        fd, empty = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.assertFalse(window._validate_sqlite_file(empty))
        os.unlink(empty)

    def test_get_selected_note_data_no_selection(self):
        """Test _get_selected_note_data returns None when no row is selected."""
        window = MainWindow()
        # No selection — currentRow() returns -1
        result = window._get_selected_note_data()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
