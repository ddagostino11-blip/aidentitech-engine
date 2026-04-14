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
        elements.append(Paragraph(f"<b>{title}:</b> {value}", styles["Normal"]))
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

    # Integration
    integration = dossier.get("integration", {})
    add("Source System", integration.get("source_system"))
    add("Site", integration.get("site"))

    # Compliance
    add("Ledger Hash", dossier.get("ledger_hash"))

    elements.append(Spacer(1, 16))
    elements.append(Paragraph("<b>Audit Trail</b>", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    for rule in dossier.get("audit", []):
        text = f"{rule.get('rule_id')} → {rule.get('outcome')}"
        elements.append(Paragraph(text, styles["Normal"]))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    buffer.seek(0)

    return buffer
