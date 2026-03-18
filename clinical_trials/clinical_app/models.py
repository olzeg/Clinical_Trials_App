from django.db import models


class Patient(models.Model):
    SEX_CHOICES = [
        ("F", "Female"),
        ("M", "Male"),
    ]

    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=1, choices=SEX_CHOICES)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    height = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.name} {self.surname}"


class Drug(models.Model):
    name = models.CharField(max_length=200)
    active_agent = models.CharField(max_length=200)
    producer = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class ClinicalTrial(models.Model):
    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("suspended", "Suspended"),
        ("terminated", "Terminated"),
    ]

    PHASE_CHOICES = [
        ("I", "Phase I"),
        ("II", "Phase II"),
        ("III", "Phase III"),
        ("IV", "Phase IV"),
    ]

    name = models.CharField(max_length=200)
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES)
    category = models.CharField(max_length=200)
    beginning_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return self.name


class SideEffect(models.Model):
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class TrialParticipation(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="participations"
    )
    trial = models.ForeignKey(
        ClinicalTrial,
        on_delete=models.CASCADE,
        related_name="participations"
    )
    drug = models.ForeignKey(
        Drug,
        on_delete=models.CASCADE,
        related_name="participations"
    )
    dose = models.CharField(max_length=100)
    inclusion_date = models.DateField()

    def __str__(self):
        return f"{self.patient} - {self.trial}"


class UndesirableEffect(models.Model):
    GRADE_CHOICES = [
        (0, "0"),
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="undesirable_effects"
    )
    trial = models.ForeignKey(
        ClinicalTrial,
        on_delete=models.CASCADE,
        related_name="undesirable_effects"
    )
    drug = models.ForeignKey(
        Drug,
        on_delete=models.CASCADE,
        related_name="undesirable_effects"
    )
    side_effect = models.ForeignKey(
        SideEffect,
        on_delete=models.CASCADE,
        related_name="undesirable_effects"
    )
    date_of_occurrence = models.DateField()
    grade = models.IntegerField(choices=GRADE_CHOICES)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.side_effect} - {self.patient}"