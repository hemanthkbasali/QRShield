import secrets

from django.conf import settings
from django.db import models


class ScanResult(models.Model):
    class RiskLevel(models.TextChoices):
        SAFE = "safe", "Safe"
        WARNING = "warning", "Warning"
        MALICIOUS = "malicious", "Malicious"
        INVALID = "invalid", "Invalid"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qr_scans")
    scan_hash = models.CharField(max_length=18, unique=True, editable=False)
    qr_image = models.ImageField(upload_to="qr_uploads/%Y/%m/%d/")
    extracted_text = models.TextField(blank=True)
    normalized_url = models.URLField(max_length=1200, blank=True)
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.INVALID)
    threats = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    report_file = models.FileField(upload_to="generated_reports/%Y/%m/%d/", blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["risk_level"]),
            models.Index(fields=["scan_hash"]),
        ]

    def save(self, *args, **kwargs):
        if not self.scan_hash:
            self.scan_hash = self._new_hash()
        super().save(*args, **kwargs)

    def _new_hash(self):
        while True:
            value = f"RaSHa{secrets.token_hex(5)}"
            if not ScanResult.objects.filter(scan_hash=value).exists():
                return value

    @property
    def is_url(self):
        return bool(self.normalized_url)

    @property
    def status_label(self):
        return self.get_risk_level_display()

    def __str__(self):
        return f"{self.scan_hash} - {self.status_label}"
