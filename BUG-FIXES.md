# Bug Fixes Summary — CS | Catat Segala

**Date:** 2026-06-20
**Test Result:** ✅ All 8 tests pass, 0 ResourceWarnings

---

## Fix 1: `remove_attachment` Index Shift Corruption 🔴

**File:** `src/dialogs/note_dialogs.py:144-159`
**Severity:** High — data loss / wrong files removed

**Problem:** When removing multiple attachments, `pop(row)` shifts subsequent indices. Selecting rows 0 and 1 would remove the wrong items.

**Fix:** Sort rows in **reverse** order before popping, so higher indices are removed first and lower indices remain valid.

```python
# Before
for item in selected_items:
    row = self.attachments_list.row(item)
    if 0 <= row < len(self.current_attachments):
        self.current_attachments.pop(row)

# After
rows_to_remove = sorted(
    [self.attachments_list.row(item) for item in selected_items],
    reverse=True
)
for row in rows_to_remove:
    if 0 <= row < len(self.current_attachments):
        self.current_attachments.pop(row)
```

---

## Fix 2: Dead Variable & Inline Import 🟡

**File:** `src/ui/main_window.py:100-105`
**Severity:** Low — dead code / code smell

**Problem:** `QLineEdit_if_used = None` was a leftover from a refactor. `QLineEdit` was imported inline inside `__init__` instead of at the top.

**Fix:** Moved `QLineEdit` to the top-level import block. Removed dead `QLineEdit_if_used` variable and inline import.

---

## Fix 3: `search_btn` KeyError Risk 🔴

**File:** `src/ui/main_window.py:107-111`
**Severity:** High — crash on startup if QSettings has corrupted language

**Problem:** `TRANSLATIONS[self.current_lang]` raised `KeyError` if `current_lang` was not in `TRANSLATIONS` (e.g., from corrupted QSettings).

**Fix:** Simplified to always use `self.t("search").replace(":", "")` which safely falls back to English.

---

## Fix 4: Test QSettings State Leak 🟡

**File:** `test_app.py:107-115`
**Severity:** Medium — flaky test

**Problem:** Persisted language setting from QSettings caused `test_main_window_init` to open with Indonesian title (`"CS | Catat Segala"`) instead of English (`"CS | Note Everything"`).

**Fix:** Added `setUp()` to `TestMainWindow` that calls `settings.clear()` before each test, ensuring a clean QSettings state.

---

## Fix 5: PyQt6 → PySide6 in Translations ⚪

**Files:** `language.ini` (en + id sections), `src/config.py:72`
**Severity:** Low — incorrect documentation / UI text

**Problem:** The `about_info` string referenced "PyQt6" but the app uses **PySide6**.

**Fix:** Changed `"PyQt6"` to `"PySide6"` in all locations (both languages in `language.ini` and the fallback dict in `config.py`).

---

## Fix 6: Database Connection Resource Warnings 🔴

**File:** `database.py`
**Severity:** High — resource leak

**Problem:** `sqlite3.Connection.__exit__` commits/rollbacks but **does NOT close** the connection. The `with self.get_connection() as conn:` pattern left connections open, causing `ResourceWarning: unclosed database` errors (16+ warnings during tests).

**Fix:** Replaced `get_connection()` with a `_connect()` context manager that properly **closes** the connection in a `finally` block. Removed redundant `conn.commit()` calls from all methods since `_connect()` handles commit/rollback automatically.

```python
# Before
def get_connection(self):
    conn = sqlite3.connect(self.db_name)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# After
@contextlib.contextmanager
def _connect(self):
    conn = sqlite3.connect(self.db_name)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## Files Changed

| File | Changes |
|---|---|
| `database.py` | Replaced `get_connection()` with `_connect()` context manager; added `close()` and `__del__` |
| `src/ui/main_window.py` | Moved `QLineEdit` import to top; removed dead variable; simplified `search_btn` |
| `src/dialogs/note_dialogs.py` | Fixed `remove_attachment` reverse-sort bug |
| `test_app.py` | Added `setUp()` to clear QSettings state |
| `language.ini` | Changed PyQt6 → PySide6 (en + id) |
| `src/config.py` | Changed PyQt6 → PySide6 in fallback translations |
