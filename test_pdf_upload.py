# Test PDF upload functionality
import requests
import os

BASE_URL = "http://localhost:8000"

def test_pdf_upload():
    """Test PDF upload endpoint"""
    
    # Create a test PDF file
    test_pdf_path = "test_document.pdf"
    with open(test_pdf_path, "w") as f:
        f.write("This is a test PDF content for testing purposes.")
    
    try:
        with open(test_pdf_path, "rb") as f:
            files = {"file": ("test_document.pdf", f, "application/pdf")}
            response = requests.post(f"{BASE_URL}/call-center/upload-pdf", files=files)
            
        print(f"Upload Status: {response.status_code}")
        print(f"Upload Response: {response.json()}")
        
        # Clean up test file
        os.remove(test_pdf_path)
        
    except Exception as e:
        print(f"Error: {e}")
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)

if __name__ == "__main__":
    test_pdf_upload()
