import os
import sys
import configparser

def load_translations():
    config = configparser.ConfigParser()
    
    # Target config path in .catat-segala folder
    folder_name = ".catat-segala"
    if not os.path.exists(folder_name):
        try:
            os.makedirs(folder_name)
        except Exception:
            pass
    config_path = os.path.join(folder_name, "language.ini")

    # Source config path (bundled/distribution location relative to package or _MEIPASS)
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    source_config_path = os.path.join(base_dir, "language.ini")

    # Copy language.ini to .catat-segala if it doesn't exist there yet
    if not os.path.exists(config_path):
        if os.path.exists(source_config_path):
            try:
                import shutil
                shutil.copy2(source_config_path, config_path)
            except Exception:
                # Fallback to source path directly if copy failed
                config_path = source_config_path

    # Default fallback translations if file is missing or keys are missing
    default_translations = {
        "en": {
            "app_title": "CS | Note Everything",
            "add_note": "Add Note",
            "edit": "Edit",
            "delete": "Delete",
            "detail": "Detail",
            "refresh": "Refresh",
            "exit": "Exit",
            "search": "Search:",
            "search_placeholder": "Search title, content, or source...",
            "clear": "Clear",
            "id": "ID",
            "title": "Title",
            "note": "Note",
            "source": "Source",
            "date_time": "Date/Time",
            "file": "&File",
            "about": "&About",
            "export_csv": "Export notes to CSV",
            "backup_db": "Backup Database",
            "warning": "Warning",
            "confirm": "Confirmation",
            "delete_confirm": "Are you sure you want to delete this note?",
            "empty_warning": "Title and Note cannot be empty!",
            "select_edit_warning": "Select a note to edit!",
            "select_delete_warning": "Select a note to delete!",
            "success": "Success",
            "export_success": "Notes successfully exported to {}",
            "backup_success": "Database successfully backed up to {}",
            "db_not_found": "Database file not found.",
            "save": "Save",
            "cancel": "Cancel",
            "close": "Close",
            "created_at": "Created At:",
            "judul_label": "Title:",
            "catatan_label": "Note:",
            "sumber_label": "Source:",
            "about_text": "<u>CS | Note Everything</u>",
            "about_info": "is Simple note with PyQt6 and Sqlite3",
            "tooltip_detail": "Double click or click 'Detail' to see full format",
            "save_csv": "Save as CSV",
        }
    }

    if not os.path.exists(config_path):
        return default_translations

    try:
        config.read(config_path, encoding="utf-8")
        translations = {}
        for section in config.sections():
            translations[section] = dict(config.items(section))
        return translations if translations else default_translations
    except Exception:
        return default_translations

TRANSLATIONS = load_translations()

def t(lang, key):
    """Translate key for a given language code."""
    return TRANSLATIONS.get(lang, TRANSLATIONS.get("en", {})).get(key, key)
