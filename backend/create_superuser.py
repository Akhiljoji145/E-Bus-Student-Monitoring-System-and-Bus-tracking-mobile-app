import os
import django
from django.db import IntegrityError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = 'akhil'
email = 'akhiljoji1451@gmail.com'
password = 'maliyil123'

try:
    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser: {username}")
        user = User(
            username=username,
            email=email,
            is_superuser=True,
            is_staff=True,
            is_active=True
        )
        user.set_password(password)
        user.save()
        print("Superuser created successfully.")
    else:
        print(f"Superuser {username} already exists.")
except Exception as e:
    print(f"Error creating superuser: {e}")
