from django.urls import path

from . import views


urlpatterns = [
    path("", views.landing, name="landing"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("scanner/", views.scanner, name="scanner"),
    path("result/<int:scan_id>/", views.result, name="result"),
    path("history/", views.history, name="history"),
    path("threat-intel/", views.threat_intel, name="threat_intel"),
    path("reports/", views.reports, name="reports"),
    path("reports/<int:scan_id>/preview/", views.report_preview, name="report_preview"),
    path("reports/<int:scan_id>/download/", views.download_report, name="download_report"),
    path("settings/", views.settings_view, name="settings"),
    path("invalid-qr/", views.invalid_qr, name="invalid_qr"),
]
