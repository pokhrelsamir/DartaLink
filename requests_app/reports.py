from io import BytesIO
from pathlib import Path
import textwrap

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _pdf_text(value):
    """Keep reportlab's built-in font usable for arbitrary user-entered text."""
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _paragraph(value, style, line_breaks=False):
    parts = str(value or "").splitlines() if line_breaks else [str(value or "")]
    escaped = [
        _pdf_text(part).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for part in parts
    ]
    return Paragraph("<br/>".join(escaped), style)


def build_requests_pdf(requests, filter_description="All visible requests"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="DartaLink request report",
        author="DartaLink",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                           fontSize=17, leading=21, textColor=colors.HexColor("#0b4f9e"),
                           alignment=TA_LEFT, spaceAfter=2)
    subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=8.5, leading=11,
                              textColor=colors.HexColor("#555555"), alignment=TA_LEFT)
    cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=7.2, leading=9,
                          alignment=TA_LEFT)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=7.5, leading=10,
                           textColor=colors.HexColor("#555555"))
    report_heading = ParagraphStyle(
        "ReportHeading", parent=styles["Heading3"], alignment=TA_LEFT,
        fontName="Helvetica-Bold", fontSize=12, leading=15,
    )

    story = []
    logo_path = Path(settings.BASE_DIR) / "static" / "img" / "nt-logo.png"
    if logo_path.exists():
        logo_image = Image(str(logo_path), width=19 * mm, height=19 * mm, kind="proportional")
        logo = Table([[logo_image]], colWidths=[25 * mm], rowHeights=[25 * mm])
        logo.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d6cfc3")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
    else:
        logo = Paragraph("Nepal Telecom", title)
    heading = [[
        logo,
        [_paragraph("DARTALINK", title), _paragraph("Administrative Request and Document Workflow", subtitle)],
        _paragraph(timezone.localtime().strftime("%d %b %Y, %I:%M %p"), small),
    ]]
    heading_table = Table(heading, colWidths=[30 * mm, 198 * mm, 38 * mm])
    heading_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, colors.HexColor("#0b4f9e")),
    ]))
    story.extend([heading_table, Spacer(1, 5 * mm)])
    story.append(_paragraph(f"Request report · {filter_description}", report_heading))
    story.append(_paragraph(
        f"{len(requests)} request(s) matched the applied filters. "
        "This report was generated from the DartaLink admin dashboard.",
        small,
    ))
    story.append(Spacer(1, 3 * mm))

    rows = [[
        _paragraph("Request", cell), _paragraph("Title", cell),
        _paragraph("Requester / Section", cell), _paragraph("Category", cell),
        _paragraph("Priority", cell), _paragraph("Status", cell),
        _paragraph("Created", cell),
    ]]
    for req in requests:
        requester = f"{req.requester.display_name}\n{req.department.name}"
        title_text = "\n".join(textwrap.wrap(_pdf_text(req.title), 42))
        rows.append([
            _paragraph(req.request_number, cell),
            _paragraph(title_text, cell, line_breaks=True),
            _paragraph(requester, cell, line_breaks=True),
            _paragraph(req.get_category_display(), cell),
            _paragraph(req.get_priority_display(), cell),
            _paragraph(req.get_status_display(), cell),
            _paragraph(req.created_at.strftime("%d %b %Y"), cell),
        ])
    table = Table(rows, repeatRows=1, colWidths=[31 * mm, 67 * mm, 52 * mm, 33 * mm, 25 * mm, 40 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fa")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#083b78")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dfe7f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfdff")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#77726a"))
        canvas.drawString(12 * mm, 7 * mm, "Nepal Telecom · DartaLink")
        canvas.drawRightString(285 * mm, 7 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="dartalink-request-report.pdf"'
    return response
