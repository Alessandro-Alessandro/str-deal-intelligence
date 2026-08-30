"""
Reads Huddleston Reef's internal investment data -- criteria, past deal
track record, and operating cost structure. These are static mocked files
in this repo (data/internal/) standing in for what would be a real
internal system (a CRM, a deal database, a finance system) in production.
"""

import json
import os
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "internal"
)

_FILES = {
    "investment_criteria": "investment_criteria.json",
    "track_record": "deal_track_record.json",
    "operating_costs": "operating_costs.json",
}


class InternalDataInput(BaseModel):
    dataset: str = Field(
        ...,
        description=(
            "Which internal dataset to load. One of: "
            "'investment_criteria', 'track_record', 'operating_costs'."
        ),
    )


class InternalDataTool(BaseTool):
    name: str = "Huddleston Reef Internal Data"
    description: str = (
        "Reads Huddleston Reef's internal investment data. Pass one of "
        "'investment_criteria' (uplift thresholds, regulatory risk tolerance, "
        "preferred property profile), 'track_record' (past deals and their "
        "actual outcomes), or 'operating_costs' (recurring and one-time costs "
        "used to compute net revenue after expenses)."
    )
    args_schema: type[BaseModel] = InternalDataInput

    def _run(self, dataset: str) -> str:
        if dataset not in _FILES:
            return (
                f"ERROR: unknown dataset '{dataset}'. "
                f"Valid options: {', '.join(_FILES.keys())}"
            )

        path = os.path.join(_DATA_DIR, _FILES[dataset])
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return f"ERROR: internal data file not found at {path}"
        except json.JSONDecodeError as e:
            return f"ERROR: internal data file at {path} is not valid JSON: {e}"

        return json.dumps(data, indent=2)
