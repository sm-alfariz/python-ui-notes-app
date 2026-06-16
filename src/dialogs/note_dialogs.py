from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTextEdit,
)
from PySide6.QtCore import Qt
from src.widgets.custom_text_edit import CustomTextEdit
from src.config import t

class NoteDialog(QDialog):
    def __init__(self, parent=None, note_data=None, lang="en"):
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
        return t(self.lang, key)

    def get_data(self):
        return {
            "title": self.title_input.text(),
            "catatan": self.catatan_input.toHtml(),  # Get HTML content
            "sumber": self.sumber_input.text(),
        }


class NoteDetailDialog(QDialog):
    def __init__(self, parent=None, note_data=None, lang="en"):
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
        return t(self.lang, key)
