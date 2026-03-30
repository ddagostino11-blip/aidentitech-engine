from pathlib import Path
import json


def load_latest_dossier() -> Path:
    files = sorted(Path("validation_output").glob("dossier_*.json"))
    if not files:
        raise FileNotFoundError("NO_DOSSIER_FOUND")
    return files[-1]


def status_of_test(test: dict) -> str:
    details = test.get("details", {})
    if isinstance(details, dict):
        return str(details.get("status", "UNKNOWN"))
    return "UNKNOWN"


def build_report(dossier: dict, dossier_path: Path) -> str:
    summary = dossier.get("summary", {})
    results = summary.get("results", []) if isinstance(summary, dict) else []

    lines = []
    lines.append("====================================")
    lines.append("AUDIT REPORT")
    lines.append("====================================")
    lines.append(f"File dossier: {dossier_path}")
    lines.append(f"Dossier type: {dossier.get('dossier_type')}")
    lines.append(f"Generated at: {dossier.get('generated_at_utc')}")
    lines.append(f"Engine version: {dossier.get('engine_version')}")
    lines.append(f"Policy version: {dossier.get('policy_version')}")
    lines.append(f"Previous hash: {dossier.get('previous_hash')}")
    lines.append(f"Dossier hash: {dossier.get('dossier_hash')}")
    lines.append(f"Signature: {dossier.get('signature')}")
    lines.append("")

    if isinstance(summary, dict):
        lines.append("SUMMARY OVERVIEW")
        lines.append(f"Suite name: {summary.get('suite_name')}")
        lines.append(f"Started at: {summary.get('started_at_utc')}")
        lines.append(f"Finished at: {summary.get('finished_at_utc')}")
        lines.append(f"Total tests: {summary.get('total')}")
        lines.append(f"Passed: {summary.get('passed')}")
        lines.append(f"Failed: {summary.get('failed')}")
        lines.append(f"Summary hash: {summary.get('summary_hash')}")
        lines.append("")
    else:
        lines.append("SUMMARY OVERVIEW")
        lines.append("Summary not structured as dict")
        lines.append("")

    lines.append("TEST RESULTS")
    if not results:
        lines.append("No test results found")
    else:
        for idx, test in enumerate(results, start=1):
            name = test.get("test_name", f"test_{idx}")
            passed = test.get("passed")
            checked = test.get("checked_at_utc")
            status = status_of_test(test)
            lines.append(f"{idx}. {name}")
            lines.append(f"   passed: {passed}")
            lines.append(f"   status: {status}")
            lines.append(f"   checked_at: {checked}")

            details = test.get("details", {})
            if isinstance(details, dict):
                result_hash = details.get("result_hash")
                if result_hash:
                    lines.append(f"   result_hash: {result_hash}")

                reason = details.get("reason")
                if reason:
                    lines.append(f"   reason: {reason}")

                original_result = details.get("original_result")
                if isinstance(original_result, dict):
                    orig_status = original_result.get("status")
                    if orig_status:
                        lines.append(f"   original_status: {orig_status}")

            lines.append("")

    lines.append("FINAL ASSESSMENT")
    if isinstance(summary, dict) and summary.get("failed") == 0:
        lines.append("PASS - validation suite completed with zero failed tests")
    else:
        lines.append("ATTENTION - review failed tests or missing summary structure")

    return "\n".join(lines)


def main():
    dossier_path = load_latest_dossier()

    with open(dossier_path, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    report_text = build_report(dossier, dossier_path)

    report_path = dossier_path.with_name(
        dossier_path.name.replace("dossier_", "audit_report_").replace(".json", ".txt")
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n====================================")
    print("AUDIT REPORT GENERATED")
    print("====================================")
    print(f"Source dossier: {dossier_path}")
    print(f"Report saved to: {report_path}")
    print("")
    print(report_text)


if __name__ == "__main__":
    main()
