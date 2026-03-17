from django.contrib import admin
from .models import Patient, Drug, ClinicalTrial, SideEffect, TrialParticipation, UndesirableEffect

admin.site.register(Patient)
admin.site.register(Drug)
admin.site.register(ClinicalTrial)
admin.site.register(SideEffect)
admin.site.register(TrialParticipation)
admin.site.register(UndesirableEffect)