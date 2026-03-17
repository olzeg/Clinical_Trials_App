from django.shortcuts import render
from .forms import ContactForm

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