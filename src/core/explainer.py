def _format_issue_detail(issue: dict) -> str:
    code = issue.get("code", "unknown_issue")
    field = issue.get("field", "unknown_field")
    actual_value = issue.get("actual_value")
    operator = issue.get("operator")
    threshold = issue.get("threshold")
    violation_value = issue.get("violation_value")

    min_inclusive = issue.get("min_inclusive")
    max_inclusive = issue.get("max_inclusive")
    min_exclusive = issue.get("min_exclusive")
    max_exclusive = issue.get("max_exclusive")

    if operator == "equals":
        return (
            f"{code}: field '{field}' has value '{actual_value}' "
            f"which matches violation value '{violation_value}'."
        )

    if operator in {"gt", "gte", "lt", "lte"} and threshold is not None:
        return (
            f"{code}: field '{field}' has value '{actual_value}' "
            f"against threshold '{threshold}' with operator '{operator}'."
        )

    if operator == "range":
        range_parts = []

        if min_inclusive is not None:
            range_parts.append(f">= {min_inclusive}")
        if min_exclusive is not None:
            range_parts.append(f"> {min_exclusive}")
        if max_inclusive is not None:
            range_parts.append(f"<= {max_inclusive}")
        if max_exclusive is not None:
            range_parts.append(f"< {max_exclusive}")

        range_text = " and ".join(range_parts) if range_parts else "defined range"

        return (
            f"{code}: field '{field}' has value '{actual_value}' "
            f"inside violation range ({range_text})."
        )

    return f"{code}: field '{field}' triggered a validation issue."


def _build_summary(status: str, primary_issue: dict | None) -> str:
    primary_code = primary_issue.get("code") if primary_issue else None

    if status == "CRITICAL":
        if primary_code:
            return f"Critical validation failure detected. Primary issue: {primary_code}."
        return "One or more critical validation rules were triggered."

    if status == "REJECTED":
        if primary_code:
            return f"The payload was rejected due to blocking issue: {primary_code}."
        return "The payload was rejected because one or more blocking conditions were found."

    if status == "REVIEW":
        if primary_code:
            return f"Validation requires review. Primary issue: {primary_code}."
        return "Validation completed with warnings that require review."

    return "Validation completed successfully with no triggered issues."


def build_explanation(result: dict) -> dict:
    issues = result.get("issues", [])
    status = result.get("status", "APPROVED")
    primary_issue = result.get("primary_issue")

    if not issues:
        return {
            "summary": "Validation completed successfully with no triggered issues.",
            "details": [
                "All evaluated rules passed."
            ]
        }

    details = []

    if primary_issue:
        details.append(
            "Primary issue: "
            + _format_issue_detail(primary_issue)
        )

    secondary_issues = []
    primary_code = primary_issue.get("code") if primary_issue else None

    for issue in issues:
        if primary_code and issue.get("code") == primary_code:
            continue
        secondary_issues.append(issue)

    for issue in secondary_issues:
        details.append(_format_issue_detail(issue))

    return {
        "summary": _build_summary(status, primary_issue),
        "details": details
    }
