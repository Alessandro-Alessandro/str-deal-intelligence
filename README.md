STR Deal Intelligence Crew

Given a single property address, this crew produces two different reports for two different audiences from the same underlying research:

Internal underwriting brief — for an STR operator deciding whether to pursue the deal. Includes a PURSUE / MANUAL REVIEW / PASS verdict driven by two gating metrics — Net Annual Profit and Cash-on-Cash Return — plus regulatory risk, a financial sensitivity table, and how the deal compares against the firm's own investment criteria and past-deal track record.
Owner outreach pitch — a warm, benefits-forward report suitable for sending directly to the property's owner. Its selling-point framing adapts to the numbers: leads with the income comparison when the STR-vs-rent margin is strong, leads with stability and hands-off management when it isn't. Contains none of the internal decision criteria, margins, or thresholds from report #1.

Same research, two audiences, two very different documents — and the separation between them is enforced architecturally, not just by prompt instruction (see Design decisions below).

Quick start
bash
git clone <this-repo>
cd str_deal_intelligence
pip install -e .
cp .env.example .env
# fill in .env -- see "API keys" below
python -m str_deal_intelligence.main

Runs against a default demo address (a real, currently-listed property — see note below). To run against a different property:

bash
python -m str_deal_intelligence.main --address "123 Main St, City, ST 00000" --owner "Jane Smith" --furnished
--owner is optional. If provided, the owner pitch addresses them by name; if not, it addresses the property generally. This field is only ever a manually-provided input — the crew never looks up or discovers property ownership on its own. See Design decisions.
--furnished — set this flag if the property already comes furnished; changes which furnishing-cost assumption the financial model uses (a light touch-up cost vs. a full buildout).
--bedrooms / --bathrooms — optional manual overrides if RentCast's public-record data is known to be stale for a specific property (e.g. a recent renovation or permit not yet reflected).

Output lands in sample_output/:

investor_underwriting_brief.md
owner_pitch_report.md
Don't want to sign up for four API keys just to see this run?

Two zero-setup options:

sample_output/ already contains real generated reports from an actual run — no setup required to see the output quality.
This crew is deployed live on CrewAI AMP. Trigger a real execution with no local setup at all: https://str-deal-intelligence-a79dc120-57ad-4e2c-ab-ffd6f2ad.crewai.com. Full execution traces — per-agent, per-tool-call, with token counts and timing — are visible on the AMP dashboard for any run.
API keys
Service	Used for	Self-serve?	Notes
Anthropic	LLM for all agents	Yes	claude-haiku-4-5 by default — cost-effective, more than sufficient for this task's reasoning demands. Swap the llm: field in config/agents.yaml for any other provider.
RentCast	Property details + long-term rent estimate	Yes, free tier (50 calls/month)	No credit card required for signup.
AirROI	STR ADR / occupancy / revenue estimate	Yes, pay-as-you-go	$10 minimum credit deposit, ~$0.01–$1.00 per call. Instant key, no sales process.
Serper	Web search for STR regulatory research	Yes, free tier	Used by the Regulatory Analyst.

All four are genuinely self-serve — no sales calls, no contracts, nothing that would have blocked a 3-day build. See Design decisions for why two well-known alternatives (AirDNA, direct Zillow access) aren't used here.

Architecture
                              address (input)
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼ async                          async ▼
        ┌──────────────────┐                ┌──────────────────┐
        │ Property Intake  │                │ Regulatory       │
        │ Specialist       │                │ Analyst          │
        │ (RentCast)       │                │ (web search)     │
        └────────┬─────────┘                └────────┬─────────┘
                 │                                    │
                 ▼                                    │
        ┌──────────────────┐                          │
        │ Market           │                          │
        │ Underwriting     │                          │
        │ Analyst (AirROI) │                          │
        └────────┬─────────┘                          │
                 │                                     │
                 ▼                                     │
        ┌──────────────────┐                          │
        │ Financial        │                          │
        │ Analyst          │                          │
        │ (net profit, CoC)│                          │
        └────────┬─────────┘                          │
                 │                                     │
                 └─────────────────┬───────────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │ Internal Fit Analyst │
                        │ (vs. firm criteria)  │
                        └──────────┬───────────┘
                                   │
            ┌──────────────────────────┴──────────────────────────┐
            ▼ async                                            async ▼
   ┌──────────────────────┐                        ┌──────────────────────┐
   │ Investor Report      │                        │ Owner Pitch          │
   │ Writer               │                        │ Writer               │
   │ (sees all 5 upstream)│                        │ (property + market   │
   │  → underwriting brief│                        │   data only)         │
   └──────────┬───────────┘                        │  → owner pitch       │
              │                                     └──────────┬───────────┘
              └─────────────────────┬───────────────────────┘
                                    ▼
                       ┌──────────────────────────┐
                       │ Deal Packet Confirmation │
                       │ (verdict + manifest)     │
                       └──────────────────────────┘

8 specialist tasks across 7 agents (the final confirmation task reuses the Investor Report Writer). Two pairs run genuinely in parallel — Property Intake + Regulatory at the start, Investor Report + Owner Pitch at the end — verified with real overlapping start_time/end_time timestamps, not just assumed from log ordering. The final confirmation task exists partly to close a real architectural constraint: CrewAI's sequential process validator rejects a crew that ends on two consecutive async tasks, since nothing downstream can act as the synchronization point. A minimal, genuinely useful closing task (verdict + manifest confirmation) satisfies that requirement instead of an arbitrary no-op.

Design decisions

Why RentCast instead of Zillow. Zillow's terms of service prohibit automated data extraction, and scraping it — directly or through a third-party scraper — puts the tool in a real gray area for something meant to demonstrate enterprise judgment. RentCast is purpose-built for exactly this use case, has genuine self-serve access with a real free tier, and returns structured data rather than fragile scraped HTML.

Why AirROI instead of AirDNA. AirDNA's API is enterprise-only — no self-serve signup, a private token issued only after a sales conversation and contract. AirROI offers the same category of data through a genuinely self-serve, pay-as-you-go API. In a real production deployment for an enterprise customer, AirDNA's broader dataset would likely justify going through that sales process — a build-speed trade-off specific to a 3-day prototype, not a claim that AirROI is strictly better.

Why owner identity is a manual input, never auto-discovered. An earlier version of this idea considered using a property-records API to automatically look up a property owner's name for outreach. I deliberately didn't build that. Automated skip-tracing to enable unsolicited outreach raises real questions — solicitation rules vary by state, and "publicly available in a deed record" is a different bar than "appropriate to automatically pull into a cold-outreach pipeline." The owner's name is an optional field the operator provides if they already have it through normal business channels.

Why the financial model treats rent as a real cost, not just a comparison baseline. An earlier version of the model divided net STR revenue by long-term rent as a coverage multiple, without ever actually subtracting rent as an expense. That's correct for a landlord comparing two income options, but wrong for an arbitrage operator who pays that rent as a real monthly cost regardless of outcome. The corrected model subtracts rent alongside management fees, platform fees, cleaning, utilities, insurance, and furnishing amortization, and gates the verdict on two metrics together: Net Annual Profit (the real dollar return) and Cash-on-Cash Return (profit relative to actual cash deployed — furnishing cost, first month's rent, security deposit). Both must clear their threshold for PURSUE; one clearing means MANUAL REVIEW; neither clearing means PASS.

Why the Owner Pitch Writer is architecturally blind to internal data, not just prompted to withhold it. In crew.py, owner_pitch_task's context list contains only property_intake_task and market_underwriting_task — it never receives the financial model or the internal fit assessment as context at all. The agent structurally cannot see this data, regardless of what its prompt says. A separate output guardrail (owner_pitch_guardrail.py) is a second, independent check scanning for internal terminology. Two independent layers, on purpose.

Why the owner pitch's selling points change based on the numbers. Rather than a fixed template, the report leads with the income comparison only when the STR-vs-rent margin is strong (>30%); otherwise it leads with deal stability — a multi-year agreement means no vacancy gaps and zero property-management responsibility for the owner, since Huddleston Reef is the tenant, not a co-host. A system that oversells a mediocre deal the same way it undersells a great one isn't actually reasoning about the deal.

Why a code guardrail on both final reports. The investor brief's guardrail checks that all required sections are present and the verdict is exactly one of PURSUE / MANUAL REVIEW / PASS. Both guardrails were unit-tested directly against known-good and known-bad sample text before ever being run against a live LLM output.

Why claude-haiku-4-5 for every agent, rather than a tiered model strategy. For a task of this size, a single cost-effective model is sufficient across all agents. In a larger production deployment, I'd tier models per agent — a cheaper model for structured extraction, a stronger model for the Financial Analyst's multi-step reasoning — the same way CrewAI's own reliability guidance recommends.

Why current_date uses a @before_kickoff hook instead of a CLI argument. Early on, the date was computed in main.py and passed into kickoff() inputs — which worked locally, but silently broke when the crew was triggered directly through CrewAI AMP, since AMP calls the crew directly and never executes main.py. Moving the logic into a @before_kickoff hook on the crew itself means it runs identically regardless of what triggers the crew — one source of truth instead of two.

What I'd change for production. Bounded retries with backoff around every external API call, beyond the single-attempt try/except each tool has now; a held-out set of past deals with known outcomes to evaluate the Financial Analyst's projections against reality over time; the AirDNA sales conversation, once this needed to scale past prototype volume; and structured (output_pydantic) enforcement on the Financial Analyst's numeric scenario table specifically, where a rigid schema fits better than it would on the long-form written reports.

Beyond this prototype: the production pipeline

Today this crew evaluates one address at a time, on request. The natural next stage: batch-scan active long-term rental listings in a target market via RentCast's active-listings endpoint, run this exact crew across each candidate address, rank results by Net Annual Profit and Cash-on-Cash Return to surface top prospects, then auto-draft — never auto-send — the owner outreach email for each qualifying property into a mailbox drafts folder for human review. Keeping a human in the loop before any outreach actually sends is a deliberate choice, consistent with how owner identity is already handled as a manual, human-provided input rather than automated discovery.

Deployment

Deployed live on CrewAI AMP: https://str-deal-intelligence-a79dc120-57ad-4e2c-ab-ffd6f2ad.crewai.com. Real execution traces — per-agent and per-tool-call, with token counts and timing — are visible on the AMP dashboard for any run, local or remote.

Sample output

A generated sample of both reports is included in sample_output/ — generate your own by running the crew with your own API keys, or trigger a run on the deployed AMP instance above with no setup at all.

A note on the demo address

The default address is 7831 Hope St, Hollywood FL — a real, currently-listed rental property. Using its public listing data (address, asking rent, bedroom count) for investment analysis is standard practice for any real estate investor or analyst; nothing about this involves private or non-public information about the property or its owner.
