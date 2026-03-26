#!/usr/bin/env python3
"""
Creative Generator — Shield Insurance Agency (David VanDyke)
Generates new ad creative specs (headline + body + image prompt) informed by
past performance data and winner memory using the schemaon framework.

Usage:
  python3 scripts/creative_generator.py generate --niche landscaper
  python3 scripts/creative_generator.py generate --niche landscaper --mutation visual_first
  python3 scripts/creative_generator.py generate --niche general --count 3
  python3 scripts/creative_generator.py remember --niche landscaper --file specs/winner.json --score 8.2
  python3 scripts/creative_generator.py memory --niche landscaper
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Schemaon framework ────────────────────────────────────────────────────────

sys.path.insert(0, '/home/kingjames/agents')
from biomimicry.schemaon import Schemaon
from biomimicry.schemaon_memory import MemoryCapability, CapabilitySchemaon, add_exemplar_if_good
from biomimicry.llm_backend import OpenAINativeJSONClient, LLMConfig

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
WINNER_MEMORY_DIR = PROJECT_ROOT / 'resources' / 'winner-memory'
GENERATED_SPECS_DIR = PROJECT_ROOT / 'resources' / 'generated-specs'

WINNER_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_SPECS_DIR.mkdir(parents=True, exist_ok=True)

# ── Niche context ─────────────────────────────────────────────────────────────

NICHE_CONTEXT = {
    'general': (
        "Michigan homeowners and small business owners. Main concern: overpaying for coverage "
        "they already have. David shops 50+ carriers to find better rates."
    ),
    'landscaper': (
        "Michigan landscaping business owners and crew leads. Main concerns: general liability "
        "if someone gets hurt on a job, equipment theft/damage, and workers comp. They're busy, "
        "skeptical of corporate stuff, and respond to people who understand their work."
    ),
    'contractor': (
        "Michigan contractors: electricians, plumbers, HVAC, roofers, general contractors. "
        "Need GL, tools/equipment coverage, workers comp. Often need a COI fast for a new job."
    ),
    'restaurant': (
        "Michigan restaurant and bar owners. Need GL, liquor liability, property, and sometimes "
        "workers comp. Tight margins, wary of price increases."
    ),
    'home-business': (
        "Michigan residents running businesses from home: bookkeepers, consultants, crafters, "
        "Etsy sellers. Their homeowner's policy doesn't cover business losses — most don't know this."
    ),
}

VALID_NICHES = list(NICHE_CONTEXT.keys())

VALID_MUTATIONS = [
    'visual_first',
    'copy_variation',
    'hook_angle',
    'crossover',
    'new_concept',
]

# ── Compliance constraints ────────────────────────────────────────────────────

COMPLIANCE_CONSTRAINTS = [
    "Do not claim 'cheapest', 'lowest price', 'best price', or 'guaranteed savings'",
    "Do not use superlatives like 'best insurance' without qualification",
    "Do not use fear-mongering or catastrophizing language",
    "Claims about carrier count (50+) are factual and allowed",
    "Phrases like 'better rate', 'save money', 'compare rates' are acceptable",
]

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert direct-response copywriter specializing in Facebook ads for small business insurance. Your job is to generate ad creative specs that will resonate with specific niche audiences in Michigan.

Rules:
- Never claim "cheapest", "lowest price", "guaranteed savings", or "best" (insurance compliance)
- Never use fear-mongering language
- Lead with the audience's identity or specific pain point, not generic insurance talk
- Image prompts must be clean flat graphic design (NOT photorealistic) with navy (#1a365d) and gold (#d69e2e) colors
- Headlines must be under 40 characters
- Body copy must feel like it's from a real person, not a corporation\
"""

# ── Schemaon schemas ──────────────────────────────────────────────────────────

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "niche": {"type": "string", "description": "niche slug"},
        "niche_context": {"type": "string", "description": "description of this audience and their insurance needs"},
        "mutation_directive": {
            "type": "string",
            "description": "one of: visual_first, copy_variation, hook_angle, crossover, new_concept",
        },
        "top_performers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "body_copy": {"type": "string"},
                    "image_description": {"type": "string"},
                    "ctr": {"type": "number"},
                    "cpl": {"type": "number"},
                    "jury_score": {"type": "number"},
                },
                "required": ["headline", "body_copy"],
                "additionalProperties": False,
            },
            "description": "can be empty",
        },
        "bottom_performers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "body_copy": {"type": "string"},
                    "reason_failed": {"type": "string"},
                },
                "required": ["headline", "body_copy"],
                "additionalProperties": False,
            },
            "description": "can be empty",
        },
        "constraints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "compliance rules",
        },
    },
    "required": [
        "niche",
        "niche_context",
        "mutation_directive",
        "top_performers",
        "bottom_performers",
        "constraints",
    ],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "max 40 chars, punchy"},
        "body_copy": {"type": "string", "description": "max 125 chars, conversational"},
        "image_prompt": {
            "type": "string",
            "description": "detailed Ideogram V_2A_TURBO prompt, design-style, square 1:1, navy/gold palette",
        },
        "hook_angle": {
            "type": "string",
            "description": "one of: savings, trust, speed, niche_identity, pain_point, social_proof",
        },
        "mutation_type": {"type": "string", "description": "what type of variation this is"},
        "rationale": {"type": "string", "description": "why this should work for this audience"},
        "compliance_note": {
            "type": "string",
            "description": "confirm no prohibited claims (no 'cheapest', 'guaranteed savings', 'best price')",
        },
    },
    "required": [
        "headline",
        "body_copy",
        "image_prompt",
        "hook_angle",
        "mutation_type",
        "rationale",
        "compliance_note",
    ],
    "additionalProperties": False,
}

# ── Memory helpers ────────────────────────────────────────────────────────────


def memory_path(niche: str) -> Path:
    return WINNER_MEMORY_DIR / f"{niche}.json"


def load_memory(niche: str) -> list[dict]:
    """Load exemplars from disk for a given niche."""
    path = memory_path(niche)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_memory(niche: str, exemplars: list[dict]) -> None:
    """Persist exemplars to disk."""
    memory_path(niche).write_text(
        json.dumps(exemplars, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def build_memory_capability(niche: str) -> MemoryCapability:
    """Create a MemoryCapability pre-loaded with winner exemplars for the niche."""
    exemplars = load_memory(niche)
    return MemoryCapability(
        exemplars=exemplars,
        max_exemplars=5,
        role_hint="winning ads",
    )


# ── Generator ─────────────────────────────────────────────────────────────────


def pick_mutation(forced: str | None, niche: str, memory: MemoryCapability) -> str:
    """Return a mutation directive, cycling through types based on memory depth."""
    if forced:
        return forced
    depth = len(memory.exemplars)
    return VALID_MUTATIONS[depth % len(VALID_MUTATIONS)]


def build_generator(memory: MemoryCapability) -> CapabilitySchemaon:
    """Build a CapabilitySchemaon wired with memory."""
    client = OpenAINativeJSONClient(config=LLMConfig(model='gpt-4o-mini'))
    schemaon = Schemaon(
        id='shield_creative_generator',
        input_schema=INPUT_SCHEMA,
        system_prompt=SYSTEM_PROMPT,
        output_schema=OUTPUT_SCHEMA,
        client=client,
    )
    return CapabilitySchemaon(inner=schemaon, capabilities=[memory])


def generate_spec(niche: str, mutation: str, memory: MemoryCapability) -> dict:
    """Run the schemaon and return the raw output dict."""
    winner_exemplars = memory.exemplars
    top_performers = []
    for ex in winner_exemplars:
        try:
            spec_data = json.loads(ex.get('code', '{}'))
            top_performers.append({
                'headline': spec_data.get('headline', ''),
                'body_copy': spec_data.get('body_copy', ''),
                'image_description': spec_data.get('image_prompt', ''),
                'jury_score': float(ex.get('score', 0.0)),
            })
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    input_data = {
        'niche': niche,
        'niche_context': NICHE_CONTEXT[niche],
        'mutation_directive': mutation,
        'top_performers': top_performers,
        'bottom_performers': [],
        'constraints': COMPLIANCE_CONSTRAINTS,
    }

    generator = build_generator(memory)
    return generator.process(input_data)


def save_spec(niche: str, spec: dict) -> tuple[Path, Path]:
    """Save spec to latest and timestamped files. Returns (latest_path, ts_path)."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    latest_path = GENERATED_SPECS_DIR / f'{niche}_latest.json'
    ts_path = GENERATED_SPECS_DIR / f'{niche}_{timestamp}.json'

    payload = json.dumps(spec, indent=2, ensure_ascii=False)
    latest_path.write_text(payload, encoding='utf-8')
    ts_path.write_text(payload, encoding='utf-8')
    return latest_path, ts_path


def print_spec(spec: dict, niche: str, mutation: str, memory_count: int) -> None:
    """Print generated spec in the standard terminal format."""
    compliance_ok = 'prohibited' not in spec.get('compliance_note', '').lower()
    compliance_symbol = 'OK' if compliance_ok else 'REVIEW NEEDED'

    print()
    print('=' * 39)
    print(f'  CREATIVE GENERATOR \u2014 {niche}')
    print(f'  Mutation: {mutation} | Memory: {memory_count} exemplars loaded')
    print('=' * 39)
    print()
    print(f'Headline:    {spec["headline"]}')
    print(f'Body:        {spec["body_copy"]}')
    print(f'Hook angle:  {spec["hook_angle"]}')
    print(f'Mutation:    {spec["mutation_type"]}')
    print()
    print('Image prompt:')
    # Wrap image prompt lines at ~70 chars
    prompt_text = spec['image_prompt']
    words = prompt_text.split()
    line = '  '
    for word in words:
        if len(line) + len(word) + 1 > 72:
            print(line)
            line = '  ' + word
        else:
            line = line + (' ' if line != '  ' else '') + word
    if line.strip():
        print(line)
    print()
    print('Rationale:')
    rationale_text = spec['rationale']
    words = rationale_text.split()
    line = '  '
    for word in words:
        if len(line) + len(word) + 1 > 72:
            print(line)
            line = '  ' + word
        else:
            line = line + (' ' if line != '  ' else '') + word
    if line.strip():
        print(line)
    print()
    print(f'Compliance: \u2713 {compliance_symbol}')
    if not compliance_ok:
        print(f'  Note: {spec["compliance_note"]}')
    print()
    print('\u2500\u2500\u2500 Next steps \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')
    headline_escaped = spec["headline"].replace('"', '\\"')
    body_escaped = spec["body_copy"].replace('"', '\\"')
    image_escaped = spec["image_prompt"][:60].replace('"', '\\"')
    print(f'1. Run jury:  python3 scripts/creative_jury.py score --headline "{headline_escaped}" --body "{body_escaped}" --image-desc "{image_escaped}..." --niche {niche}')
    print(f'2. Generate:  python3 scripts/meta_studio.py generate {niche} --prompt "..." --yes')
    print(f'3. Remember:  python3 scripts/creative_generator.py remember --niche {niche} --score 8.5')
    print()


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_generate(args: argparse.Namespace) -> None:
    niche = args.niche
    count = getattr(args, 'count', 1) or 1
    mutation_override = getattr(args, 'mutation', None)

    memory = build_memory_capability(niche)

    for i in range(count):
        if count > 1:
            print(f'\n[{i + 1}/{count}] Generating creative for niche: {niche}')

        mutation = pick_mutation(mutation_override, niche, memory)

        print(f'Calling LLM (model: gpt-4o-mini, niche: {niche}, mutation: {mutation})...', flush=True)
        spec = generate_spec(niche, mutation, memory)

        latest_path, ts_path = save_spec(niche, spec)
        print(f'Saved: {latest_path}')
        print(f'       {ts_path}')

        print_spec(spec, niche, mutation, len(memory.exemplars))


def cmd_remember(args: argparse.Namespace) -> None:
    niche = args.niche
    score = args.score
    file_arg = getattr(args, 'file', None)

    if file_arg:
        spec_path = Path(file_arg)
        if not spec_path.is_absolute():
            spec_path = PROJECT_ROOT / file_arg
    else:
        spec_path = GENERATED_SPECS_DIR / f'{niche}_latest.json'

    if not spec_path.is_file():
        print(f'Error: spec file not found: {spec_path}', file=sys.stderr)
        print(f'Hint: run `generate --niche {niche}` first, or pass --file <path>', file=sys.stderr)
        sys.exit(1)

    spec = json.loads(spec_path.read_text(encoding='utf-8'))

    MIN_SCORE = 7.0
    if score < MIN_SCORE:
        print(f'Score {score} is below minimum threshold ({MIN_SCORE}). Not storing.')
        return

    memory = build_memory_capability(niche)
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    headline = spec.get('headline', '')
    description = f'{niche}:{headline}'
    code = json.dumps({
        'headline': spec.get('headline', ''),
        'body_copy': spec.get('body_copy', ''),
        'image_prompt': spec.get('image_prompt', ''),
    }, ensure_ascii=False)

    # add_exemplar_if_good uses threshold in [0,1], but we store scores 0-10.
    # We bypass threshold by appending directly to keep the 0-10 score domain.
    exemplar = {
        'task_id': timestamp,
        'description': description,
        'code': code,
        'score': score,
    }
    memory.exemplars.append(exemplar)
    if len(memory.exemplars) > memory.max_exemplars:
        memory.exemplars.pop(0)

    save_memory(niche, memory.exemplars)
    print(f'Added to winner memory for niche "{niche}":')
    print(f'  Score:    {score}')
    print(f'  Headline: {headline}')
    print(f'  Total exemplars stored: {len(memory.exemplars)}')
    print(f'  Memory file: {memory_path(niche)}')


def cmd_memory(args: argparse.Namespace) -> None:
    niche = args.niche
    exemplars = load_memory(niche)

    if not exemplars:
        print(f'No winner memory found for niche "{niche}".')
        print(f'Expected file: {memory_path(niche)}')
        return

    print()
    print('=' * 39)
    print(f'  WINNER MEMORY \u2014 {niche}')
    print(f'  {len(exemplars)} exemplar(s) stored')
    print('=' * 39)
    print()

    for i, ex in enumerate(exemplars, 1):
        print(f'[{i}] Task ID:     {ex.get("task_id", "unknown")}')
        print(f'    Description: {ex.get("description", "")}')
        print(f'    Score:       {ex.get("score", "n/a")}')
        try:
            spec_data = json.loads(ex.get('code', '{}'))
            print(f'    Headline:    {spec_data.get("headline", "")}')
            body = spec_data.get("body_copy", "")
            print(f'    Body:        {body[:80]}{"..." if len(body) > 80 else ""}')
        except (json.JSONDecodeError, TypeError):
            print(f'    Code:        {str(ex.get("code", ""))[:80]}')
        print()


# ── CLI ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='creative_generator.py',
        description='Generate ad creative specs for Shield Insurance Agency (David VanDyke)',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # generate
    gen = sub.add_parser('generate', help='Generate new creative spec(s)')
    gen.add_argument(
        '--niche',
        required=True,
        choices=VALID_NICHES,
        help='Target niche',
    )
    gen.add_argument(
        '--mutation',
        choices=VALID_MUTATIONS,
        default=None,
        help='Force a specific mutation type',
    )
    gen.add_argument(
        '--count',
        type=int,
        default=1,
        metavar='N',
        help='Number of variants to generate (default: 1)',
    )

    # remember
    rem = sub.add_parser('remember', help='Add a spec to winner memory')
    rem.add_argument('--niche', required=True, choices=VALID_NICHES)
    rem.add_argument(
        '--file',
        default=None,
        metavar='PATH',
        help='Path to spec JSON (default: resources/generated-specs/{niche}_latest.json)',
    )
    rem.add_argument(
        '--score',
        type=float,
        required=True,
        help='Jury/performance score (0-10). Only stored if >= 7.0.',
    )

    # memory
    mem = sub.add_parser('memory', help='Show winner memory for a niche')
    mem.add_argument('--niche', required=True, choices=VALID_NICHES)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'remember':
        cmd_remember(args)
    elif args.command == 'memory':
        cmd_memory(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
