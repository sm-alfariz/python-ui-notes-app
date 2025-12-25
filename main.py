import sys
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                               QTableWidgetItem, QVBoxLayout, QWidget, QMenu,
                               QPushButton, QHBoxLayout, QDialog, QFormLayout,
                               QLineEdit, QTextEdit, QMessageBox, QHeaderView)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from database import DatabaseManager

class NoteDialog(QDialog):
    def __init__(self, parent=None, note_data=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Catatan" if note_data is None else "Ubah Catatan")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QFormLayout(self)
        
        self.title_input = QLineEdit()
        self.catatan_input = QTextEdit()
        self.catatan_input.setAcceptRichText(True)  # Enable HTML support
        self.sumber_input = QLineEdit()
        
        if note_data:
            self.title_input.setText(note_data[1] if note_data[1] else "")
            self.catatan_input.setHtml(note_data[2])  # Use setHtml instead of setPlainText
            self.sumber_input.setText(note_data[3] if note_data[3] else "")
            
        layout.addRow("Judul:", self.title_input)
        layout.addRow("Catatan:", self.catatan_input)
        layout.addRow("Sumber:", self.sumber_input)
        
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Simpan")
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
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # ID and Created At info
        info_layout = QFormLayout()
        id_label = QLineEdit(str(note_data[0]) if note_data else "")
        id_label.setReadOnly(True)
        created_label = QLineEdit(str(note_data[4]) if note_data and len(note_data) > 4 else "")
        created_label.setReadOnly(True)
        
        info_layout.addRow("ID:", id_label)
        info_layout.addRow("Dibuat Pada:", created_label)
        layout.addLayout(info_layout)
        
        # Title
        title_layout = QFormLayout()
        title_text = QLineEdit(note_data[1] if note_data and note_data[1] else "-")
        title_text.setReadOnly(True)
        title_layout.addRow("Judul:", title_text)
        layout.addLayout(title_layout)
        
        # Sumber
        sumber_layout = QFormLayout()
        sumber_text = QLineEdit(note_data[3] if note_data and note_data[3] else "-")
        sumber_text.setReadOnly(True)
        sumber_layout.addRow("Sumber:", sumber_text)
        layout.addLayout(sumber_layout)
        
        # Catatan content
        layout.addWidget(QWidget())  # Spacer
        catatan_label = QWidget()
        catatan_label_layout = QVBoxLayout(catatan_label)
        catatan_label_layout.setContentsMargins(0, 0, 0, 0)
        from PySide6.QtWidgets import QLabel
        label = QLabel("Catatan:")
        label.setStyleSheet("font-weight: bold;")
        catatan_label_layout.addWidget(label)
        layout.addWidget(catatan_label)
        
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
        self.setGeometry(100, 100, 800, 500)
    
        self.create_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar layout for buttons
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
        self.refresh_btn.clicked.connect(self.load_notes)
        self.exit_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.detail_btn)
        button_layout.addWidget(self.exit_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(button_layout)
        
        # Search bar layout
        search_layout = QHBoxLayout()
        from PySide6.QtWidgets import QLabel
        search_label = QLabel("Cari:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari berdasarkan judul, catatan, atau sumber...")
        self.search_input.returnPressed.connect(self.search_notes)
        self.search_btn = QPushButton("Cari")
        self.clear_search_btn = QPushButton("Clear")
        self.search_btn.clicked.connect(self.search_notes)
        self.clear_search_btn.clicked.connect(self.clear_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)
        
        main_layout.addLayout(search_layout)

        # Create the table widget
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(["ID", "Judul", "Catatan", "Sumber", "Tgl/Jam"])
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.doubleClicked.connect(self.view_detail)  # Add double-click handler
        
        main_layout.addWidget(self.tableWidget)
        
        self.load_notes()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def load_notes(self):
        notes = self.db.get_all_notes()
        self.tableWidget.setRowCount(len(notes))
        
        for row_index, note in enumerate(notes):
            for col_index, data in enumerate(note):
                if col_index == 2:  # Catatan column - render HTML
                    # Create a QTextEdit for displaying HTML
                    text_widget = QTextEdit()
                    text_widget.setHtml(str(data) if data is not None else "")
                    text_widget.setReadOnly(True)
                    text_widget.setFrameStyle(0)  # Remove frame
                    text_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                    text_widget.setMaximumHeight(60)
                    self.tableWidget.setCellWidget(row_index, col_index, text_widget)
                elif col_index == 4:  # created_at column - format date
                    formatted_date = self.format_date(data)
                    item = QTableWidgetItem(formatted_date)
                    self.tableWidget.setItem(row_index, col_index, item)
                else:
                    item = QTableWidgetItem(str(data) if data is not None else "")
                    self.tableWidget.setItem(row_index, col_index, item)
            # Set row height for each row inside the loop
            self.tableWidget.setRowHeight(row_index, 60)
        
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def add_note(self):
        dialog = NoteDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"].strip():
                QMessageBox.warning(self, "Peringatan", "Judul tidak boleh kosong!")
                return
            if not data["catatan"].strip():
                QMessageBox.warning(self, "Peringatan", "Catatan tidak boleh kosong!")
                return
            sumber = data["sumber"].strip() if data["sumber"].strip() else None
            self.db.add_note(data["title"], data["catatan"], sumber)
            self.load_notes()

    def edit_note(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih catatan yang ingin diubah!")
            return
            
        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).text()
        # Get HTML content from the QTextEdit widget
        catatan_widget = self.tableWidget.cellWidget(selected_row, 2)
        catatan = catatan_widget.toHtml() if catatan_widget else ""
        sumber = self.tableWidget.item(selected_row, 3).text()
        
        dialog = NoteDialog(self, (note_id, title, catatan, sumber))
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"].strip():
                QMessageBox.warning(self, "Peringatan", "Judul tidak boleh kosong!")
                return
            if not data["catatan"].strip():
                QMessageBox.warning(self, "Peringatan", "Catatan tidak boleh kosong!")
                return
            sumber = data["sumber"].strip() if data["sumber"].strip() else None
            self.db.update_note(note_id, data["title"], data["catatan"], sumber)
            self.load_notes()

    def view_detail(self):
        selected_row = self.tableWidget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih catatan yang ingin dilihat!")
            return
            
        note_id = int(self.tableWidget.item(selected_row, 0).text())
        title = self.tableWidget.item(selected_row, 1).text()
        catatan_widget = self.tableWidget.cellWidget(selected_row, 2)
        catatan = catatan_widget.toHtml() if catatan_widget else ""
        sumber = self.tableWidget.item(selected_row, 3).text()
        created_at = self.tableWidget.item(selected_row, 4).text()
        
        dialog = NoteDetailDialog(self, (note_id, title, catatan, sumber, created_at))
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
            self.load_notes()

    def search_notes(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Peringatan", "Masukkan kata kunci pencarian!")
            return
        
        notes = self.db.search_notes(query)
        self.tableWidget.setRowCount(len(notes))
        
        for row_index, note in enumerate(notes):
            for col_index, data in enumerate(note):
                if col_index == 2:  # Catatan column - render HTML
                    text_widget = QTextEdit()
                    text_widget.setHtml(str(data) if data is not None else "")
                    text_widget.setReadOnly(True)
                    text_widget.setFrameStyle(0)
                    text_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                    text_widget.setMaximumHeight(60)
                    self.tableWidget.setCellWidget(row_index, col_index, text_widget)
                elif col_index == 4:  # created_at column - format date
                    formatted_date = self.format_date(data)
                    item = QTableWidgetItem(formatted_date)
                    self.tableWidget.setItem(row_index, col_index, item)
                else:
                    item = QTableWidgetItem(str(data) if data is not None else "")
                    self.tableWidget.setItem(row_index, col_index, item)
            self.tableWidget.setRowHeight(row_index, 60)
        
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

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
        self.load_notes()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
