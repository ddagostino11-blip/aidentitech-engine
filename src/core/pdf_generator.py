from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO


def generate_dossier_pdf(dossier: dict) -> BytesIO:
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    def add(title, value):
        safe_value = "" if value is None else str(value)
        elements.append(Paragraph(f"<b>{title}:</b> {safe_value}", styles["Normal"]))
        elements.append(Spacer(1, 8))

    # Header
    elements.append(Paragraph("<b>AIDENTITECH DOSSIER</b>", styles["Title"]))
    elements.append(Spacer(1, 16))

    # Core info
    add("Decision ID", dossier.get("decision_id"))
    add("Timestamp", dossier.get("decision_timestamp"))
    add("Client", dossier.get("client_id"))
    add("Module", dossier.get("module"))

    decision = dossier.get("decision", {})
    add("Status", decision.get("status"))
    add("Severity", decision.get("severity"))
    add("Risk Score", decision.get("risk_score"))
    add("Decision Code", decision.get("decision_code"))
    add("Recommended Action", decision.get("recommended_action"))
    add("Batch Disposition", decision.get("batch_disposition"))

    # Integration
    integration = dossier.get("integration", {})
    add("Source System", integration.get("source_system"))
    add("Site", integration.get("site"))
    add("Line", integration.get("line"))
    add("Ingestion Timestamp", integration.get("ingestion_timestamp"))

    # Integrity / sealing
    add("Ledger Hash", dossier.get("ledger_hash"))
    add("Dossier Hash", dossier.get("dossier_hash"))

    # Versioning
    versioning = dossier.get("versioning", {})
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Versioning</b>", styles["Heading2"]))
    elements.append(Spacer(1, 8))
    add("Engine Version", versioning.get("engine_version"))
    add("Policy Version", versioning.get("policy_version"))
    add("Rules Version", versioning.get("rules_version"))
    add("Rules Hash", versioning.get("rules_hash"))

    # Compliance
    compliance_scope = dossier.get("compliance_scope", {})
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Compliance Scope</b>", styles["Heading2"]))
    elements.append(Spacer(1, 8))
    add("Criticality", compliance_scope.get("criticality"))
    add("Regulated", compliance_scope.get("regulated"))
    add("Requires Audit Trail", compliance_scope.get("requires_audit_trail"))

    frameworks = compliance_scope.get("frameworks", [])
    if frameworks:
        add("Frameworks", ", ".join(frameworks))

    # Explanation
    explanation = dossier.get("explanation", {})
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Explanation</b>", styles["Heading2"]))
    elements.append(Spacer(1, 8))
    add("Summary", explanation.get("summary"))

    details = explanation.get("details", [])
    if details:
        for item in details:
            elements.append(Paragraph(f"- {item}", styles["Normal"]))
            elements.append(Spacer(1, 4))

    # Payload
    payload = dossier.get("payload", {})
    if payload:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<b>Normalized Payload</b>", styles["Heading2"]))
        elements.append(Spacer(1, 8))
        for key, value in payload.items():
            add(key, value)

    # Audit trail
    elements.append(Spacer(1, 16))
    elements.append(Paragraph("<b>Audit Trail</b>", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    for rule in dossier.get("audit", []):
        text = (
            f"{rule.get('rule_id')} → {rule.get('outcome')} "
            f"(field={rule.get('field')}, actual={rule.get('actual_value')})"
        )
        elements.append(Paragraph(text, styles["Normal"]))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    buffer.seek(0)

    return buffer
