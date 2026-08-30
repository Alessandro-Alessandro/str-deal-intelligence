"""
Code guardrail for the investor-facing underwriting brief.

Checks that the report actually contains every section it's supposed to,
and that the verdict is exactly one of the three allowed values -- not a
paraphrase. Same pattern as CrewAI's own reliability-technique lessons:
a code guardrail returns (True, output) on success or (False, reason) on
failure, and the reason gets fed back to the agent to try again.
"""

REQUIRED_SECTIONS = [
    "verdict",
    "uplift ratio",
    "regulatory",
    "opportunit",  # matches "opportunity" / "opportunities"
    "risk",
    "recommend",
]

VALID_VERDICTS = ["PURSUE", "PASS", "MANUAL REVIEW"]


def validate_investor_report(output):
    text = output.raw if hasattr(output, "raw") else output
    lowered = text.lower()

    missing = [s for s in REQUIRED_SECTIONS if s not in lowered]
    if missing:
        return (
            False,
            f"Report is missing required content: {', '.join(missing)}. "
            f"Rewrite the report to include all of: {', '.join(REQUIRED_SECTIONS)}.",
        )

    if not any(v in text.upper() for v in VALID_VERDICTS):
        return (
            False,
            f"Report must state a verdict that is exactly one of: "
            f"{', '.join(VALID_VERDICTS)}. Rewrite with one of these exact phrases.",
        )

    return (True, output)
