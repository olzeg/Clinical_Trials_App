from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact_view, name='contact'),
    path("patients/add/", views.add_patient, name="add_patient"),
    path("patients/", views.patient_list, name="patient_list"),
]