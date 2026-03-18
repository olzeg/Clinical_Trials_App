from django import forms
from .models import (
    Patient,
    Drug,
    ClinicalTrial,
    SideEffect,
    TrialParticipation,
    UndesirableEffect,
)

class ContactForm(forms.Form):
    name = forms.CharField(label="Imię", max_length=100)
    message = forms.CharField(label="Wiadomość", widget=forms.Textarea)

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = "__all__"


class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = "__all__"


class ClinicalTrialForm(forms.ModelForm):
    class Meta:
        model = ClinicalTrial
        fields = "__all__"


class SideEffectForm(forms.ModelForm):
    class Meta:
        model = SideEffect
        fields = "__all__"


class TrialParticipationForm(forms.ModelForm):
    class Meta:
        model = TrialParticipation
        fields = "__all__"


class UndesirableEffectForm(forms.ModelForm):
    class Meta:
        model = UndesirableEffect
        fields = "__all__"