# Synthetic dataset

Generated 2026-09-04 19:34:19 UTC by `docs/Synthetic dataset/generate_synthetic.py` (seed 42).

## What this is

- **GAN-style duplication of the real data**: every row starts from a real incident description in `data/processed/` and receives 1-3 conservative mutations (number perturbation, real-vocabulary equipment/hazard swaps, missing/positive control clauses, sentence crossover).
- **Labels are engine-computed, never hand-invented**: each generated description is run through the existing deterministic SIF engine (`analysis_pipeline.analyze_report`, no LLM).
- Schema is identical to the real set; provenance marks `source_name = synthetic`.

## Files

- `train.csv` / `validation.csv` / `test.csv` (60/20/20, seed 42, stratified on `sif_potential`)
- `generate_synthetic.py`

## Honest limitation

This is a deterministic stand-in for a true GAN (e.g. CTGAN for tabular or a text GAN for narratives) and is intended for data-augmentation validation and model comparison, not as a substitute for real incident data. A real GAN training run is future work.
