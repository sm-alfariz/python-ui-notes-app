import csv
import shutil
import os
import re
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QHeaderView,
    QFileDialog,
    QLabel,
    QComboBox,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

from database import DatabaseManager
from src.dialogs.note_dialogs import NoteDialog, NoteDetailDialog
from src.config import t, TRANSLATIONS


class MainWindow(QMainWindow):
    # Pagination constants
    PAGE_SIZE = 20

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("./assets/logo.ico"))
        self.db = DatabaseManager()
        self.current_lang = "en"
        self.setWindowTitle(self.t("app_title"))
        self.resize(900, 600)

        # Pagination state
        self._current_offset = 0
        self._current_search = None   # None means "show all"
        self._total_notes = 0

        self.create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar layout
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton(self.t("add_note"))
        self.edit_btn = QPushButton(self.t("edit"))
        self.delete_btn = QPushButton(self.t("delete"))
        self.detail_btn = QPushButton(self.t("detail"))
        self.refresh_btn = QPushButton(self.t("refresh"))
        self.exit_btn = QPushButton(self.t("exit"))

        self.add_btn.clicked.connect(self.add_note)
        self.edit_btn.clicked.connect(self.edit_note)
        self.delete_btn.clicked.connect(self.delete_note)
        self.detail_btn.clicked.connect(self.view_detail)
        self.refresh_btn.clicked.connect(lambda: self.display_notes())
        self.exit_btn.clicked.connect(self.close)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.detail_btn)
        button_layout.addStretch()

        # Language Selector
        self.lang_selector = QComboBox()
        self.lang_selector.addItem("English", "en")
        self.lang_selector.addItem("Indonesia", "id")
        self.lang_selector.currentIndexChanged.connect(self.change_language)
        button_layout.addWidget(self.lang_selector)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.exit_btn)

        main_layout.addLayout(button_layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_label = QLabel(self.t("search"))
        self.search_input = QLineEdit_if_used = None
        # Use QLineEdit
        from PySide6.QtWidgets import QLineEdit
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.search_input.returnPressed.connect(self.perform_search)

        self.search_btn = QPushButton(
            self.t("search_btn")
            if "search_btn" in TRANSLATIONS[self.current_lang]
            else self.t("search").replace(":", "")
        )
        self.search_btn.clicked.connect(self.perform_search)
        self.clear_search_btn = QPushButton(self.t("clear"))
        self.clear_search_btn.clicked.connect(self.clear_search)

        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)

        main_layout.addLayout(search_layout)

        # Table widget
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.retranslate_table_headers()
        self.tableWidget.setColumnHidden(0, True)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.doubleClicked.connect(self.view_detail)

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        main_layout.addWidget(self.tableWidget)

        # Pagination footer
        pagination_layout = QHBoxLayout()

        self.notes_status_label = QLabel("")
        self.notes_status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.notes_status_label.setStyleSheet("color: gray; font-size: 11px;")

        self.load_more_btn = QPushButton("⬇  Load More")
        self.load_more_btn.setFixedWidth(130)
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.clicked.connect(self.load_more_notes)

        pagination_layout.addWidget(self.notes_status_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.load_more_btn)

        main_layout.addLayout(pagination_layout)

        self.display_notes()

    def t(self, key):
        return t(self.current_lang, key)

    def change_language(self, index):
        self.current_lang = self.lang_selector.itemData(index)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(self.t("app_title"))
        self.add_btn.setText(self.t("add_note"))
        self.edit_btn.setText(self.t("edit"))
        self.delete_btn.setText(self.t("delete"))
        self.detail_btn.setText(self.t("detail"))
        self.refresh_btn.setText(self.t("refresh"))
        self.exit_btn.setText(self.t("exit"))
        self.search_label.setText(self.t("search"))
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.search_btn.setText(self.t("search").replace(":", ""))
        self.clear_search_btn.setText(self.t("clear"))

        self.retranslate_table_headers()
        self.create_menu_bar()  # Recreate menu bar to update labels
        self.display_notes(reset=True)  # Refresh table tooltips

    def retranslate_table_headers(self):
        self.tableWidget.setHorizontalHeaderLabels(
            [
                self.t("id"),
                self.t("title"),
                self.t("note"),
                self.t("source"),
                self.t("date_time"),
            ]
        )

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

    def create_menu_bar(self):
        self.menuBar().clear()
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu(self.t("file"))
        about_menu = menu_bar.addMenu(self.t("about"))

        about_action = QAction(self.t("about"), self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)

        export_action = QAction(self.t("export_csv"), self)
        export_action.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_action)

        backup_action = QAction(self.t("backup_db"), self)
        backup_action.triggered.connect(self.backup_notes)
        file_menu.addAction(backup_action)

        file_menu.addSeparator()

        exit_action = QAction(self.t("exit"), self)
        exit_action.setShortcut("Ctrl+Q")  # Add keyboard shortcut for exit
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_about(self):
        about_dialog = QMessageBox()
        about_dialog.setIcon(QMessageBox.Information)
        about_dialog.setWindowTitle(self.t("about"))
        about_dialog.setText(self.t("about_text"))
        about_dialog.setInformativeText(self.t("about_info"))
        about_dialog.setStandardButtons(QMessageBox.Close)
        about_dialog.exec()

    def display_notes(self, reset=True):
        """Load the first page of notes (or reset to first page)."""
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

    def _append_notes_to_table(self, notes):
        """Append a list of note rows to the table without clearing it."""
        start_row = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(start_row + len(notes))

        for i, note in enumerate(notes):
            row_index = start_row + i
            # note = (id, title, catatan_html, sumber, created_at)

            # ID (hidden)
            self.tableWidget.setItem(row_index, 0, QTableWidgetItem(str(note[0])))

            # Title
            self.tableWidget.setItem(row_index, 1, QTableWidgetItem(str(note[1])))

            # Catatan snippet – strip HTML for performance
            catatan_text = self.strip_html(str(note[2]))
            snippet = (
                (catatan_text[:100] + "...")
                if len(catatan_text) > 100
                else catatan_text
            )
            item_catatan = QTableWidgetItem(snippet)
            item_catatan.setToolTip(self.t("tooltip_detail"))
            item_catatan.setData(Qt.UserRole, note[2])
            self.tableWidget.setItem(row_index, 2, item_catatan)

            # Sumber
            self.tableWidget.setItem(
                row_index, 3, QTableWidgetItem(str(note[3]) if note[3] else "-")
            )

            # Date
            formatted_date = self.format_date(note[4])
            self.tableWidget.setItem(row_index, 4, QTableWidgetItem(formatted_date))

            self.tableWidget.setRowHeight(row_index, 35)

    def _update_pagination_ui(self):
        """Update the status label and Load More button visibility."""
        visible = self.tableWidget.rowCount()
        total = self._total_notes
        all_loaded = visible >= total

        self.notes_status_label.setText(
            f"Showing {visible} of {total} notes"
        )
        self.load_more_btn.setEnabled(not all_loaded)
        self.load_more_btn.setText(
            "✓ All loaded" if all_loaded else "⬇  Load More"
        )

    def load_more_notes(self):
        """Append the next page of notes to the table."""
        self.display_notes(reset=False)

    def strip_html(self, html_str):
        """Simple utility to strip HTML tags for text preview."""
        if not html_str:
            return ""
        # Remove tags and replace some entities
        clean = re.compile("<.*?>")
        text = re.sub(clean, "", html_str)
        return (
            text.replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )

    def perform_search(self):
        query = self.search_input.text().strip()
        self._current_search = query if query else None
        self.display_notes(reset=True)

    def add_note(self):
        dialog = NoteDialog(self, lang=self.current_lang)
        if dialog.exec():
            data = dialog.get_data()
            if (
                not data["title"].strip()
                or self.strip_html(data["catatan"]).strip() == ""
            ):
                QMessageBox.warning(self, self.t("warning"), self.t("empty_warning"))
                return

            sumber = data["sumber"].strip() or None
            self.db.add_note(data["title"], data["catatan"], sumber)
            self.display_notes()

    def edit_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.t("warning"), self.t("select_edit_warning"))
            return

        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).text()
        # Retrieve full HTML from UserRole data
        catatan_html = self.tableWidget.item(selected_row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(selected_row, 3).text()
        if sumber == "-":
            sumber = ""

        dialog = NoteDialog(
            self, (note_id, title, catatan_html, sumber), lang=self.current_lang
        )
        if dialog.exec():
            data = dialog.get_data()
            if (
                not data["title"].strip()
                or self.strip_html(data["catatan"]).strip() == ""
            ):
                QMessageBox.warning(self, self.t("warning"), self.t("empty_warning"))
                return

            sumber = data["sumber"].strip() or None
            self.db.update_note(note_id, data["title"], data["catatan"], sumber)
            self.display_notes()

    def view_detail(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            return

        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).text()
        catatan_html = self.tableWidget.item(selected_row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(selected_row, 3).text()
        created_at = self.tableWidget.item(selected_row, 4).text()

        dialog = NoteDetailDialog(
            self,
            (note_id, title, catatan_html, sumber, created_at),
            lang=self.current_lang,
        )
        dialog.exec()

    def delete_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self, self.t("warning"), self.t("select_delete_warning")
            )
            return

        note_id = int(self.tableWidget.item(selected_row, 0).text())
        reply = QMessageBox.question(
            self,
            self.t("confirm"),
            self.t("delete_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.db.delete_note(note_id)
            self.display_notes()

    def format_date(self, date_str):
        """Format date string to %d/%m/%Y %H:%M:%S format"""
        if not date_str:
            return ""
        try:
            # Parse the date from database format (YYYY-MM-DD HH:MM:SS)
            dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
            # Return formatted date
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            # If parsing fails, return the original string
            return str(date_str)

    def clear_search(self):
        self.search_input.clear()
        self._current_search = None
        self.display_notes(reset=True)

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_csv"), "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        if not file_path.endswith(".csv"):
            file_path += ".csv"

        try:
            notes = self.db.get_all_notes()
            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["ID", "Judul", "Catatan", "Sumber", "Dibuat Pada"])

                # Security: Sanitize for CSV Formula Injection
                sanitized_notes = []
                for n in notes:
                    row = list(n)
                    for i in range(len(row)):
                        val = str(row[i])
                        if val.startswith(("=", "+", "-", "@")):
                            row[i] = "'" + val  # Prefix with single quote to escape
                    sanitized_notes.append(row)

                writer.writerows(sanitized_notes)
            QMessageBox.information(
                self, self.t("success"), self.t("export_success").format(file_path)
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengekspor catatan: {str(e)}")

    def backup_notes(self):
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
                    self, self.t("success"), self.t("backup_success").format(file_path)
                )
            else:
                QMessageBox.warning(self, self.t("warning"), self.t("db_not_found"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mem-backup database: {str(e)}")
