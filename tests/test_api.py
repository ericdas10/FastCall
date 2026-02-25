import requests

# Test API endpoints
BASE_URL = "http://localhost:8000"

def test_register_call_center():
    """Register a test call center"""
    data = {
        "name": "Test Call Center",
        "username": "test_api_cc",
        "password": "password123",
        "email": "testcc@example.com",
        "domain": "finance",
        "country": "RO",
        "number": "+4000000000"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register/call-center", json=data)
        print(f"Register Call Center Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error registering call center: {e}")
        return False

def test_register_client():
    """Register a test client"""
    data = {
        "call_center_id": 1,
        "first_name": "Test",
        "last_name": "Client",
        "username": "testclient",
        "password": "password123",
        "email": "testclient@example.com",
        "country": "RO",
        "number": "+4000000001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register/client", json=data)
        print(f"Register Client Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error registering client: {e}")
        return False

def test_get_call_centers():
    """Get list of call centers"""
    try:
        response = requests.get(f"{BASE_URL}/auth/call-centers")
        print(f"Get Call Centers Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error getting call centers: {e}")
        return False

def test_login():
    """Test login"""
    data = {
        "username_or_email": "testclient",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=data)
        print(f"Login Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error logging in: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing FastCall API ===")
    
    print("\n1. Registering call center...")
    test_register_call_center()
    
    print("\n2. Getting call centers...")
    test_get_call_centers()
    
    print("\n3. Registering client...")
    test_register_client()
    
    print("\n4. Testing login...")
    test_login()
