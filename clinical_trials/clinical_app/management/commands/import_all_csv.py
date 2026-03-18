import csv
import os
from decimal import Decimal
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from clinical_app.models import (
    Patient,
    Drug,
    ClinicalTrial,
    SideEffect,
    TrialParticipation,
    UndesirableEffect,
)


class Command(BaseCommand):
    help = "Import danych z plików CSV do modeli Django z zachowaniem ID z plików"

    def handle(self, *args, **kwargs):
        data_dir = os.path.join(settings.BASE_DIR, "data")

        self.import_patients(os.path.join(data_dir, "Patient.csv"))
        self.import_drugs(os.path.join(data_dir, "Drug.csv"))
        self.import_clinical_trials(os.path.join(data_dir, "ClinicalTrial.csv"))
        self.import_side_effects(os.path.join(data_dir, "SideEffect.csv"))
        self.import_trial_participations(os.path.join(data_dir, "TrialParticipation.csv"))
        self.import_undesirable_effects(os.path.join(data_dir, "UndesirableEffect.csv"))

        self.stdout.write(self.style.SUCCESS("Import wszystkich danych zakończony."))

    def parse_date(self, value):
        if not value or not value.strip():
            return None

        value = value.strip()
        possible_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"]

        for fmt in possible_formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Nieprawidłowy format daty: {value}")

    def parse_decimal(self, value):
        if value is None or not str(value).strip():
            return None
        return Decimal(str(value).replace(",", ".").strip())

    def import_patients(self, filepath):
        with open(filepath, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                Patient.objects.update_or_create(
                    id=int(row["id"]),
                    defaults={
                        "name": row["name"].strip(),
                        "surname": row["surname"].strip(),
                        "age": int(row["age"]),
                        "gender": row["gender"].strip(),
                        "weight": self.parse_decimal(row["weight"]),
                        "height": self.parse_decimal(row["height"]),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zaimportowano Patient"))

    def import_drugs(self, filepath):
        with open(filepath, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                Drug.objects.update_or_create(
                    id=int(row["id"]),
                    defaults={
                        "name": row["name"].strip(),
                        "active_agent": row["active_agent"].strip(),
                        "producer": row["producer"].strip(),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zaimportowano Drug"))

    def import_clinical_trials(self, filepath):
        with open(filepath, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                ClinicalTrial.objects.update_or_create(
                    id=int(row["id"]),
                    defaults={
                        "name": row["name"].strip(),
                        "phase": row["phase"].strip(),
                        "category": row["category"].strip(),
                        "beginning_date": self.parse_date(row["beginning_date"]),
                        "end_date": self.parse_date(row["end_date"]),
                        "status": row["status"].strip(),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zaimportowano ClinicalTrial"))

    def import_side_effects(self, filepath):
        with open(filepath, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                SideEffect.objects.update_or_create(
                    id=int(row["id"]),
                    defaults={
                        "name": row["name"].strip(),
                        "category": row["category"].strip(),
                        "description": row["description"].strip(),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zaimportowano SideEffect"))

    def import_trial_participations(self, filepath):
        with open(filepath, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                patient = Patient.objects.get(id=int(row["patient_id"]))
                trial = ClinicalTrial.objects.get(id=int(row["trial_id"]))
                drug = Drug.objects.get(id=int(row["drug_id"]))

                TrialParticipation.objects.update_or_create(
                    id=int(row["id"]),
                    defaults={
                        "patient": patient,
                        "trial": trial,
                        "drug": drug,
                        "dose": row["dose"].strip(),
                        "inclusion_date": self.parse_date(row["inclusion_date"]),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zaimportowano TrialParticipation"))

    def import_undesirable_effects(self, filepath):
        with open(filepath, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                patient = Patient.objects.get(id=int(row["patient_id"]))
                trial = ClinicalTrial.objects.get(id=int(row["trial_id"]))
                drug = Drug.objects.get(id=int(row["drug_id"]))
                side_effect = SideEffect.objects.get(id=int(row["side_effect_id"]))

                UndesirableEffect.objects.update_or_create(
                    id=int(row["id"]),
                    defaults={
                        "patient": patient,
                        "trial": trial,
                        "drug": drug,
                        "side_effect": side_effect,
                        "date_of_occurrence": self.parse_date(row["date_of_occurrence"]),
                        "grade": int(row["grade"]),
                        "comment": row["comment"].strip(),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zaimportowano UndesirableEffect"))