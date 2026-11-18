import csv
import io
import textwrap
from typing import Literal
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from reportlab.pdfgen import canvas
from ..database import get_db
from ..dependencies import principal, source_ip
from ..schemas import Scope
from ..models import SecurityEvent
from ..services.queries import summary_data, filters, iso
from ..services.events import record_event

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def safe_cell(value):
    text = "" if value is None else str(value)
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
        else text
    )


@router.get("/summary")
def report_summary(
    scope: Scope = "live",
    days: int = Query(7, ge=1, le=90),
    user=Depends(principal),
    db=Depends(get_db),
):
    return summary_data(db, scope, days)


@router.post("/export")
def export(
    request: Request,
    format: Literal["csv", "pdf"] = "csv",
    scope: Scope = "live",
    days: int = Query(7, ge=1, le=90),
    user=Depends(principal),
    db=Depends(get_db),
):
    summary = summary_data(db, scope, days)
    metrics = [
        "total_events",
        "active_alerts",
        "high_risk_events",
        "login_success",
        "login_failed",
        "resolved_alerts",
        "resolution_rate",
    ]
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "SENTINEL security report",
                scope,
                f"Last {days} days",
                summary["generated_at"],
            ]
        )
        for key in metrics:
            writer.writerow([key, summary[key]])
        writer.writerow(["Severity", "Alerts"])
        writer.writerows(summary["severity"].items())
        writer.writerow(["Date (UTC)", "Success", "Failed", "Other"])
        for x in summary["timeline"]:
            writer.writerow([x["date"], x["success"], x["failed"], x["other"]])
        for text in summary["recommendations"]:
            writer.writerow(["Recommendation", text])
        writer.writerow([])
        writer.writerow(["Events: newest 10000 maximum"])
        writer.writerow(
            [
                "ID",
                "Timestamp UTC",
                "Type",
                "IP",
                "User ID",
                "Account",
                "Severity",
                "Demo",
            ]
        )
        for row in db.scalars(
            select(SecurityEvent)
            .where(*filters(SecurityEvent, scope, days))
            .order_by(SecurityEvent.id.desc())
            .limit(10000)
        ):
            writer.writerow(
                [
                    safe_cell(x)
                    for x in [
                        row.id,
                        iso(row.occurred_at),
                        row.event_type,
                        row.source_ip,
                        row.user_id,
                        row.metadata_json.get("account"),
                        row.severity,
                        row.is_demo,
                    ]
                ]
            )
        body, media = output.getvalue().encode("utf-8-sig"), "text/csv"
    else:
        output = io.BytesIO()
        pdf = canvas.Canvas(output, pagesize=(595, 842))
        pdf.setTitle("SENTINEL Security Report")
        y = 790

        def line(text, size=11):
            nonlocal y
            if y < 50:
                pdf.showPage()
                y = 790
            pdf.setFont("Helvetica", size)
            pdf.drawString(45, y, text)
            y -= size + 10

        line("SENTINEL / Security report", 20)
        line(f"Scope: {scope.upper()} | Last {days} days | UTC")
        line(summary["generated_at"])
        for key in metrics:
            line(f"{key.replace('_', ' ').title()}: {summary[key]}")
        line("Alert severity / resolution", 14)
        line(str(summary["severity"]))
        line(str(summary["status"]))
        line("Daily event trend", 14)
        for row in summary["timeline"]:
            line(
                f"{row['date']}  Success: {row['success']}  Failed: {row['failed']}  Other: {row['other']}"
            )
        line("Recommendations", 14)
        for item in summary["recommendations"]:
            for wrapped in textwrap.wrap(item, 85):
                line(wrapped)
        line("Signals are not confirmed attacks. Synthetic data is marked DEMO.", 10)
        pdf.save()
        body, media = output.getvalue(), "application/pdf"
    record_event(
        db,
        "report_exported",
        source_ip(request),
        user.id,
        {"format": format, "scope": scope},
    )
    db.commit()
    return Response(
        body,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="sentinel-{scope}-{days}d.{format}"'
        },
    )
