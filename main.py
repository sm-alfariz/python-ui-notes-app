import sys
import csv
import shutil
import os
import re
import configparser
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                               QTableWidgetItem, QVBoxLayout, QWidget, QMenu,
                               QPushButton, QHBoxLayout, QDialog, QFormLayout,
                               QLineEdit, QTextEdit, QMessageBox, QHeaderView,
                               QFileDialog, QLabel, QComboBox)
from PySide6.QtGui import (QAction, QImage, QIcon)
from PySide6.QtCore import Qt, QBuffer, QByteArray, QIODevice
from database import DatabaseManager

def load_translations():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'language.ini')
    
    # Default fallback translations if file is missing or keys are missing
    default_translations = {
        'en': {
            'app_title': "CS | Note Everything",
            'add_note': "Add Note",
            'edit': "Edit",
            'delete': "Delete",
            'detail': "Detail",
            'refresh': "Refresh",
            'exit': "Exit",
            'search': "Search:",
            'search_placeholder': "Search title, content, or source...",
            'clear': "Clear",
            'id': "ID",
            'title': "Title",
            'note': "Note",
            'source': "Source",
            'date_time': "Date/Time",
            'file': "&File",
            'about': "&About",
            'export_csv': "Export notes to CSV",
            'backup_db': "Backup Database",
            'warning': "Warning",
            'confirm': "Confirmation",
            'delete_confirm': "Are you sure you want to delete this note?",
            'empty_warning': "Title and Note cannot be empty!",
            'select_edit_warning': "Select a note to edit!",
            'select_delete_warning': "Select a note to delete!",
            'success': "Success",
            'export_success': "Notes successfully exported to {}",
            'backup_success': "Database successfully backed up to {}",
            'db_not_found': "Database file not found.",
            'save': "Save",
            'cancel': "Cancel",
            'close': "Close",
            'created_at': "Created At:",
            'judul_label': "Title:",
            'catatan_label': "Note:",
            'sumber_label': "Source:",
            'about_text': "<u>CS | Note Everything</u>",
            'about_info': "is Simple note with PyQt6 and Sqlite3",
            'tooltip_detail': "Double click or click 'Detail' to see full format",
            'save_csv': "Save as CSV"
        }
    }
    
    if not os.path.exists(config_path):
        return default_translations
        
    try:
        config.read(config_path, encoding='utf-8')
        translations = {}
        for section in config.sections():
            translations[section] = dict(config.items(section))
        return translations if translations else default_translations
    except Exception:
        return default_translations

TRANSLATIONS = load_translations()
class CustomTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        """
        Override default paste behavior to handle images from clipboard.
        """
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                # Convert image to base64-encoded PNG for embedding
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                base64_data = ba.toBase64().data().decode()

                # Create HTML <img> tag with embedded base64 PNG
                html_img = f'<img src="data:image/png;base64,{base64_data}">'
                self.textCursor().insertHtml(html_img)
                return  # Skip default paste
        # Fallback to default behavior for text/other formats
        super().insertFromMimeData(source)

class NoteDialog(QDialog):
    def __init__(self, parent=None, note_data=None, lang='en'):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(self.t("add_note") if note_data is None else self.t("edit"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QFormLayout(self)
        
        self.title_input = QLineEdit()
        self.catatan_input = CustomTextEdit()
        self.catatan_input.setAcceptRichText(True)  # Enable HTML support
        self.sumber_input = QLineEdit()
        
        if note_data:
            self.title_input.setText(note_data[1] if note_data[1] else "")
            # note_data[2] is the HTML content
            self.catatan_input.setHtml(note_data[2])
            self.sumber_input.setText(note_data[3] if note_data[3] else "")
            
        layout.addRow(self.t("judul_label"), self.title_input)
        layout.addRow(self.t("catatan_label"), self.catatan_input)
        layout.addRow(self.t("sumber_label"), self.sumber_input)
        
        buttons = QHBoxLayout()
        self.save_button = QPushButton(self.t("save"))
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(self.t("cancel"))
        self.cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)
        layout.addRow(buttons)

    def t(self, key):
        return TRANSLATIONS[self.lang].get(key, key)

    def get_data(self):
        return {
            "title": self.title_input.text(),
            "catatan": self.catatan_input.toHtml(),  # Get HTML content
            "sumber": self.sumber_input.text()
        }

class NoteDetailDialog(QDialog):
    def __init__(self, parent=None, note_data=None, lang='en'):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(self.t("detail"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        
        layout = QVBoxLayout(self)
        
        # Details section
        info_layout = QFormLayout()
        
        created_at = note_data[4] if note_data and len(note_data) > 4 else "-"
        created_field = QLineEdit(str(created_at))
        created_field.setReadOnly(True)
        info_layout.addRow(self.t("created_at"), created_field)
        
        title_text = QLineEdit(note_data[1] if note_data and note_data[1] else "-")
        title_text.setReadOnly(True)
        info_layout.addRow(self.t("judul_label"), title_text)
        
        sumber_text = QLineEdit(note_data[3] if note_data and note_data[3] else "-")
        sumber_text.setReadOnly(True)
        info_layout.addRow(self.t("sumber_label"), sumber_text)
        
        layout.addLayout(info_layout)
        
        # Catatan content
        label = QLabel(self.t("catatan_label"))
        label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(label)
        
        self.catatan_display = QTextEdit()
        self.catatan_display.setHtml(note_data[2] if note_data else "")
        self.catatan_display.setReadOnly(True)
        layout.addWidget(self.catatan_display)
        
        # Close button
        close_button = QPushButton(self.t("close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def t(self, key):
        return TRANSLATIONS[self.lang].get(key, key)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('./assets/logo.ico'))
        self.db = DatabaseManager()
        self.current_lang = 'en'
        self.setWindowTitle(self.t("app_title"))
        self.resize(900, 600)
    
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
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.search_btn = QPushButton(self.t("search_btn") if "search_btn" in TRANSLATIONS[self.current_lang] else self.t("search").replace(":", ""))
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
        
        self.display_notes()

    def t(self, key):
        return TRANSLATIONS[self.current_lang].get(key, key)

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
        self.create_menu_bar() # Recreate menu bar to update labels
        self.display_notes() # Refresh table tooltips

    def retranslate_table_headers(self):
        self.tableWidget.setHorizontalHeaderLabels([
            self.t("id"), self.t("title"), self.t("note"), self.t("source"), self.t("date_time")
        ])
        
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
        exit_action.setShortcut("Ctrl+Q") # Add keyboard shortcut for exit
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
        
    def display_notes(self, notes=None):
        """Unified method to display notes in the table."""
        if notes is None:
            notes = self.db.get_all_notes()
            
        self.tableWidget.setRowCount(0)
        self.tableWidget.setRowCount(len(notes))
        
        for row_index, note in enumerate(notes):
            # note = (id, title, catatan_html, sumber, created_at)
            
            # ID (hidden)
            self.tableWidget.setItem(row_index, 0, QTableWidgetItem(str(note[0])))
            
            # Title
            self.tableWidget.setItem(row_index, 1, QTableWidgetItem(str(note[1])))
            
            # Catatan snippet (Optimized: No QTextEdit in main list)
            # We strip HTML tags for the preview snippet to improve performance
            catatan_text = self.strip_html(str(note[2]))
            snippet = (catatan_text[:100] + "...") if len(catatan_text) > 100 else catatan_text
            item_catatan = QTableWidgetItem(snippet)
            item_catatan.setToolTip(self.t("tooltip_detail"))
            # Store the original HTML in the item data for retrieval if needed
            item_catatan.setData(Qt.UserRole, note[2])
            self.tableWidget.setItem(row_index, 2, item_catatan)
            
            # Sumber
            self.tableWidget.setItem(row_index, 3, QTableWidgetItem(str(note[3]) if note[3] else "-"))
            
            # Date
            formatted_date = self.format_date(note[4])
            self.tableWidget.setItem(row_index, 4, QTableWidgetItem(formatted_date))
            
            self.tableWidget.setRowHeight(row_index, 35)

    def strip_html(self, html_str):
        """Simple utility to strip HTML tags for text preview."""
        if not html_str: return ""
        # Remove tags and replace some entities
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_str)
        return text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            self.display_notes()
            return
        notes = self.db.search_notes(query)
        self.display_notes(notes)

    def add_note(self):
        dialog = NoteDialog(self, lang=self.current_lang)
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"].strip() or self.strip_html(data["catatan"]).strip() == "":
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
        if sumber == "-": sumber = ""
        
        dialog = NoteDialog(self, (note_id, title, catatan_html, sumber), lang=self.current_lang)
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"].strip() or self.strip_html(data["catatan"]).strip() == "":
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
        
        dialog = NoteDetailDialog(self, (note_id, title, catatan_html, sumber, created_at), lang=self.current_lang)
        dialog.exec()

    def delete_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, self.t("warning"), self.t("select_delete_warning"))
            return
            
        note_id = int(self.tableWidget.item(selected_row, 0).text())
        reply = QMessageBox.question(self, self.t("confirm"), self.t("delete_confirm"),
                                   QMessageBox.Yes | QMessageBox.No)
        
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
        self.display_notes()

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_csv"), "", "CSV Files (*.csv)"
        )
        if not file_path: return
            
        if not file_path.endswith('.csv'):
            file_path += '.csv'
            
        try:
            notes = self.db.get_all_notes()
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["ID", "Judul", "Catatan", "Sumber", "Dibuat Pada"])
                
                # Security: Sanitize for CSV Formula Injection
                sanitized_notes = []
                for n in notes:
                    row = list(n)
                    for i in range(len(row)):
                        val = str(row[i])
                        if val.startswith(('=', '+', '-', '@')):
                            row[i] = "'" + val  # Prefix with single quote to escape
                    sanitized_notes.append(row)
                
                writer.writerows(sanitized_notes)
            QMessageBox.information(self, self.t("success"), self.t("export_success").format(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengekspor catatan: {str(e)}")

    def backup_notes(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("backup_db"), "notes_backup.db", "SQLite Database (*.db)"
        )
        if not file_path: return
            
        try:
            db_source = self.db.db_name
            if os.path.exists(db_source):
                shutil.copy2(db_source, file_path)
                QMessageBox.information(self, self.t("success"), self.t("backup_success").format(file_path))
            else:
                QMessageBox.warning(self, self.t("warning"), self.t("db_not_found"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mem-backup database: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
