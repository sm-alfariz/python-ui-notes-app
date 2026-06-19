import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / "assets" / "logo.png"
    app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
