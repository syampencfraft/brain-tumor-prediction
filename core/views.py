from django.shortcuts import render, redirect
from .models import MRIImage
from django.core.files.storage import FileSystemStorage
import os
import tensorflow as tf
import numpy as np
from PIL import Image
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required

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

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('core:index')
        else:
            return render(request, 'core/login.html', {'form': form, 'error': 'Invalid username or password'})
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('core:home')

@login_required(login_url='core:login')
def index(request):
    images = MRIImage.objects.all().order_by('-uploaded_at')[:5]
    return render(request, 'core/index.html', {'images': images})

@login_required(login_url='core:login')
def upload_image(request):
    if request.method == 'POST' and request.FILES.get('mri_image'):
        mri_file = request.FILES['mri_image']
        mri_instance = MRIImage.objects.create(image=mri_file)
        
        # Predict
        prediction, probability = predict_tumor(mri_instance.image.path)
        
        mri_instance.prediction = prediction
        mri_instance.probability = float(probability)
        mri_instance.save()
        
        return render(request, 'core/index.html', {
            'prediction': prediction,
            'probability': f"{probability*100:.2f}%",
            'image_url': mri_instance.image.url,
            'images': MRIImage.objects.all().order_by('-uploaded_at')[:5] # Context for list
        })
    
    return redirect('core:index')

def predict_tumor(image_path):
    model = get_model()
    if model is None:
        return "Model Not Found", 0.0
    
    try:
        img = Image.open(image_path).resize((150, 150))
        img_array = np.array(img.convert('RGB')) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        # Disable progress bar
        prediction_val = model.predict(img_array, verbose=0)[0][0]
        
        if prediction_val > 0.5:
            return "Tumor Detected", prediction_val
        else:
            return "No Tumor", 1 - prediction_val
    except Exception as e:
        print(f"Error during prediction: {e}")
        return "Prediction Error", 0.0
