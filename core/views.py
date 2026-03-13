from django.shortcuts import render, redirect
from .models import MRIImage, DoctorProfile, Appointment
import os
import numpy as np
from PIL import Image
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import DoctorRegistrationForm, AppointmentForm
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
import google.generativeai as genai
import json

# Load environment variables
load_dotenv()

# Configure Gemini
API_KEY = os.getenv('GEMINI_API_KEY')
if API_KEY:
    genai.configure(api_key=API_KEY)

# Load model (placeholder for when it's ready)
MODEL_PATH = os.path.join(os.getcwd(), 'models', 'brain_tumor_model.h5')

# Global variable to hold the loaded model
_model = None

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = tf.keras.models.load_model(MODEL_PATH)
        else:
            print(f"Model not found at {MODEL_PATH}")
    return _model

def home(request):
    return render(request, 'core/home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:index')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

def doctor_signup(request):
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # login(request, user) # Don't login yet, wait for approval
            return render(request, 'core/doctor_signup.html', {
                'form': form, 
                'success': 'Registration successful! Please wait for admin approval before logging in.'
            })
    else:
        form = DoctorRegistrationForm()
    return render(request, 'core/doctor_signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Check if doctor and approved
            if hasattr(user, 'doctor_profile'):
                if not user.doctor_profile.is_approved:
                    return render(request, 'core/login.html', {
                        'form': form, 
                        'error': 'Your account is awaiting admin approval.'
                    })
            
            login(request, user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('core:dashboard_redirect')
        else:
            return render(request, 'core/login.html', {'form': form, 'error': 'Invalid username or password'})
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

@login_required(login_url='core:login')
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('core:admin_dashboard')
    if hasattr(request.user, 'doctor_profile'):
        return redirect('core:doctor_dashboard')
    return redirect('core:index')

@login_required(login_url='core:login')
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('core:index')
    
    pending_doctors = DoctorProfile.objects.filter(is_approved=False).select_related('user').order_by('-user__date_joined')
    approved_doctors = DoctorProfile.objects.filter(is_approved=True).select_related('user').order_by('-user__date_joined')
    
    return render(request, 'core/admin_dashboard.html', {
        'pending_doctors': pending_doctors,
        'approved_doctors': approved_doctors
    })

@login_required(login_url='core:login')
def approve_doctor(request, doctor_id):
    if not request.user.is_superuser:
        return redirect('core:index')
    
    doctor = DoctorProfile.objects.get(id=doctor_id)
    doctor.is_approved = True
    doctor.save()
    return redirect('core:admin_dashboard')

@login_required(login_url='core:login')
def reject_doctor(request, doctor_id):
    if not request.user.is_superuser:
        return redirect('core:index')
    
    doctor = DoctorProfile.objects.get(id=doctor_id)
    user = doctor.user
    doctor.delete()
    user.delete()
    return redirect('core:admin_dashboard')

@login_required(login_url='core:login')
def doctor_dashboard(request):
    if not hasattr(request.user, 'doctor_profile'):
        return redirect('core:index')
    appointments = Appointment.objects.filter(doctor=request.user.doctor_profile).order_by('appointment_date')
    return render(request, 'core/doctor_dashboard.html', {'appointments': appointments})

@login_required(login_url='core:login')
def doctor_profile(request):
    profile = request.user.doctor_profile
    return render(request, 'core/doctor_profile.html', {'profile': profile})

@login_required(login_url='core:login')
def list_doctors(request):
    doctors = DoctorProfile.objects.filter(is_approved=True)
    return render(request, 'core/doctor_list.html', {'doctors': doctors})

@login_required(login_url='core:login')
def book_appointment(request, doctor_id):
    doctor = DoctorProfile.objects.get(id=doctor_id)
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.user = request.user
            appointment.doctor = doctor
            appointment.save()
            return redirect('core:index')
    else:
        form = AppointmentForm()
    return render(request, 'core/book_appointment.html', {'form': form, 'doctor': doctor})

def logout_view(request):
    logout(request)
    return redirect('core:home')

@login_required(login_url='core:login')
def index(request):
    images = MRIImage.objects.all().order_by('-uploaded_at')[:5]
    user_appointments = Appointment.objects.filter(user=request.user).order_by('-appointment_date')
    return render(request, 'core/index.html', {
        'images': images,
        'user_appointments': user_appointments
    })

@login_required(login_url='core:login')
def update_appointment_status(request, appointment_id, new_status):
    appointment = Appointment.objects.get(id=appointment_id)
    
    # Security: Only the assigned doctor can update the status
    if not hasattr(request.user, 'doctor_profile') or appointment.doctor != request.user.doctor_profile:
        return redirect('core:index')
    
    if new_status in ['Confirmed', 'Cancelled']:
        appointment.status = new_status
        appointment.save()
        
    return redirect('core:doctor_dashboard')

@login_required(login_url='core:login')
def upload_image(request):
    if request.method == 'POST' and request.FILES.get('mri_image'):
        mri_file = request.FILES['mri_image']
        mri_instance = MRIImage.objects.create(image=mri_file)
        
        # Predict
        prediction, probability, details = predict_tumor(mri_instance.image.path)
        
        mri_instance.prediction = prediction
        mri_instance.probability = float(probability)
        mri_instance.save()
        
        return render(request, 'core/index.html', {
            'prediction_result': prediction,
            'probability': f"{probability*100:.2f}%",
            'details': details,
            'image_url': mri_instance.image.url,
            'images': MRIImage.objects.all().order_by('-uploaded_at')[:5] # Context for list
        })
    
    return redirect('core:index')

import time

def predict_tumor(image_path):
    if not API_KEY:
        return "Config Error", 0.0, "Gemini API key not found. Please check your .env file."
    
    max_retries = 2
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries + 1):
        try:
            # Dynamic model selection to avoid 404 errors
            available_models = [m.name for m in genai.list_models() 
                                if 'generateContent' in m.supported_generation_methods]
            
            # Prefer flash models
            model_name = 'models/gemini-1.5-flash' # Default attempt
            flash_models = [m for m in available_models if 'flash' in m]
            if flash_models:
                model_name = flash_models[0]
            model = genai.GenerativeModel(model_name)
            
            prompt = """
            Analyze this image for a brain tumor detection system.
            
            Step 1: Is this a Brain MRI Scan? 
            Answer "YES" or "NO".
            
            Step 2: If YES, is there a brain tumor detected? 
            Answer "Tumor Detected" or "No Tumor".
            Provide a confidence score between 0 and 100.
            
            Format the response strictly as JSON:
            {"is_mri": "YES", "prediction": "Tumor Detected", "confidence": 95.5, "details": "A detailed description of the AI analysis."}
            
            If Step 1 is NO, format as:
            {"is_mri": "NO", "prediction": "Not an MRI", "confidence": 0, "details": "This image does not appear to be a Brain MRI scan. Please upload a valid Brain MRI for analysis."}
            """

            with Image.open(image_path) as img:
                response = model.generate_content([prompt, img])
                text = response.text
            
            # Extract JSON from response more robustly
            try:
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(text[start:end])
                    is_mri = data.get('is_mri', 'NO')
                    
                    if is_mri == 'NO':
                        return "Not an MRI Scan", 0.0, data.get('details', "This image is not a valid brain MRI scan.")
                    
                    prediction = data.get('prediction', 'Analysis Completed')
                    confidence = float(data.get('confidence', 0.0)) / 100.0
                    details = data.get('details', "Analysis completed successfully.")
                    
                    return prediction, confidence, details
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON Parsing Error: {e}")
                # Fallback if JSON fails but text exists
                if "YES" in text.upper():
                    return "Analysis Completed", 0.85, text.strip()[:200]
            
            return "Processing Error", 0.0, "Could not parse analysis results. Please ensure the image is a clear Brain MRI."
            
        except Exception as e:
            error_msg = str(e)
            print(f"Gemini Error (Attempt {attempt+1}/{max_retries+1}): {error_msg}")
            
            # Check for DNS/Connection errors
            if "DNS resolution failed" in error_msg or "getaddrinfo" in error_msg or "deadline exceeded" in error_msg:
                if attempt < max_retries:
                    print(f"Connection issue detected. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                return "Network Error", 0.0, "The AI service is unreachable. Please check your internet connection or DNS settings. If you use a VPN or custom DNS, try disabling them temporarily."
            
            # Other errors
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            return "AI Error", 0.0, f"Error communicating with AI: {error_msg}. Please try again later."
    
    return "AI Error", 0.0, "Exceeded maximum retries for AI communication."

