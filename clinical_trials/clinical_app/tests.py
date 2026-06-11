from django.contrib.auth.models import User
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .models import ClinicalTrial, Drug, Patient, SideEffect, TrialParticipation, UndesirableEffect


class AuthenticatedTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="StrongPass123!")
        self.client.force_login(self.user)


class AuthenticationTests(TestCase):
    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_register_creates_account_and_signs_user_in(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_logout_requires_post(self):
        user = User.objects.create_user(username="tester", password="StrongPass123!")
        self.client.force_login(user)

        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)


class HomePageTests(AuthenticatedTestCase):
    def test_home_contains_main_navigation_links(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, reverse("patient_list"))
        self.assertContains(response, reverse("drug_list"))
        self.assertContains(response, reverse("clinical_trial_list"))
        self.assertContains(response, reverse("edit_database"))


class ObjectListFilteringAndPaginationTests(AuthenticatedTestCase):
    def test_patient_list_paginates_with_get_parameters(self):
        for index in range(15):
            Patient.objects.create(
                name=f"Patient{index}",
                surname="Test",
                age=20 + index,
                gender="F" if index % 2 else "M",
                weight="70.00",
                height="170.00",
            )

        response = self.client.get(reverse("patient_list"), {"per_page": "6", "page": "2"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["object_cards"]), 6)
        self.assertContains(response, "per_page=6&page=1")
        self.assertContains(response, "Go to page")

    def test_patient_list_filters_are_read_from_get_and_prefill_form(self):
        Patient.objects.create(
            name="Anna",
            surname="Nowak",
            age=42,
            gender="F",
            weight="63.50",
            height="168.00",
        )
        Patient.objects.create(
            name="Jan",
            surname="Kowalski",
            age=28,
            gender="M",
            weight="82.00",
            height="181.00",
        )

        response = self.client.get(
            reverse("patient_list"),
            {"q": "Anna", "min_value": "40", "max_value": "50", "per_page": "12"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anna Nowak")
        self.assertNotContains(response, "Jan Kowalski")
        self.assertContains(response, 'name="q" value="Anna"', html=False)
        self.assertContains(response, 'name="min_value" value="40"', html=False)
        self.assertContains(response, 'name="max_value" value="50"', html=False)


class InteractiveDetailViewsTests(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            name="Anna",
            surname="Nowak",
            age=42,
            gender="F",
            weight="63.50",
            height="168.00",
        )
        self.drug = Drug.objects.create(
            name="CardioX",
            active_agent="Xylomed",
            producer="MedNova",
        )
        self.trial = ClinicalTrial.objects.create(
            name="Heart Recovery",
            phase="II",
            category="Cardiology",
            beginning_date="2026-01-10",
            end_date="2026-09-10",
            status="ongoing",
        )
        self.side_effect = SideEffect.objects.create(
            name="Headache",
            category="Neurological",
            description="Sample description",
        )
        TrialParticipation.objects.create(
            patient=self.patient,
            trial=self.trial,
            drug=self.drug,
            dose="10 mg",
            inclusion_date="2026-01-15",
        )
        UndesirableEffect.objects.create(
            patient=self.patient,
            trial=self.trial,
            drug=self.drug,
            side_effect=self.side_effect,
            date_of_occurrence="2026-02-01",
            grade=2,
            comment="Observed after 2 weeks",
        )

    def test_drug_detail_view_contains_dashboard(self):
        response = self.client.get(reverse("drug_detail", args=[self.drug.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clinical trials using this drug")
        self.assertContains(response, "Side effect distribution")

    def test_clinical_trial_detail_view_contains_dashboard(self):
        response = self.client.get(reverse("clinical_trial_detail", args=[self.trial.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trial profile")
        self.assertContains(response, "Adverse event distribution")

    def test_patient_detail_view_contains_participation_data(self):
        response = self.client.get(reverse("patient_detail", args=[self.patient.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient profile")
        self.assertContains(response, "Heart Recovery")


class DataToolsTests(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            name="Anna",
            surname="Nowak",
            age=42,
            gender="F",
            weight="63.50",
            height="168.00",
        )
        self.drug = Drug.objects.create(
            name="CardioX",
            active_agent="Xylomed",
            producer="MedNova",
        )
        self.trial = ClinicalTrial.objects.create(
            name="Heart Recovery",
            phase="II",
            category="Cardiology",
            beginning_date="2026-01-10",
            end_date="2026-09-10",
            status="ongoing",
        )
        TrialParticipation.objects.create(
            patient=self.patient,
            trial=self.trial,
            drug=self.drug,
            dose="10 mg",
            inclusion_date="2026-01-15",
        )

    def test_export_patient_participations_returns_csv(self):
        response = self.client.get(reverse("export_patient_participations"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("patient_participations.csv", response["Content-Disposition"])
        self.assertContains(response, "Anna Nowak")
        self.assertContains(response, "Heart Recovery")

    def test_trial_status_chart_returns_svg(self):
        response = self.client.get(reverse("trial_status_chart_svg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertContains(response, "<svg", html=False)
        self.assertContains(response, "Clinical trials by status")

    def test_upload_text_file_extracts_and_imports_patient_rows(self):
        uploaded_file = SimpleUploadedFile(
            "patients.csv",
            b"name,surname,age,gender,weight,height\nJan,Kowalski,35,M,82.5,181\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("data_tools"),
            {"data_file": uploaded_file, "import_patients": "on"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jan")
        self.assertEqual(Patient.objects.filter(name="Jan", surname="Kowalski").count(), 1)

    def test_upload_text_file_accepts_polish_patient_headers(self):
        uploaded_file = SimpleUploadedFile(
            "pacjenci.csv",
            "imię;nazwisko;wiek;płeć;waga;wzrost\nEwa;Zielinska;31;K;58,5;166\n".encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("data_tools"),
            {"data_file": uploaded_file, "import_patients": "on"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ewa")
        self.assertEqual(Patient.objects.filter(name="Ewa", surname="Zielinska").count(), 1)

    def test_upload_rejects_images(self):
        uploaded_file = SimpleUploadedFile(
            "image.png",
            b"fake image",
            content_type="image/png",
        )

        response = self.client.post(reverse("data_tools"), {"data_file": uploaded_file})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Image files are not accepted.")
