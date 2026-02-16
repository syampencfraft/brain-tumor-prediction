from django.db import models

class MRIImage(models.Model):
    image = models.ImageField(upload_to='mri_scans/')
    prediction = models.CharField(max_length=50, blank=True, null=True)
    probability = models.FloatField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MRI Scan {self.id} - {self.prediction}"
