from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from src.core.db import (
    get_case_by_decision_id,
    get_latest_review_by_decision_id,
)
from src.core.dossier_seal import (
    build_dossier_payload,
    compute_dossier_signature,
)

router = APIRouter(tags=["verify"])


def _fmt(value):
    if value is None:
        return ""
    return str(value).strip()


def _fmt_bool(value):
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return ""


def _normalize_reviewer(reviewer: str | None) -> str:
    if not reviewer:
        return "System"
    r = str(reviewer).lower().strip()
    if r in ["aidentitech", "system", "engine"]:
        return "System"
    return reviewer


def _compute_signature_validation(case: dict) -> tuple[str | None, bool | None]:
    stored_signature = case.get("signature")
    if not stored_signature:
        return None, None

    dossier_payload = build_dossier_payload(case)
    computed_signature = compute_dossier_signature(dossier_payload)
    return stored_signature, stored_signature == computed_signature


def _build_verify_payload(decision_id: str) -> dict:
    case = get_case_by_decision_id(decision_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    latest_review = get_latest_review_by_decision_id(decision_id)

    engine_status = case.get("status")
    final_status = latest_review.get("action") if latest_review else engine_status
    has_admin_override = bool(latest_review)

    latest_event_timestamp = (
        latest_review.get("created_at")
        if latest_review
        else case.get("decision_timestamp")
    )

    override_reason = latest_review.get("reason") if latest_review else None
    override_reviewer = _normalize_reviewer(
        latest_review.get("reviewer_id") if latest_review else None
    )

    signature, signature_valid = _compute_signature_validation(case)

    return {
        "verified": True,
        "decision_id": case.get("decision_id"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "engine_status": engine_status,
        "final_status": final_status,
        "severity": case.get("severity"),
        "risk_score": case.get("risk_score"),
        "decision_code": case.get("decision_code"),
        "has_admin_override": has_admin_override,
        "latest_event_timestamp": latest_event_timestamp,
        "ledger_hash": case.get("ledger_hash"),
        "dossier_hash": case.get("dossier_hash"),
        "signature": signature,
        "signature_valid": signature_valid,
        "override_reason": override_reason,
        "override_reviewer": override_reviewer,
    }


@router.get("/verify/{decision_id}")
def verify_case(decision_id: str):
    return _build_verify_payload(decision_id)


@router.get("/verify/{decision_id}/view", response_class=HTMLResponse)
def verify_case_view(decision_id: str):
    data = _build_verify_payload(decision_id)

    final_status = _fmt(data["final_status"]) or "UNKNOWN"
    engine_status = _fmt(data["engine_status"])
    has_override = bool(data["has_admin_override"])
    override_reason = _fmt(data["override_reason"])
    override_reviewer = _fmt(data["override_reviewer"])
    verified = bool(data["verified"])
    signature_value = _fmt(data["signature"])
    signature_valid = data["signature_valid"]

    status_color = "#991B1B" if final_status == "REJECTED" else "#065F46"
    status_bg = "#FEF2F2" if final_status == "REJECTED" else "#ECFDF5"
    verified_color = "#065F46" if verified else "#991B1B"

    if signature_valid is True:
        signature_status = "VALID"
        signature_status_color = "#065F46"
        signature_status_bg = "#ECFDF5"
    elif signature_valid is False:
        signature_status = "INVALID"
        signature_status_color = "#991B1B"
        signature_status_bg = "#FEF2F2"
    else:
        signature_status = "NOT AVAILABLE"
        signature_status_color = "#6B7280"
        signature_status_bg = "#F3F4F6"

    override_block = ""
    if has_override:
        override_block = f"""
        <div class="alert">
          <div class="alert-title">Governance Override</div>
          <div class="alert-text">Final decision differs from the automated decision.</div>
          <div class="alert-meta"><b>Reviewer:</b> {override_reviewer}</div>
          <div class="alert-meta"><b>Reason:</b> {override_reason or "Not specified"}</div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Aidentitech Verification</title>
      <style>
        body {{
          margin: 0;
          background: #f6f7f9;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial;
          color: #111;
        }}
        .wrap {{
          max-width: 900px;
          margin: 40px auto;
          padding: 0 20px;
        }}
        .card {{
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 14px;
          overflow: hidden;
        }}
        .header {{
          padding: 24px;
          border-bottom: 1px solid #eee;
        }}
        .brand {{
          font-weight: 700;
          font-size: 18px;
          margin-bottom: 6px;
        }}
        .status {{
          margin-top: 12px;
          background: {status_color};
          color: white;
          padding: 8px 14px;
          display: inline-block;
          border-radius: 8px;
          font-weight: 700;
        }}
        .verified {{
          margin-left: 10px;
          font-size: 12px;
          padding: 6px 10px;
          border-radius: 999px;
          background: {status_bg};
          color: {verified_color};
          font-weight: 700;
        }}
        .sig-badge {{
          display: inline-block;
          margin-left: 10px;
          font-size: 12px;
          padding: 6px 10px;
          border-radius: 999px;
          background: {signature_status_bg};
          color: {signature_status_color};
          font-weight: 700;
        }}
        .section {{
          padding: 20px 24px;
          border-top: 1px solid #f0f0f0;
        }}
        .grid {{
          display: grid;
          grid-template-columns: 220px 1fr;
          gap: 10px;
        }}
        .label {{
          color: #6b7280;
          font-size: 12px;
        }}
        .value {{
          font-weight: 600;
          word-break: break-word;
        }}
        .mono {{
          font-family: monospace;
          font-size: 12px;
        }}
        .alert {{
          margin-top: 14px;
          background: #fef2f2;
          border: 1px solid #fecaca;
          padding: 12px;
          border-radius: 8px;
          color: #7f1d1d;
        }}
        .alert-title {{
          font-weight: 700;
          margin-bottom: 4px;
        }}
        .alert-text {{
          margin-bottom: 6px;
        }}
        .alert-meta {{
          margin-top: 3px;
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">

          <div class="header">
            <div class="brand">Aidentitech</div>
            <div class="status">{final_status}</div>
            <span class="verified">VERIFIED: {str(verified).upper()}</span>
            <span class="sig-badge">SIGNATURE: {signature_status}</span>
            {override_block}
          </div>

          <div class="section">
            <div class="grid">
              <div class="label">Decision ID</div>
              <div class="value mono">{_fmt(data["decision_id"])}</div>

              <div class="label">Client</div>
              <div class="value">{_fmt(data["client_id"])}</div>

              <div class="label">Module</div>
              <div class="value">{_fmt(data["module"])}</div>

              <div class="label">Automated</div>
              <div class="value">{engine_status}</div>

              <div class="label">Final</div>
              <div class="value">{final_status}</div>

              <div class="label">Severity</div>
              <div class="value">{_fmt(data["severity"])}</div>

              <div class="label">Risk Score</div>
              <div class="value">{_fmt(data["risk_score"])}</div>

              <div class="label">Override</div>
              <div class="value">{_fmt_bool(data["has_admin_override"])}</div>

              <div class="label">Timestamp</div>
              <div class="value mono">{_fmt(data["latest_event_timestamp"])}</div>
            </div>
          </div>

          <div class="section">
            <div class="grid">
              <div class="label">Ledger Hash</div>
              <div class="value mono">{_fmt(data["ledger_hash"])}</div>

              <div class="label">Dossier Hash</div>
              <div class="value mono">{_fmt(data["dossier_hash"])}</div>

              <div class="label">Signature</div>
              <div class="value mono">{signature_value or "Not available"}</div>

              <div class="label">Signature Valid</div>
              <div class="value">{signature_status}</div>
            </div>
          </div>

        </div>
      </div>
    </body>
    </html>
    """
    return html
