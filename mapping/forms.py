from django import forms
from .models import SpatialVector

class VectorFileUploadForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea, required=False)