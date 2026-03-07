from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DoctorProfile, Appointment

class DoctorRegistrationForm(UserCreationForm):
    license_number = forms.CharField(max_length=50, required=True)
    specialization = forms.CharField(max_length=100, required=True)
    hospital_name = forms.CharField(max_length=200, required=True)
    profile_pic = forms.ImageField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            DoctorProfile.objects.create(
                user=user,
                license_number=self.cleaned_data['license_number'],
                specialization=self.cleaned_data['specialization'],
                hospital_name=self.cleaned_data['hospital_name'],
                profile_pic=self.cleaned_data.get('profile_pic')
            )
        return user

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'message']
        widgets = {
            'appointment_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional message for the doctor...'}),
        }
