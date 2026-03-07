from django.db import models
from django.contrib.auth.models import User

class MRIImage(models.Model):
    image = models.ImageField(upload_to='mri_scans/')
    prediction = models.CharField(max_length=50, blank=True, null=True)
    probability = models.FloatField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MRI Scan {self.id} - {self.prediction}"

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    license_number = models.CharField(max_length=50)
    specialization = models.CharField(max_length=100)
    hospital_name = models.CharField(max_length=200)
    profile_pic = models.ImageField(upload_to='doctor_profiles/', null=True, blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Dr. {self.user.username} - {self.specialization} ({'Approved' if self.is_approved else 'Pending'})"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appointment: {self.user.username} with {self.doctor.user.username} on {self.appointment_date}"
