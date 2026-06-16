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

if __name__ == "__main__":
    test_db()
