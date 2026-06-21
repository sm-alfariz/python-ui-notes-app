from database import DatabaseManager
import os

def test_db():
    print("Starting database tests...")
    db_test_name = "test_notes.db"
    if os.path.exists(f".catat-segala/{db_test_name}"):
        os.remove(f".catat-segala/{db_test_name}")

    db = DatabaseManager(db_test_name)

    # Test Add Note
    print("Testing add_note...")
    db.add_note("Test Title", "<p>Test Content</p>", "Test Source")

    # Test Get All
    print("Testing get_all_notes...")
    notes = db.get_all_notes()
    assert len(notes) == 1
    assert notes[0][1] == "Test Title"
    assert notes[0][2] == "<p>Test Content</p>"
    assert notes[0][3] == "Test Source"
    print("Add/Get tests passed!")

    # Test Search
    print("Testing search_notes...")
    results = db.search_notes("Title")
    assert len(results) == 1
    results = db.search_notes("None")
    assert len(results) == 0
    print("Search tests passed!")

    # Test Update
    print("Testing update_note...")
    db.update_note(notes[0][0], "New Title", "New Content", "New Source")
    updated_notes = db.get_all_notes()
    assert updated_notes[0][1] == "New Title"
    print("Update tests passed!")

    # Test Attachments
    print("Testing attachments...")
    note_id = updated_notes[0][0]
    att_id = db.add_attachment(note_id, "test_file.txt", "text/plain", b"Hello SQLite attachments!")

    atts = db.get_attachments_by_note_id(note_id)
    assert len(atts) == 1
    assert atts[0][2] == "test_file.txt"
    assert atts[0][3] == "text/plain"
    assert atts[0][4] == b"Hello SQLite attachments!"

    print("Attachment retrieval passed!")

    # Test Delete Note Cascading
    print("Testing delete_note and cascading attachments...")
    db.delete_note(note_id)
    final_notes = db.get_all_notes()
    assert len(final_notes) == 0

    # Verify attachment is deleted automatically
    remaining_atts = db.get_attachments_by_note_id(note_id)
    assert len(remaining_atts) == 0
    print("Cascade Delete tests passed!")

    # Cleanup
    if os.path.exists(f".catat-segala/{db_test_name}"):
        os.remove(f".catat-segala/{db_test_name}")
    print("All database tests passed successfully!")


def test_validate_sqlite_file():
    """Test _validate_sqlite_file helper by importing it from MainWindow."""
    print("\nStarting SQLite validation tests...")
    import tempfile
    import shutil
    from src.ui.main_window import MainWindow

    m = MainWindow.__new__(MainWindow)

    # Create a valid SQLite database file
    db_src = "test_validate_src.db"
    if os.path.exists(f".catat-segala/{db_src}"):
        os.remove(f".catat-segala/{db_src}")
    db = DatabaseManager(db_src)
    db.add_note("Validate Test", "<p>Content</p>")

    valid_path = f".catat-segala/{db_src}"
    assert m._validate_sqlite_file(valid_path) == "valid"
    print("Valid SQLite file test passed!")

    # Test with a text file
    txt_path = ".catat-segala/test_validate.txt"
    with open(txt_path, "w") as f:
        f.write("This is not a database")
    assert m._validate_sqlite_file(txt_path) == "invalid"
    print("Invalid text file test passed!")

    # Test with an empty file
    empty_path = ".catat-segala/test_validate_empty.db"
    with open(empty_path, "w") as f:
        pass
    assert m._validate_sqlite_file(empty_path) == "invalid"
    print("Empty file test passed!")

    # Cleanup
    for path in [valid_path, txt_path, empty_path]:
        if os.path.exists(path):
            os.remove(path)
    print("All SQLite validation tests passed!")


def test_restore_database():
    """Test restore database by copying a backup over the current database."""
    print("\nStarting restore database tests...")
    import shutil
    from src.ui.main_window import MainWindow
    from database import DatabaseManager

    # Create a source database with data
    src_name = "test_restore_src.db"
    src_path = f".catat-segala/{src_name}"
    if os.path.exists(src_path):
        os.remove(src_path)
    src_db = DatabaseManager(src_name)
    note_id = src_db.add_note("Restored Note", "<p>Restored Content</p>", "Restored Source")
    src_db.close = lambda: None  # prevent issues

    # Create a target database (empty)
    tgt_name = "test_restore_tgt.db"
    tgt_path = f".catat-segala/{tgt_name}"
    if os.path.exists(tgt_path):
        os.remove(tgt_path)
    tgt_db = DatabaseManager(tgt_name)
    assert len(tgt_db.get_all_notes()) == 0

    # Perform restore: copy src over tgt
    shutil.copy2(src_path, tgt_path)

    # Reinitialize DatabaseManager to pick up restored data
    tgt_db = DatabaseManager(tgt_name)
    notes = tgt_db.get_all_notes()
    assert len(notes) == 1
    assert notes[0][1] == "Restored Note"
    assert notes[0][2] == "<p>Restored Content</p>"
    assert notes[0][3] == "Restored Source"
    print("Restore database test passed!")

    # Cleanup
    for path in [src_path, tgt_path]:
        if os.path.exists(path):
            os.remove(path)
    print("All restore database tests passed!")


if __name__ == "__main__":
    test_db()
    test_validate_sqlite_file()
    test_restore_database()
