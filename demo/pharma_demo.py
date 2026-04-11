import sys
import time

BASE_URL = "http://127.0.0.1:8000"


def line():
    print("=" * 76)


def soft_line():
    print("-" * 76)


def section(title: str):
    print()
    line()
    print(title)
    line()


def ok(message: str):
    print(f"✔ {message}")


def info(message: str):
    print(f"➜ {message}")


def warn(message: str):
    print(f"⚠ {message}")


def fail(message: str):
    print(f"✖ {message}")


def pause(seconds: float = 1.2):
    time.sleep(seconds)


def print_audit_steps(steps):
    if not steps:
        fail("Audit trail is empty.")
        return False

    ok("Audit trail retrieved")
    print()
    print("Audit steps:")
    soft_line()

    for index, step in enumerate(steps, start=1):
        action = step.get("action", "unknown")
        actor = step.get("actor", "unknown")
        timestamp = step.get("timestamp", "unknown")
        notes = step.get("notes")

        print(f"{index}. Action    : {action}")
        print(f"   Actor     : {actor}")
        print(f"   Timestamp : {timestamp}")
        if notes:
            print(f"   Notes     : {notes}")
        soft_line()

    return True


def normalize_text(value: str):
    value = (value or "").strip()
    return value if value else None


def parse_temperature(raw_value: str):
    raw_value = (raw_value or "").strip()

    if not raw_value:
        return None, None

    try:
        return float(raw_value), None
    except ValueError:
        return None, "Temperature is not a valid number"


def parse_gmp(raw_value: str):
    raw_value = (raw_value or "").strip().lower()

    if not raw_value:
        return None, None

    if raw_value in {"yes", "y"}:
        return True, None

    if raw_value in {"no", "n"}:
        return False, None

    return None, "GMP compliance value is invalid"


def evaluate_operational_case(
    client_id,
    product_id,
    batch,
    temperature,
    gmp_compliant,
    temperature_error=None,
    gmp_error=None,
):
    missing_fields = []
    absurd_reasons = []
    risk_reasons = []

    if not client_id:
        missing_fields.append("client_id")

    if not product_id:
        missing_fields.append("product_id")

    if not batch:
        missing_fields.append("batch")

    if temperature is None and not temperature_error:
        missing_fields.append("temperature")

    if gmp_compliant is None and not gmp_error:
        missing_fields.append("gmp_compliant")

    if missing_fields:
        return {
            "outcome": "INSUFFICIENT DATA",
            "missing_fields": missing_fields,
            "reasons": ["Insufficient mandatory input to perform evaluation"],
            "confidence": "N/A",
            "dossier_ready": False,
            "risk_score": None,
        }

    if temperature_error:
        absurd_reasons.append(temperature_error)

    if gmp_error:
        absurd_reasons.append(gmp_error)

    if temperature is not None and (temperature < -50 or temperature > 100):
        absurd_reasons.append("Temperature outside plausible physical range")

    if batch and len(batch) < 3:
        absurd_reasons.append("Batch identifier too short to be considered valid")

    if absurd_reasons:
        return {
            "outcome": "NOT APPROVED",
            "missing_fields": [],
            "reasons": absurd_reasons,
            "confidence": "0.99",
            "dossier_ready": False,
            "risk_score": "HIGH",
        }

    if gmp_compliant is False:
        risk_reasons.append("GMP compliance missing")

    if temperature is not None and temperature >= 8:
        risk_reasons.append("Temperature out of controlled range")

    if risk_reasons:
        return {
            "outcome": "RISK ANALYSIS REQUIRED",
            "missing_fields": [],
            "reasons": risk_reasons,
            "confidence": "0.92",
            "dossier_ready": False,
            "risk_score": "MEDIUM/HIGH",
        }

    return {
        "outcome": "AUDIT READY DOSSIER",
        "missing_fields": [],
        "reasons": ["All mandatory parameters are complete and compliant"],
        "confidence": "0.97",
        "dossier_ready": True,
        "risk_score": "LOW",
    }


def build_operational_audit(
    client_id,
    product_id,
    batch,
    active_regime,
    outcome,
    reasons,
    missing_fields=None,
):
    steps = [
        {
            "action": "input_received",
            "actor": "SYSTEM",
            "timestamp": "synthetic-demo-ts-01",
            "notes": f"client={client_id or 'N/A'} | product={product_id or 'N/A'} | batch={batch or 'N/A'}",
        },
        {
            "action": "regime_bound",
            "actor": "SYSTEM",
            "timestamp": "synthetic-demo-ts-02",
            "notes": active_regime,
        },
    ]

    if outcome == "INSUFFICIENT DATA":
        steps.append(
            {
                "action": "validation_blocked_incomplete_data",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-03",
                "notes": ", ".join(missing_fields or []),
            }
        )
    elif outcome == "NOT APPROVED":
        steps.append(
            {
                "action": "plausibility_check_failed",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-03",
                "notes": " | ".join(reasons),
            }
        )
        steps.append(
            {
                "action": "case_not_approved",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-04",
                "notes": active_regime,
            }
        )
    elif outcome == "RISK ANALYSIS REQUIRED":
        steps.append(
            {
                "action": "risk_analysis_triggered",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-03",
                "notes": " | ".join(reasons),
            }
        )
        steps.append(
            {
                "action": "dossier_withheld",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-04",
                "notes": "Awaiting risk review under active regime",
            }
        )
    elif outcome == "AUDIT READY DOSSIER":
        steps.append(
            {
                "action": "case_validated",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-03",
                "notes": active_regime,
            }
        )
        steps.append(
            {
                "action": "dossier_released",
                "actor": "SYSTEM",
                "timestamp": "synthetic-demo-ts-04",
                "notes": "Audit-ready dossier released",
            }
        )

    return steps


def run_operational_case():
    section("AIDENTITECH | OPERATIONAL PRE-COMPLIANCE CASE")
    print("Scenario:")
    print("Caso operativo pharma: dossier / batch validation sotto normativa attiva.")
    print()
    print("Obiettivo:")
    print("Mostrare come il sistema classifica automaticamente un caso reale")
    print("in base alla normativa attiva, prima di un audit regolatorio classico.")

    print()
    print("Inserisci i dati del caso.")
    print("Puoi lasciare campi vuoti per simulare dati insufficienti.")
    print()

    client_id = normalize_text(input("Client ID [blank allowed]: "))
    product_id = normalize_text(input("Product ID [blank allowed]: "))
    batch = normalize_text(input("Batch [blank allowed]: "))
    temperature, temperature_error = parse_temperature(input("Temperature [blank allowed]: "))
    gmp_compliant, gmp_error = parse_gmp(input("GMP compliant? (yes/no) [blank allowed]: "))

    active_regime = "GMP_v1_ACTIVE"

    evaluation = evaluate_operational_case(
        client_id=client_id,
        product_id=product_id,
        batch=batch,
        temperature=temperature,
        gmp_compliant=gmp_compliant,
        temperature_error=temperature_error,
        gmp_error=gmp_error,
    )

    outcome = evaluation["outcome"]
    reasons = evaluation["reasons"]
    missing_fields = evaluation["missing_fields"]
    confidence = evaluation["confidence"]
    risk_score = evaluation["risk_score"]
    dossier_ready = evaluation["dossier_ready"]

    section("CONTEXT")
    print(f"Active regulatory regime : {active_regime}")
    print("Regulatory change        : none detected")
    print("Processing mode          : operational pre-compliance")

    section("INPUT SUMMARY")
    print(f"Client ID                : {client_id or 'MISSING'}")
    print(f"Product ID               : {product_id or 'MISSING'}")
    print(f"Batch                    : {batch or 'MISSING'}")
    print(f"Temperature              : {temperature if temperature is not None else 'MISSING'}")
    print(
        f"GMP compliant            : "
        f"{'YES' if gmp_compliant is True else 'NO' if gmp_compliant is False else 'MISSING'}"
    )

    pause()

    section("STEP 1 | INPUT COMPLETENESS AND PLAUSIBILITY CHECK")
    info(f"Evaluating case under active regime: {active_regime}")
    pause()

    if missing_fields:
        warn("Mandatory data missing")
        print("Missing fields:")
        for field in missing_fields:
            print(f"  - {field}")
    else:
        ok("Mandatory input completeness verified")

    if temperature_error or gmp_error:
        warn("Input plausibility issues detected")
        if temperature_error:
            print(f"  - {temperature_error}")
        if gmp_error:
            print(f"  - {gmp_error}")

    pause()

    section("STEP 2 | PRE-COMPLIANCE DECISION ENGINE")
    info("Classifying case automatically...")
    pause()

    if risk_score:
        ok(f"Risk score: {risk_score}")

    if confidence:
        ok(f"Decision confidence: {confidence}")

    if outcome == "INSUFFICIENT DATA":
        warn("Case classified: INSUFFICIENT DATA")
        print("Explanation:")
        for reason in reasons:
            print(f"  - {reason}")

    elif outcome == "NOT APPROVED":
        fail("Case classified: NOT APPROVED")
        print("Explanation:")
        for reason in reasons:
            print(f"  - {reason}")

    elif outcome == "RISK ANALYSIS REQUIRED":
        warn("Case classified: RISK ANALYSIS REQUIRED")
        print("Explanation:")
        for reason in reasons:
            print(f"  - {reason}")

    elif outcome == "AUDIT READY DOSSIER":
        ok("Case classified: AUDIT READY DOSSIER")
        print("Explanation:")
        for reason in reasons:
            print(f"  - {reason}")

    if dossier_ready:
        ok("Dossier release authorized under active regime")
    else:
        warn("Dossier release not authorized at current decision state")

    pause()

    section("STEP 3 | SYNTHETIC AUDIT TRAIL")
    info("Generating operational audit trail...")
    pause()

    synthetic_audit = build_operational_audit(
        client_id=client_id,
        product_id=product_id,
        batch=batch,
        active_regime=active_regime,
        outcome=outcome,
        reasons=reasons,
        missing_fields=missing_fields,
    )

    if not print_audit_steps(synthetic_audit):
        sys.exit(1)

    section("FINAL RESULT")
    print("Business outcome:")

    if outcome == "INSUFFICIENT DATA":
        print("  - Evaluation blocked before compliance classification")
        print("  - Missing information detected early")
        print("  - No false approval issued")
        print("  - Additional data required before proceeding")

    elif outcome == "NOT APPROVED":
        print("  - Case rejected before audit submission")
        print("  - Implausible or invalid input detected")
        print("  - Preventive compliance barrier activated")
        print("  - No dossier released")

    elif outcome == "RISK ANALYSIS REQUIRED":
        print("  - Case did not pass automatic release")
        print("  - Risk analysis required before proceeding")
        print("  - Reasons captured and explained")
        print("  - No dossier released under current state")

    elif outcome == "AUDIT READY DOSSIER":
        print("  - Case passed automated pre-compliance checks")
        print("  - Dossier classified as audit-ready")
        print("  - No blocking issues detected")
        print("  - Full traceability preserved")

    print(f"  - Decision remains linked to regime: {active_regime}")

    print()
    if outcome == "AUDIT READY DOSSIER":
        ok("End state: dossier released and audit-ready")
    elif outcome == "RISK ANALYSIS REQUIRED":
        warn("End state: case held for risk analysis")
    elif outcome == "NOT APPROVED":
        fail("End state: case not approved")
    else:
        warn("End state: evaluation blocked due to insufficient data")

    print()
    ok("Operational demo complete")


def run_regulatory_change_case():
    section("AIDENTITECH | REGULATORY GOVERNANCE CASE")
    print("Scenario:")
    print("Sentinel rileva un delta normativo e attiva la governance del cambio regime.")
    print()
    print("Obiettivo:")
    print("Mostrare detection del cambio, versioning, freeze legacy, gate legale")
    print("e audit trail completo del passaggio normativo.")

    current_regime = "GMP_v1_ACTIVE"
    pending_regime = "GMP_v2_PENDING"
    activated_regime = "GMP_v2_ACTIVE"
    delta_name = "NEW_GMP_RULE_v2"
    impact = "HIGH"

    print()
    print("Scegli decisione legale sul nuovo regime:")
    print("1. Approve activation")
    print("2. Reject activation")
    choice = input("Selection [1]: ").strip() or "1"
    decision = "approve" if choice == "1" else "reject"

    section("REGULATORY CONTEXT")
    print(f"Current active regime     : {current_regime}")
    print(f"Detected delta            : {delta_name}")
    print(f"Impact level              : {impact}")
    print(f"Proposed new regime       : {pending_regime}")

    pause()

    section("STEP 1 | SENTINEL DETECTS REGULATORY DELTA")
    info("Sentinel scanning regulatory updates...")
    pause()
    warn(f"Regulatory delta detected: {delta_name}")
    warn(f"Impact level: {impact}")
    ok("Change requires governance workflow")

    pause()

    section("STEP 2 | VERSIONING AND LEGACY FREEZE")
    info("Creating pending regulatory version...")
    pause()
    ok(f"New regime prepared: {pending_regime}")
    ok(f"Legacy regime frozen for transition control: {current_regime}")
    ok("Routing activation request to legal gate")

    pause()

    section("STEP 3 | LEGAL ACTIVATION GATE")
    info("Legal team reviewing normative delta...")
    pause()
    ok(f"Legal decision applied: {decision.upper()}")

    if decision == "approve":
        active_regime = activated_regime
        warn("Legacy regime remains frozen for historical traceability")
        ok(f"New active regime: {active_regime}")
    else:
        active_regime = current_regime
        warn("New regime activation rejected")
        ok(f"Current regime remains active: {active_regime}")

    pause()

    section("STEP 4 | SYNTHETIC AUDIT TRAIL")
    synthetic_audit = [
        {
            "action": "delta_detected",
            "actor": "SENTINEL",
            "timestamp": "synthetic-demo-ts-01",
            "notes": delta_name,
        },
        {
            "action": "version_created",
            "actor": "SYSTEM",
            "timestamp": "synthetic-demo-ts-02",
            "notes": pending_regime,
        },
        {
            "action": "legacy_regime_frozen",
            "actor": "SYSTEM",
            "timestamp": "synthetic-demo-ts-03",
            "notes": current_regime,
        },
        {
            "action": "legal_approved" if decision == "approve" else "legal_rejected",
            "actor": "LEGAL_TEAM",
            "timestamp": "synthetic-demo-ts-04",
            "notes": f"{decision} activation of {pending_regime}",
        },
        {
            "action": "regime_activated" if decision == "approve" else "regime_activation_blocked",
            "actor": "SYSTEM",
            "timestamp": "synthetic-demo-ts-05",
            "notes": active_regime,
        },
    ]

    if not print_audit_steps(synthetic_audit):
        sys.exit(1)

    section("FINAL RESULT")
    print("Business outcome:")
    print("  - Regulatory change detected automatically")
    print("  - New normative version created")
    print("  - Legacy regime preserved for historical continuity")
    print("  - Human legal approval used as governance gate")
    print("  - Full audit trail preserved across the transition")

    print()
    if decision == "approve":
        ok(f"End state: {activated_regime} activated successfully")
    else:
        warn(f"End state: activation blocked, {current_regime} remains active")

    print()
    ok("Regulatory governance demo complete")


def run_demo():
    section("AIDENTITECH | PLATFORM DEMO")
    print("This demo shows the two core modes of the platform:")
    print("1. Operational pre-compliance under active regulation")
    print("2. Regulatory governance and normative versioning")

    print()
    print("Choose demo mode:")
    print("1. Operational pre-compliance case")
    print("2. Regulatory change governance case")
    mode = input("Selection [1]: ").strip() or "1"

    if mode == "1":
        run_operational_case()
    elif mode == "2":
        run_regulatory_change_case()
    else:
        fail("Invalid selection.")
        sys.exit(1)


if __name__ == "__main__":
    run_demo()

