import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.core.files import File
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .detector import analyze_payload
from .forms import ProfileSettingsForm, QRUploadForm, RegisterForm
from .models import ScanResult
from .qr_reader import QRDecodeError, decode_qr_image
from .report_generator import generate_security_report
from .utils import get_client_ip, get_dashboard_metrics, get_threat_intel_metrics, get_user_scan_queryset
from .validators import clean_status_filter, normalize_search


logger = logging.getLogger(__name__)


def landing(request):
    return render(request, "pages/landing.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            if not request.POST.get("remember"):
                request.session.set_expiry(0)
            return redirect(request.GET.get("next") or "dashboard")
        messages.error(request, "Invalid credentials.")
    elif request.method == "POST":
        messages.error(request, "Invalid username or password.")

    return render(request, "auth/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.email = form.cleaned_data["email"]
        user.first_name = form.cleaned_data.get("first_name", "")
        user.save()
        login(request, user)
        messages.success(request, "Account created. QRShield is ready.")
        return redirect("dashboard")

    return render(request, "auth/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required
def dashboard(request):
    metrics = get_dashboard_metrics(request.user)
    return render(request, "pages/dashboard.html", {"metrics": metrics})


@login_required
def scanner(request):
    form = QRUploadForm(request.POST or None, request.FILES or None)
    metrics = get_dashboard_metrics(request.user)
    selected_scan = get_scan_from_query(request)

    if request.method == "POST":
        if form.is_valid():
            scan = ScanResult.objects.create(
                user=request.user,
                qr_image=form.cleaned_data["image"],
                source_ip=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
            )
            try:
                decoded = decode_qr_image(Path(scan.qr_image.path))
                analysis = analyze_payload(decoded.payload)
                scan.extracted_text = decoded.payload
                scan.normalized_url = analysis["normalized_url"]
                scan.risk_score = analysis["risk_score"]
                scan.risk_level = analysis["risk_level"]
                scan.threats = analysis["threats"]
                scan.recommendations = analysis["recommendations"]
                scan.metadata = {**analysis["metadata"], "decoder": decoded.engine}
                scan.save()
                messages.success(request, "QR decoded and analyzed successfully.")
                return redirect(f"{reverse('scanner')}?scan={scan.id}")
            except QRDecodeError as exc:
                scan.risk_level = ScanResult.RiskLevel.INVALID
                scan.risk_score = 0
                scan.threats = [
                    {
                        "title": "Invalid QR",
                        "description": str(exc),
                        "severity": "low",
                        "weight": 0,
                        "evidence": "No readable QR symbol",
                    }
                ]
                scan.recommendations = [
                    "Upload a clear, uncropped QR image.",
                    "Avoid reflections, heavy blur, and extreme perspective distortion.",
                ]
                scan.save()
                messages.error(request, "No readable QR code was found in that image.")
                return redirect(f"{reverse('scanner')}?scan={scan.id}")
            except Exception as exc:
                logger.exception("QR scan analysis failed for scan %s", scan.id)
                scan.risk_level = ScanResult.RiskLevel.INVALID
                scan.risk_score = 0
                scan.threats = [
                    {
                        "title": "Analysis error",
                        "description": "QRShield could not complete this scan safely.",
                        "severity": "low",
                        "weight": 0,
                        "evidence": "The uploaded image could not be processed by the analysis pipeline.",
                    }
                ]
                scan.save()
                messages.error(request, "The QR image was uploaded, but analysis could not be completed.")
                return redirect(f"{reverse('scanner')}?scan={scan.id}")
        messages.error(request, "Please upload a readable QR image under 5 MB.")

    return render(request, "pages/scanner.html", {"form": form, "metrics": metrics, "selected_scan": selected_scan})


@login_required
def result(request, scan_id):
    scan = get_owned_scan(request.user, scan_id)
    return render(request, "pages/result.html", {"scan": scan})


@login_required
def history(request):
    query = normalize_search(request.GET.get("q"))
    status = clean_status_filter(request.GET.get("status"))
    qs = get_user_scan_queryset(request.user)

    if query:
        qs = qs.filter(
            Q(scan_hash__icontains=query)
            | Q(extracted_text__icontains=query)
            | Q(normalized_url__icontains=query)
        )
    if status:
        qs = qs.filter(risk_level=status)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "pages/history.html",
        {
            "scans": page_obj.object_list,
            "page_obj": page_obj,
            "querystring": query_params.urlencode(),
            "query": query,
            "status": status,
            "metrics": get_dashboard_metrics(request.user),
        },
    )


@login_required
def threat_intel(request):
    metrics = get_threat_intel_metrics(request.user)
    return render(request, "pages/threat_intel.html", {"intel": metrics})


@login_required
def reports(request):
    query = normalize_search(request.GET.get("q"))
    status = clean_status_filter(request.GET.get("status"))
    qs = get_user_scan_queryset(request.user)

    if query:
        qs = qs.filter(
            Q(scan_hash__icontains=query)
            | Q(extracted_text__icontains=query)
            | Q(normalized_url__icontains=query)
        )
    if status:
        qs = qs.filter(risk_level=status)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "pages/reports.html",
        {
            "scans": page_obj.object_list,
            "page_obj": page_obj,
            "querystring": query_params.urlencode(),
            "query": query,
            "status": status,
            "total_reports": qs.exclude(report_file="").count(),
        },
    )


@login_required
def report_preview(request, scan_id):
    scan = get_owned_scan(request.user, scan_id)
    return render(request, "pages/report_preview.html", {"scan": scan})


@login_required
def download_report(request, scan_id):
    scan = get_owned_scan(request.user, scan_id)
    try:
        pdf_path = generate_security_report(scan)
        with pdf_path.open("rb") as handle:
            scan.report_file.save(pdf_path.name, File(handle), save=True)
        return FileResponse(pdf_path.open("rb"), as_attachment=True, filename=pdf_path.name, content_type="application/pdf")
    except Exception as exc:
        logger.exception("Report generation failed for scan %s", scan.id)
        messages.error(request, "Report generation failed. Please try again after reviewing the scan details.")
        return redirect("report_preview", scan_id=scan.id)


@login_required
def settings_view(request):
    profile_form = ProfileSettingsForm(request.POST or None, instance=request.user)
    password_form = PasswordChangeForm(request.user, request.POST or None)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile" and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile settings updated.")
            return redirect("settings")
        if action == "password" and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated securely.")
            return redirect("settings")
        messages.error(request, "Please review the highlighted settings fields.")

    return render(
        request,
        "pages/settings.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )


@login_required
def invalid_qr(request):
    scan_id = request.GET.get("scan")
    scan = None
    if scan_id:
        try:
            scan = get_owned_scan(request.user, scan_id)
        except Http404:
            scan = None
    return render(request, "pages/invalid_qr.html", {"scan": scan})


def get_scan_from_query(request):
    scan_id = request.GET.get("scan")
    if not scan_id:
        return None
    try:
        return get_owned_scan(request.user, scan_id)
    except (Http404, ValueError):
        return None


def get_owned_scan(user, scan_id):
    return get_object_or_404(ScanResult, id=scan_id, user=user)


def bad_request(request, exception=None):
    return render(
        request,
        "pages/error.html",
        {
            "status_code": 400,
            "title": "Request could not be processed",
            "message": "Please review the submitted data and try again.",
        },
        status=400,
    )


def permission_denied(request, exception=None):
    return render(
        request,
        "pages/error.html",
        {
            "status_code": 403,
            "title": "Access denied",
            "message": "You do not have permission to view this QRShield resource.",
        },
        status=403,
    )


def page_not_found(request, exception=None):
    return render(
        request,
        "pages/error.html",
        {
            "status_code": 404,
            "title": "Page not found",
            "message": "The requested QRShield page or scan record was not found.",
        },
        status=404,
    )


def server_error(request):
    return render(
        request,
        "pages/error.html",
        {
            "status_code": 500,
            "title": "Something went wrong",
            "message": "QRShield could not complete the request safely. Please return to the scanner and try again.",
        },
        status=500,
    )
