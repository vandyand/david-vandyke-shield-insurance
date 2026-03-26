"""creative_jury.py — Pre-screen ad creatives through target-audience personas.

Usage:
    python3 scripts/creative_jury.py score \
        --headline "..." --body "..." --image-desc "..." --niche landscaper [--save]
    python3 scripts/creative_jury.py score-file specs/my_ad.json [--save]

Niche options: general, landscaper, contractor, restaurant, home_business
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Schemaon framework
# ---------------------------------------------------------------------------
sys.path.insert(0, "/home/kingjames/agents")
from biomimicry.schemaon import Schemaon
from biomimicry.llm_backend import OpenAINativeJSONClient, LLMConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JURY_RESULTS_DIR = PROJECT_ROOT / "resources" / "jury-results"

VALID_NICHES = {"general", "landscaper", "contractor", "restaurant", "home_business"}

# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

PERSONAS: dict[str, dict[str, str]] = {
    "landscaper_owner": {
        "display_name": "Mike",
        "niche": "landscaper",
        "description": (
            "You are Mike, a 42-year-old owner of a 4-person landscaping crew in "
            "Grand Rapids, Michigan. You're skeptical of ads, always busy, and only "
            "click things that feel directly relevant to your work."
        ),
    },
    "landscaper_employee": {
        "display_name": "Jake",
        "niche": "landscaper",
        "description": (
            "You are Jake, a 28-year-old landscaper working for a small company in "
            "Michigan. You see this ad on your phone during a lunch break."
        ),
    },
    "contractor_owner": {
        "display_name": "Tom",
        "niche": "contractor",
        "description": (
            "You are Tom, a self-employed electrician in Michigan, 45 years old, "
            "running jobs solo. You've been burned by bad insurance before."
        ),
    },
    "contractor_employee": {
        "display_name": "Carlos",
        "niche": "contractor",
        "description": (
            "You are Carlos, a 32-year-old HVAC technician in Michigan. Your boss "
            "just told the crew to look into their own liability coverage."
        ),
    },
    "restaurant_owner": {
        "display_name": "Linda",
        "niche": "restaurant",
        "description": (
            "You are Linda, 50, owner of a family restaurant in Kalamazoo, Michigan "
            "for 15 years. Tight margins, skeptical of any new expense."
        ),
    },
    "restaurant_manager": {
        "display_name": "Derek",
        "niche": "restaurant",
        "description": (
            "You are Derek, 35, manager of a mid-size bar and grill in Michigan. "
            "You handle the insurance renewals."
        ),
    },
    "home_business_owner": {
        "display_name": "Sarah",
        "niche": "home_business",
        "description": (
            "You are Sarah, 38, running a home-based bookkeeping business in Michigan "
            "while raising two kids. Cost-conscious."
        ),
    },
    "general_homeowner": {
        "display_name": "Bob",
        "niche": "general",
        "description": (
            "You are Bob, 48, a Michigan homeowner who's been with the same insurer "
            "for 10 years and just got a renewal notice with a big price increase."
        ),
    },
    "general_business": {
        "display_name": "Priya",
        "niche": "general",
        "description": (
            "You are Priya, 40, owner of a small retail shop in Michigan, looking "
            "for better business insurance."
        ),
    },
}

# Map each niche to its 2 niche-specific persona keys
NICHE_PERSONA_MAP: dict[str, list[str]] = {
    "landscaper": ["landscaper_owner", "landscaper_employee"],
    "contractor": ["contractor_owner", "contractor_employee"],
    "restaurant": ["restaurant_owner", "restaurant_manager"],
    "home_business": ["home_business_owner"],  # only 1 niche-specific
    "general": [],  # no niche-specific; use 2 general below
}

# General personas always appended
GENERAL_PERSONAS = ["general_homeowner", "general_business"]


def get_jury_personas(niche: str) -> list[str]:
    """Return ordered list of persona keys for a given niche (niche + general)."""
    niche_specific = NICHE_PERSONA_MAP.get(niche, [])
    combined = niche_specific + GENERAL_PERSONAS
    # Deduplicate while preserving order (in case niche IS general)
    seen: set[str] = set()
    result: list[str] = []
    for p in combined:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Schemaon definition
# ---------------------------------------------------------------------------

JURY_INPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "body_copy": {"type": "string"},
        "image_description": {"type": "string"},
        "niche": {"type": "string"},
        "persona_name": {"type": "string"},
        "persona_description": {"type": "string"},
    },
    "required": [
        "headline",
        "body_copy",
        "image_description",
        "niche",
        "persona_name",
        "persona_description",
    ],
    "additionalProperties": False,
}

JURY_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Score from 1 to 10",
        },
        "would_click": {"type": "boolean"},
        "first_impression": {
            "type": "string",
            "description": "One sentence first impression",
        },
        "resonance": {
            "type": "string",
            "description": "What specifically speaks to you, or 'nothing'",
        },
        "concerns": {
            "type": "string",
            "description": "What's unclear or off-putting",
        },
        "suggestions": {
            "type": "string",
            "description": "One improvement suggestion",
        },
    },
    "required": [
        "score",
        "would_click",
        "first_impression",
        "resonance",
        "concerns",
        "suggestions",
    ],
    "additionalProperties": False,
}

JURY_SYSTEM_PROMPT = (
    "You are playing the role described in persona_description. "
    "You just saw this Facebook ad while scrolling. "
    "React honestly as that person. Score it 1-10. "
    "Be critical — most ads are mediocre. "
    "A 7+ means you'd genuinely consider clicking."
)


def build_jury_schemaon(config: LLMConfig) -> Schemaon:
    client = OpenAINativeJSONClient(config=config)
    return Schemaon(
        id="creative_jury_v1",
        input_schema=JURY_INPUT_SCHEMA,
        system_prompt=JURY_SYSTEM_PROMPT,
        output_schema=JURY_OUTPUT_SCHEMA,
        client=client,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

WIDTH = 47


def _divider(char: str = "─", width: int = WIDTH) -> str:
    return char * width


def print_header(niche: str) -> None:
    border = "═" * WIDTH
    title = f"CREATIVE JURY — {niche}"
    padding = (WIDTH - len(title)) // 2
    print(f"\n{border}")
    print(f"{'':>{padding}}{title}")
    print(f"{border}\n")


def print_spec(headline: str, body: str, image_desc: str) -> None:
    print(f"Headline:  {headline}")
    print(f"Body:      {body}")
    print(f"Image:     {image_desc}")
    print()


def print_persona_result(persona_key: str, result: dict) -> None:
    persona = PERSONAS[persona_key]
    display = persona["display_name"]
    click_str = "YES" if result["would_click"] else "NO"
    print(f"─── Persona: {display} ({persona_key}) ───")
    print(f"Score: {result['score']}/10  |  Would click: {click_str}")
    print(f"First impression: \"{result['first_impression']}\"")
    print(f"Resonance: {result['resonance']}")
    print(f"Concerns: {result['concerns']}")
    print(f"Suggestions: {result['suggestions']}")
    print()


def print_verdict(scores: list[int], clicks: list[bool]) -> tuple:
    avg = sum(scores) / len(scores)
    click_count = sum(1 for c in clicks if c)
    click_rate_pct = int(click_count / len(clicks) * 100)
    total = len(clicks)

    if avg >= 6.5:
        verdict_label = "PASS"
        verdict_icon = "[PASS]"
        verdict_msg = "Approve for image generation"
    elif avg >= 5.5:
        verdict_label = "FLAG"
        verdict_icon = "[FLAG]"
        verdict_msg = "Revise before proceeding"
    else:
        verdict_label = "REJECT"
        verdict_icon = "[REJECT]"
        verdict_msg = "Do not proceed — rework the creative"

    print(_divider())
    print("─── VERDICT " + "─" * (WIDTH - 12))
    print(f"Avg Score:   {avg:.1f} / 10")
    print(f"Click Rate:  {click_rate_pct}% ({click_count}/{total} would click)")
    print(f"Result:      {verdict_icon} {verdict_label} — {verdict_msg}")
    print(_divider())
    print()

    return verdict_label, avg, click_rate_pct, click_count, total


# ---------------------------------------------------------------------------
# Core scoring logic
# ---------------------------------------------------------------------------

def run_jury(
    headline: str,
    body: str,
    image_desc: str,
    niche: str,
    llm_config: LLMConfig,
) -> dict:
    """Run all personas for the given niche; print results; return full data."""
    jury = build_jury_schemaon(llm_config)

    print_header(niche)
    print_spec(headline, body, image_desc)

    persona_keys = get_jury_personas(niche)
    scores: list[int] = []
    clicks: list[bool] = []
    persona_results: list[dict] = []

    for persona_key in persona_keys:
        persona = PERSONAS[persona_key]
        input_data = {
            "headline": headline,
            "body_copy": body,
            "image_description": image_desc,
            "niche": niche,
            "persona_name": persona["display_name"],
            "persona_description": persona["description"],
        }
        result = jury.process(input_data)
        scores.append(result["score"])
        clicks.append(result["would_click"])
        persona_results.append({"persona_key": persona_key, **result})
        print_persona_result(persona_key, result)

    verdict_label, avg_score, click_rate_pct, click_count, total = print_verdict(
        scores, clicks
    )

    return {
        "headline": headline,
        "body_copy": body,
        "image_description": image_desc,
        "niche": niche,
        "personas": persona_results,
        "aggregate": {
            "avg_score": round(avg_score, 2),
            "click_rate_pct": click_rate_pct,
            "click_count": click_count,
            "total_personas": total,
            "verdict": verdict_label,
        },
    }


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------

def save_result(result: dict) -> Path:
    JURY_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    niche = result.get("niche", "unknown")
    filename = f"{niche}_{ts}.json"
    out_path = JURY_RESULTS_DIR / filename
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved jury result to: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def check_env() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print(
            "ERROR: OPENAI_API_KEY environment variable is not set.\n"
            "Export it before running: export OPENAI_API_KEY=sk-...",
            file=sys.stderr,
        )
        sys.exit(1)


def make_llm_config() -> LLMConfig:
    model = os.environ.get("BIOMIMICRY_LLM_MODEL", "gpt-4o-mini")
    return LLMConfig(model=model)


def cmd_score(args: argparse.Namespace) -> None:
    check_env()
    niche = args.niche.lower().replace("-", "_")
    if niche not in VALID_NICHES:
        print(
            f"ERROR: --niche must be one of: {', '.join(sorted(VALID_NICHES))}",
            file=sys.stderr,
        )
        sys.exit(1)
    config = make_llm_config()
    result = run_jury(
        headline=args.headline,
        body=args.body,
        image_desc=args.image_desc,
        niche=niche,
        llm_config=config,
    )
    if args.save:
        save_result(result)


def cmd_score_file(args: argparse.Namespace) -> None:
    check_env()
    spec_path = Path(args.spec_file)
    if not spec_path.is_file():
        print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: could not parse JSON spec file: {exc}", file=sys.stderr)
        sys.exit(1)

    required_fields = {"headline", "body", "image_desc", "niche"}
    missing = required_fields - set(spec.keys())
    if missing:
        print(
            f"ERROR: spec file is missing required fields: {', '.join(sorted(missing))}\n"
            f"Required: {', '.join(sorted(required_fields))}",
            file=sys.stderr,
        )
        sys.exit(1)

    niche = spec["niche"].lower().replace("-", "_")
    if niche not in VALID_NICHES:
        print(
            f"ERROR: niche in spec must be one of: {', '.join(sorted(VALID_NICHES))}",
            file=sys.stderr,
        )
        sys.exit(1)

    config = make_llm_config()
    result = run_jury(
        headline=spec["headline"],
        body=spec["body"],
        image_desc=spec["image_desc"],
        niche=niche,
        llm_config=config,
    )
    if args.save:
        save_result(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creative_jury.py",
        description="Pre-screen ad creatives through target-audience personas.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- score subcommand ---
    score_parser = subparsers.add_parser(
        "score",
        help="Score an ad creative provided as CLI arguments.",
    )
    score_parser.add_argument("--headline", required=True, help="Ad headline text")
    score_parser.add_argument("--body", required=True, help="Ad body copy")
    score_parser.add_argument(
        "--image-desc", dest="image_desc", required=True, help="Image description"
    )
    score_parser.add_argument(
        "--niche",
        required=True,
        help=f"Target niche: {', '.join(sorted(VALID_NICHES))}",
    )
    score_parser.add_argument(
        "--save",
        action="store_true",
        help="Save full jury result to resources/jury-results/",
    )
    score_parser.set_defaults(func=cmd_score)

    # --- score-file subcommand ---
    file_parser = subparsers.add_parser(
        "score-file",
        help="Score an ad creative read from a JSON spec file.",
    )
    file_parser.add_argument(
        "spec_file",
        help=(
            "Path to JSON file with keys: headline, body, image_desc, niche. "
            "Example: {\"headline\": \"...\", \"body\": \"...\", "
            "\"image_desc\": \"...\", \"niche\": \"landscaper\"}"
        ),
    )
    file_parser.add_argument(
        "--save",
        action="store_true",
        help="Save full jury result to resources/jury-results/",
    )
    file_parser.set_defaults(func=cmd_score_file)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
