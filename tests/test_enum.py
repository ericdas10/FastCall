# Test enum validation
import requests
import json

BASE_URL = "http://localhost:8000"

def test_enum_validation():
    """Test different enum formats"""
    
    # Test 1: Lowercase (current frontend)
    data1 = {
        "name": "Test1",
        "username": "testcc123", 
        "password": "StrongPass123",
        "email": "admin12@testcc.com",
        "domain": "healthcare",
        "country": "US",
        "number": "0742889857"
    }
    
    # Test 2: Uppercase enum key
    data2 = {
        "name": "Test2",
        "username": "testcc456", 
        "password": "StrongPass123",
        "email": "admin2@testcc.com",
        "domain": "HEALTHCARE",
        "country": "US",
        "number": "0742889858"
    }
    
    print("=== Test 1: Lowercase (current frontend) ===")
    try:
        response = requests.post(f"{BASE_URL}/auth/register/call-center", json=data1)
        print(f"Status: {response.status_code}")
        if response.status_code == 422:
            print("Error:", response.json())
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test 2: Uppercase enum key ===")
    try:
        response = requests.post(f"{BASE_URL}/auth/register/call-center", json=data2)
        print(f"Status: {response.status_code}")
        if response.status_code == 422:
            print("Error:", response.json())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_enum_validation()
