"""Mixin for note CRUD operations."""

from PySide6.QtWidgets import QMessageBox

from src.dialogs.note_dialogs import NoteDialog, NoteDetailDialog
from src.ui.utils.string_utils import strip_html


class NoteOperationsMixin:
    """Mixin providing note CRUD operations (Create, Read, Update, Delete).

    This mixin assumes the host class provides:
        - self.tableWidget: QTableWidget instance
        - self.db: DatabaseManager instance
        - self.current_lang: Current language code
        - self.t(key): Translation function
        - self.display_notes(): Method to refresh the table
    """

    def add_note(self) -> None:
        """Open dialog to add a new note."""
        dialog = NoteDialog(self, lang=self.current_lang)
        if dialog.exec():
            data = dialog.get_data()
            if not self._validate_note_data(data):
                return

            sumber = data["sumber"].strip() or None
            note_id = self.db.add_note(
                data["title"], data["catatan"], sumber, data.get("is_locked", 0)
            )

            # Save attachments
            for att in data["attachments"]:
                self.db.add_attachment(note_id, att["name"], att["mime"], att["blob"])

            self.display_notes()

    def edit_note(self) -> None:
        """Open dialog to edit the selected note."""
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self, self.t("warning"), self.t("select_edit_warning")
            )
            return

        note_data = self._get_note_data_from_row(selected_row)
        dialog = NoteDialog(self, note_data, lang=self.current_lang)

        if dialog.exec():
            data = dialog.get_data()
            if not self._validate_note_data(data):
                return

            self._update_note_in_database(note_data[0], data)
            self.display_notes()

    def view_detail(self) -> None:
        """Open dialog to view note details."""
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            return

        note_data = self._get_full_note_data(selected_row)
        dialog = NoteDetailDialog(self, note_data, lang=self.current_lang)
        dialog.exec()

    def delete_note(self) -> None:
        """Delete selected note(s) after confirmation."""
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, self.t("warning"), self.t("select_delete_warning")
            )
            return

        count = len(selected_rows)
        confirm_msg = self._get_delete_confirmation_message(count)

        reply = QMessageBox.question(
            self,
            self.t("confirm"),
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            note_ids = self._extract_note_ids(selected_rows)
            for nid in note_ids:
                self.db.delete_note(nid)
            self.display_notes()

    def toggle_lock(self, row: int) -> None:
        """Toggle the lock state of the note at the given row.

        Args:
            row: The row index of the note to toggle.
        """
        note_data = self._get_note_data_from_row(row)
        new_locked = 0 if note_data[5] else 1
        self.db.update_note(
            note_data[0], note_data[1], note_data[2], note_data[3], new_locked
        )
        self.display_notes()

    # --- Helper methods ---

    def _validate_note_data(self, data: dict) -> bool:
        """Validate note data before saving.

        Args:
            data: The note data dictionary from the dialog.

        Returns:
            True if valid, False otherwise.
        """
        if not data["title"].strip() or strip_html(data["catatan"]).strip() == "":
            QMessageBox.warning(self, self.t("warning"), self.t("empty_warning"))
            return False
        return True

    def _get_note_data_from_row(self, row: int) -> tuple:
        """Get note data needed for editing from a table row.

        Args:
            row: The row index.

        Returns:
            Tuple of (id, title, catatan_html, sumber, None, is_locked).
        """
        note_id = int(self.tableWidget.item(row, 0).text())
        title = self.tableWidget.item(row, 1).data(Qt.UserRole)
        catatan_html = self.tableWidget.item(row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(row, 3).data(Qt.UserRole)
        is_locked = self.tableWidget.item(row, 4).data(Qt.UserRole)

        return (note_id, title, catatan_html, sumber, None, is_locked)

    def _get_full_note_data(self, row: int) -> tuple:
        """Get full note data for detail view from a table row.

        Args:
            row: The row index.

        Returns:
            Tuple of (id, title, catatan_html, sumber, created_at, is_locked).
        """
        note_id = int(self.tableWidget.item(row, 0).text())
        title = self.tableWidget.item(row, 1).data(Qt.UserRole)
        catatan_html = self.tableWidget.item(row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(row, 3).data(Qt.UserRole)
        is_locked = self.tableWidget.item(row, 4).data(Qt.UserRole)
        created_at = self.tableWidget.item(row, 6).text()

        return (note_id, title, catatan_html, sumber, created_at, is_locked)

    def _update_note_in_database(self, note_id: int, data: dict) -> None:
        """Update a note in the database with new data.

        Args:
            note_id: The ID of the note to update.
            data: The new note data from the dialog.
        """
        sumber = data["sumber"].strip() or None
        self.db.update_note(
            note_id, data["title"], data["catatan"], sumber, data.get("is_locked", 0)
        )

        # Sync attachments
        self._sync_attachments(note_id, data["attachments"])

    def _sync_attachments(self, note_id: int, current_attachments: list) -> None:
        """Synchronize attachments for a note.

        Args:
            note_id: The ID of the note.
            current_attachments: List of current attachment dicts from dialog.
        """
        db_atts = self.db.get_attachments_by_note_id(note_id)
        db_att_ids = {att[0] for att in db_atts}
        current_att_ids = {
            att["id"] for att in current_attachments if att["id"] is not None
        }

        # Delete attachments that were removed
        for att in db_atts:
            if att[0] not in current_att_ids:
                self.db.delete_attachment(att[0])

        # Add new attachments
        for att in current_attachments:
            if att["id"] is None:
                self.db.add_attachment(note_id, att["name"], att["mime"], att["blob"])

    def _get_delete_confirmation_message(self, count: int) -> str:
        """Get the confirmation message for deleting notes.

        Args:
            count: Number of notes to delete.

        Returns:
            The confirmation message string.
        """
        confirm_msg = self.t("delete_confirm")
        if count > 1:
            confirm_msg = f"{self.t('delete_confirm').rstrip('?')} {count} notes?"
        return confirm_msg

    def _extract_note_ids(self, selected_rows: list) -> list:
        """Extract note IDs from selected table rows.

        Args:
            selected_rows: List of QModelIndex objects.

        Returns:
            List of note IDs as integers.
        """
        return [
            int(self.tableWidget.item(idx.row(), 0).text()) for idx in selected_rows
        ]


# Import Qt here to avoid issues in the class definition
from PySide6.QtCore import Qt