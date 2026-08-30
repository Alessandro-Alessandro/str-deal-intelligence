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

DEFAULT_ADDRESS = "1448 Dewey St, Hollywood, FL 33020"
DEFAULT_OWNER_NAME = ""  # left blank -> owner report addresses the property generally


def run():
    parser = argparse.ArgumentParser(description="STR Deal Intelligence Crew")
    parser.add_argument("--address", default=DEFAULT_ADDRESS, help="Property address to evaluate")
    parser.add_argument(
        "--owner",
        default=DEFAULT_OWNER_NAME,
        help="Owner's name, if known -- optional, never auto-discovered by the crew",
    )
    args = parser.parse_args()

    inputs = {
        "address": args.address,
        "owner_name": args.owner,
        "current_date": date.today().strftime("%B %-d, %Y"),
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
