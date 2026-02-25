# Test with exact frontend data
import requests

BASE_URL = "http://localhost:8000"

def test_frontend_data():
    """Test with exact data from frontend"""
    data = {
        "name": "Test1",
        "username": "testcc123", 
        "password": "StrongPass123",
        "email": "admin1@testcc.com",
        "domain": "healthcare",
        "country": "US",
        "number": "0742889857"
    }
    
    print("Sending data:", data)
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register/call-center", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 422:
            print("Validation errors:")
            print(response.json())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_frontend_data()
