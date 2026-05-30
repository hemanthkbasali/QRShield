# Generated for the QRShield mini-project.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ScanResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scan_hash", models.CharField(editable=False, max_length=18, unique=True)),
                ("qr_image", models.ImageField(upload_to="qr_uploads/%Y/%m/%d/")),
                ("extracted_text", models.TextField(blank=True)),
                ("normalized_url", models.URLField(blank=True, max_length=1200)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                (
                    "risk_level",
                    models.CharField(
                        choices=[
                            ("safe", "Safe"),
                            ("warning", "Warning"),
                            ("malicious", "Malicious"),
                            ("invalid", "Invalid"),
                        ],
                        default="invalid",
                        max_length=16,
                    ),
                ),
                ("threats", models.JSONField(blank=True, default=list)),
                ("recommendations", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("report_file", models.FileField(blank=True, upload_to="generated_reports/%Y/%m/%d/")),
                ("source_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qr_scans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "-created_at"], name="scanner_sca_user_id_31e6c5_idx"),
                    models.Index(fields=["risk_level"], name="scanner_sca_risk_le_b4a5a1_idx"),
                    models.Index(fields=["scan_hash"], name="scanner_sca_scan_ha_f65450_idx"),
                ],
            },
        ),
    ]
