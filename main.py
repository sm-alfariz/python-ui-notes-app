import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./assets/logo.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
