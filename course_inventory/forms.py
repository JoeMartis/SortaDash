# SPDX-License-Identifier: AGPL-3.0-or-later
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SavedView


class CourseTagForm(forms.Form):
    key = forms.CharField(max_length=64, label=_("Tag key"))
    value = forms.CharField(max_length=128, label=_("Tag value"))


class SavedViewForm(forms.ModelForm):
    class Meta:
        model = SavedView
        fields = ("name", "shared")
        labels = {"name": _("Name"), "shared": _("Shared with other staff")}
