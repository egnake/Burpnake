from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import csv
import json
import io

from app.modules.database import get_findings, get_exchanges

router = APIRouter()


@router.get("/findings/csv")
def export_findings_csv():
    findings = get_findings()
    output = io.StringIO()
    if findings:
        safe = [{k: v for k, v in f.items() if k not in ('steps_to_test',)} for f in findings]
        writer = csv.DictWriter(output, fieldnames=safe[0].keys())
        writer.writeheader()
        writer.writerows(safe)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=burpnake_findings.csv"},
    )


@router.get("/findings/json")
def export_findings_json():
    findings = get_findings()
    data = json.dumps(findings, indent=2, default=str).encode()
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=burpnake_findings.json"},
    )


@router.get("/exchanges/json")
def export_exchanges_json():
    exchanges = get_exchanges(limit=1000)
    for ex in exchanges:
        ex.pop("request_b64", None)
        ex.pop("response_b64", None)
    data = json.dumps(exchanges, indent=2, default=str).encode()
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=burpnake_exchanges.json"},
    )
