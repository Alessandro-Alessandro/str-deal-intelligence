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

Most terms are matched as raw substrings (deliberate -- e.g. "margin"
should also catch "margins", "underwrit" should also catch
"underwriting"). "pass" is the one exception: matched as a whole word
only, via regex. A raw substring check on "pass" also matched
"passive"/"passively" ("generate passive income" is completely normal
owner-facing language), which exhausted the guardrail's retries and
crashed the whole crew run.

"huddleston reef" is deliberately NOT on this list. The owner pitch now
frames the deal as a landlord/tenant relationship (Huddleston Reef signs
a multi-year lease as the owner's tenant), which requires naming the
firm -- that's just who the owner would be signing with, not proprietary
decision data. The terms below still block the actual internal
underwriting vocabulary (uplift ratio, investment criteria, margins,
underwriting jargon, verdict language, track record).
"""

import re

FORBIDDEN_TERMS = [
    "uplift ratio",
    "investment criteria",
    "internal",
    "margin",
    "underwrit",  # matches "underwriting" / "underwrite"
    "pursue",
    "pass",
    "manual review",
    "track record",
]

_WHOLE_WORD_ONLY = {"pass": re.compile(r"\bpass\b")}


def _term_found(term: str, lowered_text: str) -> bool:
    pattern = _WHOLE_WORD_ONLY.get(term)
    return bool(pattern.search(lowered_text)) if pattern else term in lowered_text


def validate_owner_pitch(output):
    text = output.raw if hasattr(output, "raw") else output
    lowered = text.lower()

    leaked = [term for term in FORBIDDEN_TERMS if _term_found(term, lowered)]
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
