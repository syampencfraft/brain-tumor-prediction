from django.shortcuts import render, redirect
from .models import MRIImage
from django.core.files.storage import FileSystemStorage
import os
import tensorflow as tf
import numpy as np
from PIL import Image

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

def index(request):
    images = MRIImage.objects.all().order_by('-uploaded_at')[:5]
    return render(request, 'core/index.html', {'images': images})

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
            'image_url': mri_instance.image.url
        })
    
    return redirect('index')

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
