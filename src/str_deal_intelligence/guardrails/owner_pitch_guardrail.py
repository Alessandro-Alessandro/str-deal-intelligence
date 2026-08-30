"""
Code guardrail for the owner-facing pitch report.

This is a data-boundary control, not a formatting check. The Owner Pitch
Writer agent is already wired (in crew.py) to receive only the fields it
needs -- it never gets the Internal Fit Analyst's task output at all. This
guardrail is the second, independent layer: even if the agent somehow
mentions an internal term it picked up from general context, the output
gets rejected and rewritten before it ever reaches a real property owner.

Two layers of defense (context scoping + output guardrail) is deliberate:
either one failing alone shouldn't be enough to leak proprietary data.
"""

FORBIDDEN_TERMS = [
    "uplift ratio",
    "huddleston reef",
    "investment criteria",
    "internal",
    "margin",
    "underwrit",  # matches "underwriting" / "underwrite"
    "pursue",
    "pass",
    "manual review",
    "track record",
]


def validate_owner_pitch(output):
    text = output.raw if hasattr(output, "raw") else output
    lowered = text.lower()

    leaked = [term for term in FORBIDDEN_TERMS if term in lowered]
    if leaked:
        return (
            False,
            f"This report will be sent directly to a property owner and must not "
            f"contain internal terminology or figures. Found: {', '.join(leaked)}. "
            f"Rewrite in plain, owner-facing language -- projected earnings and the "
            f"value of partnering with us, nothing about internal thresholds, margins, "
            f"or decision criteria.",
        )

    return (True, output)
