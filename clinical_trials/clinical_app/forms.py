from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(label="Imię", max_length=100)
    message = forms.CharField(label="Wiadomość", widget=forms.Textarea)