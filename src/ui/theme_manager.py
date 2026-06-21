"""Theme management for the application.

Handles loading, applying, and persisting theme preferences.
"""

import os
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMenu

from src.config import _get_source_dir


class ThemeManager:
    """Manages application themes loaded from QSS files.

    Handles copying built-in themes to a user-writable location,
    loading themes at startup, and persisting theme preferences.

    Attributes:
        settings: QSettings instance for persisting preferences.
        themes_dir: Path to the directory containing theme QSS files.
    """

    # Organization and app name for QSettings
    SETTINGS_ORG = "CatatSegala"
    SETTINGS_APP = "python-ui-notes-app"

    # Target directory for themes (user-writable)
    TARGET_THEMES_DIR = ".catat-segala/themes"

    def __init__(self):
        """Initialize the theme manager and ensure themes are available."""
        self.settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        self.themes_dir = self._setup_themes_dir()

    def _setup_themes_dir(self) -> str:
        """Set up the themes directory and copy built-in themes.

        Returns:
            Path to the themes directory.
        """
        # Determine source themes directory
        source_themes_dir = os.path.join(_get_source_dir(), "src", "themes")

        # Create target directory if needed
        target_themes_dir = self.TARGET_THEMES_DIR
        if not os.path.exists(target_themes_dir):
            try:
                os.makedirs(target_themes_dir)
            except OSError:
                pass

        # Copy built-in themes to target if not already there
        if os.path.exists(source_themes_dir) and os.path.exists(target_themes_dir):
            for file_name in os.listdir(source_themes_dir):
                if file_name.endswith(".qss"):
                    src_file = os.path.join(source_themes_dir, file_name)
                    tgt_file = os.path.join(target_themes_dir, file_name)
                    if not os.path.exists(tgt_file):
                        try:
                            shutil.copy2(src_file, tgt_file)
                        except OSError:
                            pass

        return target_themes_dir

    def get_saved_theme(self) -> str:
        """Get the saved theme filename from settings.

        Returns:
            The saved theme filename, or empty string if not set.
        """
        return self.settings.value("theme", "")

    def save_theme(self, theme_filename: str) -> None:
        """Save the selected theme to settings.

        Args:
            theme_filename: The filename of the theme to save.
        """
        self.settings.setValue("theme", theme_filename)

    def apply_theme(self, qss_path: str) -> bool:
        """Apply a theme from a QSS file.

        Args:
            qss_path: Path to the QSS file to apply.

        Returns:
            True if the theme was applied successfully, False otherwise.
        """
        app = QApplication.instance()
        if not app:
            return False

        if qss_path and os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
                return True
            except OSError:
                return False
        else:
            app.setStyleSheet("")
            return True

    def populate_theme_menu(
        self, menu: QMenu, callback: callable, parent=None
    ) -> QActionGroup:
        """Populate a menu with available theme options.

        Args:
            menu: The QMenu to populate with theme actions.
            callback: The function to call when a theme is selected.
            parent: The parent widget for the QActionGroup.

        Returns:
            QActionGroup containing the theme actions.
        """
        theme_group = QActionGroup(parent)
        theme_group.setExclusive(True)

        saved_theme = self.get_saved_theme()

        if os.path.exists(self.themes_dir):
            for file_name in sorted(os.listdir(self.themes_dir)):
                if file_name.endswith(".qss"):
                    theme_name = file_name.replace(".qss", "").replace("_", " ").title()
                    action = QAction(theme_name, parent)
                    action.setCheckable(True)

                    qss_path = os.path.join(self.themes_dir, file_name)
                    action.setData(qss_path)
                    action.triggered.connect(callback)

                    theme_group.addAction(action)
                    menu.addAction(action)

                    # Check and apply saved theme
                    if saved_theme and os.path.basename(qss_path) == saved_theme:
                        action.setChecked(True)
                        self.apply_theme(qss_path)

        return theme_group