"""Mixin for export and import functionality (CSV, HTML, PDF, database backup)."""

import csv
import os
import re
import shutil
import sqlite3

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFont, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QFileDialog, QMessageBox


class ExportImportMixin:
    """Mixin providing export and import functionality.

    This mixin assumes the host class provides:
        - self.tableWidget: QTableWidget instance
        - self.db: DatabaseManager instance
        - self.search_input: QLineEdit for search input
        - self.current_lang: Current language code
        - self.t(key): Translation function
        - self.display_notes(): Method to refresh the table
        - self._get_selected_note_data(): Method to get selected note data
    """

    # --- Filename Sanitization ---

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to be compatible with Windows filesystem.
        
        Handles:
        - Invalid characters: < > : " / \\ | ? *
        - Control characters (ASCII 0-31)
        - Reserved names: CON, PRN, AUX, NUL, COM1-9, LPT1-9
        - Leading/trailing spaces and dots
        - Consecutive underscores
        
        Args:
            filename: The original filename.
        
        Returns:
            Sanitized filename safe for all platforms (especially Windows).
        """
        # Windows reserved names
        reserved_names = {
            'con', 'prn', 'aux', 'nul',
            'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
            'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
        }
        
        # Characters invalid on Windows
        invalid_chars = r'<>:"/\|?*'
        sanitized = filename
        
        # Remove control characters (ASCII 0-31)
        sanitized = ''.join(c if ord(c) >= 32 else '' for c in sanitized)
        
        # Replace invalid characters
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        
        # Remove consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # Check if result is a reserved name (without extension)
        name_without_ext = sanitized.rsplit('.', 1)[0] if '.' in sanitized else sanitized
        if name_without_ext.lower() in reserved_names:
            sanitized = '_' + sanitized
        
        return sanitized if sanitized and sanitized.strip('_') else 'export'

    @staticmethod
    def _sanitize_file_path(file_path: str) -> str:
        """Sanitize a complete file path to be Windows-compatible.
        
        Preserves the directory structure but sanitizes each path component
        and the filename.
        
        Args:
            file_path: The complete file path.
        
        Returns:
            Sanitized file path safe for Windows.
        """
        if not file_path:
            return 'export'
        
        # Use os.path to handle path properly
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        
        # Sanitize only the filename, keep directory as-is
        sanitized_name = ExportImportMixin._sanitize_filename(file_name)
        
        # Reconstruct path
        if file_dir:
            return os.path.join(file_dir, sanitized_name)
        else:
            return sanitized_name

    # --- CSV Export ---

    def export_to_csv(self) -> None:
        """Export all notes to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_csv"), "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        # Ensure .csv extension
        if not file_path.endswith(".csv"):
            file_path += ".csv"
        
        # Sanitize the complete file path
        file_path = self._sanitize_file_path(file_path)

        try:
            notes = self.db.get_all_notes()
            self._write_csv_file(file_path, notes)
            QMessageBox.information(
                self, self.t("success"), self.t("export_success").format(file_path)
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export notes: {e}")

    def _write_csv_file(self, file_path: str, notes: list) -> None:
        """Write notes to a CSV file with sanitization.

        Args:
            file_path: Path to the CSV file.
            notes: List of note tuples to write.
        """
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ID", "Judul", "Catatan", "Sumber", "Dibuat Pada"])

            sanitized_notes = self._sanitize_csv_data(notes)
            writer.writerows(sanitized_notes)

    def _sanitize_csv_data(self, notes: list) -> list:
        """Sanitize note data to prevent CSV formula injection.

        Args:
            notes: List of note tuples.

        Returns:
            Sanitized list of note data.
        """
        sanitized = []
        for note in notes:
            row = list(note)
            for i in range(len(row)):
                val = str(row[i])
                if val.startswith(("=", "+", "-", "@")):
                    row[i] = "'" + val
            sanitized.append(row)
        return sanitized

    # --- HTML Export ---

    def export_note_as_html(self) -> None:
        """Export the selected note as a standalone HTML file."""
        data = self._get_selected_note_data()
        if not data:
            return

        title = data["title"] or "note"
        sanitized_title = self._sanitize_filename(title)
        full_html = self._build_html_content(data)

        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_html"), f"{sanitized_title}.html", "HTML Files (*.html)"
        )
        if not file_path:
            return
        
        # Ensure .html extension
        if not file_path.endswith(".html"):
            file_path += ".html"
        
        # Sanitize the complete file path
        file_path = self._sanitize_file_path(file_path)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_html)
            QMessageBox.information(
                self,
                self.t("success"),
                self.t("export_html_success").format(file_path),
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.critical(
                self, "Error", self.t("export_html_error").format(str(e))
            )

    def _build_html_content(self, data: dict) -> str:
        """Build standalone HTML content for a note.

        Args:
            data: Dictionary with note data.

        Returns:
            Complete HTML document as string.
        """
        title = data["title"] or "note"
        sumber = data["sumber"] or "-"
        catatan_html = data["catatan_html"] or ""
        created_at = data["created_at"] or "-"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; line-height: 1.6; color: #333; }}
        h1 {{ color: #222; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
        .metadata {{ color: #666; margin-bottom: 20px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="metadata">
        <p><strong>Source:</strong> {sumber}</p>
        <p><strong>Date:</strong> {created_at}</p>
    </div>
    <hr>
    {catatan_html}
</body>
</html>"""

    # --- PDF Export ---

    def export_note_as_pdf(self) -> None:
        """Export the selected note as a PDF file."""
        data = self._get_selected_note_data()
        if not data:
            return

        title = data["title"] or "note"
        sanitized_title = self._sanitize_filename(title)
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_pdf"), f"{sanitized_title}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        
        # Ensure .pdf extension
        if not file_path.endswith(".pdf"):
            file_path += ".pdf"
        
        # Sanitize the complete file path
        file_path = self._sanitize_file_path(file_path)

        try:
            self._write_pdf_file(file_path, data)
            QMessageBox.information(
                self,
                self.t("success"),
                self.t("export_pdf_success").format(file_path),
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.critical(
                self, "Error", self.t("export_pdf_error").format(str(e))
            )

    def _write_pdf_file(self, file_path: str, data: dict) -> None:
        """Write a note to a PDF file.

        Args:
            file_path: Path to the PDF file.
            data: Dictionary with note data.
        """
        title = data["title"] or "note"
        sumber = data["sumber"] or "-"
        catatan_html = data["catatan_html"] or ""
        created_at = data["created_at"] or "-"

        # Strip inline font-size from note content
        catatan_clean = re.sub(r'font-size:\s*\d+[^;"]*;', '', catatan_html)

        html_content = f"""
        <h1>{title}</h1>
        <p><strong>Source:</strong> {sumber}</p>
        <p><strong>Date:</strong> {created_at}</p>
        <hr>
        {catatan_clean}
        """

        doc = QTextDocument()
        doc.setDefaultFont(QFont("sans-serif", 11))
        doc.setHtml(html_content)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)

        doc.print_(printer)

    # --- Database Backup/Restore ---

    def backup_notes(self) -> None:
        """Backup the database to a user-selected file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("backup_db"), "notes_backup.db", "SQLite Database (*.db)"
        )
        if not file_path:
            return

        try:
            db_source = self.db.db_name
            if os.path.exists(db_source):
                shutil.copy2(db_source, file_path)
                QMessageBox.information(
                    self,
                    self.t("success"),
                    self.t("backup_success").format(file_path),
                )
            else:
                QMessageBox.warning(self, self.t("warning"), self.t("db_not_found"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to backup database: {e}")

    def restore_database(self) -> None:
        """Restore the database from a user-selected .db file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.t("restore_db"), "", "SQLite Database (*.db)"
        )
        if not file_path:
            return

        validation = self._validate_sqlite_file(file_path)
        if validation == "invalid":
            QMessageBox.warning(self, self.t("warning"), self.t("restore_invalid_db"))
            return

        reply = self._get_restore_confirmation(validation)
        if reply != QMessageBox.Yes:
            return

        try:
            self._do_restore_database(file_path)
            QMessageBox.information(
                self, self.t("success"), self.t("restore_success").format(file_path)
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", self.t("restore_error").format(str(e)))

    def _validate_sqlite_file(self, file_path: str) -> str:
        """Validate if a file is a valid SQLite database.

        Args:
            file_path: Path to the file to validate.

        Returns:
            "valid", "empty", "no_table", or "invalid".
        """
        try:
            if os.path.getsize(file_path) == 0:
                return "invalid"

            with open(file_path, "rb") as f:
                header = f.read(16)
            if header != b"SQLite format 3\x00":
                return "invalid"

            conn = sqlite3.connect(f"file:{file_path}?mode=ro", uri=True)
            conn.execute("SELECT count(*) FROM sqlite_master")

            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='notes'"
            )
            if not cursor.fetchone():
                conn.close()
                return "no_table"

            cursor = conn.execute("SELECT COUNT(*) FROM notes")
            count = cursor.fetchone()[0]
            conn.close()

            return "empty" if count == 0 else "valid"
        except (sqlite3.DatabaseError, Exception):
            return "invalid"

    def _get_restore_confirmation(self, validation: str) -> QMessageBox.StandardButton:
        """Get user confirmation for database restore.

        Args:
            validation: The validation result string.

        Returns:
            The user's response (QMessageBox.Yes or QMessageBox.No).
        """
        if validation == "no_table":
            return QMessageBox.warning(
                self,
                self.t("warning"),
                self.t("restore_no_notes_table"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        elif validation == "empty":
            return QMessageBox.warning(
                self,
                self.t("warning"),
                self.t("restore_empty_db"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        else:
            return QMessageBox.warning(
                self,
                self.t("warning"),
                self.t("restore_confirm"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

    def _do_restore_database(self, file_path: str) -> None:
        """Perform the actual database restore.

        Args:
            file_path: Path to the backup file to restore from.
        """
        from database import DatabaseManager

        db_target = self.db.db_name
        shutil.copy2(file_path, db_target)

        # Reinitialize DatabaseManager
        self.db = DatabaseManager()

        # Reset state and refresh
        self._current_offset = 0
        self._current_search = None
        self.search_input.clear()
        self.display_notes(reset=True)