import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..nlp.summarizer import llm_available, llm_summary, local_summary
from ..security import staff_only
from ..services import Filters, feedback_rows, scope_label
from .analytics import _kpis, filters_dep

router = APIRouter(prefix="/api/reports", tags=["reports"])

_FONT, _BOLD = "Helvetica", "Helvetica-Bold"
for path, bold in (("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),):
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont("DejaVu", path))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold if os.path.exists(bold) else path))
        _FONT, _BOLD = "DejaVu", "DejaVu-Bold"

INK = colors.HexColor("#1b1d3a")
ACCENT = colors.HexColor("#6b4de6")
MUTED = colors.HexColor("#6b6f94")
H1 = ParagraphStyle("h1", fontName=_BOLD, fontSize=20, leading=24, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle("h2", fontName=_BOLD, fontSize=13, leading=17, textColor=ACCENT, spaceBefore=12, spaceAfter=6)
BODY = ParagraphStyle("body", fontName=_FONT, fontSize=10, leading=14, textColor=INK)
SMALL = ParagraphStyle("small", fontName=_FONT, fontSize=8.5, leading=12, textColor=MUTED)
QUOTE = ParagraphStyle("quote", parent=SMALL, leftIndent=10, textColor=colors.HexColor("#44476b"))


def _p(text, style=BODY):
    return Paragraph(escape(str(text)), style)


@router.get("/summary.pdf")
def summary_pdf(ai: bool = False, f: Filters = Depends(filters_dep),
                user: User = Depends(staff_only), db: Session = Depends(get_db)):
    rows = feedback_rows(db, user, f)
    label = scope_label(db, f)
    s = local_summary(rows, label)
    if ai and llm_available():
        s = llm_summary(rows, s, label)
    k = _kpis(rows)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Student Feedback Report", author="Pulse — Student Feedback AI")
    el = [
        _p("Student Feedback Analysis Report", H1),
        _p(f"Scope: {label}  ·  Generated {datetime.now():%d %b %Y %H:%M}  ·  by {user.name}", SMALL),
        Spacer(1, 8),
    ]

    kpi = [["Responses", "Avg rating", "Positive", "Negative", "Satisfaction index"],
           [str(k["total"]), f"{k['avg_rating']}/5" if k["avg_rating"] else "—",
            f"{round(k['positive_share'] * 100)}%", f"{round(k['negative_share'] * 100)}%",
            f"{k['satisfaction_index']:+}"]]
    t = Table(kpi, colWidths=[34 * mm] * 5)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), _FONT, 8.5), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("FONT", (0, 1), (-1, 1), _BOLD, 15), ("TEXTCOLOR", (0, 1), (-1, 1), INK),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f1ff")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9d3ff")),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    el += [t, _p("Summary" + (" (AI-generated)" if s.get("source") == "llm" else ""), H2), _p(s["overview"])]

    for title, key in (("Strengths", "strengths"), ("Main problems", "problems")):
        if s.get(key):
            el.append(_p(title, H2))
            for item in s[key]:
                el.append(Paragraph(f"<b>{escape(item['topic'])}</b> — {escape(item.get('detail', ''))}", BODY))
                for ex in item.get("examples", [])[:2]:
                    el.append(_p(f"“{ex}”", QUOTE))
                el.append(Spacer(1, 4))

    if s.get("suggestions"):
        el.append(_p("Improvement suggestions from students", H2))
        for sg in s["suggestions"]:
            m = f"  ({sg['mentions']} similar)" if sg.get("mentions") and sg["mentions"] > 1 else ""
            el.append(_p(f"•  {sg['text']}{m}"))

    if s.get("aspects"):
        el.append(_p("Topic breakdown", H2))
        data = [["Topic", "Mentions", "Positive", "Neutral", "Negative", "Negative %"]]
        for a in s["aspects"]:
            data.append([a["topic"], a["total"], a["positive"], a["neutral"], a["negative"],
                         f"{round(a['negative_share'] * 100)}%"])
        tt = Table(data, colWidths=[62 * mm, 21 * mm, 21 * mm, 21 * mm, 21 * mm, 24 * mm], repeatRows=1)
        tt.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), _BOLD, 9), ("FONT", (0, 1), (-1, -1), _FONT, 9),
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f5fc")]),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dcdaf0")),
        ]))
        el.append(tt)

    el += [Spacer(1, 14), _p("All comments are anonymized; personal data is masked before analysis.", SMALL)]
    doc.build(el)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=feedback_report_{datetime.now():%Y%m%d}.pdf"})
