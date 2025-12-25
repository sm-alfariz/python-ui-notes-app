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
    
    # Test Delete
    print("Testing delete_note...")
    db.delete_note(notes[0][0])
    final_notes = db.get_all_notes()
    assert len(final_notes) == 0
    print("Delete tests passed!")
    
    # Cleanup
    if os.path.exists(f".catat-segala/{db_test_name}"):
        os.remove(f".catat-segala/{db_test_name}")
    print("All database tests passed successfully!")

if __name__ == "__main__":
    test_db()
