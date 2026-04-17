from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def draw_header_footer(canvas, doc):
    canvas.saveState()

    # HEADER
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(colors.HexColor("#111111"))
    canvas.drawString(28 * mm, 285 * mm, "Aidentitech")

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(28 * mm, 281 * mm, "Certified Technical Dossier")

    canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
    canvas.setLineWidth(0.5)
    canvas.line(28 * mm, 278 * mm, 182 * mm, 278 * mm)

    # FOOTER
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(
        28 * mm,
        15 * mm,
        "Aidentitech — Cryptographically verifiable compliance record"
    )
    canvas.drawRightString(182 * mm, 15 * mm, f"Page {doc.page}")

    canvas.restoreState()


def generate_dossier_pdf(dossier: dict) -> BytesIO:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=28 * mm,
        rightMargin=28 * mm,
        topMargin=30 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111111"),
        spaceBefore=18,
        spaceAfter=10,
    )

    field_label_style = ParagraphStyle(
        "FieldLabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#9CA3AF"),
        alignment=TA_LEFT,
        spaceAfter=1,
    )

    field_value_style = ParagraphStyle(
        "FieldValueStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#111111"),
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#111111"),
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    small_style = ParagraphStyle(
        "SmallStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4B5563"),
        alignment=TA_LEFT,
        spaceAfter=3,
    )

    mono_style = ParagraphStyle(
        "MonoStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#111111"),
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    elements = []

    def clean(value):
        if value is None:
            return ""
        return (
            str(value)
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\x0c", "")
            .strip()
        )

    def add_kv_block(items, mono_keys=None):
        mono_keys = mono_keys or set()
        rows = []

        for label, value in items:
            value = clean(value)
            if not value:
                continue

            value_style = mono_style if label in mono_keys else field_value_style

            rows.append([
                Paragraph(clean(label), field_label_style),
                Paragraph(value, value_style),
            ])

        if not rows:
            return

        table = Table(rows, colWidths=[42 * mm, 84 * mm])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 6))

    def add_section(title):
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(clean(title), section_style))

    def add_divider():
        divider = Table([[""]], colWidths=[126 * mm], rowHeights=[0.5 * mm])
        divider.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#D1D5DB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(divider)
        elements.append(Spacer(1, 6))

    # spacing iniziale perché header è disegnato dal canvas
    elements.append(Spacer(1, 8))
    add_divider()

    # ===== OVERVIEW =====
    add_section("Document Overview")
    add_kv_block([
        ("Dossier Type", dossier.get("dossier_type")),
        ("Decision ID", dossier.get("decision_id")),
        ("Timestamp", dossier.get("decision_timestamp")),
        ("Client", dossier.get("client_id")),
        ("Module", dossier.get("module")),
    ])

    # ===== DECISION =====
    decision = dossier.get("decision", {})
    add_section("Decision Outcome")
    add_kv_block([
        ("Engine Status", dossier.get("engine_status")),
        ("Final Status", dossier.get("final_status")),
        ("Decision Code", decision.get("decision_code")),
        ("Severity", decision.get("severity")),
        ("Risk Score", decision.get("risk_score")),
        ("Recommended Action", decision.get("recommended_action")),
        ("Batch Disposition", decision.get("batch_disposition")),
    ])

    # ===== LIFECYCLE =====
    add_section("Decision Lifecycle")
    add_kv_block([
        ("Human Review", dossier.get("has_human_review")),
        ("Admin Override", dossier.get("has_admin_override")),
        ("Latest Action", dossier.get("latest_review_action")),
        ("Review Count", dossier.get("review_count")),
        ("Override Count", dossier.get("override_count")),
        ("Latest Event Timestamp", dossier.get("latest_event_timestamp")),
        ("Events Count", dossier.get("events_count")),
    ])

    # ===== VERSIONING =====
    versioning = dossier.get("versioning", {})
    if isinstance(versioning, dict) and any(v not in (None, "", [], {}) for v in versioning.values()):
        add_section("Versioning")
        add_kv_block(
            [
                ("Engine Version", versioning.get("engine_version")),
                ("Policy Version", versioning.get("policy_version")),
                ("Rules Version", versioning.get("rules_version")),
                ("Rules Hash", versioning.get("rules_hash")),
            ],
            mono_keys={"Rules Hash"},
        )

    # ===== COMPLIANCE =====
    compliance_scope = dossier.get("compliance_scope", {})
    if isinstance(compliance_scope, dict) and (
        any(v not in (None, "", [], {}) for k, v in compliance_scope.items() if k != "frameworks")
        or compliance_scope.get("frameworks")
    ):
        add_section("Compliance Scope")
        frameworks = compliance_scope.get("frameworks", [])
        add_kv_block([
            ("Criticality", compliance_scope.get("criticality")),
            ("Regulated", compliance_scope.get("regulated")),
            ("Requires Audit Trail", compliance_scope.get("requires_audit_trail")),
            ("Frameworks", ", ".join(clean(x) for x in frameworks if clean(x)) if frameworks else ""),
        ])

    # ===== EXPLANATION =====
    explanation = dossier.get("explanation", {})
    if isinstance(explanation, dict) and (explanation.get("summary") or explanation.get("details")):
        add_section("Technical Explanation")

        summary = clean(explanation.get("summary"))
        if summary:
            elements.append(Paragraph(summary, body_style))
            elements.append(Spacer(1, 4))

        for item in explanation.get("details", []):
            item = clean(item)
            if item:
                elements.append(Paragraph(f"• {item}", body_style))

        elements.append(Spacer(1, 6))

    # ===== TIMELINE =====
    timeline = dossier.get("timeline", [])
    if timeline:
        add_section("Event Timeline")

        for item in timeline:
            event_type = clean(item.get("type"))
            timestamp = clean(item.get("timestamp"))
            data = item.get("data", {}) or {}

            elements.append(Paragraph(
                f"<b>{event_type}</b> &nbsp;&nbsp;<font color='#6B7280'>{timestamp}</font>",
                body_style,
            ))

            if event_type == "DECISION":
                detail = (
                    f"Status: {clean(data.get('status'))} | "
                    f"Severity: {clean(data.get('severity'))} | "
                    f"Risk: {clean(data.get('risk_score'))}"
                )
            elif event_type in {"REVIEW", "OVERRIDE"}:
                detail = (
                    f"Action: {clean(data.get('action'))} | "
                    f"Reviewer: {clean(data.get('reviewer_id'))} | "
                    f"Reason: {clean(data.get('reason'))}"
                )
            else:
                detail = clean(data)

            elements.append(Paragraph(detail, small_style))
            elements.append(Spacer(1, 6))

    # ===== AUDIT =====
    audit = dossier.get("audit", [])
    if audit:
        add_section("Rule Evaluation Log")

        for rule in audit:
            rule_id = clean(rule.get("rule_id"))
            outcome = clean(rule.get("outcome"))

            line = f"• <b>{rule_id}</b>"
            if outcome:
                line += f" <font color='#6B7280'>({outcome})</font>"

            elements.append(Paragraph(line, body_style))

        elements.append(Spacer(1, 6))

    # ===== PROOF =====
    proof = dossier.get("proof", {}) or {}
    add_section("Certification & Integrity Evidence")
    add_kv_block(
        [
            ("Ledger Hash", dossier.get("ledger_hash") or proof.get("ledger_hash")),
            ("Latest Ledger Hash", dossier.get("latest_ledger_hash")),
            ("Checkpoint Hash", proof.get("checkpoint_hash")),
            ("Anchor SHA256", proof.get("anchor_sha256")),
            ("Anchor External Path", clean(proof.get("anchor_external_path")).replace("/Users/domenico/Desktop/", ".../")),
            ("Timestamp Status", proof.get("timestamp_status")),
            ("Timestamp Provider", proof.get("timestamp_provider")),
            ("Timestamp Proof", proof.get("timestamp_proof")),
        ],
        mono_keys={"Ledger Hash", "Latest Ledger Hash", "Checkpoint Hash", "Anchor SHA256"},
    )

    # ===== HASH =====
    add_section("Dossier Fingerprint")
    add_kv_block(
        [("Hash", dossier.get("dossier_hash"))],
        mono_keys={"Hash"},
    )

    # ===== FOOTER CONTENT =====
    elements.append(Spacer(1, 12))
    add_divider()
    elements.append(Paragraph(
        "Certified by Aidentitech — Cryptographically verifiable compliance record.",
        small_style,
    ))
    elements.append(Paragraph(
        "This document is generated by Aidentitech and represents a cryptographically verifiable record of a compliance decision.",
        small_style,
    ))
    elements.append(Paragraph(
        "Integrity may be independently verified using the associated ledger hash, checkpoint reference, and anchoring evidence.",
        small_style,
    ))

    doc.build(
        elements,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer,
    )
    buffer.seek(0)
    return buffer
