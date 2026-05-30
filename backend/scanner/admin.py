from django.contrib import admin

from .models import ScanResult


@admin.register(ScanResult)
class ScanResultAdmin(admin.ModelAdmin):
    list_display = ("scan_hash", "user", "risk_level", "risk_score", "created_at")
    list_filter = ("risk_level", "created_at")
    search_fields = ("scan_hash", "extracted_text", "normalized_url", "user__username", "user__email")
    readonly_fields = ("scan_hash", "created_at", "updated_at")
