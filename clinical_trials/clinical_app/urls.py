from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import path

from . import views

protected_urlpatterns = [
    path("", login_required(views.home), name="home"),
    path("data-guide/", login_required(views.data_guide), name="data_guide"),
    path("data-tools/", login_required(views.data_tools), name="data_tools"),
    path(
        "exports/patient-participations.csv/",
        login_required(views.export_patient_participations),
        name="export_patient_participations",
    ),
    path(
        "charts/trial-status.svg/",
        login_required(views.trial_status_chart_svg),
        name="trial_status_chart_svg",
    ),
    path("edytuj-baze-danych/", login_required(views.edit_database), name="edit_database"),
    path("patients/add/", login_required(views.add_patient), name="add_patient"),
    path("patients/", login_required(views.patient_list), name="patient_list"),
    path("patients/<int:pk>/", login_required(views.patient_detail), name="patient_detail"),
    path("drugs/add/", login_required(views.add_drug), name="add_drug"),
    path("drugs/", login_required(views.drug_list), name="drug_list"),
    path("drugs/<int:pk>/", login_required(views.drug_detail), name="drug_detail"),
    path("clinical-trials/add/", login_required(views.add_clinical_trial), name="add_clinical_trial"),
    path("clinical-trials/", login_required(views.clinical_trial_list), name="clinical_trial_list"),
    path(
        "clinical-trials/<int:pk>/",
        login_required(views.clinical_trial_detail),
        name="clinical_trial_detail",
    ),
    path("side-effects/add/", login_required(views.add_side_effect), name="add_side_effect"),
    path("side-effects/", login_required(views.side_effect_list), name="side_effect_list"),
    path(
        "trial-participations/add/",
        login_required(views.add_trial_participation),
        name="add_trial_participation",
    ),
    path(
        "trial-participations/",
        login_required(views.trial_participation_list),
        name="trial_participation_list",
    ),
    path(
        "undesirable-effects/add/",
        login_required(views.add_undesirable_effect),
        name="add_undesirable_effect",
    ),
    path(
        "undesirable-effects/",
        login_required(views.undesirable_effect_list),
        name="undesirable_effect_list",
    ),
]

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
] + protected_urlpatterns
