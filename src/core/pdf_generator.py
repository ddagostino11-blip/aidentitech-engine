from io import BytesIO
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.core.dossier_normalizer import normalize_dossier_payload


BRAND_NAME = "Aidentitech"
BRAND_SUBTITLE = "Certified Technical Dossier"


def draw_header_footer(canvas, doc):
    canvas.saveState()

    canvas.setFillColor(colors.HexColor("#111111"))
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(24 * mm, 286 * mm, BRAND_NAME)

    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(24 * mm, 281.5 * mm, BRAND_SUBTITLE)

    canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
    canvas.setLineWidth(0.6)
    canvas.line(24 * mm, 278 * mm, 186 * mm, 278 * mm)

    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        24 * mm,
        14 * mm,
        f"{BRAND_NAME} — Cryptographically verifiable compliance record",
    )
    canvas.drawRightString(186 * mm, 14 * mm, f"Page {doc.page}")

    canvas.restoreState()


def generate_dossier_pdf(dossier: dict) -> BytesIO:
    dossier = normalize_dossier_payload(dossier).model_dump()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=24 * mm,
        rightMargin=24 * mm,
        topMargin=34 * mm,
        bottomMargin=22 * mm,
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
        spaceAfter=8,
    )

    field_label_style = ParagraphStyle(
        "FieldLabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#9CA3AF"),
        alignment=TA_LEFT,
        spaceAfter=0,
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

    field_value_emphasis_style = ParagraphStyle(
        "FieldValueEmphasisStyle",
        parent=field_value_style,
        textColor=colors.HexColor("#991B1B"),
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
        spaceAfter=0,
    )

    badge_title_style = ParagraphStyle(
        "BadgeTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=1,
    )

    badge_style = ParagraphStyle(
        "BadgeStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    badge_sub_style = ParagraphStyle(
        "BadgeSubStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    governance_alert_title_style = ParagraphStyle(
        "GovernanceAlertTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#7F1D1D"),
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    governance_alert_body_style = ParagraphStyle(
        "GovernanceAlertBodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#7F1D1D"),
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    timeline_heading_style = ParagraphStyle(
        "TimelineHeadingStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#111111"),
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    timeline_detail_style = ParagraphStyle(
        "TimelineDetailStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111111"),
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    check_name_style = ParagraphStyle(
        "CheckNameStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111111"),
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    check_status_style = ParagraphStyle(
        "CheckStatusStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#065F46"),
        alignment=TA_RIGHT,
        spaceAfter=0,
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

    def status_color(status: str):
        s = clean(status).upper()
        if s == "REJECTED":
            return colors.HexColor("#991B1B")
        if s == "APPROVED":
            return colors.HexColor("#065F46")
        return colors.HexColor("#1F2937")

    def normalize_anchor_filename(value: str) -> str:
        raw = clean(value)
        if not raw:
            return ""

        filename = os.path.basename(raw.replace("\\", "/"))
        filename = filename.replace("+00-00", "Z")
        filename = filename.replace("..", "")
        return filename

    def get_override_reason() -> str:
        timeline = dossier.get("timeline", []) or []
        for item in reversed(timeline):
            if clean(item.get("type")).upper() == "OVERRIDE":
                data = item.get("data", {}) or {}
                return clean(data.get("reason"))
        return ""

    def get_override_reviewer() -> str:
        timeline = dossier.get("timeline", []) or []
        for item in reversed(timeline):
            if clean(item.get("type")).upper() == "OVERRIDE":
                data = item.get("data", {}) or {}
                reviewer = clean(data.get("reviewer_id"))
                if reviewer.lower() == "aidentitech":
                    return "System"
                return reviewer or "System"
        return "System"

    def normalize_check_status(value: str) -> str:
        v = clean(value).lower()
        if v == "passed":
            return "✔ PASSED"
        if v == "failed":
            return "✖ FAILED"
        return v.upper() if v else "UNKNOWN"

    def classify_rule(rule_id: str) -> str:
        r = clean(rule_id).lower()

        if any(token in r for token in ["product", "batch", "required_"]):
            if any(token in r for token in ["temperature"]):
                return "Temperature Control"
            if any(token in r for token in ["gmp", "deviation", "capa"]):
                return "Quality & Compliance"
            return "Data Integrity"

        if any(token in r for token in ["gmp", "deviation", "capa"]):
            return "Quality & Compliance"

        if "temperature" in r:
            return "Temperature Control"

        return "Automated Checks"

    def grouped_audit_rows(audit_rows: list[dict]) -> list:
        grouped = {}
        order = []

        for rule in audit_rows:
            group_name = classify_rule(rule.get("rule_id"))
            if group_name not in grouped:
                grouped[group_name] = []
                order.append(group_name)
            grouped[group_name].append(rule)

        rows = []
        for group_name in order:
            rows.append(("__GROUP__", group_name, ""))
            for rule in grouped[group_name]:
                rows.append((
                    clean(rule.get("rule_id")) or "-",
                    normalize_check_status(rule.get("outcome")),
                    "rule",
                ))
        return rows

    def add_section(title: str):
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(clean(title), section_style))

    def add_divider():
        elements.append(HRFlowable(
            width="100%",
            thickness=0.6,
            color=colors.HexColor("#D1D5DB"),
            spaceBefore=0,
            spaceAfter=8,
        ))

    def add_kv_block(items, mono_keys=None, value_styles=None):
        mono_keys = mono_keys or set()
        value_styles = value_styles or {}
        rows = []

        for label, value in items:
            value = clean(value)
            if not value:
                continue

            current_value_style = value_styles.get(
                label,
                mono_style if label in mono_keys else field_value_style
            )

            rows.append([
                Paragraph(clean(label), field_label_style),
                Paragraph(value, current_value_style),
            ])

        if not rows:
            return

        table = Table(rows, colWidths=[40 * mm, 98 * mm])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 4))

    def add_audit_table(audit_rows):
        rows = grouped_audit_rows(audit_rows)
        if not rows:
            return

        table_rows = []
        styles_cmds = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]

        row_index = 0
        for name, status, kind in rows:
            if name == "__GROUP__":
                table_rows.append([
                    Paragraph(f"<b>{status.upper()}</b>", small_style),
                    Paragraph("", small_style),
                ])
                styles_cmds.extend([
                    ("SPAN", (0, row_index), (1, row_index)),
                    ("BACKGROUND", (0, row_index), (1, row_index), colors.HexColor("#F9FAFB")),
                    ("TOPPADDING", (0, row_index), (1, row_index), 6),
                    ("BOTTOMPADDING", (0, row_index), (1, row_index), 4),
                ])
            else:
                table_rows.append([
                    Paragraph(name, check_name_style),
                    Paragraph(status, check_status_style),
                ])
            row_index += 1

        table = Table(table_rows, colWidths=[100 * mm, 38 * mm])
        table.setStyle(TableStyle(styles_cmds))
        elements.append(table)
        elements.append(Spacer(1, 6))

    def add_governance_alert(reason: str):
        content = [
            [Paragraph("Governance Override", governance_alert_title_style)],
            [Paragraph("Final decision overridden due to audit finding.", governance_alert_body_style)],
        ]

        if reason:
            content.append([Paragraph(f"Reason: {reason}", governance_alert_body_style)])

        alert_table = Table(content, colWidths=[138 * mm])
        alert_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#7F1D1D")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#FECACA")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(alert_table)
        elements.append(Spacer(1, 10))

    def add_override_event_block(timestamp: str, action: str, reviewer: str, reason: str):
        block_rows = [
            [Paragraph("GOVERNANCE OVERRIDE EVENT", timeline_heading_style)],
            [Paragraph(f"<b>Timestamp:</b> {timestamp}", timeline_detail_style)],
            [Paragraph(f"<b>Action:</b> {action}", timeline_detail_style)],
            [Paragraph(f"<b>Reviewer:</b> {reviewer}", timeline_detail_style)],
            [Paragraph(f"<b>Reason:</b> {reason}", timeline_detail_style)],
        ]

        box = Table(block_rows, colWidths=[138 * mm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(box)
        elements.append(Spacer(1, 8))

    elements.append(Spacer(1, 8))

    final_status = clean(dossier.get("final_status") or dossier.get("engine_status"))
    decision = dossier.get("decision", {}) or {}
    override_reason = get_override_reason()
    override_reviewer = get_override_reviewer()

    banner_left = [
        Paragraph("COMPLIANCE DECISION", badge_title_style),
        Paragraph(final_status or "UNSPECIFIED", badge_style),
        Paragraph(
            f"Decision Code: {clean(decision.get('decision_code')) or 'N/A'}",
            badge_sub_style,
        ),
    ]

    banner_right = [
        Paragraph(
            f"<b>Severity</b><br/>{clean(decision.get('severity')) or clean(dossier.get('severity')) or 'N/A'}",
            badge_sub_style,
        ),
        Paragraph(
            f"<b>Risk Score</b><br/>{clean(decision.get('risk_score')) or clean(dossier.get('risk_score')) or 'N/A'}",
            badge_sub_style,
        ),
    ]

    banner = Table(
        [[banner_left, banner_right]],
        colWidths=[92 * mm, 46 * mm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_color(final_status)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "Audit-validated compliance decision with full traceability.",
        small_style,
    ))
    elements.append(Spacer(1, 8))

    if dossier.get("has_admin_override"):
        add_governance_alert(override_reason)

    add_section("Document Overview")
    add_kv_block([
        ("Dossier Type", dossier.get("dossier_type")),
        ("Decision ID", dossier.get("decision_id")),
        ("Timestamp", dossier.get("decision_timestamp")),
        ("Client", dossier.get("client_name") or clean(dossier.get("client_id"))),
        ("Module", dossier.get("module")),
    ])

    add_section("Decision Outcome")
    add_kv_block(
        [
            ("Automated Decision", dossier.get("engine_status")),
            ("Final Decision", dossier.get("final_status")),
            ("Decision Code", decision.get("decision_code")),
            ("Severity", decision.get("severity") or dossier.get("severity")),
            ("Risk Score", decision.get("risk_score") or dossier.get("risk_score")),
            ("Recommended Action", decision.get("recommended_action")),
            ("Batch Disposition", decision.get("batch_disposition")),
        ],
        value_styles={
            "Automated Decision": field_value_style,
            "Final Decision": field_value_emphasis_style if clean(dossier.get("final_status")).upper() == "REJECTED" else field_value_style,
        },
    )

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

    versioning = dossier.get("versioning", {}) or {}
    if any(v not in (None, "", [], {}) for v in versioning.values()):
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

    compliance_scope = dossier.get("compliance_scope", {}) or {}
    if compliance_scope:
        frameworks = compliance_scope.get("frameworks", []) or []
        add_section("Compliance Scope")
        add_kv_block([
            ("Criticality", compliance_scope.get("criticality")),
            ("Regulated", compliance_scope.get("regulated")),
            ("Requires Audit Trail", compliance_scope.get("requires_audit_trail")),
            ("Frameworks", ", ".join(clean(x) for x in frameworks if clean(x))),
        ])

    explanation = dossier.get("explanation", {}) or {}
    if explanation.get("summary") or explanation.get("details") or dossier.get("has_admin_override"):
        add_section("Technical Explanation")

        summary = clean(explanation.get("summary"))
        if dossier.get("has_admin_override") and summary:
            summary = "Initial validation completed successfully with no triggered issues."

        if summary:
            elements.append(Paragraph(summary, body_style))
            elements.append(Spacer(1, 6))

        details = explanation.get("details", []) or []
        if details:
            for item in details:
                item = clean(item)
                if item:
                    elements.append(Paragraph(f"• {item}", body_style))
            elements.append(Spacer(1, 6))

        if dossier.get("has_admin_override"):
            elements.append(Paragraph(
                "Final decision overridden due to governance audit action.",
                body_style,
            ))
            if override_reason:
                elements.append(Paragraph(
                    f"Reason: {override_reason}",
                    body_style,
                ))
            elements.append(Spacer(1, 6))

    timeline = dossier.get("timeline", []) or []
    if timeline:
        add_section("Event Timeline")

        for item in timeline:
            event_type = clean(item.get("type")).upper()
            timestamp = clean(item.get("timestamp"))
            data = item.get("data", {}) or {}

            if event_type == "DECISION":
                elements.append(Paragraph(
                    f"<b>DECISION</b> &nbsp;&nbsp;<font color='#6B7280'>{timestamp}</font>",
                    body_style,
                ))
                detail = (
                    f"<b>Status:</b> {clean(data.get('status'))}<br/>"
                    f"<b>Severity:</b> {clean(data.get('severity'))}<br/>"
                    f"<b>Risk:</b> {clean(data.get('risk_score'))}"
                )
                elements.append(Paragraph(detail, timeline_detail_style))
                elements.append(Spacer(1, 6))

            elif event_type == "OVERRIDE":
                add_override_event_block(
                    timestamp=timestamp,
                    action=clean(data.get("action")),
                    reviewer=("System" if clean(data.get("reviewer_id")).lower() == "aidentitech" else clean(data.get("reviewer_id")) or "System"),
                    reason=clean(data.get("reason")),
                )

            elif event_type == "REVIEW":
                elements.append(Paragraph(
                    f"<b>REVIEW</b> &nbsp;&nbsp;<font color='#6B7280'>{timestamp}</font>",
                    body_style,
                ))
                detail = (
                    f"<b>Action:</b> {clean(data.get('action'))}<br/>"
                    f"<b>Reviewer:</b> {clean(data.get('reviewer_id'))}<br/>"
                    f"<b>Reason:</b> {clean(data.get('reason'))}"
                )
                elements.append(Paragraph(detail, timeline_detail_style))
                elements.append(Spacer(1, 6))

            else:
                elements.append(Paragraph(
                    f"<b>{event_type}</b> &nbsp;&nbsp;<font color='#6B7280'>{timestamp}</font>",
                    body_style,
                ))
                elements.append(Paragraph(clean(data), timeline_detail_style))
                elements.append(Spacer(1, 6))

    audit = dossier.get("audit", []) or []
    if audit:
        add_section("Automated Checks (Pre-Audit)")
        add_audit_table(audit)

    if dossier.get("has_admin_override"):
        add_section("Governance Decision")
        add_kv_block([
            ("Previous Decision", dossier.get("engine_status")),
            ("Final Decision", dossier.get("final_status")),
            ("Reviewer", "System" if override_reviewer.lower() == "aidentitech" else override_reviewer),
            ("Reason", override_reason),
        ])

    proof = dossier.get("proof", {}) or {}
    add_section("Certification & Integrity Evidence")
    add_kv_block(
        [
            ("Ledger Hash", dossier.get("ledger_hash") or proof.get("ledger_hash")),
            ("Latest Ledger Hash", dossier.get("latest_ledger_hash")),
            ("Checkpoint Hash", proof.get("checkpoint_hash")),
            ("Anchor SHA256", proof.get("anchor_sha256")),
            ("Anchor External File", normalize_anchor_filename(proof.get("anchor_external_path"))),
            ("Timestamp Status", proof.get("timestamp_status")),
            ("Timestamp Provider", proof.get("timestamp_provider")),
            ("Timestamp Proof", proof.get("timestamp_proof")),
        ],
        mono_keys={"Ledger Hash", "Latest Ledger Hash", "Checkpoint Hash", "Anchor SHA256"},
    )

    add_section("Dossier Fingerprint")
    add_kv_block(
        [("Hash", dossier.get("dossier_hash"))],
        mono_keys={"Hash"},
    )

    elements.append(Spacer(1, 10))
    add_divider()
    elements.append(Paragraph(
        f"Certified by {BRAND_NAME} — Cryptographically verifiable compliance record.",
        small_style,
    ))
    elements.append(Paragraph(
        f"This document is generated by {BRAND_NAME} and represents a cryptographically verifiable record of a compliance decision.",
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
