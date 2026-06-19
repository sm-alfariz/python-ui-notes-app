import os
import mimetypes
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QFileDialog,
    QListWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt
from src.widgets.custom_text_edit import CustomTextEdit
from src.config import t
from database import DatabaseManager

class NoteDialog(QDialog):
    def __init__(self, parent=None, note_data=None, lang="en"):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(self.t("add_note") if note_data is None else self.t("edit"))
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)

        layout = QFormLayout(self)

        self.title_input = QLineEdit()
        self.catatan_input = CustomTextEdit()
        self.catatan_input.setAcceptRichText(True)  # Enable HTML support
        self.sumber_input = QLineEdit()

        self.db = DatabaseManager()
        self.current_attachments = []

        if note_data:
            self.title_input.setText(note_data[1] if note_data[1] else "")
            # note_data[2] is the HTML content
            self.catatan_input.setHtml(note_data[2] if note_data[2] else "")
            self.sumber_input.setText(note_data[3] if note_data[3] else "")
            
            # Load attachments
            try:
                note_id = note_data[0]
                db_attachments = self.db.get_attachments_by_note_id(note_id)
                for att in db_attachments:
                    self.current_attachments.append({
                        "id": att[0],
                        "name": att[2],
                        "mime": att[3],
                        "blob": att[4]
                    })
            except Exception as e:
                print(f"Error loading attachments in NoteDialog: {e}")

        layout.addRow(self.t("judul_label"), self.title_input)
        layout.addRow(self.t("catatan_label"), self.catatan_input)
        layout.addRow(self.t("sumber_label"), self.sumber_input)

        # Attachments UI List
        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(100)
        self.attachments_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fcfcfc;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        self.attachments_list.itemDoubleClicked.connect(self.download_attachment)
        self.update_attachments_list()

        att_buttons_layout = QHBoxLayout()
        self.add_att_btn = QPushButton(self.t("add_attachment"))
        self.add_att_btn.clicked.connect(self.add_attachment)
        self.remove_att_btn = QPushButton(self.t("remove_attachment"))
        self.remove_att_btn.clicked.connect(self.remove_attachment)

        att_buttons_layout.addWidget(self.add_att_btn)
        att_buttons_layout.addWidget(self.remove_att_btn)

        att_container = QVBoxLayout()
        att_container.addWidget(self.attachments_list)
        att_container.addLayout(att_buttons_layout)

        layout.addRow(self.t("attachments"), att_container)

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
        return t(self.lang, key)

    def get_data(self):
        return {
            "title": self.title_input.text(),
            "catatan": self.catatan_input.toHtml(),  # Get HTML content
            "sumber": self.sumber_input.text(),
            "attachments": self.current_attachments
        }

    def add_attachment(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, self.t("add_attachment"), "", "All Files (*.*)"
        )
        for path in file_paths:
            name = os.path.basename(path)
            mime, _ = mimetypes.guess_type(path)
            if not mime:
                mime = "application/octet-stream"
            try:
                with open(path, "rb") as f:
                    blob = f.read()
                self.current_attachments.append({
                    "id": None,
                    "name": name,
                    "mime": mime,
                    "blob": blob
                })
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal membaca file: {str(e)}")
        self.update_attachments_list()

    def remove_attachment(self):
        selected_items = self.attachments_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.t("warning"), self.t("select_delete_warning"))
            return

        # Get rows to remove, sort in reverse to avoid index shifting
        rows_to_remove = sorted(
            [self.attachments_list.row(item) for item in selected_items],
            reverse=True
        )
        for row in rows_to_remove:
            if 0 <= row < len(self.current_attachments):
                self.current_attachments.pop(row)

        self.update_attachments_list()

    def update_attachments_list(self):
        self.attachments_list.clear()
        for att in self.current_attachments:
            self.attachments_list.addItem(att["name"])

    def download_attachment(self, item):
        row = self.attachments_list.row(item)
        if 0 <= row < len(self.current_attachments):
            att = self.current_attachments[row]
            file_path, _ = QFileDialog.getSaveFileName(
                self, self.t("save_attachment"), att["name"], "All Files (*.*)"
            )
            if file_path:
                try:
                    with open(file_path, "wb") as f:
                        f.write(att["blob"])
                    QMessageBox.information(
                        self, self.t("success"), f"File saved to {file_path}"
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Gagal menyimpan file: {str(e)}")


class NoteDetailDialog(QDialog):
    def __init__(self, parent=None, note_data=None, lang="en"):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(self.t("detail"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

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

        # Attachments Section
        att_label = QLabel(self.t("attachments"))
        att_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(att_label)

        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(80)
        self.attachments_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fcfcfc;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        self.attachments_list.itemDoubleClicked.connect(self.download_attachment)
        layout.addWidget(self.attachments_list)

        self.db = DatabaseManager()
        self.attachments = []
        if note_data:
            try:
                note_id = note_data[0]
                db_attachments = self.db.get_attachments_by_note_id(note_id)
                for att in db_attachments:
                    self.attachments.append({
                        "id": att[0],
                        "name": att[2],
                        "mime": att[3],
                        "blob": att[4]
                    })
                    self.attachments_list.addItem(att[2])
            except Exception as e:
                print(f"Error loading attachments in NoteDetailDialog: {e}")

        if not self.attachments:
            self.attachments_list.addItem(self.t("no_attachments"))
            self.attachments_list.setEnabled(False)

        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.save_att_btn = QPushButton(self.t("save_attachment"))
        self.save_att_btn.clicked.connect(self.download_selected_attachment)
        if not self.attachments:
            self.save_att_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_att_btn)

        close_button = QPushButton(self.t("close"))
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)

    def t(self, key):
        return t(self.lang, key)

    def download_attachment(self, item):
        if not self.attachments:
            return
        row = self.attachments_list.row(item)
        if 0 <= row < len(self.attachments):
            att = self.attachments[row]
            file_path, _ = QFileDialog.getSaveFileName(
                self, self.t("save_attachment"), att["name"], "All Files (*.*)"
            )
            if file_path:
                try:
                    with open(file_path, "wb") as f:
                        f.write(att["blob"])
                    QMessageBox.information(
                        self, self.t("success"), f"File saved to {file_path}"
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Gagal menyimpan file: {str(e)}")

    def download_selected_attachment(self):
        selected_items = self.attachments_list.selectedItems()
        if selected_items:
            self.download_attachment(selected_items[0])
