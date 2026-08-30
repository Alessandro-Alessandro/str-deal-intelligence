# STR Deal Intelligence Crew

Given a single property address, this crew produces **two different reports for two different audiences** from the same underlying research:

1. **Internal underwriting brief** — for an STR operator deciding whether to pursue the deal. Includes a PURSUE / PASS / MANUAL REVIEW verdict, the STR Uplift Ratio, regulatory risk, and how the deal compares against the firm's own investment criteria and past-deal track record.
2. **Owner outreach pitch** — a warm, benefits-forward report suitable for sending directly to the property's owner, focused entirely on their earning potential and the value of partnering with an operator. Contains none of the internal decision criteria, margins, or thresholds from report #1.

Same research, two audiences, two very different documents — and the separation between them is enforced architecturally, not just by prompt instruction (see **Design decisions** below).

## Quick start

```bash
git clone <this-repo>
cd str_deal_intelligence
pip install -e .
cp .env.example .env
# fill in .env -- see "API keys" below
python -m str_deal_intelligence.main
```

Runs against a default demo address (a real, currently-listed property — see note below). To run against a different property:

```bash
python -m str_deal_intelligence.main --address "123 Main St, City, ST 00000" --owner "Jane Smith"
```

`--owner` is optional. If provided, the owner pitch addresses them by name; if not, it addresses the property generally. **This field is only ever a manually-provided input — the crew never looks up or discovers property ownership on its own.** See Design decisions.

Output lands in `sample_output/`:
- `investor_underwriting_brief.md`
- `owner_pitch_report.md`

## API keys

| Service | Used for | Self-serve? | Notes |
|---|---|---|---|
| OpenAI | LLM for all agents | Yes | `gpt-4o-mini` by default — cost-effective, multimodal-capable, more than sufficient for this task's reasoning demands. Swap the `llm:` field in `config/agents.yaml` for any other provider. |
| [RentCast](https://www.rentcast.io/api) | Property details + long-term rent estimate | Yes, free tier (50 calls/month) | No credit card required for signup. |
| [AirROI](https://www.airroi.com/api) | STR ADR / occupancy / revenue estimate | Yes, pay-as-you-go | $10 minimum credit deposit, ~$0.01–$1.00 per call. Instant key, no sales process. |
| [Serper](https://serper.dev) | Web search for STR regulatory research | Yes, free tier | Used by the Regulatory Analyst. |

All four are genuinely self-serve — no sales calls, no contracts, nothing that would have blocked a 3-day build. See Design decisions for why two well-known alternatives (AirDNA, direct Zillow access) aren't used here.

## Architecture

```
                    ┌─────────────────────┐
                    │   address (input)    │
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼ (async, parallel)                ▼ (async, parallel)
    ┌───────────────────────┐          ┌─────────────────────┐
    │ Property Intake        │          │ Regulatory Analyst   │
    │ Specialist (RentCast)  │          │ (web search)          │
    └───────────┬─────────────┘          └──────────┬───────────┘
                │                                    │
                ▼                                    │
    ┌───────────────────────┐                        │
    │ Market Underwriting     │                        │
    │ Analyst (AirROI)        │                        │
    └───────────┬─────────────┘                        │
                │                                    │
                ▼                                    │
    ┌───────────────────────┐                        │
    │ Financial Analyst        │                        │
    │ (uplift ratio, net rev)  │                        │
    └───────────┬─────────────┘                        │
                └──────────────────┬─────────────────┘
                                   ▼
                       ┌───────────────────────┐
                       │ Internal Fit Analyst     │
                       │ (vs. Huddleston criteria)│
                       └───────────┬─────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼ (sees everything)                        ▼ (async, sees only
    ┌───────────────────────┐                  property + market data)
    │ Investor Report Writer  │          ┌─────────────────────────┐
    │  → underwriting brief   │          │ Owner Pitch Writer         │
    └───────────────────────┘          │  → owner outreach report   │
                                        └─────────────────────────┘
```

7 specialist agents, each with a single narrow job. Two agents run in parallel at the start (neither depends on the other), and the two final writer agents run in parallel at the end.

## Design decisions

**Why RentCast instead of Zillow.** Zillow's terms of service prohibit automated data extraction, and scraping it — directly or through a third-party scraper — puts the tool in a real gray area for something meant to demonstrate enterprise judgment. RentCast is purpose-built for exactly this use case, has genuine self-serve access with a real free tier, and returns structured data rather than fragile scraped HTML that breaks whenever a page layout changes.

**Why AirROI instead of AirDNA.** AirDNA is the more recognized name in STR data, and I looked at it first. Its API, however, is enterprise-only — no self-serve signup, no public pricing, a private token issued only after a sales conversation and a contract. That's incompatible with a self-serve prototype. AirROI offers the same category of data (comparable-based ADR, occupancy, revenue projections) through a genuinely self-serve, pay-as-you-go API. **In a real production deployment for an enterprise customer, AirDNA's broader dataset and industry standing would likely justify going through that sales process** — this is a build-speed trade-off specific to a 3-day prototype, not a claim that AirROI is strictly better.

**Why owner identity is a manual input, never auto-discovered.** An earlier version of this idea considered using a property-records API (e.g., ATTOM) to automatically look up a property owner's name for the outreach report. I deliberately didn't build that. Automated skip-tracing to enable unsolicited outreach raises real questions — solicitation rules vary meaningfully by state, and "publicly available in a deed record" is a different bar than "appropriate to automatically pull into a cold-outreach pipeline." For this prototype, the owner's name is an optional field the operator provides if they already have it through normal business channels. A production version of this tool would need a real compliance review of outreach rules in each target jurisdiction before automating identity discovery — not something to bolt on without that review.

**Why the Owner Pitch Writer is architecturally blind to internal data, not just prompted to withhold it.** Look at `crew.py`: `owner_pitch_task`'s `context` list contains only `property_intake_task` and `market_underwriting_task`. It never receives `financial_task` (which contains the STR Uplift Ratio and cost breakdown) or `internal_fit_task` (which contains Huddleston Reef's actual investment thresholds) as context at all — the agent structurally cannot see this data, regardless of what its prompt says. A separate output guardrail (`owner_pitch_guardrail.py`) is a second, independent check that scans for internal terminology even if it somehow entered the agent's reasoning through another path. Two independent layers, on purpose — neither one failing alone is enough to leak proprietary data into a report sent to a stranger.

**Why a code guardrail on both final reports.** The investor brief's guardrail checks that all required sections are present and that the verdict is exactly one of PURSUE / PASS / MANUAL REVIEW — not a paraphrase a downstream system would fail to parse. Both guardrails were tested directly against known-good and known-bad sample text before ever being run against a live LLM output (see the test commands in the appendix below).

**Why `gpt-4o-mini` for every agent, rather than a tiered model strategy.** For a task of this size and reasoning depth, a single cost-effective, multimodal-capable model is sufficient across all seven agents — the assignment's own guidance notes model choice matters less than system design here. In a larger production deployment, I'd expect to tier models per agent (a cheaper model for the Property Intake Specialist's structured extraction, a stronger model for the Financial Analyst's multi-step reasoning), the same way CrewAI's own reliability guidance recommends.

**What I'd change for production.** Real error handling around every external API call (RentCast, AirROI, Serper) beyond the try/except already in each tool — specifically bounded retries with backoff rather than a single attempt; a held-out set of past deals with known outcomes to actually evaluate the Financial Analyst's projections against reality over time, the same discipline the internal track record data is meant to eventually support; and the AirDNA sales conversation, once this needed to scale past prototype volume.

## Sample output

A generated sample of both reports is included in `sample_output/` — generate your own by running the crew with your own API keys; the files there reflect a real run against the default demo address.

## A note on the demo address

The default address (1448 Dewey St, Hollywood, FL) is a real, currently-listed rental property. Using its public listing data — address, asking rent, bedroom count — for investment analysis is standard practice for any real estate investor or analyst; nothing about this involves private or non-public information about the property or its owner.
