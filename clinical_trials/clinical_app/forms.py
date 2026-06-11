from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    ClinicalTrial,
    Drug,
    Patient,
    SideEffect,
    TrialParticipation,
    UndesirableEffect,
)


class BootstrapFormMixin:
    """Adds Bootstrap classes to Django form widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = "form-control"

            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"

            existing_classes = widget.attrs.get("class", "").strip()
            widget.attrs["class"] = f"{existing_classes} {css_class}".strip()

            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 4)

            if isinstance(widget, forms.DateInput):
                widget.input_type = "date"


class AccountCreationForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(label="Email address", required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class PatientForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Patient
        fields = "__all__"


class DrugForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Drug
        fields = "__all__"


class ClinicalTrialForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ClinicalTrial
        fields = "__all__"
        widgets = {
            "beginning_date": forms.DateInput(),
            "end_date": forms.DateInput(),
        }


class SideEffectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SideEffect
        fields = "__all__"


class TrialParticipationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TrialParticipation
        fields = "__all__"
        widgets = {
            "inclusion_date": forms.DateInput(),
        }


class UndesirableEffectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = UndesirableEffect
        fields = "__all__"
        widgets = {
            "date_of_occurrence": forms.DateInput(),
        }


class DataUploadForm(BootstrapFormMixin, forms.Form):
    data_file = forms.FileField(
        label="Data file",
        help_text="Upload a CSV, TSV or TXT file. Image files are not accepted.",
    )
    import_patients = forms.BooleanField(
        label="Create patient records from matching rows",
        required=False,
    )

    allowed_extensions = (".csv", ".tsv", ".txt")
    blocked_content_types = ("image/",)

    def clean_data_file(self):
        data_file = self.cleaned_data["data_file"]
        filename = data_file.name.lower()
        content_type = getattr(data_file, "content_type", "") or ""

        if content_type.startswith(self.blocked_content_types):
            raise forms.ValidationError("Image files are not accepted.")

        if not filename.endswith(self.allowed_extensions):
            raise forms.ValidationError("Upload a CSV, TSV or TXT file.")

        return data_file
