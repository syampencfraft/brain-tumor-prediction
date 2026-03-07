import os
import django
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brain_tumor_detector.settings')
django.setup()

from core.models import DoctorProfile

# Create admin if doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword123')
    print("Created superuser 'admin' with password 'adminpassword123'")
else:
    print("Superuser 'admin' already exists")

# Approve doctors
doctors = DoctorProfile.objects.all()
for dr in doctors:
    dr.is_approved = True
    dr.save()
    print(f"Approved doctor: {dr.user.username}")
