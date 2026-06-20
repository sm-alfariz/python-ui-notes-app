import csv
import shutil
import os
import re
from datetime import datetime
from pathlib import Path
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
    QLineEdit,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QMenu,
)
from PySide6.QtGui import QAction, QIcon, QDesktopServices
from PySide6.QtCore import Qt, QSettings, QUrl
from database import DatabaseManager
from src.dialogs.note_dialogs import NoteDialog, NoteDetailDialog
from src.config import t, TRANSLATIONS


class HTMLDelegate(QStyledItemDelegate):
    """Delegate to render HTML content in table cells using QTextDocument."""

    def paint(self, painter, option, index):
        from PySide6.QtGui import QTextDocument

        # Prefer UserRole+1 (snippet HTML), fall back to display text
        html_content = index.data(Qt.UserRole + 1) or index.data(Qt.DisplayRole)

        if not html_content:
            super().paint(painter, option, index)
            return

        doc = QTextDocument()
        doc.setHtml(str(html_content))

        painter.save()

        # Draw selection highlight
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Render document clipped to cell
        painter.translate(option.rect.topLeft())
        clip = option.rect.translated(-option.rect.topLeft())
        painter.setClipRect(clip)
        doc.setTextWidth(clip.width())
        doc.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index):
        from PySide6.QtGui import QTextDocument

        html_content = index.data(Qt.UserRole + 1) or index.data(Qt.DisplayRole)
        if not html_content:
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setHtml(str(html_content))
        doc.setTextWidth(option.rect.width())
        return doc.size().toSize()


class MainWindow(QMainWindow):
    """Main application window for the note-taking application.

    Provides the primary user interface for managing notes, including
    creating, editing, deleting, searching, and viewing note details.
    Supports paginated note display, internationalization (i18n),
    theme switching, CSV export, and database backup functionality.

    Attributes:
        PAGE_SIZE (int): Number of notes displayed per page. Defaults to 20.
        db (DatabaseManager): Instance of the database manager for note operations.
        current_lang (str): Current language code (e.g., 'en', 'id').
        tableWidget (QTableWidget): The table widget displaying note entries.
        _current_offset (int): Current pagination offset for note loading.
        _current_search (str or None): Current search filter query, or None for all notes.
        _total_notes (int): Total number of notes matching the current filter.
        settings (QSettings): Persistent settings for theme and language preferences.
    """    
    # Pagination constants
    PAGE_SIZE = 20

    def __init__(self):
        super().__init__()
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"
        self.setWindowIcon(QIcon(str(icon_path)))
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
        # Load saved language from QSettings (if available)
        try:
            saved_lang = self.settings.value("language", "")
            if saved_lang:
                # Prevent triggering change_language before UI fully built
                self.lang_selector.blockSignals(True)
                for i in range(self.lang_selector.count()):
                    if self.lang_selector.itemData(i) == saved_lang:
                        self.lang_selector.setCurrentIndex(i)
                        break
                self.lang_selector.blockSignals(False)
        except Exception:
            pass
        button_layout.addWidget(self.lang_selector)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.exit_btn)

        main_layout.addLayout(button_layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_label = QLabel(self.t("search"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.search_input.returnPressed.connect(self.perform_search)

        self.search_btn = QPushButton(
            self.t("search").replace(":", "")
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
        self.tableWidget.setColumnCount(6)
        self.retranslate_table_headers()
        self.tableWidget.setColumnHidden(0, True)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.doubleClicked.connect(self.view_detail)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.show_context_menu)

        # Use HTML delegate for catatan column (col 2)
        self.tableWidget.setItemDelegateForColumn(2, HTMLDelegate(self.tableWidget))

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

        # Apply saved language now that UI widgets exist
        try:
            saved_lang = self.settings.value("language", "")
            if saved_lang:
                # update current_lang and retranslate UI
                self.current_lang = saved_lang
                self.retranslate_ui()
        except Exception:
            pass

        self.display_notes()

    def t(self, key):
        return t(self.current_lang, key)

    def change_language(self, index):
        self.current_lang = self.lang_selector.itemData(index)
        # Only retranslate if UI widgets have been created
        try:
            if hasattr(self, "search_label"):
                self.retranslate_ui()
        except Exception:
            pass
        # Persist language selection
        try:
            self.settings.setValue("language", self.current_lang)
        except Exception:
            pass

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
                self.t("lock"),
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

        view_menu = menu_bar.addMenu(self.t("view"))
        theme_menu = view_menu.addMenu(self.t("theme"))
        
        from PySide6.QtGui import QActionGroup
        import sys
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        # QSettings to persist theme selection
        self.settings = QSettings("CatatSegala", "python-ui-notes-app")
        saved_theme = self.settings.value("theme", "")
        
        # Handle PyInstaller compilation with _MEIPASS
        # __file__ is in src/ui/ so we need to go up 3 levels to reach the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        base_dir = getattr(sys, '_MEIPASS', project_root)
        source_themes_dir = os.path.join(base_dir, "src", "themes")
        
        target_themes_dir = os.path.join(".catat-segala", "themes")
        if not os.path.exists(target_themes_dir):
            try:
                os.makedirs(target_themes_dir)
            except Exception:
                pass
                
        # Copy built-in themes to .catat-segala/themes if they are not there
        if os.path.exists(source_themes_dir) and os.path.exists(target_themes_dir):
            for file_name in os.listdir(source_themes_dir):
                if file_name.endswith(".qss"):
                    src_file = os.path.join(source_themes_dir, file_name)
                    tgt_file = os.path.join(target_themes_dir, file_name)
                    if not os.path.exists(tgt_file):
                        try:
                            shutil.copy2(src_file, tgt_file)
                        except Exception:
                            pass
                            
        themes_dir = target_themes_dir
        
        if os.path.exists(themes_dir):
            for file_name in sorted(os.listdir(themes_dir)):
                if file_name.endswith(".qss"):
                    theme_name = file_name.replace(".qss", "").replace("_", " ").title()
                    action = QAction(theme_name, self)
                    action.setCheckable(True)
                    qss_path = os.path.join(themes_dir, file_name)
                    action.setData(qss_path)
                    action.triggered.connect(self.change_theme)
                    self.theme_group.addAction(action)
                    theme_menu.addAction(action)
                    # If this theme matches saved setting, check and apply it
                    try:
                        if saved_theme and os.path.basename(qss_path) == saved_theme:
                            action.setChecked(True)
                            from PySide6.QtWidgets import QApplication
                            app = QApplication.instance()
                            if app and os.path.exists(qss_path):
                                with open(qss_path, "r", encoding="utf-8") as f:
                                    app.setStyleSheet(f.read())
                    except Exception:
                        pass

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

        restore_action = QAction(self.t("restore_db"), self)
        restore_action.triggered.connect(self.restore_database)
        file_menu.addAction(restore_action)

        file_menu.addSeparator()

        exit_action = QAction(self.t("exit"), self)
        exit_action.setShortcut("Ctrl+Q")  # Add keyboard shortcut for exit
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def change_theme(self):
        action = self.sender()
        if action:
            qss_file = action.data()
            try:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app and qss_file and os.path.exists(qss_file):
                    with open(qss_file, "r", encoding="utf-8") as f:
                        app.setStyleSheet(f.read())
                    # Persist selected theme filename
                    try:
                        self.settings.setValue("theme", os.path.basename(qss_file))
                    except Exception:
                        pass
                elif app:
                    app.setStyleSheet("")
            except Exception as e:
                print(f"Failed to load theme: {e}")

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
            # note = (id, title, catatan_html, sumber, created_at, is_locked)
            is_locked = note[5] if len(note) > 5 else 0

            # ID (hidden)
            self.tableWidget.setItem(row_index, 0, QTableWidgetItem(str(note[0])))

            # Title — always show real title
            item_title = QTableWidgetItem(str(note[1]))
            item_title.setData(Qt.UserRole, note[1])
            self.tableWidget.setItem(row_index, 1, item_title)

            # Catatan (Note) — hide if locked
            if is_locked:
                item_catatan = QTableWidgetItem("🔒")
                item_catatan.setData(Qt.UserRole, note[2])
                big_font = item_catatan.font()
                big_font.setPointSize(16)
                item_catatan.setFont(big_font)
                item_catatan.setTextAlignment(Qt.AlignCenter)
            else:
                catatan_text = self.strip_html(str(note[2]))
                words = catatan_text.split()
                if len(words) > 3:
                    snippet = " ".join(words[:3]) + "..."
                else:
                    snippet = catatan_text
                html_snippet = self._build_snippet_html(note[2], snippet)
                item_catatan = QTableWidgetItem()
                item_catatan.setToolTip(self.t("tooltip_detail"))
                item_catatan.setData(Qt.DisplayRole, snippet)
                item_catatan.setData(Qt.UserRole, note[2])  # original full HTML for edit/detail
                item_catatan.setData(Qt.UserRole + 1, html_snippet)  # formatted snippet for display
            self.tableWidget.setItem(row_index, 2, item_catatan)

            # Sumber — hide if locked
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

            # Lock indicator
            lock_text = "🔒" if is_locked else "🔓"
            item_lock = QTableWidgetItem(lock_text)
            lock_font = item_lock.font()
            lock_font.setPointSize(16)
            item_lock.setFont(lock_font)
            item_lock.setTextAlignment(Qt.AlignCenter)
            item_lock.setData(Qt.UserRole, is_locked)
            self.tableWidget.setItem(row_index, 4, item_lock)

            # Date (column shifted to 5)
            formatted_date = self.format_date(note[4])
            self.tableWidget.setItem(row_index, 5, QTableWidgetItem(formatted_date))

            row_h = 45 if is_locked else 35
            self.tableWidget.setRowHeight(row_index, row_h)

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
        # Remove <style> and <script> blocks first (content + tags)
        text = re.sub(r"<style[^>]*>.*?</style>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove remaining tags and replace some entities
        clean = re.compile("<.*?>")
        text = re.sub(clean, "", text)
        return (
            text.replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )

    def _build_snippet_html(self, original_html, plain_snippet):
        """Build a safe HTML snippet for table display.

        Takes the first ~150 chars of the original HTML after removing
        <style>, <script>, <head>, <html>, <body> wrappers, then lets
        QTextDocument render it with inline formatting preserved.
        """
        if not original_html:
            return plain_snippet

        import re as _re

        try:
            # Remove <style>, <script>, <head> blocks entirely
            cleaned = _re.sub(r"<(style|script|head)[^>]*>.*?</\1>", " ", original_html, flags=_re.DOTALL | _re.IGNORECASE)
            # Remove comments
            cleaned = _re.sub(r"<!--.*?-->", " ", cleaned, flags=_re.DOTALL)
            # Remove wrapper tags
            cleaned = _re.sub(r"</?(html|body|meta|title|div|section|article|header|footer)[^>]*/?>", " ", cleaned, flags=_re.IGNORECASE)
            # Collapse whitespace
            cleaned = _re.sub(r"\s+", " ", cleaned).strip()

            # Find where the first word of our snippet appears in the plain text
            words = plain_snippet.rstrip(".").split()
            if not words:
                return plain_snippet

            # Find the plain-text offset of our first word
            plain = _re.sub(r"<[^>]+>", "", cleaned)
            plain = _re.sub(r"\s+", " ", plain).strip()
            idx = plain.find(words[0])
            if idx < 0:
                return plain_snippet

            # Walk HTML to find the HTML position corresponding to plain-text idx
            pos = 0
            in_tag = False
            html_offset = 0
            for i, ch in enumerate(cleaned):
                if ch == "<":
                    in_tag = True
                    continue
                if ch == ">":
                    in_tag = False
                    html_offset = i + 1
                    continue
                if not in_tag:
                    if pos == idx:
                        # Back up to include any opening tags
                        search_back = cleaned[:i]
                        last_open = search_back.rfind("<")
                        start = last_open if last_open >= 0 and ">" not in cleaned[last_open:i] else i

                        # Extract enough HTML to cover ~3 words of plain text
                        # Count plain chars until we have enough
                        target = len(" ".join(words[:3])) + 5  # small margin
                        cp = 0
                        end = start
                        in_t = False
                        for j in range(start, len(cleaned)):
                            c = cleaned[j]
                            if c == "<":
                                in_t = True
                                continue
                            if c == ">":
                                in_t = False
                                continue
                            if not in_t:
                                cp += 1
                                if cp >= target:
                                    end = j + 1
                                    # Include up to 2 closing tags right after
                                    rest = cleaned[j + 1:j + 40]
                                    for cm in _re.finditer(r"</(\w+)>", rest):
                                        end = cm.end() + j + 1
                                        break
                                    break

                        snippet = cleaned[start:end]
                        # Close any unclosed inline tags
                        for tag in _re.findall(r"<(b|i|u|strong|em)(?:\s[^>]*)?>", snippet, _re.IGNORECASE):
                            close_pattern = _re.compile(rf"</{tag}>", _re.IGNORECASE)
                            if not close_pattern.search(snippet):
                                snippet += f"</{tag}>"
                        return snippet
                    pos += 1

            return plain_snippet
        except Exception:
            return plain_snippet

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
            note_id = self.db.add_note(data["title"], data["catatan"], sumber, data.get("is_locked", 0))
            
            # Save attachments
            for att in data["attachments"]:
                self.db.add_attachment(note_id, att["name"], att["mime"], att["blob"])
                
            self.display_notes()

    def edit_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.t("warning"), self.t("select_edit_warning"))
            return

        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).data(Qt.UserRole)
        # Retrieve full HTML from UserRole data
        catatan_html = self.tableWidget.item(selected_row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(selected_row, 3).data(Qt.UserRole)
        is_locked = self.tableWidget.item(selected_row, 4).data(Qt.UserRole)

        dialog = NoteDialog(
            self, (note_id, title, catatan_html, sumber, None, is_locked), lang=self.current_lang
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
            self.db.update_note(note_id, data["title"], data["catatan"], sumber, data.get("is_locked", 0))
            
            # Sync attachments
            db_atts = self.db.get_attachments_by_note_id(note_id)
            db_att_ids = {att[0] for att in db_atts}
            current_att_ids = {att["id"] for att in data["attachments"] if att["id"] is not None}
            
            # Delete attachments that were in DB but are not in current_attachments anymore
            for att in db_atts:
                if att[0] not in current_att_ids:
                    self.db.delete_attachment(att[0])
            
            # Add new attachments (id is None)
            for att in data["attachments"]:
                if att["id"] is None:
                    self.db.add_attachment(note_id, att["name"], att["mime"], att["blob"])

            self.display_notes()

    def view_detail(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            return

        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).data(Qt.UserRole)
        catatan_html = self.tableWidget.item(selected_row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(selected_row, 3).data(Qt.UserRole)
        is_locked = self.tableWidget.item(selected_row, 4).data(Qt.UserRole)
        created_at = self.tableWidget.item(selected_row, 5).text()

        dialog = NoteDetailDialog(
            self,
            (note_id, title, catatan_html, sumber, created_at, is_locked),
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

    def show_context_menu(self, pos):
        """Show right-click context menu on the table with detail, edit, delete, and lock/unlock."""
        index = self.tableWidget.indexAt(pos)
        if not index.isValid():
            return

        # Select the row that was right-clicked
        self.tableWidget.selectRow(index.row())

        row = index.row()
        is_locked = self.tableWidget.item(row, 4).data(Qt.UserRole)

        style = self.style()
        menu = QMenu(self)

        # Detail action with built-in Qt icon
        detail_action = QAction(
            style.standardIcon(QStyle.SP_MessageBoxInformation), self.t("detail"), self
        )
        detail_action.triggered.connect(self.view_detail)
        menu.addAction(detail_action)

        # Edit action with built-in Qt icon
        edit_action = QAction(
            style.standardIcon(QStyle.SP_FileDialogInfoView), self.t("edit"), self
        )
        edit_action.triggered.connect(self.edit_note)
        menu.addAction(edit_action)

        # Delete action with built-in Qt icon
        delete_action = QAction(
            style.standardIcon(QStyle.SP_DialogDiscardButton), self.t("delete"), self
        )
        delete_action.triggered.connect(self.delete_note)
        menu.addAction(delete_action)

        menu.addSeparator()

        # Lock / Unlock toggle action with built-in Qt icon
        if is_locked:
            lock_label = TRANSLATIONS.get(self.current_lang, {}).get("unlock", "Unlock")
            lock_icon = style.standardIcon(QStyle.SP_DialogNoButton)
        else:
            lock_label = self.t("lock")
            lock_icon = style.standardIcon(QStyle.SP_DialogApplyButton)

        lock_action = QAction(lock_icon, lock_label, self)
        lock_action.triggered.connect(lambda: self.toggle_lock(row))
        menu.addAction(lock_action)

        menu.addSeparator()

        # Export as HTML action
        export_html_action = QAction(
            style.standardIcon(QStyle.SP_FileIcon), self.t("export_html"), self
        )
        export_html_action.triggered.connect(self.export_note_as_html)
        menu.addAction(export_html_action)

        # Export as PDF action
        export_pdf_action = QAction(
            style.standardIcon(QStyle.SP_FileDialogDetailedView), self.t("export_pdf"), self
        )
        export_pdf_action.triggered.connect(self.export_note_as_pdf)
        menu.addAction(export_pdf_action)

        menu.exec(self.tableWidget.viewport().mapToGlobal(pos))

    def toggle_lock(self, row):
        """Toggle the lock state of the note at the given row."""
        note_id = int(self.tableWidget.item(row, 0).text())
        title = self.tableWidget.item(row, 1).data(Qt.UserRole)
        catatan_html = self.tableWidget.item(row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(row, 3).data(Qt.UserRole)
        is_locked = self.tableWidget.item(row, 4).data(Qt.UserRole)

        new_locked = 0 if is_locked else 1
        self.db.update_note(note_id, title, catatan_html, sumber, new_locked)
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

    def _validate_sqlite_file(self, file_path):
        """Check if the given file is a valid SQLite database."""
        try:
            import sqlite3
            # Check file is not empty
            if os.path.getsize(file_path) == 0:
                return False
            # Check SQLite magic header (first 16 bytes = "SQLite format 3\000")
            with open(file_path, "rb") as f:
                header = f.read(16)
            if header != b"SQLite format 3\x00":
                return False
            # Verify the file can be opened and queried
            conn = sqlite3.connect(f"file:{file_path}?mode=ro", uri=True)
            conn.execute("SELECT count(*) FROM sqlite_master")
            conn.close()
            return True
        except (sqlite3.DatabaseError, Exception):
            return False

    def restore_database(self):
        """Restore the database from a user-selected .db file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.t("restore_db"), "", "SQLite Database (*.db)"
        )
        if not file_path:
            return

        # Validate the selected file is a valid SQLite database
        if not self._validate_sqlite_file(file_path):
            QMessageBox.warning(
                self, self.t("warning"), self.t("restore_invalid_db")
            )
            return

        # Show confirmation warning
        reply = QMessageBox.warning(
            self,
            self.t("warning"),
            self.t("restore_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            db_target = self.db.db_name

            # Copy the selected file over the current database
            shutil.copy2(file_path, db_target)

            # Reinitialize DatabaseManager so it picks up the new file
            self.db = DatabaseManager()

            # Reset pagination and search state, then refresh the table
            self._current_offset = 0
            self._current_search = None
            self.search_input.clear()
            self.display_notes(reset=True)

            QMessageBox.information(
                self, self.t("success"), self.t("restore_success").format(file_path)
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", self.t("restore_error").format(str(e))
            )

    def _get_selected_note_data(self):
        """Helper to retrieve note data from the selected table row."""
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            return None
        return {
            "title": self.tableWidget.item(selected_row, 1).data(Qt.UserRole),
            "catatan_html": self.tableWidget.item(selected_row, 2).data(Qt.UserRole),
            "sumber": self.tableWidget.item(selected_row, 3).data(Qt.UserRole),
            "created_at": self.tableWidget.item(selected_row, 5).text(),
        }

    def export_note_as_html(self):
        """Export the selected note as a standalone HTML file."""
        data = self._get_selected_note_data()
        if not data:
            return

        title = data["title"] or "note"
        sumber = data["sumber"] or "-"
        catatan_html = data["catatan_html"] or ""
        created_at = data["created_at"] or "-"

        full_html = f"""<!DOCTYPE html>
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

        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_html"), f"{title}.html", "HTML Files (*.html)"
        )
        if not file_path:
            return
        if not file_path.endswith(".html"):
            file_path += ".html"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_html)
            QMessageBox.information(
                self, self.t("success"),
                self.t("export_html_success").format(file_path),
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.critical(
                self, "Error", self.t("export_html_error").format(str(e))
            )

    def export_note_as_pdf(self):
        """Export the selected note as a PDF file using QTextDocument + QPrinter."""
        data = self._get_selected_note_data()
        if not data:
            return

        title = data["title"] or "note"
        sumber = data["sumber"] or "-"
        catatan_html = data["catatan_html"] or ""
        created_at = data["created_at"] or "-"

        # Strip inline font-size from note content to avoid scaling issues
        catatan_clean = re.sub(r'font-size:\s*\d+[^;"]*;', '', catatan_html)

        html_content = f"""
        <h1>{title}</h1>
        <p><strong>Source:</strong> {sumber}</p>
        <p><strong>Date:</strong> {created_at}</p>
        <hr>
        {catatan_clean}
        """

        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_pdf"), f"{title}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        if not file_path.endswith(".pdf"):
            file_path += ".pdf"

        try:
            from PySide6.QtGui import QTextDocument, QFont
            from PySide6.QtPrintSupport import QPrinter

            doc = QTextDocument()
            doc.setDefaultFont(QFont("sans-serif", 11))
            doc.setHtml(html_content)

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

            doc.print_(printer)

            QMessageBox.information(
                self, self.t("success"),
                self.t("export_pdf_success").format(file_path),
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.critical(
                self, "Error", self.t("export_pdf_error").format(str(e))
            )
