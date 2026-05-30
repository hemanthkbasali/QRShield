import math
from collections import Counter
from datetime import timedelta
from urllib.parse import urlparse

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import ScanResult


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, int(round(value))))


def shannon_entropy(value):
    if not value:
        return 0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def risk_palette(level):
    return {
        "safe": {"label": "Safe", "color": "emerald", "ring": "#38f29b"},
        "warning": {"label": "Warning", "color": "amber", "ring": "#f7c948"},
        "malicious": {"label": "Malicious", "color": "rose", "ring": "#ff2d68"},
        "invalid": {"label": "Invalid", "color": "zinc", "ring": "#a1a1aa"},
    }.get(level, {"label": "Unknown", "color": "zinc", "ring": "#a1a1aa"})


def get_user_scan_queryset(user):
    return ScanResult.objects.filter(user=user)


def _risk_counts(qs):
    return {
        "safe": qs.filter(risk_level=ScanResult.RiskLevel.SAFE).count(),
        "warning": qs.filter(risk_level=ScanResult.RiskLevel.WARNING).count(),
        "malicious": qs.filter(risk_level=ScanResult.RiskLevel.MALICIOUS).count(),
        "invalid": qs.filter(risk_level=ScanResult.RiskLevel.INVALID).count(),
    }


def _domain_from_url(value):
    try:
        hostname = (urlparse(value or "").hostname or "").lower()
    except ValueError:
        return ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def _daily_scan_series(qs, days=14):
    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)
    grouped = (
        qs.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total=Count("id"),
            safe=Count("id", filter=Q(risk_level=ScanResult.RiskLevel.SAFE)),
            warning=Count("id", filter=Q(risk_level=ScanResult.RiskLevel.WARNING)),
            malicious=Count("id", filter=Q(risk_level=ScanResult.RiskLevel.MALICIOUS)),
            invalid=Count("id", filter=Q(risk_level=ScanResult.RiskLevel.INVALID)),
        )
        .order_by("day")
    )
    by_day = {item["day"]: item for item in grouped}

    labels = []
    series = {"total": [], "safe": [], "warning": [], "malicious": [], "invalid": []}
    for offset in range(days):
        current = start_date + timedelta(days=offset)
        labels.append(current.strftime("%d %b"))
        item = by_day.get(current, {})
        for key in series:
            series[key].append(item.get(key, 0))
    return {"labels": labels, **series}


def _top_suspicious_domains(qs, limit=6):
    counter = Counter()
    risky = qs.filter(risk_level__in=[ScanResult.RiskLevel.WARNING, ScanResult.RiskLevel.MALICIOUS]).exclude(
        normalized_url=""
    )
    for scan in risky.only("normalized_url"):
        domain = _domain_from_url(scan.normalized_url)
        if domain:
            counter[domain] += 1
    return [{"domain": domain, "count": count} for domain, count in counter.most_common(limit)]


def _top_detection_reasons(qs, limit=6):
    counter = Counter()
    for scan in qs.only("threats"):
        for threat in scan.threats or []:
            title = threat.get("title") or "Detection indicator"
            counter[title] += 1
    return [{"title": title, "count": count} for title, count in counter.most_common(limit)]


def _report_queryset(qs):
    return qs.exclude(report_file="")


def get_dashboard_metrics(user):
    qs = get_user_scan_queryset(user)
    total = qs.count()
    counts = _risk_counts(qs)
    avg_score = qs.aggregate(value=Avg("risk_score"))["value"] or 0
    recent = list(qs[:6])
    recent_malicious = list(qs.filter(risk_level=ScanResult.RiskLevel.MALICIOUS).exclude(normalized_url="")[:5])
    reports = _report_queryset(qs)
    trend = _daily_scan_series(qs, days=14)
    reports_generated = reports.count()
    return {
        "total": total,
        "malicious": counts["malicious"],
        "warning": counts["warning"],
        "safe": counts["safe"],
        "invalid": counts["invalid"],
        "blocked": counts["malicious"] + counts["warning"],
        "avg_score": round(avg_score),
        "recent": recent,
        "recent_malicious": recent_malicious,
        "recent_reports": list(reports.order_by("-updated_at")[:5]),
        "reports_generated": reports_generated,
        "safe_rate": round((counts["safe"] / total) * 100) if total else 0,
        "chart_data": {
            "risk_distribution": {
                "labels": ["Safe", "Warning", "Malicious", "Invalid"],
                "values": [counts["safe"], counts["warning"], counts["malicious"], counts["invalid"]],
            },
            "trend": trend,
            "reports": {
                "labels": ["Generated", "Pending"],
                "values": [reports_generated, max(total - reports_generated, 0)],
            },
        },
    }


def get_threat_intel_metrics(user):
    qs = get_user_scan_queryset(user)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_qs = qs.filter(created_at__gte=thirty_days_ago)
    total = qs.count()
    counts = _risk_counts(qs)
    recent_counts = _risk_counts(recent_qs)
    reports = _report_queryset(qs)
    trend = _daily_scan_series(qs, days=30)
    top_domains = _top_suspicious_domains(qs)
    top_reasons = _top_detection_reasons(qs)

    reports_generated = reports.count()
    return {
        "total": total,
        "safe": counts["safe"],
        "warning": counts["warning"],
        "malicious": counts["malicious"],
        "invalid": counts["invalid"],
        "total_recent": recent_qs.count(),
        "malicious_recent": recent_counts["malicious"],
        "warning_recent": recent_counts["warning"],
        "safe_recent": recent_counts["safe"],
        "recent_threats": list(
            qs.filter(risk_level__in=[ScanResult.RiskLevel.WARNING, ScanResult.RiskLevel.MALICIOUS])[:6]
        ),
        "top_domains": top_domains,
        "top_threats": top_reasons,
        "reports_generated": reports_generated,
        "report_rate": round((reports_generated / total) * 100) if total else 0,
        "recent_reports": list(reports.order_by("-updated_at")[:5]),
        "chart_data": {
            "risk_distribution": {
                "labels": ["Safe", "Warning", "Malicious", "Invalid"],
                "values": [counts["safe"], counts["warning"], counts["malicious"], counts["invalid"]],
            },
            "trend": trend,
            "top_domains": {
                "labels": [item["domain"] for item in top_domains],
                "values": [item["count"] for item in top_domains],
            },
            "reports": {
                "labels": ["Generated", "Pending"],
                "values": [reports_generated, max(total - reports_generated, 0)],
            },
        },
    }
