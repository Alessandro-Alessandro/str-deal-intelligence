"""
RentCast property + long-term rent estimate tool.

Docs: https://developers.rentcast.io/reference/introduction
NOTE: Endpoint paths and response field names below reflect RentCast's
publicly documented API as of this writing. Verify against the live docs
before the first real run -- vendor APIs occasionally rename fields.

Requires RENTCAST_API_KEY in the environment.
"""

import os
import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

RENTCAST_BASE_URL = "https://api.rentcast.io/v1"
REQUEST_TIMEOUT_SECONDS = 15


class RentCastPropertyInput(BaseModel):
    address: str = Field(
        ...,
        description=(
            "Full property address, e.g. '1448 Dewey St, Hollywood, FL 33020'. "
            "Should include street, city, state, and zip for best match accuracy."
        ),
    )


class RentCastPropertyTool(BaseTool):
    name: str = "RentCast Property Lookup"
    description: str = (
        "Looks up a property by address and returns structured details "
        "(bedrooms, bathrooms, square footage, property type) plus a "
        "long-term rent estimate from RentCast's AVM. Use this to get "
        "ground-truth property facts and a traditional-lease rent baseline "
        "before any short-term-rental analysis."
    )
    args_schema: type[BaseModel] = RentCastPropertyInput

    def _run(self, address: str) -> str:
        api_key = os.getenv("RENTCAST_API_KEY")
        if not api_key:
            return (
                "ERROR: RENTCAST_API_KEY is not set in the environment. "
                "Sign up at rentcast.io/api and add the key to .env before running."
            )

        headers = {"X-Api-Key": api_key, "Accept": "application/json"}

        try:
            # Property details
            details_resp = requests.get(
                f"{RENTCAST_BASE_URL}/properties",
                params={"address": address},
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            details_resp.raise_for_status()
            details = details_resp.json()

            # Long-term rent estimate (AVM)
            rent_resp = requests.get(
                f"{RENTCAST_BASE_URL}/avm/rent/long-term",
                params={"address": address},
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            rent_resp.raise_for_status()
            rent_estimate = rent_resp.json()

        except requests.exceptions.Timeout:
            return (
                f"ERROR: RentCast request timed out after {REQUEST_TIMEOUT_SECONDS}s "
                f"for address '{address}'. Property data unavailable for this run."
            )
        except requests.exceptions.HTTPError as e:
            return (
                f"ERROR: RentCast returned an HTTP error ({e.response.status_code}) "
                f"for address '{address}'. Response: {e.response.text[:300]}"
            )
        except requests.exceptions.RequestException as e:
            return f"ERROR: RentCast request failed for '{address}': {str(e)}"

        return (
            f"Property details for {address}:\n"
            f"{details}\n\n"
            f"Long-term rent estimate (AVM):\n"
            f"{rent_estimate}"
        )
