import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.config import ASSETS_DIR
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(ASSETS_DIR, "logo.png")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
