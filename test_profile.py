from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
user = User.objects.filter(email='roniahamed.jvai@gmail.com').first()
if not user:
    print("User not found!")
    exit(1)

client = APIClient()
client.force_authenticate(user=user)

# Let's test the PATCH endpoint
patch_data = {
    'first_name': 'Roni Test',
    'last_name': 'Ahamed Test',
    'bio': 'This is a test bio.',
    'location_name': 'Sylhet, Bangladesh',
    'latitude': 24.8949,
    'longitude': 91.8687
}

print("Testing PATCH /api/users/profile/...")
response = client.patch('/api/users/profile/', patch_data, format='json')
print(f"PATCH Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("PATCH Response Data:")
    print(f"- first_name: {data.get('first_name')}")
    print(f"- last_name: {data.get('last_name')}")
    print(f"- bio: {data.get('bio')}")
    print(f"- location_name: {data.get('location_name')}")
    print(f"- lat: {data.get('lat')}")
    print(f"- lng: {data.get('lng')}")
    print(f"- post_count: {data.get('post_count')}")
    print(f"- events_count: {data.get('events_count')}")
else:
    print(f"Error: {response.content}")

