"""Sprint 5 manager-only dashboard endpoints. All feedback is anonymous and role-scoped."""
from __future__ import annotations

import io
from collections import Counter, defaultdict
from datetime import datetime
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Course, Department, Feedback, Service, User
from ..security import managers
from ..services import Filters, feedback_rows, scope_label, sort_semesters
from .analytics import _kpis

router = APIRouter(prefix="/api/management", tags=["Sprint 5 management"])


def scope_params(
    semester: str | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    service_id: int | None = None,
    instructor_id: int | None = None,
):
    return Filters(semester=semester, department_id=department_id,
                   course_id=course_id, service_id=service_id,
                   instructor_id=instructor_id)


def _groups(db: Session, user: User, f: Filters, by: str):
    rows = feedback_rows(db, user, f)
    if by == "course":
        names = {c.id: f"{c.code} — {c.title}" for c in db.scalars(select(Course))}
        key = "course_id"
    elif by == "service":
        names = {s.id: s.name for s in db.scalars(select(Service))}
        key = "service_id"
    else:
        names = {d.id: d.name for d in db.scalars(select(Department))}
        key = "department_id"
    buckets = defaultdict(list)
    for r in rows:
        if r.get(key):
            buckets[r[key]].append(r)
    out = []
    for ident, items in buckets.items():
        kpi = _kpis(items)
        out.append({"id": ident, "name": names.get(ident, str(ident)), **kpi})
    return sorted(out, key=lambda x: (-x["total"], x["name"]))


@router.get("/university")
def university(f: Filters = Depends(scope_params), user: User = Depends(managers), db: Session = Depends(get_db)):
    """Actual users/catalogue counts, never made-up demo totals. Manager scope is enforced."""
    courses_stmt = select(Course)
    if user.role == "manager" and user.department_id:
        courses_stmt = courses_stmt.where(Course.department_id == user.department_id)
    courses = db.scalars(courses_stmt).all()
    depts = db.scalars(select(Department).order_by(Department.name)).all()
    if user.role == "manager" and user.department_id:
        depts = [d for d in depts if d.id == user.department_id]
    services = db.scalars(select(Service)).all()
    users = db.scalars(select(User).where(User.is_active.is_(True))).all()
    if user.role == "manager" and user.department_id:
        users = [u for u in users if u.department_id == user.department_id]
    counts = Counter(u.role for u in users)
    dept_counts = Counter(c.department_id for c in courses)
    rows = feedback_rows(db, user, f)
    kinds = Counter(r["kind"] for r in rows)
    source_counts = dict(db.execute(select(Feedback.source, func.count(Feedback.id)).group_by(Feedback.source)).all())
    return {
        "users_total": len(users), "students": counts["student"],
        "professors": counts["faculty"], "managers": counts["manager"],
        "admins": counts["admin"], "departments": len(depts),
        "courses": len(courses), "services": len(services),
        "feedback_total": len(rows), "course_feedback": kinds["course"],
        "service_feedback": kinds["service"],
        "departments_detail": [{"id": d.id, "name": d.name, "courses": dept_counts[d.id],
                                "users": sum(u.department_id == d.id for u in users)} for d in depts],
        "sample_data_present": source_counts.get("seed", 0) > 0,
    }


@router.get("/comparison")
def comparison(by: str = Query("course", pattern="^(course|department|service)$"),
               f: Filters = Depends(scope_params), user: User = Depends(managers), db: Session = Depends(get_db)):
    """Paired group ratings for selected period and preceding period, including services."""
    all_rows = feedback_rows(db, user, Filters(**{**f.__dict__, "semester": None}))
    periods = sort_semesters(r["semester"] for r in all_rows)
    current = f.semester if f.semester in periods else (periods[-1] if periods else None)
    previous = periods[periods.index(current)-1] if current and periods.index(current)>0 else None
    fcur = Filters(**{**f.__dict__, "semester": current})
    fprev = Filters(**{**f.__dict__, "semester": previous}) if previous else None
    present = _groups(db, user, fcur, by) if current else []
    earlier = _groups(db, user, fprev, by) if fprev else []
    prev_lookup = {r["id"]: r for r in earlier}
    all_lookup = {r["id"]: r for r in present}
    result = []
    for ident in dict.fromkeys([*(r["id"] for r in present), *(r["id"] for r in earlier)]):
        a, b = all_lookup.get(ident), prev_lookup.get(ident)
        result.append({"id": ident, "name": (a or b)["name"],
                       "current": a, "previous": b})
    return {"current_semester": current, "previous_semester": previous,
            "items": result[:16], "total_groups": len(result)}


def _report_rows(db: Session, user: User, f: Filters, section: str):
    kpi = _kpis(feedback_rows(db, user, f))
    if section == "overview":
        return ["Indicator", "Value"], [
            ["Feedback responses", kpi["total"]], ["Average satisfaction / 5", kpi["avg_rating"] or "—"],
            ["Positive responses", kpi["positive"]], ["Neutral responses", kpi["neutral"]],
            ["Negative responses", kpi["negative"]], ["Net sentiment", kpi["satisfaction_index"]],
        ]
    if section == "trends":
        by_sem = defaultdict(list)
        for r in feedback_rows(db, user, Filters(**{**f.__dict__, "semester": None})):
            by_sem[r["semester"]].append(r)
        return ["Semester", "Responses", "Avg rating", "Positive %", "Neutral %", "Negative %"], [
            [s, (k := _kpis(by_sem[s]))["total"], k["avg_rating"] or "—",
             round(k["positive"] / k["total"] * 100, 1), round(k["neutral"] / k["total"] * 100, 1),
             round(k["negative"] / k["total"] * 100, 1)] for s in sort_semesters(by_sem)
        ]
    if section.startswith("compare_"):
        by = section.removeprefix("compare_")
        if by not in {"course", "department", "service"}:
            by = "course"
        return ["Name", "Responses", "Avg rating", "Positive %", "Negative %"], [
            [r["name"], r["total"], r["avg_rating"] or "—",
             round(r["positive_share"]*100, 1), round(r["negative_share"]*100, 1)]
            for r in _groups(db, user, f, by)
        ]
    # Alerts are saved historical evaluations, not alerts manufactured on the client.
    from .analytics import _visible_alerts
    from ..models import Alert
    alerts = _visible_alerts(db.scalars(select(Alert).order_by(Alert.created_at.desc())).all(), user, db)
    return ["Area", "Previous semester", "Current semester", "Previous negative %", "Current negative %", "Topic"], [
        [a.scope_name, a.previous_semester, a.semester,
         round(a.previous_share * 100, 1), round(a.negative_share * 100, 1), a.top_topic or "—"] for a in alerts
    ]


@router.get("/report")
def report(section: str = Query("overview", pattern="^(overview|trends|alerts|compare_course|compare_department|compare_service)$"),
           format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
           f: Filters = Depends(scope_params), user: User = Depends(managers), db: Session = Depends(get_db)):
    columns, data = _report_rows(db, user, f, section)
    title = "SDU Feedback — " + section.replace("_", " ").title()
    label = scope_label(db, f)
    filename = f"sdu_{section}_{datetime.now():%Y%m%d}.{format}"
    buffer = io.BytesIO()
    if format == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
        wb = Workbook()
        ws = wb.active
        ws.title = section[:31]
        ws.append([title]); ws.append(["Selected filters", label]); ws.append(["Generated", datetime.now().isoformat(timespec="minutes")]); ws.append([])
        ws.append(columns)
        for row in data: ws.append(row)
        ws.freeze_panes = "A6"
        for cell in ws[5]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="203C6C")
        for col in ws.columns:
            width = min(62, max(16, max(len(str(c.value or "")) for c in col) + 3))
            ws.column_dimensions[get_column_letter(col[0].column)].width = width
        wb.save(buffer)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        from reportlab.lib.styles import ParagraphStyle
        header_style = ParagraphStyle("ReportHeader", parent=styles["BodyText"], textColor=colors.white, fontName="Helvetica-Bold")
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title=title, leftMargin=28, rightMargin=28)
        story = [Paragraph(escape(title), styles["Title"]), Paragraph("Filters: " + escape(label), styles["Normal"]), Spacer(1, 14)]
        rows = [columns] + [list(map(lambda x: str(x if x is not None else "—"), row)) for row in data]
        if len(rows) == 1: rows.append(["No data available"] + [""] * (len(columns)-1))
        cells = [[Paragraph(escape(str(value))[:120], header_style if i == 0 else styles["BodyText"]) for value in row] for i, row in enumerate(rows)]
        widths = [ (landscape(A4)[0]-56) / len(columns)] * len(columns)
        table = Table(cells, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,0),colors.HexColor("#203C6C")),
            ("TEXTCOLOR", (0,0),(-1,0),colors.white),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),[colors.white, colors.HexColor("#EDF2F8")]),
            ("VALIGN", (0,0),(-1,-1),"TOP"),
            ("BOTTOMPADDING", (0,0),(-1,-1),8),
        ]))
        story.append(table)
        doc.build(story)
        media = "application/pdf"
    buffer.seek(0)
    return StreamingResponse(buffer, media_type=media,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
