from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
from io import StringIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import (
    AccountCreationForm,
    ClinicalTrialForm,
    DataUploadForm,
    DrugForm,
    PatientForm,
    SideEffectForm,
    TrialParticipationForm,
    UndesirableEffectForm,
)
from .models import (
    ClinicalTrial,
    Drug,
    Patient,
    SideEffect,
    TrialParticipation,
    UndesirableEffect,
)


MODEL_CONFIG = {
    "patient": {
        "form_class": PatientForm,
        "queryset": Patient.objects.all,
        "search_fields": ["name", "surname", "gender"],
        "numeric_filter": {"field": "age", "label": "Age"},
        "title_plural": "Patients",
        "title_singular": "patient",
        "icon": "fa-user-injured",
    },
    "drug": {
        "form_class": DrugForm,
        "queryset": Drug.objects.all,
        "search_fields": ["name", "active_agent", "producer"],
        "numeric_filter": {"field": "id", "label": "ID"},
        "title_plural": "Drugs",
        "title_singular": "drug",
        "icon": "fa-pills",
    },
    "clinical_trial": {
        "form_class": ClinicalTrialForm,
        "queryset": ClinicalTrial.objects.all,
        "search_fields": ["name", "phase", "category", "status"],
        "numeric_filter": {"field": "id", "label": "ID"},
        "title_plural": "Clinical Trials",
        "title_singular": "clinical trial",
        "icon": "fa-flask-vial",
    },
    "side_effect": {
        "form_class": SideEffectForm,
        "queryset": SideEffect.objects.all,
        "search_fields": ["name", "category", "description"],
        "numeric_filter": {"field": "id", "label": "ID"},
        "title_plural": "Side Effects",
        "title_singular": "side effect",
        "icon": "fa-triangle-exclamation",
    },
    "trial_participation": {
        "form_class": TrialParticipationForm,
        "queryset": TrialParticipation.objects.select_related("patient", "trial", "drug").all,
        "search_fields": [
            "patient__name",
            "patient__surname",
            "trial__name",
            "drug__name",
            "dose",
        ],
        "numeric_filter": {"field": "id", "label": "ID"},
        "title_plural": "Trial Participations",
        "title_singular": "trial participation",
        "icon": "fa-user-group",
    },
    "undesirable_effect": {
        "form_class": UndesirableEffectForm,
        "queryset": UndesirableEffect.objects.select_related(
            "patient", "trial", "drug", "side_effect"
        ).all,
        "search_fields": [
            "patient__name",
            "patient__surname",
            "trial__name",
            "drug__name",
            "side_effect__name",
            "comment",
        ],
        "numeric_filter": {"field": "grade", "label": "Grade"},
        "title_plural": "Adverse Events",
        "title_singular": "adverse event",
        "icon": "fa-notes-medical",
    },
}

DETAIL_VIEW_NAMES = {
    "patient": "patient_detail",
    "drug": "drug_detail",
    "clinical_trial": "clinical_trial_detail",
}

PER_PAGE_CHOICES = [6, 12, 24, 48]

EXPORT_COLUMNS = [
    ("patient_id", "Patient ID"),
    ("patient", "Patient"),
    ("age", "Age"),
    ("gender", "Gender"),
    ("trial", "Clinical trial"),
    ("phase", "Phase"),
    ("status", "Trial status"),
    ("drug", "Drug"),
    ("dose", "Dose"),
    ("inclusion_date", "Inclusion date"),
]

UPLOAD_PREVIEW_LIMIT = 10

AGE_FILTERS = [
    {"id": "all", "label": "All ages"},
    {"id": "under_30", "label": "Under 30"},
    {"id": "30_49", "label": "30-49"},
    {"id": "50_64", "label": "50-64"},
    {"id": "65_plus", "label": "65+"},
]

AGE_LABELS = {
    "all": "All ages",
    "under_30": "Under 30",
    "30_49": "30-49",
    "50_64": "50-64",
    "65_plus": "65+",
}


def register(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = AccountCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. You are now signed in.")
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = AccountCreationForm()

    return render(request, "registration/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


def _age_bucket(age):
    if age < 30:
        return "under_30"
    if age < 50:
        return "30_49"
    if age < 65:
        return "50_64"
    return "65_plus"


def _format_date(value):
    return value.strftime("%Y-%m-%d") if value else "Not scheduled"


def _trial_status_badge(status, label):
    tone_map = {
        "ongoing": "ongoing",
        "planned": "planned",
        "completed": "completed",
        "terminated": "cancelled",
        "suspended": "cancelled",
    }
    return {
        "label": label,
        "tone": tone_map.get(status, "completed"),
    }


def _serialize_patient_effect_profile(patient, effects):
    patient_effects = [effect for effect in effects if effect.patient_id == patient.id]
    unique_effect_names = sorted({effect.side_effect.name for effect in patient_effects})
    return {
        "patient": str(patient),
        "age": patient.age,
        "age_group": _age_bucket(patient.age),
        "has_effect": bool(unique_effect_names),
        "effect_names": unique_effect_names,
    }


def _build_chart_payload(records):
    return {
        "filters": AGE_FILTERS,
        "defaultFilter": "all",
        "metrics": [
            {"id": "effect_rate", "label": "Patients with side effects"},
            {"id": "top_side_effects", "label": "Most common side effects"},
        ],
        "defaultMetric": "effect_rate",
        "records": records,
        "emptyMessage": "No side effect data for the current filter.",
    }


def _serialize_effect_event(effect):
    age_group = _age_bucket(effect.patient.age)
    return {
        "side_effect": effect.side_effect.name,
        "side_effect_category": effect.side_effect.category or "Uncategorized",
        "grade": f"Grade {effect.grade}",
        "gender": effect.patient.get_gender_display(),
        "age_group": AGE_LABELS[age_group],
        "phase": effect.trial.get_phase_display(),
        "trial_status": effect.trial.get_status_display(),
        "trial_category": effect.trial.category,
        "trial_name": effect.trial.name,
        "drug_name": effect.drug.name,
    }


def _unique_values(records, key):
    values = sorted({record[key] for record in records if record.get(key)})
    return [{"id": value, "label": value} for value in values]


def _build_donut_chart_payload(records, group_fields, filter_fields):
    return {
        "defaultGroup": group_fields[0]["id"] if group_fields else "",
        "groupOptions": group_fields,
        "filters": [
            {
                "id": field["id"],
                "label": field["label"],
                "options": [{"id": "all", "label": f"All {field['label'].lower()}"}] + _unique_values(records, field["id"]),
            }
            for field in filter_fields
        ],
        "records": records,
        "emptyMessage": "No adverse event records for the selected filter set.",
    }


def _object_summary(model_key, obj):
    if model_key == "drug":
        return obj.active_agent
    if model_key == "clinical_trial":
        return f"{obj.get_phase_display()} | {obj.get_status_display()}"
    if model_key == "patient":
        return f"Age {obj.age} | {obj.get_gender_display()}"
    if model_key == "side_effect":
        return obj.category
    if model_key == "trial_participation":
        return f"{obj.drug} | {obj.trial}"
    if model_key == "undesirable_effect":
        return f"{obj.side_effect} | grade {obj.grade}"
    return ""


def _get_int_param(request, name, default=None):
    value = request.GET.get(name, "")
    if value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _filter_object_queryset(request, queryset, config):
    search_query = request.GET.get("q", "").strip()
    min_value = _get_int_param(request, "min_value")
    max_value = _get_int_param(request, "max_value")
    numeric_field = config["numeric_filter"]["field"]

    if search_query:
        search_filter = Q()
        for field_name in config["search_fields"]:
            search_filter |= Q(**{f"{field_name}__icontains": search_query})
        queryset = queryset.filter(search_filter)

    if min_value is not None:
        queryset = queryset.filter(**{f"{numeric_field}__gte": min_value})

    if max_value is not None:
        queryset = queryset.filter(**{f"{numeric_field}__lte": max_value})

    return queryset, {
        "q": search_query,
        "min_value": request.GET.get("min_value", "").strip(),
        "max_value": request.GET.get("max_value", "").strip(),
    }


def _get_per_page(request):
    per_page = _get_int_param(request, "per_page", 12)
    return per_page if per_page in PER_PAGE_CHOICES else 12


def _querystring_without(request, *excluded_keys):
    query = request.GET.copy()
    for key in excluded_keys:
        query.pop(key, None)
    return query.urlencode()


def _model_sections():
    sections = []
    for key, config in MODEL_CONFIG.items():
        sections.append({
            "title_plural": config["title_plural"],
            "title_singular": config["title_singular"],
            "add_url_name": f"add_{key}",
            "list_url_name": f"{key}_list",
            "icon": config["icon"],
        })
    return sections


def _patient_export_rows():
    participations = (
        TrialParticipation.objects.select_related("patient", "trial", "drug")
        .order_by("patient__surname", "patient__name", "trial__name")
    )
    for participation in participations:
        patient = participation.patient
        trial = participation.trial
        yield {
            "patient_id": patient.id,
            "patient": str(patient),
            "age": patient.age,
            "gender": patient.get_gender_display(),
            "trial": trial.name,
            "phase": trial.get_phase_display(),
            "status": trial.get_status_display(),
            "drug": participation.drug.name,
            "dose": participation.dose,
            "inclusion_date": participation.inclusion_date,
        }


def _decode_uploaded_file(uploaded_file):
    raw_data = uploaded_file.read()
    for encoding in ("utf-8-sig", "utf-8", "cp1250"):
        try:
            return raw_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_data.decode("utf-8", errors="replace")


def _read_tabular_text(text):
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(StringIO(text), dialect=dialect)
    rows = []
    for row in reader:
        cleaned_row = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }
        if any(cleaned_row.values()):
            rows.append(cleaned_row)
    return rows


def _patient_data_from_row(row):
    aliases = {
        "name": ("name", "first_name", "imie", "imię"),
        "surname": ("surname", "last_name", "nazwisko"),
        "age": ("age", "wiek"),
        "gender": ("gender", "sex", "plec", "płeć"),
        "weight": ("weight", "waga"),
        "height": ("height", "wzrost"),
    }

    def pick(field):
        for alias in aliases[field]:
            if alias in row and row[alias] != "":
                return row[alias]
        return ""

    gender = pick("gender").upper()
    if gender in {"K", "FEMALE", "WOMAN", "KOBIETA"}:
        gender = "F"
    elif gender in {"M", "MALE", "MAN", "MEZCZYZNA", "MĘŻCZYZNA"}:
        gender = "M"

    data = {
        "name": pick("name"),
        "surname": pick("surname"),
        "age": pick("age"),
        "gender": gender,
        "weight": pick("weight").replace(",", "."),
        "height": pick("height").replace(",", "."),
    }
    return data


def _validate_patient_data(data):
    required_fields = ["name", "surname", "age", "gender", "weight", "height"]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return False, f"Missing: {', '.join(missing_fields)}"

    try:
        age = int(data["age"])
        weight = Decimal(data["weight"])
        height = Decimal(data["height"])
    except (ValueError, InvalidOperation):
        return False, "Age, weight and height must be numeric."

    if age < 0 or data["gender"] not in {"F", "M"}:
        return False, "Age must be positive and gender must be F or M."

    data["age"] = age
    data["weight"] = weight
    data["height"] = height
    return True, "Ready"


def _extract_patient_rows(rows, should_import):
    extracted = []
    created_count = 0

    for index, row in enumerate(rows, start=1):
        patient_data = _patient_data_from_row(row)
        is_valid, status = _validate_patient_data(patient_data)

        if should_import and is_valid:
            Patient.objects.create(**patient_data)
            created_count += 1
            status = "Imported"

        extracted.append({
            "row_number": index,
            "data": patient_data,
            "is_valid": is_valid,
            "status": status,
        })

    return extracted, created_count


def home(request):
    status_counts = {
        item["status"]: item["total"]
        for item in ClinicalTrial.objects.values("status").annotate(total=Count("id"))
    }
    active_trials = status_counts.get("ongoing", 0)
    planned_trials = status_counts.get("planned", 0)
    completed_trials = status_counts.get("completed", 0)
    patient_total = Patient.objects.count()
    drug_total = Drug.objects.count()
    trial_total = ClinicalTrial.objects.count()
    participation_total = TrialParticipation.objects.count()
    side_effect_total = SideEffect.objects.count()
    adverse_event_total = UndesirableEffect.objects.count()
    patients_with_events = (
        UndesirableEffect.objects.values("patient_id").distinct().count()
    )

    dashboard_stats = [
        {
            "label": "Patients",
            "value": patient_total,
            "note": "Registered patient profiles",
            "icon": "fa-user-injured",
            "url_name": "patient_list",
        },
        {
            "label": "Drugs",
            "value": drug_total,
            "note": "Treatments stored in the database",
            "icon": "fa-pills",
            "url_name": "drug_list",
        },
        {
            "label": "Clinical trials",
            "value": trial_total,
            "note": f"{active_trials} ongoing, {planned_trials} planned",
            "icon": "fa-flask-vial",
            "url_name": "clinical_trial_list",
        },
        {
            "label": "Participations",
            "value": participation_total,
            "note": "Patient-trial-drug links",
            "icon": "fa-user-group",
            "url_name": "trial_participation_list",
        },
        {
            "label": "Side effects",
            "value": side_effect_total,
            "note": "Defined effect dictionary",
            "icon": "fa-triangle-exclamation",
            "url_name": "side_effect_list",
        },
        {
            "label": "Adverse events",
            "value": adverse_event_total,
            "note": f"{patients_with_events} patients with reports",
            "icon": "fa-notes-medical",
            "url_name": "undesirable_effect_list",
        },
    ]

    trial_status_cards = [
        {
            "label": label,
            "value": status_counts.get(status, 0),
            "tone": _trial_status_badge(status, label)["tone"],
            "icon": "fa-circle",
        }
        for status, label in ClinicalTrial.STATUS_CHOICES
    ]

    recent_events = (
        UndesirableEffect.objects.select_related("patient", "trial", "drug", "side_effect")
        .order_by("-date_of_occurrence")[:6]
    )

    context = {
        "dashboard_stats": dashboard_stats,
        "trial_status_cards": trial_status_cards,
        "recent_events": recent_events,
        "completed_trials": completed_trials,
    }
    return render(request, "home.html", context)


def export_patient_participations(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="patient_participations.csv"'
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow([label for _, label in EXPORT_COLUMNS])
    for row in _patient_export_rows():
        writer.writerow([row[key] for key, _ in EXPORT_COLUMNS])

    return response


def trial_status_chart_svg(request):
    counts = {
        item["status"]: item["total"]
        for item in ClinicalTrial.objects.values("status").annotate(total=Count("id"))
    }
    values = [
        (label, counts.get(status, 0), _trial_status_badge(status, label)["tone"])
        for status, label in ClinicalTrial.STATUS_CHOICES
    ]
    max_value = max([value for _, value, _ in values] + [1])
    palette = {
        "ongoing": "#22c55e",
        "planned": "#eab308",
        "completed": "#94a3b8",
        "cancelled": "#ef4444",
    }
    width = 760
    height = 360
    chart_top = 74
    bar_height = 34
    row_gap = 18
    label_x = 38
    bar_x = 220
    max_bar_width = 440
    rows = []

    for index, (label, value, tone) in enumerate(values):
        y = chart_top + index * (bar_height + row_gap)
        bar_width = int(max_bar_width * value / max_value)
        color = palette.get(tone, "#2563eb")
        rows.append(
            f'<text x="{label_x}" y="{y + 23}" class="label">{escape(label)}</text>'
            f'<rect x="{bar_x}" y="{y}" width="{max_bar_width}" height="{bar_height}" rx="8" class="track" />'
            f'<rect x="{bar_x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="8" fill="{color}" />'
            f'<text x="{bar_x + max_bar_width + 24}" y="{y + 23}" class="value">{value}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">Clinical trial status chart</title>
<desc id="desc">Dynamic chart generated from current clinical trial records.</desc>
<style>
    .bg {{ fill: #ffffff; }}
    .title {{ fill: #1f2937; font: 700 24px Arial, sans-serif; }}
    .subtitle {{ fill: #667085; font: 14px Arial, sans-serif; }}
    .label {{ fill: #344054; font: 600 15px Arial, sans-serif; }}
    .value {{ fill: #1f2937; font: 700 16px Arial, sans-serif; }}
    .track {{ fill: #e9eef8; }}
</style>
<rect class="bg" width="100%" height="100%" rx="18" />
<text x="38" y="38" class="title">Clinical trials by status</text>
<text x="38" y="60" class="subtitle">Generated live from the database</text>
{''.join(rows)}
</svg>"""

    return HttpResponse(svg, content_type="image/svg+xml")


def data_tools(request):
    extracted_rows = []
    uploaded_filename = ""
    total_rows = 0
    created_count = 0

    if request.method == "POST":
        form = DataUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["data_file"]
            uploaded_filename = uploaded_file.name
            text = _decode_uploaded_file(uploaded_file)
            parsed_rows = _read_tabular_text(text)
            total_rows = len(parsed_rows)
            extracted_rows, created_count = _extract_patient_rows(
                parsed_rows,
                form.cleaned_data["import_patients"],
            )
            if created_count:
                messages.success(request, f"Imported {created_count} patient records.")
            elif total_rows:
                messages.info(request, f"Extracted {total_rows} rows from the file.")
            else:
                messages.warning(request, "No tabular rows were found in the file.")
    else:
        form = DataUploadForm()

    return render(request, "clinical_app/data_tools.html", {
        "form": form,
        "extracted_rows": extracted_rows[:UPLOAD_PREVIEW_LIMIT],
        "uploaded_filename": uploaded_filename,
        "total_rows": total_rows,
        "created_count": created_count,
        "preview_limit": UPLOAD_PREVIEW_LIMIT,
    })


def edit_database(request):
    return render(request, "clinical_app/edit_database.html", {"sections": _model_sections()})


def data_guide(request):
    guide_sections = [
        {
            "title": "Trial category",
            "icon": "fa-layer-group",
            "description": (
                "The trial category describes the medical area or disease studied in the trial. "
                "It helps group and filter studies by specialty."
            ),
            "details": [
                {"label": "Oncology", "text": "Trials focused on cancer, tumor biology, and anticancer therapies."},
                {"label": "Cardiology", "text": "Trials related to heart disease, blood vessels, and cardiovascular treatment."},
                {"label": "Neurology", "text": "Trials studying the nervous system, for example epilepsy or Parkinson's disease."},
                {"label": "Diabetes", "text": "Trials related to diabetes, glucose control, and metabolic treatment."},
            ],
        },
        {
            "title": "Trial phase",
            "icon": "fa-flask",
            "description": (
                "The phase shows how far the clinical trial has progressed "
                "and what the main goal is at that stage."
            ),
            "details": [
                {"label": "Phase I", "text": "First studies in humans, focused mainly on safety and dose."},
                {"label": "Phase II", "text": "Early check of effectiveness with continued safety monitoring."},
                {"label": "Phase III", "text": "Larger comparison studies before approval."},
                {"label": "Phase IV", "text": "Post-marketing follow-up after the treatment is introduced."},
            ],
        },
        {
            "title": "Trial status",
            "icon": "fa-signal",
            "description": "The status shows what is currently happening with the trial.",
            "details": [
                {"label": "Planned", "text": "The trial is prepared but has not started yet."},
                {"label": "Ongoing", "text": "The trial is active and participants are being monitored."},
                {"label": "Completed", "text": "The study ended according to plan."},
                {"label": "Suspended", "text": "The trial is temporarily paused."},
                {"label": "Terminated", "text": "The trial stopped early and will not continue."},
            ],
        },
        {
            "title": "Side effect category",
            "icon": "fa-triangle-exclamation",
            "description": (
                "The side effect category groups similar adverse events together. "
                "This makes reports easier to compare and analyze."
            ),
            "details": [
                {"label": "Gastrointestinal", "text": "Digestive system symptoms such as nausea, vomiting, or diarrhea."},
                {"label": "Neurological", "text": "Nervous system symptoms such as dizziness, tremor, or sensory changes."},
                {"label": "Dermatological", "text": "Skin-related symptoms such as rash, itching, or redness."},
                {"label": "Cardiovascular", "text": "Heart and circulation symptoms such as arrhythmia or increased blood pressure."},
            ],
        },
        {
            "title": "Adverse event grade",
            "icon": "fa-chart-line",
            "description": "The grade shows how severe the adverse event was for the patient.",
            "details": [
                {"label": "Grade 0", "text": "No adverse event reported."},
                {"label": "Grade 1", "text": "Mild symptoms."},
                {"label": "Grade 2", "text": "Moderate symptoms."},
                {"label": "Grade 3", "text": "Severe symptoms requiring significant medical attention."},
                {"label": "Grade 4", "text": "Life-threatening consequences."},
                {"label": "Grade 5", "text": "Death related to the adverse event."},
            ],
        },
    ]
    return render(request, "clinical_app/data_guide.html", {"guide_sections": guide_sections})


def _add_object(request, model_key):
    config = MODEL_CONFIG[model_key]
    form_class = config["form_class"]

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect(f"{model_key}_list")
    else:
        form = form_class()

    return render(request, "clinical_app/add_object.html", {
        "form": form,
        "title_singular": config["title_singular"],
        "title_plural": config["title_plural"],
        "list_url_name": f"{model_key}_list",
        "icon": config["icon"],
    })


def _object_list(request, model_key):
    config = MODEL_CONFIG[model_key]
    base_queryset = config["queryset"]()
    has_any_objects = base_queryset.exists()
    objects, filter_values = _filter_object_queryset(request, base_queryset, config)

    if not objects.ordered:
        objects = objects.order_by("pk")

    per_page = _get_per_page(request)
    paginator = Paginator(objects, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    paginated_objects = page_obj.object_list
    detail_view_name = DETAIL_VIEW_NAMES.get(model_key)
    object_cards = []

    for obj in paginated_objects:
        object_cards.append({
            "label": str(obj),
            "summary": _object_summary(model_key, obj),
            "detail_url": reverse(detail_view_name, args=[obj.pk]) if detail_view_name else "",
        })

    return render(request, "clinical_app/object_list.html", {
        "objects": paginated_objects,
        "object_cards": object_cards,
        "page_obj": page_obj,
        "paginator": paginator,
        "has_any_objects": has_any_objects,
        "filtered_count": paginator.count,
        "filter_values": filter_values,
        "numeric_filter": config["numeric_filter"],
        "per_page": per_page,
        "per_page_choices": PER_PAGE_CHOICES,
        "querystring_without_page": _querystring_without(request, "page"),
        "querystring_without_page_size": _querystring_without(request, "page", "per_page"),
        "title_plural": config["title_plural"],
        "title_singular": config["title_singular"],
        "add_url_name": f"add_{model_key}",
        "icon": config["icon"],
        "detail_view_name": detail_view_name,
    })


def drug_detail(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    participations = list(
        drug.participations.select_related("patient", "trial").order_by("trial__name", "patient__surname")
    )
    effects = list(
        drug.undesirable_effects.select_related("patient", "trial", "side_effect").order_by("-date_of_occurrence")
    )

    unique_trials = []
    seen_trials = set()
    for participation in participations:
        if participation.trial_id not in seen_trials:
            seen_trials.add(participation.trial_id)
            unique_trials.append(participation.trial)

    trial_patient_counter = Counter(participation.trial.name for participation in participations)
    side_effect_counter = Counter(effect.side_effect.name for effect in effects)
    grade_counter = Counter(effect.grade for effect in effects)
    patient_records = []
    seen_patients = set()
    for participation in participations:
        if participation.patient_id in seen_patients:
            continue
        seen_patients.add(participation.patient_id)
        patient_records.append(_serialize_patient_effect_profile(participation.patient, effects))
    effect_records = [_serialize_effect_event(effect) for effect in effects]

    dashboard_data = {
        "headlineStats": [
            {"label": "Clinical trials", "value": len(unique_trials), "note": "Trials using this drug"},
            {"label": "Patients", "value": len(patient_records), "note": "Participants exposed to this drug"},
            {"label": "Average event grade", "value": round(sum(grade_counter.elements()) / len(effects), 1) if effects else 0, "note": "Mean severity of reported events"},
        ],
        "insights": [
            {"label": "Top side effect", "value": side_effect_counter.most_common(1)[0][0] if side_effect_counter else "No data"},
            {"label": "Busiest trial", "value": trial_patient_counter.most_common(1)[0][0] if trial_patient_counter else "No linked trials"},
            {"label": "Unique side effects", "value": len(side_effect_counter)},
            {"label": "Status mix", "value": len({trial.get_status_display() for trial in unique_trials}) or 0},
        ],
        "timeline": [
            {
                "date": _format_date(effect.date_of_occurrence),
                "title": effect.side_effect.name,
                "meta": f"{effect.patient} | {effect.trial.name} | grade {effect.grade}",
                "tone": "alert",
            }
            for effect in effects[:8]
        ],
        "chart": _build_donut_chart_payload(
            effect_records,
            [
                {"id": "side_effect", "label": "Side effect"},
                {"id": "side_effect_category", "label": "Side effect category"},
                {"id": "grade", "label": "Grade"},
                {"id": "gender", "label": "Gender"},
                {"id": "age_group", "label": "Age group"},
                {"id": "phase", "label": "Trial phase"},
                {"id": "trial_status", "label": "Trial status"},
                {"id": "trial_category", "label": "Condition"},
            ],
            [
                {"id": "gender", "label": "Gender"},
                {"id": "age_group", "label": "Age group"},
                {"id": "grade", "label": "Grade"},
                {"id": "phase", "label": "Trial phase"},
                {"id": "trial_status", "label": "Trial status"},
                {"id": "trial_category", "label": "Condition"},
                {"id": "side_effect_category", "label": "Side effect category"},
            ],
        ),
    }

    return render(request, "clinical_app/drug_detail.html", {
        "drug": drug,
        "participations": participations,
        "unique_trials": unique_trials,
        "effects": effects[:10],
        "dashboard_data": dashboard_data,
    })


def clinical_trial_detail(request, pk):
    trial = get_object_or_404(ClinicalTrial, pk=pk)
    participations = list(
        trial.participations.select_related("patient", "drug").order_by("drug__name", "patient__surname")
    )
    effects = list(
        trial.undesirable_effects.select_related("patient", "drug", "side_effect").order_by("-date_of_occurrence")
    )

    unique_drugs = []
    seen_drugs = set()
    for participation in participations:
        if participation.drug_id not in seen_drugs:
            seen_drugs.add(participation.drug_id)
            unique_drugs.append(participation.drug)

    drug_counter = Counter(participation.drug.name for participation in participations)
    side_effect_counter = Counter(effect.side_effect.name for effect in effects)
    grade_counter = Counter(effect.grade for effect in effects)
    patient_records = []
    seen_patients = set()
    for participation in participations:
        if participation.patient_id in seen_patients:
            continue
        seen_patients.add(participation.patient_id)
        patient_records.append(_serialize_patient_effect_profile(participation.patient, effects))
    effect_records = [_serialize_effect_event(effect) for effect in effects]

    dashboard_data = {
        "statusBadge": _trial_status_badge(trial.status, trial.get_status_display()),
        "headlineStats": [
            {"label": "Patients", "value": len(patient_records), "note": "Active linked participants"},
            {"label": "Drugs", "value": len(unique_drugs), "note": "Products used in this trial"},
            {"label": "Average event grade", "value": round(sum(grade_counter.elements()) / len(effects), 1) if effects else 0, "note": "Mean severity of reported events"},
        ],
        "insights": [
            {"label": "Top drug", "value": drug_counter.most_common(1)[0][0] if drug_counter else "No linked drugs"},
            {"label": "Top side effect", "value": side_effect_counter.most_common(1)[0][0] if side_effect_counter else "No data"},
            {"label": "Unique side effects", "value": len(side_effect_counter)},
            {"label": "Reported events", "value": len(effects)},
        ],
        "timeline": [
            {
                "date": _format_date(effect.date_of_occurrence),
                "title": effect.side_effect.name,
                "meta": f"{effect.patient} | {effect.drug.name} | grade {effect.grade}",
                "tone": "alert",
            }
            for effect in effects[:8]
        ],
        "chart": _build_donut_chart_payload(
            effect_records,
            [
                {"id": "side_effect", "label": "Side effect"},
                {"id": "side_effect_category", "label": "Side effect category"},
                {"id": "grade", "label": "Grade"},
                {"id": "gender", "label": "Gender"},
                {"id": "age_group", "label": "Age group"},
                {"id": "drug_name", "label": "Drug"},
            ],
            [
                {"id": "gender", "label": "Gender"},
                {"id": "age_group", "label": "Age group"},
                {"id": "grade", "label": "Grade"},
                {"id": "drug_name", "label": "Drug"},
                {"id": "side_effect_category", "label": "Side effect category"},
            ],
        ),
    }

    return render(request, "clinical_app/clinical_trial_detail.html", {
        "trial": trial,
        "participations": participations,
        "unique_drugs": unique_drugs,
        "effects": effects[:10],
        "dashboard_data": dashboard_data,
    })


def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    participations = list(
        patient.participations.select_related("trial", "drug").order_by("-inclusion_date")
    )
    effects = list(
        patient.undesirable_effects.select_related("trial", "drug", "side_effect").order_by("-date_of_occurrence")
    )

    latest_participation = participations[0] if participations else None
    dashboard_data = {
        "headlineStats": [
            {"label": "Age", "value": patient.age, "note": "Years"},
            {"label": "Participations", "value": len(participations), "note": "Linked trial entries"},
            {"label": "Adverse events", "value": len(effects), "note": "Registered for this patient"},
        ],
        "insights": [
            {"label": "Gender", "value": patient.get_gender_display()},
            {"label": "Weight", "value": f"{patient.weight} kg"},
            {"label": "Height", "value": f"{patient.height} cm"},
            {"label": "Latest trial", "value": latest_participation.trial.name if latest_participation else "No trial assigned"},
        ],
        "timeline": [
            {
                "date": _format_date(participation.inclusion_date),
                "title": participation.trial.name,
                "meta": f"Drug: {participation.drug.name} | dose: {participation.dose}",
                "tone": "info",
            }
            for participation in participations
        ] + [
            {
                "date": _format_date(effect.date_of_occurrence),
                "title": effect.side_effect.name,
                "meta": f"{effect.trial.name} | {effect.drug.name} | grade {effect.grade}",
                "tone": "alert",
            }
            for effect in effects
        ],
    }

    dashboard_data["timeline"].sort(key=lambda entry: entry["date"], reverse=True)

    return render(request, "clinical_app/patient_detail.html", {
        "patient": patient,
        "participations": participations,
        "effects": effects,
        "dashboard_data": dashboard_data,
    })


def add_patient(request):
    return _add_object(request, "patient")


def patient_list(request):
    return _object_list(request, "patient")


def add_drug(request):
    return _add_object(request, "drug")


def drug_list(request):
    return _object_list(request, "drug")


def add_clinical_trial(request):
    return _add_object(request, "clinical_trial")


def clinical_trial_list(request):
    return _object_list(request, "clinical_trial")


def add_side_effect(request):
    return _add_object(request, "side_effect")


def side_effect_list(request):
    return _object_list(request, "side_effect")


def add_trial_participation(request):
    return _add_object(request, "trial_participation")


def trial_participation_list(request):
    return _object_list(request, "trial_participation")


def add_undesirable_effect(request):
    return _add_object(request, "undesirable_effect")


def undesirable_effect_list(request):
    return _object_list(request, "undesirable_effect")
