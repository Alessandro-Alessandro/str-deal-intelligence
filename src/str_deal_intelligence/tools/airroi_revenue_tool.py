"""
AirROI short-term-rental revenue calculator tool.

Docs: https://www.airroi.com/api/documentation

Uses the /listings/comparables endpoint, not /calculator -- /calculator
requires an existing Airbnb listing_id, which an off-market property
being underwritten doesn't have. /listings/comparables instead takes an
address plus bedrooms/baths/guests and returns nearby comparable
listings with TTM/L90D revenue, ADR, and occupancy metrics, which is
what this tool needs to estimate.

Requires AIRROI_API_KEY in the environment. AirROI is pay-as-you-go
(credits deposited up front) -- see README for setup notes.
"""

import os
import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

AIRROI_BASE_URL = "https://api.airroi.com"
REQUEST_TIMEOUT_SECONDS = 15


class AirROIRevenueInput(BaseModel):
    address: str = Field(..., description="Full property address to estimate STR performance for.")
    bedrooms: int = Field(
        ...,
        description=(
            "Bedroom count for the property, used to match against comparable "
            "STR listings for an accurate ADR/occupancy estimate. Pull this from "
            "the RentCast property lookup result before calling this tool."
        ),
    )
    bathrooms: float = Field(
        ...,
        description=(
            "Bathroom count for the property (decimals allowed, e.g. 2.5). "
            "Pull this from the RentCast property lookup result before calling "
            "this tool."
        ),
    )
    guests: int | None = Field(
        None,
        description=(
            "Max guest capacity for the property. If unknown, leave unset -- "
            "the tool will estimate it from bedroom count (2 guests per "
            "bedroom, minimum 2)."
        ),
    )


class AirROIRevenueTool(BaseTool):
    name: str = "AirROI STR Revenue Estimator"
    description: str = (
        "Estimates short-term-rental performance for a specific property: "
        "projected average daily rate (ADR), occupancy rate, and annual gross "
        "revenue, based on comparable Airbnb listings in the area. Requires "
        "the property's address, bedroom count, and bathroom count for an "
        "accurate comp match. Use this after RentCast has returned property "
        "details."
    )
    args_schema: type[BaseModel] = AirROIRevenueInput

    def _run(self, address: str, bedrooms: int, bathrooms: float, guests: int | None = None) -> str:
        api_key = os.getenv("AIRROI_API_KEY")
        if not api_key:
            return (
                "ERROR: AIRROI_API_KEY is not set in the environment. "
                "Sign up at airroi.com/api, deposit the $10 minimum credit, "
                "and add the key to .env before running."
            )

        if guests is None:
            guests = max(2, bedrooms * 2)

        headers = {"X-API-KEY": api_key, "Accept": "application/json"}

        try:
            resp = requests.get(
                f"{AIRROI_BASE_URL}/listings/comparables",
                params={
                    "address": address,
                    "bedrooms": bedrooms,
                    "baths": bathrooms,
                    "guests": guests,
                    "room_type": "entire_home",
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()

        except requests.exceptions.Timeout:
            return (
                f"ERROR: AirROI request timed out after {REQUEST_TIMEOUT_SECONDS}s "
                f"for '{address}'. STR revenue estimate unavailable for this run."
            )
        except requests.exceptions.HTTPError as e:
            return (
                f"ERROR: AirROI returned an HTTP error ({e.response.status_code}) "
                f"for '{address}'. Response: {e.response.text[:300]}"
            )
        except requests.exceptions.RequestException as e:
            return f"ERROR: AirROI request failed for '{address}': {str(e)}"

        return f"AirROI STR revenue estimate for {address} ({bedrooms}BR):\n{data}"
