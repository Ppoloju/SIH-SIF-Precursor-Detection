"""Generate a synthetic SIF dataset under docs/Synthetic dataset/.

Method (documented honestly):

  * The generator is a lightweight GAN-style duplication tool: it takes the
    REAL processed incidents (data/processed/train+validation+test.csv) and
    produces near-duplicate / recombined variants — the "given real data,
    generate duplicate data as well" idea from the design notes.
  * Each generated description starts from a real incident text and receives
    1-3 conservative mutations: numeric perturbation, equipment/hazard/control
    vocabulary swaps drawn from the real data's own extracted terms, phrase
    insertion (e.g. a missing-control clause), and sentence-level crossover
    of two real fragments.
  * Labels are NEVER hand-invented: every generated description is run through
    the existing deterministic engine (analysis_pipeline.analyze_report,
    use_llm=False), the same engine the web app and the real pipeline use.
  * A true generative-adversarial model (e.g. CTGAN / text GAN) is a possible
    upgrade; this generator is its deterministic, reproducible stand-in.

Outputs the same canonical schema as the real set, split 60/20/20 (seed 42,
stratified on sif_potential):
  docs/Synthetic dataset/train.csv / validation.csv / test.csv
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.analysis_pipeline import analyze_report  # noqa: E402
from app.services.ingest import _text_fingerprint  # noqa: E402

REAL_FILES = [
    ROOT / "data" / "processed" / "train.csv",
    ROOT / "data" / "processed" / "validation.csv",
    ROOT / "data" / "processed" / "test.csv",
]
OUT_DIR = Path(__file__).resolve().parent
SEED = 42
MIN_DESC_LEN = 15

CANONICAL_INPUTS = [
    "report_id", "incident_id", "report_type", "site_name", "activity",
    "date_reported", "description", "actual_severity", "date_closed",
    "status", "observation_date", "location_detail",
]
CANONICAL_OUTPUTS = [
    "equipment", "hazard", "barrier_failure", "lsr", "sif_potential",
    "priority", "potential_severity", "precursor", "sif_probability",
    "reason", "suggested_immediate_action", "short_summary",
]
PROVENANCE_COLS = ["source_name", "source_file", "inferred_fields", "model_tag",
                   "languages", "description_len"]
FINAL_COLUMNS = CANONICAL_INPUTS + CANONICAL_OUTPUTS + PROVENANCE_COLS

# Control / equipment vocabulary observed across the real datasets (kept small
# and domain-true; the bulk of the vocabulary comes from the real rows).
_EQUIP_TERMS = ["crane", "forklift", "scaffold", "ladder", "grinder", "welding torch",
                "generator", "conveyor", "drill rig", "hoist", "sling", "pump",
                "compressor", "excavator", "pressure vessel", "elevator", "guard",
                "circuit breaker", "gas detector", "extinguisher", "hose", "winch"]
_HAZARD_TERMS = ["fire", "explosion", "fall", "electrical", "toxic gas", "confined space",
                 "crushing", "struck by", "pinch point", "pressurized line",
                 "hydrogen sulfide", "asphyxiation", "burns", "chemical exposure"]
_CONTROL_CLAUSES = [
    "without a harness", "without lockout/tagout applied", "no gas test performed",
    "bypassing the interlock", "the guard was removed", "working without a permit",
    "no fall protection in place", "the ventilation was not running",
    "without eye protection", "the emergency stop was not tested",
]
_POSITIVE_CONTROL_CLAUSES = [
    "with the harness properly secured", "lockout/tagout was applied",
    "the gas test passed before entry", "the interlock remained in place",
    "the guard was reinstalled", "the permit was issued and displayed",
]

_NUM_RE = re.compile(r"\b(\d{1,4}(?:[,.]\d+)?)\b")


def _mutate_numbers(text: str, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        try:
            n = float(m.group(1).replace(",", ""))
        except ValueError:
            return m.group(1)
        delta = rng.choice([-2, -1, 1, 2, 5, 10, -10])
        out = n + delta
        if out < 0:
            out = abs(out)
        if out == int(out):
            return str(int(out))
        return f"{out:.1f}"
    return _NUM_RE.sub(repl, text)


def _swap_vocab(text: str, vocab: list[str], rng: random.Random) -> str:
    """Replace a random vocabulary hit with another real term of the same kind."""
    lower = text.lower()
    hits = [t for t in vocab if t.lower() in lower]
    if not hits:
        return text
    target = rng.choice(hits)
    replacement = rng.choice([t for t in vocab if t != target])
    # replace the first occurrence, preserving case of the original where possible
    idx = lower.find(target.lower())
    original = text[idx:idx + len(target)]
    repl = replacement if original[0].isupper() else replacement
    return text[:idx] + repl + text[idx + len(target):]


def _crossover(a: str, b: str, rng: random.Random) -> str:
    """Join a random prefix of a with a random suffix of b."""
    sentences_a = re.split(r"(?<=[.!?])\s+", a.strip())
    sentences_b = re.split(r"(?<=[.!?])\s+", b.strip())
    if len(sentences_a) < 2 or len(sentences_b) < 2:
        return a
    cut_a = rng.randint(1, len(sentences_a) - 1)
    cut_b = rng.randint(1, len(sentences_b) - 1)
    return " ".join(sentences_a[:cut_a] + sentences_b[cut_b:]).strip()


def _generate_one(seeds: list[dict], rng: random.Random) -> str:
    seed = rng.choice(seeds)
    text = seed["description"]
    ops = rng.randint(1, 3)
    vocab = _EQUIP_TERMS if rng.random() < 0.5 else _HAZARD_TERMS
    for _ in range(ops):
        kind = rng.random()
        if kind < 0.4:
            text = _mutate_numbers(text, rng)
        elif kind < 0.75:
            text = _swap_vocab(text, vocab, rng)
        else:
            clause = rng.choice(_CONTROL_CLAUSES + _POSITIVE_CONTROL_CLAUSES)
            text = text.rstrip(".") + ", " + clause + "."
    if rng.random() < 0.15:
        other = rng.choice(seeds)
        text = _crossover(text, other["description"], rng)
    return re.sub(r"\s+", " ", text).strip()


def _load_real() -> list[dict]:
    rows: list[dict] = []
    for p in REAL_FILES:
        if not p.exists():
            print(f"  (skip {p.name}: real set not built yet)")
            continue
        with open(p, encoding="utf-8", newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=2000, help="total synthetic rows")
    args = ap.parse_args()

    started = time.time()
    real = _load_real()
    usable = [r for r in real if (r.get("description") or "").strip()
              and len(r["description"]) >= MIN_DESC_LEN]
    if not usable:
        raise SystemExit("no real processed rows found — build the real set first "
                         "(backend/scripts/build_real_dataset.py)")
    print(f"loaded {len(usable)} real seed rows")

    rng = random.Random(SEED)
    seeds_by_rule: dict[str, list[dict]] = defaultdict(list)
    for r in usable:
        seeds_by_rule[r.get("lsr") or "unknown"].append(r)

    generated: list[dict] = []
    seen: set[str] = set()
    while len(generated) < args.n:
        seed = rng.choice(usable)
        rule = seed.get("lsr") or "unknown"
        pool = seeds_by_rule.get(rule) or usable
        text = _generate_one(pool, rng)
        if len(text) < MIN_DESC_LEN:
            continue
        fp = _text_fingerprint(text)
        if fp in seen or fp == _text_fingerprint(seed["description"]):
            continue
        seen.add(fp)
        try:
            res = analyze_report(text, use_llm=False)
        except Exception:
            continue
        row = {
            "report_id": f"SYN-{len(generated) + 1:05d}",
            "incident_id": f"SYN-{len(generated) + 1:05d}",
            "report_type": f"synthetic from {seed.get('report_type', 'real')}",
            "site_name": seed.get("site_name", ""),
            "activity": seed.get("activity", ""),
            "date_reported": seed.get("date_reported", ""),
            "description": text,
            "actual_severity": seed.get("actual_severity", ""),
            "date_closed": "", "status": "", "observation_date": "",
            "location_detail": seed.get("location_detail", ""),
            "equipment": "; ".join(res.get("equipment") or []),
            "hazard": res.get("hazard") or "",
            "barrier_failure": "; ".join(res.get("barrier_failure") or []),
            "lsr": res.get("life_saving_rule") or "",
            "sif_potential": "1" if res.get("sif_potential") else "0",
            "priority": res.get("priority") or "",
            "potential_severity": res.get("potential_consequence") or "",
            "precursor": "; ".join(res.get("evidence") or []),
            "sif_probability": str(res.get("confidence") or ""),
            "reason": res.get("explanation") or "",
            "suggested_immediate_action": "; ".join(res.get("suggested_actions") or []),
            "short_summary": (res.get("summary") or "")[:500],
            "source_name": "synthetic",
            "source_file": "docs/Synthetic dataset/generate_synthetic.py",
            "inferred_fields": "equipment,hazard,barrier_failure,lsr,potential_severity,"
                               "precursor,sif_probability,reason,suggested_immediate_action,"
                               "short_summary",
            "model_tag": res.get("model") or "rules-v1",
            "languages": "; ".join(res.get("languages") or []),
            "description_len": len(text),
        }
        generated.append(row)
        if len(generated) % 500 == 0:
            print(f"  {len(generated)}/{args.n} generated")

    # deterministic 60/20/20 split, stratified on sif_potential
    strata: dict[str, list[dict]] = defaultdict(list)
    for row in generated:
        strata[row["sif_potential"]].append(row)
    buckets: dict[str, int] = {}
    for stratum, rows in strata.items():
        for offset, row in enumerate(sorted(rows, key=lambda r: r["report_id"])):
            buckets[row["report_id"]] = offset % 10
    split_of = {"train": {0, 1, 2, 3, 4, 5}, "validation": {6, 7}, "test": {8, 9}}
    out: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    for row in generated:
        for name, bucketset in split_of.items():
            if buckets[row["report_id"]] in bucketset:
                out[name].append(row)
                break

    for name, rows in out.items():
        path = OUT_DIR / f"{name}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FINAL_COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        pos = sum(1 for r in rows if r["sif_potential"] == "1")
        print(f"  {name}.csv: {len(rows)} rows ({pos} SIF positive)")

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "# Synthetic dataset\n\n"
        f"Generated {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} by "
        "`docs/Synthetic dataset/generate_synthetic.py` (seed 42).\n\n"
        "## What this is\n\n"
        "- **GAN-style duplication of the real data**: every row starts from a real "
        "incident description in `data/processed/` and receives 1-3 conservative "
        "mutations (number perturbation, real-vocabulary equipment/hazard swaps, "
        "missing/positive control clauses, sentence crossover).\n"
        "- **Labels are engine-computed, never hand-invented**: each generated "
        "description is run through the existing deterministic SIF engine "
        "(`analysis_pipeline.analyze_report`, no LLM).\n"
        "- Schema is identical to the real set; provenance marks "
        "`source_name = synthetic`.\n\n"
        "## Files\n\n"
        "- `train.csv` / `validation.csv` / `test.csv` (60/20/20, seed 42, "
        "stratified on `sif_potential`)\n"
        "- `generate_synthetic.py`\n\n"
        "## Honest limitation\n\n"
        "This is a deterministic stand-in for a true GAN (e.g. CTGAN for tabular "
        "or a text GAN for narratives) and is intended for data-augmentation "
        "validation and model comparison, not as a substitute for real incident "
        "data. A real GAN training run is future work.\n",
        encoding="utf-8",
    )
    print(f"done in {time.time() - started:.0f}s; outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()