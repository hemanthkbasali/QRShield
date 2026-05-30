from html import escape
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="QRTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=colors.HexColor("#17111f"),
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    base.add(
        ParagraphStyle(
            name="QRSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#7c3aed"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    base.add(
        ParagraphStyle(
            name="QRBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2c2633"),
        )
    )
    return base


def risk_color(level):
    return {
        "safe": colors.HexColor("#16a34a"),
        "warning": colors.HexColor("#f59e0b"),
        "malicious": colors.HexColor("#e11d48"),
        "invalid": colors.HexColor("#71717a"),
    }.get(level, colors.HexColor("#71717a"))


def _safe_text(value, fallback=""):
    text = fallback if value is None or value == "" else str(value)
    return escape(text)


def _p(value, style, fallback=""):
    return Paragraph(_safe_text(value, fallback), style)


def generate_security_report(scan):
    output_dir = Path(settings.REPORTS_ROOT)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"QRShield_Report_{scan.scan_hash}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"QRShield Security Report {scan.scan_hash}",
    )
    styles = _styles()
    story = [
        Paragraph("QRShield Security Report", styles["QRTitle"]),
        Paragraph("QR Phishing Detection & Security Report Generator", styles["QRBody"]),
        Spacer(1, 0.16 * inch),
    ]

    summary_rows = [
        [_p("Scan ID", styles["QRBody"]), _p(scan.scan_hash, styles["QRBody"])],
        [_p("Timestamp", styles["QRBody"]), _p(timezone.localtime(scan.created_at).strftime("%d %b %Y, %I:%M %p"), styles["QRBody"])],
        [_p("Risk Classification", styles["QRBody"]), _p(scan.status_label, styles["QRBody"])],
        [_p("Risk Score", styles["QRBody"]), _p(f"{scan.risk_score}/100", styles["QRBody"])],
        [_p("Extracted Payload", styles["QRBody"]), _p(scan.extracted_text, styles["QRBody"], "No decoded payload")],
        [_p("Normalized URL", styles["QRBody"]), _p(scan.normalized_url, styles["QRBody"], "Not a standard URL")],
    ]

    summary_table = Table(summary_rows, colWidths=[1.7 * inch, 5.0 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f0ff")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5b21b6")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#ddd6fe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#fbfaff")]),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.14 * inch))

    qr_image_path = Path(scan.qr_image.path) if scan.qr_image else None
    if qr_image_path and qr_image_path.exists():
        story.append(Paragraph("Submitted QR Image", styles["QRSection"]))
        story.append(Image(str(qr_image_path), width=1.55 * inch, height=1.55 * inch))

    story.append(Paragraph("Threat Details", styles["QRSection"]))
    threats = scan.threats or []
    if threats:
        threat_rows = [["Threat", "Severity", "Evidence", "Weight"]]
        for threat in threats:
            threat_rows.append(
                [
                    _p(threat.get("title", "Threat"), styles["QRBody"]),
                    _p(threat.get("severity", "medium").title(), styles["QRBody"]),
                    _p(threat.get("evidence", "") or threat.get("description", ""), styles["QRBody"]),
                    _p(str(threat.get("weight", "")), styles["QRBody"]),
                ]
            )
        threat_table = Table(threat_rows, colWidths=[1.6 * inch, 0.8 * inch, 3.6 * inch, 0.7 * inch])
        threat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#21172c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c4b5fd")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(threat_table)
    else:
        story.append(Paragraph("No active phishing indicators were detected by the heuristic engine.", styles["QRBody"]))

    story.append(Paragraph("Security Recommendations", styles["QRSection"]))
    for item in scan.recommendations or []:
        story.append(Paragraph(f"- {_safe_text(item)}", styles["QRBody"]))

    story.append(Spacer(1, 0.18 * inch))
    footer = Table(
        [[f"Generated by QRShield at {timezone.localtime(timezone.now()).strftime('%d %b %Y, %I:%M %p')}"]],
        colWidths=[6.7 * inch],
    )
    footer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), risk_color(scan.risk_level)),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(footer)

    doc.build(story)
    return output_path
