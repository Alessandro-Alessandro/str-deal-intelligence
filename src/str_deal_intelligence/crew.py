"""
STR Deal Intelligence Crew.

Architecture, in order of execution:

  Stage 1 (parallel -- both only need the raw address):
    - property_intake_task    (RentCast: property facts + long-term rent)
    - regulatory_task         (web search: STR regulatory risk flag)     [async]

  Stage 2 (needs property_intake's bedroom count):
    - market_underwriting_task (AirROI: ADR / occupancy / gross revenue)

  Stage 3 (needs property_intake + market_underwriting):
    - financial_task           (net revenue, STR Uplift Ratio, breakeven)

  Stage 4 (needs financial + regulatory):
    - internal_fit_task        (checks against Huddleston Reef's real criteria)

  Stage 5 (parallel -- two different audiences, two different data diets):
    - investor_report_task     (sees everything)                        
    - owner_pitch_task         (sees ONLY property + market data)        [async]

The investor/owner split at Stage 5 is a deliberate control boundary, not
just a prompt instruction: owner_pitch_task's context list does not
include internal_fit_task, so the agent never receives Huddleston Reef's
proprietary thresholds or margin data in the first place. The output
guardrail (owner_pitch_guardrail.py) is a second, independent check on
top of that -- defense in depth, not a single point of failure.
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

from str_deal_intelligence.tools.rentcast_property_tool import RentCastPropertyTool
from str_deal_intelligence.tools.airroi_revenue_tool import AirROIRevenueTool
from str_deal_intelligence.tools.internal_data_tool import InternalDataTool
from str_deal_intelligence.guardrails.investor_report_guardrail import (
    validate_investor_report,
)
from str_deal_intelligence.guardrails.owner_pitch_guardrail import (
    validate_owner_pitch,
)


@CrewBase
class StrDealIntelligenceCrew:
    """Dual-report STR deal evaluator: internal underwriting brief + owner pitch."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---------------------------------------------------------------- agents

    @agent
    def property_intake_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["property_intake_specialist"],
            tools=[RentCastPropertyTool()],
            verbose=True,
        )

    @agent
    def regulatory_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["regulatory_analyst"],
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def market_underwriting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["market_underwriting_analyst"],
            tools=[AirROIRevenueTool()],
            verbose=True,
        )

    @agent
    def financial_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["financial_analyst"],
            tools=[InternalDataTool()],
            allow_code_execution=True,
            code_execution_mode="safe",
            verbose=True,
        )

    @agent
    def internal_fit_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["internal_fit_analyst"],
            tools=[InternalDataTool()],
            verbose=True,
        )

    @agent
    def investor_report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["investor_report_writer"],
            verbose=True,
        )

    @agent
    def owner_pitch_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["owner_pitch_writer"],
            verbose=True,
        )

    # ----------------------------------------------------------------- tasks

    @task
    def property_intake_task(self) -> Task:
        return Task(
            config=self.tasks_config["property_intake_task"],
            agent=self.property_intake_specialist(),
        )

    @task
    def regulatory_task(self) -> Task:
        return Task(
            config=self.tasks_config["regulatory_task"],
            agent=self.regulatory_analyst(),
            async_execution=True,
        )

    @task
    def market_underwriting_task(self) -> Task:
        return Task(
            config=self.tasks_config["market_underwriting_task"],
            agent=self.market_underwriting_analyst(),
            context=[self.property_intake_task()],
        )

    @task
    def financial_task(self) -> Task:
        return Task(
            config=self.tasks_config["financial_task"],
            agent=self.financial_analyst(),
            context=[self.property_intake_task(), self.market_underwriting_task()],
        )

    @task
    def internal_fit_task(self) -> Task:
        return Task(
            config=self.tasks_config["internal_fit_task"],
            agent=self.internal_fit_analyst(),
            context=[self.financial_task(), self.regulatory_task()],
        )

    @task
    def investor_report_task(self) -> Task:
        return Task(
            config=self.tasks_config["investor_report_task"],
            agent=self.investor_report_writer(),
            context=[
                self.property_intake_task(),
                self.regulatory_task(),
                self.market_underwriting_task(),
                self.financial_task(),
                self.internal_fit_task(),
            ],
            guardrail=validate_investor_report,
            output_file="sample_output/investor_underwriting_brief.md",
        )

    @task
    def owner_pitch_task(self) -> Task:
        # Deliberately NOT given internal_fit_task in context -- see module
        # docstring. This agent structurally cannot see proprietary
        # thresholds or margin data; it isn't just told not to share them.
        return Task(
            config=self.tasks_config["owner_pitch_task"],
            agent=self.owner_pitch_writer(),
            context=[self.property_intake_task(), self.market_underwriting_task()],
            async_execution=True,
            guardrail=validate_owner_pitch,
            output_file="sample_output/owner_pitch_report.md",
        )

    # ----------------------------------------------------------------- crew

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
