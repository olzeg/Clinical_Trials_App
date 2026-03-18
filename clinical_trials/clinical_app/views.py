from django.shortcuts import render, redirect
from .forms import ContactForm
from .models import Patient
from .forms import PatientForm

def home(request):
    return render(request, "home.html")

def contact_view(request):
    submitted_data = None

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            submitted_data = {
                "name": form.cleaned_data["name"],
                "message": form.cleaned_data["message"],
            }
    else:
        form = ContactForm()

    return render(request, "contact.html", {
        "form": form,
        "submitted_data": submitted_data,
    })

def add_patient(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("patient_list")
    else:
        form = PatientForm()

    return render(request, "clinical_app/add_patient.html", {"form": form})


def patient_list(request):
    patients = Patient.objects.all()
    return render(request, "clinical_app/patient_list.html", {"patients": patients})