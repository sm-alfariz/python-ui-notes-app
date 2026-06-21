"""Mixin for table display and pagination management."""

import os
import re
from PySide6.QtWidgets import QTableWidgetItem, QMenu
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

from src.config import ASSETS_DIR

from src.config import TRANSLATIONS
from src.ui.utils.string_utils import strip_html, build_snippet_html
from src.ui.utils.date_utils import format_date


class TableManagementMixin:
    """Mixin providing table display, pagination, and context menu functionality.

    This mixin assumes the host class provides:
        - self.tableWidget: QTableWidget instance
        - self.db: DatabaseManager instance
        - self.current_lang: Current language code
        - self.t(key): Translation function
        - self.view_detail(): Method to view note details
        - self.edit_note(): Method to edit a note
        - self.delete_note(): Method to delete a note
        - self.toggle_lock(row): Method to toggle note lock state
        - self.export_note_as_html(): Method to export note as HTML
        - self.export_note_as_pdf(): Method to export note as PDF
    """

    # Pagination constants
    PAGE_SIZE = 20

    def display_notes(self, reset: bool = True) -> None:
        """Load the first page of notes (or reset to first page).

        Args:
            reset: If True, clear the table and start from offset 0.
        """
        if reset:
            self._current_offset = 0
            self.tableWidget.setRowCount(0)

        self._total_notes = self.db.get_total_notes_count(self._current_search)
        notes = self.db.get_notes_paginated(
            offset=self._current_offset,
            limit=self.PAGE_SIZE,
            search_query=self._current_search,
        )
        self._append_notes_to_table(notes)
        self._current_offset += len(notes)
        self._update_pagination_ui()

    def _append_notes_to_table(self, notes: list) -> None:
        """Append a list of note rows to the table without clearing it.

        Args:
            notes: List of note tuples from the database.
        """
        start_row = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(start_row + len(notes))

        # Batch-fetch attachment counts for all notes in this page
        note_ids = [n[0] for n in notes]
        att_counts = self.db.get_attachment_counts(note_ids)

        for i, note in enumerate(notes):
            row_index = start_row + i
            self._populate_table_row(row_index, note, att_counts)

    def _populate_table_row(
        self, row_index: int, note: tuple, att_counts: dict
    ) -> None:
        """Populate a single table row with note data.

        Args:
            row_index: The row index in the table.
            note: The note tuple (id, title, catatan_html, sumber, created_at, is_locked).
            att_counts: Dictionary mapping note IDs to attachment counts.
        """
        # note = (id, title, catatan_html, sumber, created_at, is_locked)
        is_locked = note[5] if len(note) > 5 else 0

        # ID (hidden)
        self.tableWidget.setItem(row_index, 0, QTableWidgetItem(str(note[0])))

        # Title — always show real title
        item_title = QTableWidgetItem(str(note[1]))
        item_title.setData(Qt.UserRole, note[1])
        self.tableWidget.setItem(row_index, 1, item_title)

        # Catatan (Note) — hide if locked
        self._set_catatan_item(row_index, note, is_locked)

        # Sumber — hide if locked
        self._set_sumber_item(row_index, note, is_locked)

        # Lock indicator
        self._set_lock_item(row_index, is_locked)

        # Attachment count (column 5)
        self._set_attachment_item(row_index, note, att_counts)

        # Date (column 6)
        formatted_date = format_date(note[4])
        self.tableWidget.setItem(row_index, 6, QTableWidgetItem(formatted_date))

        # Set row height
        row_height = 45 if is_locked else 35
        self.tableWidget.setRowHeight(row_index, row_height)

    def _set_catatan_item(self, row_index: int, note: tuple, is_locked: int) -> None:
        """Set the catatan (note content) table item.

        Args:
            row_index: The row index in the table.
            note: The note tuple.
            is_locked: Whether the note is locked.
        """
        if is_locked:
            item_catatan = QTableWidgetItem("🔒")
            item_catatan.setData(Qt.UserRole, note[2])
            big_font = item_catatan.font()
            big_font.setPointSize(16)
            item_catatan.setFont(big_font)
            item_catatan.setTextAlignment(Qt.AlignCenter)
        else:
            catatan_text = strip_html(str(note[2]))
            words = catatan_text.split()
            snippet = " ".join(words[:3]) + "..." if len(words) > 3 else catatan_text
            html_snippet = build_snippet_html(note[2], snippet)

            item_catatan = QTableWidgetItem()
            item_catatan.setToolTip(self.t("tooltip_detail"))
            item_catatan.setData(Qt.DisplayRole, snippet)
            item_catatan.setData(Qt.UserRole, note[2])  # original full HTML
            item_catatan.setData(Qt.UserRole + 1, html_snippet)  # formatted snippet

        self.tableWidget.setItem(row_index, 2, item_catatan)

    def _set_sumber_item(self, row_index: int, note: tuple, is_locked: int) -> None:
        """Set the sumber (source) table item.

        Args:
            row_index: The row index in the table.
            note: The note tuple.
            is_locked: Whether the note is locked.
        """
        if is_locked:
            item_sumber = QTableWidgetItem("🔒")
            item_sumber.setData(Qt.UserRole, note[3] if note[3] else "")
            big_font = item_sumber.font()
            big_font.setPointSize(16)
            item_sumber.setFont(big_font)
            item_sumber.setTextAlignment(Qt.AlignCenter)
        else:
            item_sumber = QTableWidgetItem(str(note[3]) if note[3] else "-")
            item_sumber.setData(Qt.UserRole, note[3] if note[3] else "")

        self.tableWidget.setItem(row_index, 3, item_sumber)

    def _set_lock_item(self, row_index: int, is_locked: int) -> None:
        """Set the lock indicator table item.

        Args:
            row_index: The row index in the table.
            is_locked: Whether the note is locked.
        """
        lock_text = "🔒" if is_locked else "🔓"
        item_lock = QTableWidgetItem(lock_text)
        lock_font = item_lock.font()
        lock_font.setPointSize(16)
        item_lock.setFont(lock_font)
        item_lock.setTextAlignment(Qt.AlignCenter)
        item_lock.setData(Qt.UserRole, is_locked)
        self.tableWidget.setItem(row_index, 4, item_lock)

    def _set_attachment_item(
        self, row_index: int, note: tuple, att_counts: dict
    ) -> None:
        """Set the attachment count table item.

        Args:
            row_index: The row index in the table.
            note: The note tuple.
            att_counts: Dictionary mapping note IDs to attachment counts.
        """
        count = att_counts.get(note[0], 0)
        att_text = str(count) if count > 0 else self.t("no_attachments")
        item_att = QTableWidgetItem(att_text)
        if count > 0:
            item_att.setToolTip(self.t("attachments").rstrip(":"))
        item_att.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(row_index, 5, item_att)

    def _update_pagination_ui(self) -> None:
        """Update the status label and Load More button visibility."""
        visible = self.tableWidget.rowCount()
        total = self._total_notes
        all_loaded = visible >= total

        self.notes_status_label.setText(f"Showing {visible} of {total} notes")
        self.load_more_btn.setEnabled(not all_loaded)
        self.load_more_btn.setText("✓ All loaded" if all_loaded else "⬇  Load More")

    def load_more_notes(self) -> None:
        """Append the next page of notes to the table."""
        self.display_notes(reset=False)

    def show_context_menu(self, pos) -> None:
        """Show right-click context menu on the table.

        Args:
            pos: The position where the context menu was requested.
        """
        index = self.tableWidget.indexAt(pos)
        if not index.isValid():
            return

        # Select the row that was right-clicked
        self.tableWidget.selectRow(index.row())

        row = index.row()
        is_locked = self.tableWidget.item(row, 4).data(Qt.UserRole)

        menu = QMenu(self)

        self._add_context_menu_actions(menu, row, is_locked)

        menu.exec(self.tableWidget.viewport().mapToGlobal(pos))

    @staticmethod
    def _icon(filename: str) -> QIcon:
        """Return a QIcon from the assets folder.

        Args:
            filename: Image file name inside assets/.
        Returns:
            QIcon (empty fallback if file missing).
        """
        return QIcon(os.path.join(ASSETS_DIR, filename))

    def _add_context_menu_actions(self, menu: QMenu, row: int, is_locked: int) -> None:
        """Add actions to the context menu.

        Args:
            menu: The QMenu to add actions to.
            row: The selected row index.
            is_locked: Whether the note is locked.
        """

        # Detail action
        detail_action = QAction(
            self._icon("detail-notes.png"),
            self.t("detail"),
            self,
        )
        detail_action.triggered.connect(self.view_detail)
        menu.addAction(detail_action)

        # Edit action
        edit_action = QAction(
            self._icon("edit-notes.png"),
            self.t("edit"),
            self,
        )
        edit_action.triggered.connect(self.edit_note)
        menu.addAction(edit_action)

        # Delete action
        delete_action = QAction(
            self._icon("delete-notes.png"),
            self.t("delete"),
            self,
        )
        delete_action.triggered.connect(self.delete_note)
        menu.addAction(delete_action)

        menu.addSeparator()

        # Lock / Unlock toggle action
        if is_locked:
            lock_label = TRANSLATIONS.get(self.current_lang, {}).get(
                "unlock", "Unlock"
            )
            lock_icon = self._icon("unlock.png")
        else:
            lock_label = self.t("lock")
            lock_icon = self._icon("lock.png")

        lock_action = QAction(lock_icon, lock_label, self)
        lock_action.triggered.connect(lambda: self.toggle_lock(row))
        menu.addAction(lock_action)

        menu.addSeparator()

        # Export actions
        export_html_action = QAction(
            self._icon("export-html.png"),
            self.t("export_html"),
            self,
        )
        export_html_action.triggered.connect(self.export_note_as_html)
        menu.addAction(export_html_action)

        export_pdf_action = QAction(
            self._icon("export-pdf.png"),
            self.t("export_pdf"),
            self,
        )
        export_pdf_action.triggered.connect(self.export_note_as_pdf)
        menu.addAction(export_pdf_action)

    def _get_selected_note_data(self) -> dict | None:
        """Retrieve note data from the selected table row.

        Returns:
            Dictionary with note data, or None if no row is selected.
        """
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            return None

        return {
            "title": self.tableWidget.item(selected_row, 1).data(Qt.UserRole),
            "catatan_html": self.tableWidget.item(selected_row, 2).data(Qt.UserRole),
            "sumber": self.tableWidget.item(selected_row, 3).data(Qt.UserRole),
            "created_at": self.tableWidget.item(selected_row, 6).text(),
        }