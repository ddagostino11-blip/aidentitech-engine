from pathlib import Path
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _stringify(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def _write_lines(pdf: canvas.Canvas, lines: List[str], x: int, y: int, line_height: int = 16) -> int:
    current_y = y

    for line in lines:
        if current_y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            current_y = 800

        pdf.drawString(x, current_y, line[:110])
        current_y -= line_height

    return current_y


def export_dossier_pdf(dossier: Dict[str, Any], output_path: str) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output), pagesize=A4)
    pdf.setTitle(f"Dossier {dossier.get('dossier_id', '')}")

    y = 800
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Aidentitech Pre-Compliance Dossier")
    y -= 30

    pdf.setFont("Helvetica", 10)

    header_lines = [
        f"Dossier ID: {dossier.get('dossier_id')}",
        f"Dossier Type: {dossier.get('dossier_type')}",
        f"Module: {dossier.get('module')}",
        f"Jurisdiction: {dossier.get('jurisdiction')}",
        f"Generated At: {dossier.get('generated_at')}",
        ""
    ]
    y = _write_lines(pdf, header_lines, 50, y)

    payload = dossier.get("payload_received", {})
    payload_lines = ["PAYLOAD RECEIVED"]
    for key, value in payload.items():
        payload_lines.append(f"- {key}: {_stringify(value)}")
    payload_lines.append("")
    y = _write_lines(pdf, payload_lines, 50, y)

    decision = dossier.get("decision", {})
    decision_lines = [
        "DECISION",
        f"- Status: {_stringify(decision.get('status'))}",
        f"- Severity: {_stringify(decision.get('severity'))}",
        f"- Risk Score: {_stringify(decision.get('risk_score'))}",
        f"- Recommended Action: {_stringify(decision.get('recommended_action'))}",
        ""
    ]
    y = _write_lines(pdf, decision_lines, 50, y)

    issues = decision.get("issues", [])
    issue_lines = ["ISSUES"]
    if not issues:
        issue_lines.append("- None")
    else:
        for issue in issues:
            if isinstance(issue, dict):
                issue_lines.append(
                    f"- {issue.get('code', 'unknown')} | field={issue.get('field')} | "
                    f"value={issue.get('actual_value')} | threshold={issue.get('threshold')}"
                )
            else:
                issue_lines.append(f"- {_stringify(issue)}")
    issue_lines.append("")
    y = _write_lines(pdf, issue_lines, 50, y)

    explanation = decision.get("explanation", {})
    explanation_lines = [
        "EXPLANATION",
        f"- Summary: {_stringify(explanation.get('summary'))}"
    ]
    for detail in explanation.get("details", []):
        explanation_lines.append(f"- {_stringify(detail)}")
    explanation_lines.append("")
    y = _write_lines(pdf, explanation_lines, 50, y)

    regulatory_context = dossier.get("regulatory_context", {})
    regulatory_lines = [
        "REGULATORY CONTEXT",
        f"- Delta Detected: {_stringify(regulatory_context.get('delta_detected'))}",
        f"- Delta Reference: {_stringify(regulatory_context.get('delta_reference'))}",
        f"- Rule Version Reference: {_stringify(regulatory_context.get('rule_version_reference'))}",
        ""
    ]
    y = _write_lines(pdf, regulatory_lines, 50, y)

    immutable_evidence = dossier.get("immutable_evidence", {})
    evidence_lines = [
        "IMMUTABLE EVIDENCE",
        f"- Record Type: {_stringify(immutable_evidence.get('record_type'))}",
        f"- SHA256: {_stringify(immutable_evidence.get('sha256'))}",
        ""
    ]
    y = _write_lines(pdf, evidence_lines, 50, y)

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        50,
        max(y - 20, 40),
        "This PDF is a human-readable rendering of the canonical dossier record."
    )

    pdf.save()
    return str(output)
