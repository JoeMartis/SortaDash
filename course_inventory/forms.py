from django import forms

from .models import SavedView


class CourseTagForm(forms.Form):
    key = forms.CharField(max_length=64)
    value = forms.CharField(max_length=128)


class SavedViewForm(forms.ModelForm):
    class Meta:
        model = SavedView
        fields = ("name", "shared")
