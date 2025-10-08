from fastapi.testclient import TestClient
from pathlib import Path
import io

def test_upload_file(client: TestClient):
    """
    Test uploading a file successfully.
    """
    file_content = b"This is a test file."
    file_name = "test_upload.txt"
    
    response = client.post(
        "/api/v1/uploads/",
        files={"file": (file_name, io.BytesIO(file_content), "text/plain")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "file_path" in data
    
    # Verify the file was created and has the correct content
    file_path = Path(data["file_path"])
    assert file_path.exists()
    assert file_path.read_bytes() == file_content
    
    # Clean up the created file
    file_path.unlink()

def test_upload_file_invalid_filename(client: TestClient):
    """
    Test that uploading a file with a directory traversal attempt is blocked.
    """
    file_content = b"This is a malicious file."
    file_name = "../test_upload.txt"
    
    response = client.post(
        "/api/v1/uploads/",
        files={"file": (file_name, io.BytesIO(file_content), "text/plain")},
    )
    
    assert response.status_code == 400
    assert "Invalid filename" in response.text
