# ML training report (training split only)

Generated 2026-09-04 20:17:22 UTC — backend-only; not displayed in the frontend.

## Discipline

- **learns from:** training split only
- **validation used for:** nothing in this report (reserved for final model confirmation)
- **test used for:** evaluate_test_once() — a single held-out evaluation
- **leakage controls:** ['TF-IDF fitted inside every fold (pipeline)', 'Grouped folds by incident_id', 'Nested CV for hyperparameters']

## stratified_kfold

Standard stratified k-fold on the training split; class ratio preserved in every fold.

| metric | mean | std | min | max | 95% CI |
|---|---|---|---|---|---|
| precision | 0.4714 | 0.0073 | 0.4608 | 0.4811 | [0.465, 0.4778] |
| recall | 0.75 | 0.0193 | 0.7277 | 0.7822 | [0.7331, 0.7669] |
| f1 | 0.5789 | 0.0103 | 0.5643 | 0.5907 | [0.5698, 0.5879] |
| accuracy | 0.8323 | 0.0032 | 0.8276 | 0.8368 | [0.8295, 0.8352] |

## repeated_stratified

Repeats with different shuffles to estimate variance and a 95% confidence interval.

| metric | mean | std | min | max | 95% CI |
|---|---|---|---|---|---|
| precision | 0.4675 | 0.0113 | 0.4425 | 0.4856 | [0.4618, 0.4733] |
| recall | 0.7487 | 0.0231 | 0.6995 | 0.7822 | [0.737, 0.7604] |
| f1 | 0.5754 | 0.0115 | 0.5543 | 0.5907 | [0.5696, 0.5812] |
| accuracy | 0.8302 | 0.0058 | 0.817 | 0.839 | [0.8273, 0.8331] |

## leave_one_out

One held-out row per fit — lowest bias, highest variance; sampled to 300 rows (LOO is O(n) fits).

| metric | mean | std | min | max | 95% CI |
|---|---|---|---|---|---|
| precision | 0.463 | 0.0 | 0.463 | 0.463 | [0.463, 0.463] |
| recall | 0.5208 | 0.0 | 0.5208 | 0.5208 | [0.5208, 0.5208] |
| f1 | 0.4902 | 0.0 | 0.4902 | 0.4902 | [0.4902, 0.4902] |
| accuracy | 0.8267 | 0.0 | 0.8267 | 0.8267 | [0.8267, 0.8267] |

## grouped

Folds are whole incidents — fragments of one event can never leak across folds.

| metric | mean | std | min | max | 95% CI |
|---|---|---|---|---|---|
| precision | 0.471 | 0.0136 | 0.456 | 0.4868 | [0.4591, 0.4828] |
| recall | 0.7603 | 0.0133 | 0.7444 | 0.7755 | [0.7487, 0.772] |
| f1 | 0.5815 | 0.01 | 0.5703 | 0.5974 | [0.5727, 0.5903] |
| accuracy | 0.8321 | 0.0061 | 0.8238 | 0.8398 | [0.8268, 0.8374] |

## nested

Hyperparameters selected on training folds only via inner CV; outer folds give an unbiased generalization estimate. This is the anti-overfitting gold standard.

| metric | mean | std | min | max | 95% CI |
|---|---|---|---|---|---|
| precision | 0.5406 | 0.0138 | 0.516 | 0.5577 | [0.5285, 0.5527] |
| recall | 0.6631 | 0.028 | 0.6386 | 0.7178 | [0.6385, 0.6876] |
| f1 | 0.5955 | 0.0184 | 0.5708 | 0.6277 | [0.5794, 0.6116] |
| accuracy | 0.8616 | 0.0054 | 0.8527 | 0.8694 | [0.8569, 0.8663] |

## learning_curve

F1 vs training-set size with a train-vs-CV gap used to detect under/overfitting.

| train rows | fraction | train F1 | CV F1 | gap |
|---|---|---|---|---|
| 526 | 0.08 | 0.905 | 0.46 | 0.445 |
| 1580 | 0.24 | 0.815 | 0.4836 | 0.3314 |
| 3160 | 0.48 | 0.7511 | 0.5685 | 0.1826 |
| 5268 | 0.8 | 0.7279 | 0.5789 | 0.149 |

**Diagnosis:** Overfitting signal: training F1 (0.728) is 0.149 above CV F1 (0.579). The CV curve is still rising at the maximum training size — more training data and/or stronger regularization should help.
## Final held-out test evaluation (one-shot)

- test rows: **2192** (336 SIF positive)
- precision: **0.459**
- recall: **0.75**
- f1: **0.5695**
- accuracy: **0.8262**
- Model fit on TRAINING split only; evaluated ONCE on the untouched TEST split.
