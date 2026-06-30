import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

def get_token():
    # Login as admin to get token
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.tokens import RefreshToken
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    User = get_user_model()
    user, _ = User.objects.get_or_create(email='admin@test.com', username='admin')
    if _:
        user.set_password('admin123')
        user.save()
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def test_endpoint(name, url, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}{url}", headers=headers)
        print(f"--- {name} ---")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2)[:500] + "...\n")
        else:
            print("Error:", response.text[:500] + "\n")
    except Exception as e:
        print(f"--- {name} ---")
        print(f"Exception: {e}\n")

try:
    token = get_token()
    print("Obtained JWT Token.\n")
    
    # Test Swagger
    print("--- Swagger Schema ---")
    schema_resp = requests.get(f"{BASE_URL}/schema/")
    print(f"Status: {schema_resp.status_code}")
    if schema_resp.status_code == 200:
        print("Schema loaded successfully!\n")
    else:
        print("Failed to load schema.\n")
        
    # Test Discovery Endpoints
    test_endpoint("Global Search (All)", "/discovery/search/?q=club&type=all", token)
    test_endpoint("Global Search (Clubs)", "/discovery/search/?q=club&type=clubs", token)
    test_endpoint("Trending Summary", "/discovery/trending/summary/?lat=40.7128&lng=-74.0060", token)
    test_endpoint("Trending List", "/discovery/trending/", token)
    test_endpoint("Heatmap Zones", "/discovery/heatmap/zones/?lat=40.7128&lng=-74.0060&radius=20&time_filter=live", token)
    test_endpoint("Heatmap Stats", "/discovery/heatmap/stats/?lat=40.7128&lng=-74.0060&radius=20&time_filter=live", token)
    test_endpoint("Nearby Venues", "/discovery/nearby/?lat=40.7128&lng=-74.0060&radius=10", token)
    
except Exception as e:
    print(f"Global Exception: {e}")
    sys.exit(1)
