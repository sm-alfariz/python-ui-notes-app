import sys
import csv
import shutil
import os
import re
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                               QTableWidgetItem, QVBoxLayout, QWidget, QMenu,
                               QPushButton, QHBoxLayout, QDialog, QFormLayout,
                               QLineEdit, QTextEdit, QMessageBox, QHeaderView,
                               QFileDialog, QLabel)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt
from database import DatabaseManager

class NoteDialog(QDialog):
    def __init__(self, parent=None, note_data=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Catatan" if note_data is None else "Ubah Catatan")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QFormLayout(self)
        
        self.title_input = QLineEdit()
        self.catatan_input = QTextEdit()
        self.catatan_input.setAcceptRichText(True)  # Enable HTML support
        self.sumber_input = QLineEdit()
        
        if note_data:
            self.title_input.setText(note_data[1] if note_data[1] else "")
            # note_data[2] is the HTML content
            self.catatan_input.setHtml(note_data[2])
            self.sumber_input.setText(note_data[3] if note_data[3] else "")
            
        layout.addRow("Judul:", self.title_input)
        layout.addRow("Catatan:", self.catatan_input)
        layout.addRow("Sumber:", self.sumber_input)
        
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Simpan")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Batal")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "title": self.title_input.text(),
            "catatan": self.catatan_input.toHtml(),  # Get HTML content
            "sumber": self.sumber_input.text()
        }

class NoteDetailDialog(QDialog):
    def __init__(self, parent=None, note_data=None):
        super().__init__(parent)
        self.setWindowTitle("Detail Catatan")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        
        layout = QVBoxLayout(self)
        
        # Details section
        info_layout = QFormLayout()
        
        created_at = note_data[4] if note_data and len(note_data) > 4 else "-"
        created_field = QLineEdit(str(created_at))
        created_field.setReadOnly(True)
        info_layout.addRow("Dibuat Pada:", created_field)
        
        title_text = QLineEdit(note_data[1] if note_data and note_data[1] else "-")
        title_text.setReadOnly(True)
        info_layout.addRow("Judul:", title_text)
        
        sumber_text = QLineEdit(note_data[3] if note_data and note_data[3] else "-")
        sumber_text.setReadOnly(True)
        info_layout.addRow("Sumber:", sumber_text)
        
        layout.addLayout(info_layout)
        
        # Catatan content
        label = QLabel("Catatan:")
        label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(label)
        
        self.catatan_display = QTextEdit()
        self.catatan_display.setHtml(note_data[2] if note_data else "")
        self.catatan_display.setReadOnly(True)
        layout.addWidget(self.catatan_display)
        
        # Close button
        close_button = QPushButton("Tutup")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setWindowTitle("CS | Catat Segala")
        self.resize(900, 600)
    
        self.create_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar layout
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Tambah Catatan")
        self.edit_btn = QPushButton("Ubah")
        self.delete_btn = QPushButton("Hapus")
        self.detail_btn = QPushButton("Detail")
        self.refresh_btn = QPushButton("Refresh")
        self.exit_btn = QPushButton("Keluar")
        
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
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.exit_btn)
        
        main_layout.addLayout(button_layout)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Cari:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari judul, isi, atau sumber...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.search_btn = QPushButton("Cari")
        self.search_btn.clicked.connect(self.perform_search)
        self.clear_search_btn = QPushButton("Clear")
        self.clear_search_btn.clicked.connect(self.clear_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)
        
        main_layout.addLayout(search_layout)

        # Table widget
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(["ID", "Judul", "Catatan", "Sumber", "Tgl/Jam"])
        self.tableWidget.setColumnHidden(0, True)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.doubleClicked.connect(self.view_detail)
        
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        main_layout.addWidget(self.tableWidget)
        
        self.display_notes()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        about_menu = menu_bar.addMenu("&About")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)
        
        export_action = QAction("&Export notes to CSV", self)
        export_action.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_action)
        
        backup_action = QAction("&Backup Database", self)
        backup_action.triggered.connect(self.backup_notes)
        file_menu.addAction(backup_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q") # Add keyboard shortcut for exit
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_about(self):
        about_dialog = QMessageBox()
        about_dialog.setIcon(QMessageBox.Information)
        about_dialog.setText("CS | Catat Segala")
        about_dialog.setInformativeText("is Simple note with PyQt6 and Sqlite3 this is open source go to github repository <a href='https://github.com/fendoz/catat-segala'> github link</a> for the code")
        about_dialog.setStandardButtons(QMessageBox.Close)
        about_dialog.exec_()
        
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
            item_catatan.setToolTip("Klik 2x atau klik 'Detail' untuk melihat format lengkap")
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
        dialog = NoteDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"].strip() or self.strip_html(data["catatan"]).strip() == "":
                QMessageBox.warning(self, "Peringatan", "Judul dan Catatan tidak boleh kosong!")
                return
                
            sumber = data["sumber"].strip() or None
            self.db.add_note(data["title"], data["catatan"], sumber)
            self.display_notes()

    def edit_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih catatan yang ingin diubah!")
            return
            
        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).text()
        # Retrieve full HTML from UserRole data
        catatan_html = self.tableWidget.item(selected_row, 2).data(Qt.UserRole)
        sumber = self.tableWidget.item(selected_row, 3).text()
        if sumber == "-": sumber = ""
        
        dialog = NoteDialog(self, (note_id, title, catatan_html, sumber))
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"].strip() or self.strip_html(data["catatan"]).strip() == "":
                QMessageBox.warning(self, "Peringatan", "Judul dan Catatan tidak boleh kosong!")
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
        
        dialog = NoteDetailDialog(self, (note_id, title, catatan_html, sumber, created_at))
        dialog.exec()

    def delete_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih catatan yang ingin dihapus!")
            return
            
        note_id = int(self.tableWidget.item(selected_row, 0).text())
        reply = QMessageBox.question(self, "Konfirmasi", "Apakah Anda yakin ingin menghapus catatan ini?",
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
            self, "Simpan sebagai CSV", "", "CSV Files (*.csv)"
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
            QMessageBox.information(self, "Sukses", f"Catatan berhasil diekspor ke {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengekspor catatan: {str(e)}")

    def backup_notes(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", "notes_backup.db", "SQLite Database (*.db)"
        )
        if not file_path: return
            
        try:
            db_source = self.db.db_name
            if os.path.exists(db_source):
                shutil.copy2(db_source, file_path)
                QMessageBox.information(self, "Sukses", f"Database berhasil di-backup ke {file_path}")
            else:
                QMessageBox.warning(self, "Peringatan", "File database tidak ditemukan.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mem-backup database: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
