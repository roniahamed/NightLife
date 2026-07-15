import os
import django
import sys

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
user = User.objects.filter(email='roniahamed.jvai@gmail.com').first()
if not user:
    print("User not found!")
    sys.exit(1)

client = APIClient()
client.force_authenticate(user=user)

data = {
    'first_name': 'Roni',
    'last_name': 'Ahamed',
    'bio': 'New bio test',
    'location_name': 'Dhaka, Bangladesh',
    'latitude': 23.8103,
    'longitude': 90.4125
}

response = client.patch('/api/users/profile/', data, format='json')
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
