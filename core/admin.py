from django.contrib import admin
from .models import MRIImage

@admin.register(MRIImage)
class MRIImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'prediction', 'probability', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
