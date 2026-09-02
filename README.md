STR Deal Intelligence Crew

Given a single property address, this CrewAI crew produces two reports for two audiences from one run of research:

Investor underwriting brief — an internal go/no-go analysis with a PURSUE / MANUAL REVIEW / PASS verdict gated on two metrics (Net Annual Profit and Cash-on-Cash Return), plus regulatory risk, a financial sensitivity table, and fit against the firm's investment criteria.
Owner outreach pitch — a warm, owner-facing letter that references the property's own listing. It contains none of the verdict, thresholds, or margins from the brief.

The separation between them is enforced architecturally — the owner-pitch writer never receives the internal data as context — not by a prompt asking it to stay quiet. See Design decisions.

Quick start
bash
git clone <this-repo>
cd str_deal_intelligence
pip install -e .
cp .env.example .env        # fill in keys — see API keys below
python -m str_deal_intelligence.main

Runs against a default demo address. To run your own:

bash
python -m str_deal_intelligence.main --address "123 Main St, City, ST 00000" --owner "Jane Smith" --furnished
--owner (optional) — if given, the pitch addresses them by name. Owner identity is only ever a manual input; the crew never looks it up on its own.
--furnished — switches the furnishing-cost assumption (light touch-up vs. full buildout).
--bedrooms / --bathrooms — manual overrides when RentCast's public-record data is stale.

Both reports are written to sample_output/.

Want to see it run without setting up keys? The repo already contains real generated reports in sample_output/, and the crew is deployed live on CrewAI AMP (see Deployment) with full execution traces.

Architecture
                              address (input)
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼ async                          async ▼
        ┌──────────────────┐                ┌──────────────────┐
        │ Property Intake  │                │ Regulatory       │
        │ (RentCast)       │                │ Analyst (Serper) │
        └────────┬─────────┘                └────────┬─────────┘
                 │                                    │
                 ▼                                    │
        ┌──────────────────┐                          │
        │ Market           │                          │
        │ Underwriting     │                          │
        │ (AirROI)         │                          │
        └────────┬─────────┘                          │
                 │                                     │
                 ▼                                     │
        ┌──────────────────┐                           │
        │ Financial        │                           │
        │ Analyst          │                           │
        │ (sandboxed math) │                           │
        └────────┬─────────┘                           │
                 │                                      │
                 └──────────────┬───────────────────────┘
                                ▼
                       ┌──────────────────┐
                       │ Internal Fit     │
                       │ Analyst          │
                       └────────┬─────────┘
                                │
       ┌────────────────────────┴────────────────────────┐
       │ sees all 5 upstream                              │ sees property + market ONLY
       ▼ async                                      async ▼
┌──────────────────┐                              ┌──────────────────┐
│ Investor Report  │                              │ Owner Pitch      │
│ Writer           │                              │ Writer           │
└────────┬─────────┘                              └────────┬─────────┘
         └──────────────────────┬────────────────────────┘
                                ▼
                       ┌──────────────────┐
                       │ Deal Packet      │
                       │ Confirmation     │
                       └──────────────────┘

7 agents, 8 tasks, sequential process. Two pairs run genuinely in parallel — Property Intake + Regulatory at the start, and the two writers at the end — confirmed by overlapping start/end timestamps, not assumed from log order. The closing Deal Packet task also satisfies a real CrewAI constraint: the sequential-process validator rejects a crew that ends on two consecutive async tasks, so this task acts as the synchronization point rather than being a no-op.

Note the two data paths into the writers: the Investor Report Writer receives all five upstream tasks; the Owner Pitch Writer receives only Property Intake and Market Underwriting. The financial model and internal-fit scoring are never in its context.

API keys
Service	Used for	Self-serve?
Anthropic	LLM for all agents (claude-haiku-4-5 by default)	Yes
RentCast	Property details + long-term rent	Yes — free tier, no card
AirROI	STR ADR / occupancy / revenue	Yes — pay-as-you-go, instant key
Serper	Web search for regulatory research	Yes — free tier

All four are genuinely self-serve — no sales calls or contracts. Swap the llm: field in config/agents.yaml to use a different model provider.

Design decisions

The Owner Pitch Writer is architecturally blind to internal data. In crew.py, owner_pitch_task's context list contains only property_intake_task and market_underwriting_task — it never receives the financial model or internal-fit assessment at all. This is least-privilege context per agent: the writer can't leak what it was never given. A separate output guardrail (owner_pitch_guardrail.py) scans for internal terminology as a second, independent layer.

The financial model treats rent as a real cost. For a rental-arbitrage operator, long-term rent is a monthly expense paid regardless of outcome — so it's subtracted alongside management fees, platform fees, cleaning, utilities, insurance, and furnishing amortization. The verdict gates on two metrics together: Net Annual Profit (real dollar return) and Cash-on-Cash Return (return on cash actually deployed). Both clear → PURSUE; one clears → MANUAL REVIEW; neither → PASS.

RentCast over Zillow. Zillow's terms prohibit automated extraction; scraping it is a gray area for a tool meant to show enterprise judgment. RentCast is purpose-built, self-serve, and returns structured data instead of fragile HTML.

AirROI over AirDNA. AirDNA is enterprise-only — a private token issued after a sales process. AirROI offers the same category of data self-serve and pay-as-you-go. In a real production deployment, AirDNA's broader dataset would likely justify that sales process; this is a build-speed trade-off, not a claim that AirROI is strictly better.

Owner identity is a manual input, never auto-discovered. Automated skip-tracing for unsolicited outreach raises real compliance questions that vary by state. The owner's name is an optional field the operator supplies through normal business channels.

Deployment

Deployed live on CrewAI AMP. Real execution traces — per-agent and per-tool-call, with token counts, timing, and cost — are visible on the AMP dashboard for any run.

REST API
bash
# discover required inputs
curl -H "Authorization: Bearer $CREW_TOKEN" $CREW_URL/inputs

# kick off a run
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CREW_TOKEN" \
  -d '{"inputs": {"address": "7831 Hope St, Hollywood, FL 33024", "owner_name": ""}}' \
  $CREW_URL/kickoff

# poll for status + result
curl -H "Authorization: Bearer $CREW_TOKEN" $CREW_URL/status/<kickoff_id>
Production notes

Beyond this prototype, the natural next stage is to batch-scan a market's active long-term listings via RentCast, run this exact crew on each candidate, rank by Net Annual Profit and Cash-on-Cash Return, and auto-draft (never auto-send) owner outreach into a review folder for human sign-off — keeping a human in the loop before anything sends.

Other production hardening: bounded retries with backoff on every external call; a held-out set of past deals to evaluate the Financial Analyst's projections against real outcomes; per-agent model tiering (a cheaper model for extraction, a stronger one for the financial reasoning); and structured (output_pydantic) enforcement on the numeric scenario table specifically.

A note on the demo address

The default address is a real, currently-listed rental property. Using public listing data (address, asking rent, bedroom count) for investment analysis is standard practice; nothing here involves private or non-public information about the property or its owner.
