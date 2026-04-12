def build_explanation(result: dict) -> dict:
    issues = result.get("issues", [])
    status = result.get("status", "APPROVED")

    if not issues:
        return {
            "summary": "Validation completed successfully with no triggered issues.",
            "details": [
                "All evaluated rules passed."
            ]
        }

    details = []
    for issue in issues:
        field = issue.get("field")
        actual_value = issue.get("actual_value")
        threshold = issue.get("threshold")
        code = issue.get("code")

        if threshold is not None:
            details.append(
                f"{code}: field '{field}' has value '{actual_value}' against threshold/expected '{threshold}'."
            )
        else:
            details.append(
                f"{code}: field '{field}' triggered a validation issue."
            )

    if status == "CRITICAL":
        summary = "One or more critical validation rules were triggered."
    elif status == "REJECTED":
        summary = "The payload was rejected because one or more blocking conditions were found."
    elif status == "REVIEW":
        summary = "Validation completed with warnings that require review."
    else:
        summary = "Validation completed successfully."

    return {
        "summary": summary,
        "details": details
    }
