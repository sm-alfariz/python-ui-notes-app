"""Main application window for the note-taking application.

This module provides the primary user interface for managing notes, including
creating, editing, deleting, searching, and viewing note details.

The MainWindow class is organized using mixins to separate concerns:
    - TableManagementMixin: Table display, pagination, context menus
    - NoteOperationsMixin: CRUD operations for notes
    - ExportImportMixin: CSV, HTML, PDF export and database backup/restore
"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from database import DatabaseManager
from src.config import ASSETS_DIR, t
from src.ui.delegates import HTMLDelegate
from src.ui.mixins import ExportImportMixin, NoteOperationsMixin, TableManagementMixin
from src.ui.theme_manager import ThemeManager


class MainWindow(
    TableManagementMixin, NoteOperationsMixin, ExportImportMixin, QMainWindow
):
    """Main application window for the note-taking application.

    Provides the primary user interface for managing notes, including
    creating, editing, deleting, searching, and viewing note details.
    Supports paginated note display, internationalization (i18n),
    theme switching, CSV export, and database backup functionality.

    The class uses mixins to organize functionality by concern:
        - TableManagementMixin: Table display and pagination
        - NoteOperationsMixin: Note CRUD operations
        - ExportImportMixin: Export and backup functionality
    """

    def __init__(self):
        """Initialize the main window and set up the UI."""
        super().__init__()

        # Initialize core attributes
        self._init_core_attributes()

        # Set up window properties
        self._setup_window()

        # Build the UI
        self._create_menu_bar()
        self._setup_central_widget()

        # Load saved settings
        self._load_saved_settings()

        # Display initial notes
        self.display_notes()

    # -------------------------------------------------------------------------
    # Initialization Methods
    # -------------------------------------------------------------------------

    def _init_core_attributes(self) -> None:
        """Initialize core attributes needed by mixins and the main class."""
        # Database
        self.db = DatabaseManager()

        # Language
        self.current_lang = "en"

        # Settings
        self.settings = QSettings("CatatSegala", "python-ui-notes-app")

        # Theme manager
        self.theme_manager = ThemeManager()

        # Pagination state
        self._current_offset = 0
        self._current_search = None
        self._total_notes = 0

    def _setup_window(self) -> None:
        """Set up window properties."""
        self.setWindowIcon(QIcon(os.path.join(ASSETS_DIR, "logo.png")))
        self.setWindowTitle(self.t("app_title"))
        self.resize(900, 600)

    def _setup_central_widget(self) -> None:
        """Set up the central widget with all UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Build UI sections
        self._create_toolbar(main_layout)
        self._create_search_bar(main_layout)
        self._create_table_widget(main_layout)
        self._create_pagination_footer(main_layout)

    # -------------------------------------------------------------------------
    # UI Component Creation
    # -------------------------------------------------------------------------

    def _create_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """Create the toolbar with action buttons and language selector.

        Args:
            parent_layout: The parent layout to add the toolbar to.
        """
        button_layout = QHBoxLayout()

        # Create action buttons
        self.add_btn = QPushButton(self.t("add_note"))
        self.edit_btn = QPushButton(self.t("edit"))
        self.delete_btn = QPushButton(self.t("delete"))
        self.detail_btn = QPushButton(self.t("detail"))
        self.refresh_btn = QPushButton(self.t("refresh"))
        self.exit_btn = QPushButton(self.t("exit"))

        # Connect button signals
        self.add_btn.clicked.connect(self.add_note)
        self.edit_btn.clicked.connect(self.edit_note)
        self.delete_btn.clicked.connect(self.delete_note)
        self.detail_btn.clicked.connect(self.view_detail)
        self.refresh_btn.clicked.connect(lambda: self.display_notes())
        self.exit_btn.clicked.connect(self.close)

        # Add buttons to layout
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.detail_btn)
        button_layout.addStretch()

        # Language selector
        self._create_language_selector(button_layout)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.exit_btn)

        parent_layout.addLayout(button_layout)

    def _create_language_selector(self, parent_layout: QHBoxLayout) -> None:
        """Create and add the language selector combo box.

        Args:
            parent_layout: The parent layout to add the selector to.
        """
        self.lang_selector = QComboBox()
        self.lang_selector.addItem("English", "en")
        self.lang_selector.addItem("Indonesia", "id")
        self.lang_selector.currentIndexChanged.connect(self._on_language_changed)

        # Load saved language (block signals to prevent premature callback)
        saved_lang = self.settings.value("language", "")
        if saved_lang:
            self.lang_selector.blockSignals(True)
            for i in range(self.lang_selector.count()):
                if self.lang_selector.itemData(i) == saved_lang:
                    self.lang_selector.setCurrentIndex(i)
                    break
            self.lang_selector.blockSignals(False)

        parent_layout.addWidget(self.lang_selector)

    def _create_search_bar(self, parent_layout: QVBoxLayout) -> None:
        """Create the search bar with input and buttons.

        Args:
            parent_layout: The parent layout to add the search bar to.
        """
        search_layout = QHBoxLayout()

        self.search_label = QLabel(self.t("search"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.search_input.returnPressed.connect(self._perform_search)

        self.search_btn = QPushButton(self.t("search").replace(":", ""))
        self.search_btn.clicked.connect(self._perform_search)

        self.clear_search_btn = QPushButton(self.t("clear"))
        self.clear_search_btn.clicked.connect(self._clear_search)

        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)

        parent_layout.addLayout(search_layout)

    def _create_table_widget(self, parent_layout: QVBoxLayout) -> None:
        """Create and configure the table widget for displaying notes.

        Args:
            parent_layout: The parent layout to add the table to.
        """
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(7)

        # Set up headers
        self._retranslate_table_headers()

        # Configure table behavior
        self.tableWidget.setColumnHidden(0, True)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.ExtendedSelection)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.doubleClicked.connect(self.view_detail)

        # Context menu
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.show_context_menu)

        # HTML delegate for catatan column
        self.tableWidget.setItemDelegateForColumn(2, HTMLDelegate(self.tableWidget))

        # Header configuration
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        parent_layout.addWidget(self.tableWidget)

    def _create_pagination_footer(self, parent_layout: QVBoxLayout) -> None:
        """Create the pagination footer with status and load more button.

        Args:
            parent_layout: The parent layout to add the footer to.
        """
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

        parent_layout.addLayout(pagination_layout)

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        self.menuBar().clear()
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu(self.t("file"))
        self._add_file_menu_actions(file_menu)

        # View menu with themes
        view_menu = menu_bar.addMenu(self.t("view"))
        theme_menu = view_menu.addMenu(self.t("theme"))
        self.theme_group = self.theme_manager.populate_theme_menu(
            theme_menu, self._on_theme_changed, self
        )

        # About menu
        about_menu = menu_bar.addMenu(self.t("about"))
        about_action = QAction(self.t("about"), self)
        about_action.triggered.connect(self._show_about)
        about_menu.addAction(about_action)

    def _add_file_menu_actions(self, file_menu) -> None:
        """Add actions to the file menu.

        Args:
            file_menu: The file menu to add actions to.
        """
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
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_language_changed(self, index: int) -> None:
        """Handle language selection change.

        Args:
            index: The index of the newly selected language.
        """
        self.current_lang = self.lang_selector.itemData(index)

        # Retranslate UI if widgets exist
        if hasattr(self, "search_label"):
            self._retranslate_ui()

        # Persist language selection
        self.settings.setValue("language", self.current_lang)

    def _on_theme_changed(self) -> None:
        """Handle theme selection change."""
        action = self.sender()
        if action:
            qss_file = action.data()
            if self.theme_manager.apply_theme(qss_file):
                self.theme_manager.save_theme(os.path.basename(qss_file))

    def _perform_search(self) -> None:
        """Execute search with current input."""
        query = self.search_input.text().strip()
        self._current_search = query if query else None
        self.display_notes(reset=True)

    def _clear_search(self) -> None:
        """Clear the search input and reset the table."""
        self.search_input.clear()
        self._current_search = None
        self.display_notes(reset=True)

    # -------------------------------------------------------------------------
    # UI Update Methods
    # -------------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        """Update all UI text with current language translations."""
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

        self._retranslate_table_headers()
        self._create_menu_bar()
        self.display_notes(reset=True)

    def _retranslate_table_headers(self) -> None:
        """Update table headers with current language translations."""
        self.tableWidget.setHorizontalHeaderLabels(
            [
                self.t("id"),
                self.t("title"),
                self.t("note"),
                self.t("source"),
                self.t("lock"),
                self.t("attachments"),
                self.t("date_time"),
            ]
        )

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

    # -------------------------------------------------------------------------
    # Settings
    # -------------------------------------------------------------------------

    def _load_saved_settings(self) -> None:
        """Load and apply saved settings (language, theme)."""
        saved_lang = self.settings.value("language", "")
        if saved_lang:
            self.current_lang = saved_lang
            self._retranslate_ui()

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def t(self, key: str) -> str:
        """Get translation for a key in the current language.

        Args:
            key: The translation key.

        Returns:
            The translated string.
        """
        return t(self.current_lang, key)

    def _show_about(self) -> None:
        """Show the about dialog."""
        about_dialog = QMessageBox()
        about_dialog.setIcon(QMessageBox.Information)
        about_dialog.setWindowTitle(self.t("about"))
        about_dialog.setText(self.t("about_text"))
        about_dialog.setInformativeText(self.t("about_info"))
        about_dialog.setStandardButtons(QMessageBox.Close)
        about_dialog.exec()


# Required for _on_theme_changed
import os