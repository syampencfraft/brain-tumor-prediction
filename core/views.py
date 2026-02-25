from django.shortcuts import render, redirect
from .models import MRIImage
import os
import numpy as np
from PIL import Image
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
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

def predict_tumor(image_path):
    if not API_KEY:
        return "Config Error", 0.0, "Gemini API key not found. Please check your .env file."
    
    try:
        # Dynamic model selection to avoid 404 errors
        available_models = [m.name for m in genai.list_models() 
                            if 'generateContent' in m.supported_generation_methods]
        
        # Prefer flash models
        model_name = 'models/gemini-1.5-flash' # Default attempt
        flash_models = [m for m in available_models if 'flash' in m]
        if flash_models:
            model_name = flash_models[0]
        elif available_models:
            model_name = available_models[0]

        model = genai.GenerativeModel(model_name)
        img = Image.open(image_path)
        
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
        print(f"Gemini Error: {e}")
        return "AI Error", 0.0, f"Error communicating with AI: {str(e)}"
