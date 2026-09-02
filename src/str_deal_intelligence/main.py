#!/usr/bin/env python
"""
Entry point for the STR Deal Intelligence Crew.

Usage:
    python -m str_deal_intelligence.main
    python -m str_deal_intelligence.main --address "123 Main St, City, ST 00000" --owner "Jane Smith"

With no arguments, runs against a real, currently-listed property used
throughout development and testing (see README for why this address).
"""

import argparse
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from str_deal_intelligence.crew import StrDealIntelligenceCrew

DEFAULT_ADDRESS = "7831 Hope St, Hollywood, FL 33024"
DEFAULT_OWNER_NAME = ""  # left blank -> owner report addresses the property generally


def run():
    parser = argparse.ArgumentParser(description="STR Deal Intelligence Crew")
    parser.add_argument("--address", default=DEFAULT_ADDRESS, help="Property address to evaluate")
    parser.add_argument(
        "--owner",
        default=DEFAULT_OWNER_NAME,
        help="Owner's name, if known -- optional, never auto-discovered by the crew",
    )
    parser.add_argument(
        "--bedrooms",
        type=int,
        default=None,
        help=(
            "Manual bedroom-count override, used instead of RentCast's value. "
            "Public/assessor records can lag a renovation or permit -- use this "
            "when you know the true count."
        ),
    )
    parser.add_argument(
        "--bathrooms",
        type=float,
        default=None,
        help="Manual bathroom-count override, used instead of RentCast's value.",
    )
    parser.add_argument(
        "--furnished",
        action="store_true",
        default=False,
        help=(
            "Property is already furnished -- use the lighter touch-up setup "
            "cost instead of a full furnishing buildout in the financial model."
        ),
    )
    args = parser.parse_args()

    inputs = {
        "address": args.address,
        "owner_name": args.owner,
        "current_date": date.today().strftime("%B %-d, %Y"),
        "bedroom_override": str(args.bedrooms) if args.bedrooms is not None else "none provided",
        "bathroom_override": str(args.bathrooms) if args.bathrooms is not None else "none provided",
        "already_furnished": str(args.furnished),
    }

    print(f"\nRunning STR Deal Intelligence Crew for: {args.address}\n")
    result = StrDealIntelligenceCrew().crew().kickoff(inputs=inputs)

    print("\n--- DONE ---")
    print("Investor brief:  sample_output/investor_underwriting_brief.md")
    print("Owner pitch:     sample_output/owner_pitch_report.md")
    return result


def plot():
    StrDealIntelligenceCrew().crew().plot()


if __name__ == "__main__":
    run()
