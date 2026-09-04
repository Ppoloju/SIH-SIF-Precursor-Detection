# Model comparison — processed/train.csv

- rows: **6585**  (SIF positive: **1012**, 15.4%)
- cross-validation: **5-fold stratified** on the training set, seed 42
- feature pipeline: TF-IDF (1-2 word grams, 10k features, Latin + Indic scripts), fitted per fold only
- rule baseline: the existing deterministic engine's text-derived `sif_potential` verdicts, evaluated on each held-out fold

## Aggregate (mean over folds, std in parentheses)

| model | precision | recall | F1 | accuracy |
|---|---|---|---|---|
| Rule-based engine (ours) | 1.0 ± 0.0 | 1.0 ± 0.0 | 1.0 ± 0.0 | 1.0 ± 0.0 |
| Logistic Regression | 0.475 ± 0.007 | 0.747 ± 0.013 | 0.581 ± 0.008 | 0.834 ± 0.004 |
| Linear SVM | 0.564 ± 0.008 | 0.617 ± 0.024 | 0.589 ± 0.015 | 0.868 ± 0.003 |
| Decision Tree | 0.394 ± 0.01 | 0.703 ± 0.036 | 0.505 ± 0.014 | 0.788 ± 0.008 |
| LDA + PCA | 0.591 ± 0.032 | 0.428 ± 0.034 | 0.496 ± 0.031 | 0.866 ± 0.007 |

## Per-fold detail

| model | fold | n | precision | recall | F1 | accuracy |
| Rule-based engine (ours) | 1 | 1317 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 2 | 1317 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 3 | 1317 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 4 | 1317 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 5 | 1317 | 1.0 | 1.0 | 1.0 | 1.0 |
| Logistic Regression | 1 | 1317 | 0.481 | 0.767 | 0.592 | 0.838 |
| Logistic Regression | 2 | 1317 | 0.47 | 0.728 | 0.571 | 0.832 |
| Logistic Regression | 3 | 1317 | 0.466 | 0.743 | 0.573 | 0.83 |
| Logistic Regression | 4 | 1317 | 0.486 | 0.749 | 0.589 | 0.839 |
| Logistic Regression | 5 | 1317 | 0.471 | 0.749 | 0.578 | 0.831 |
| Linear SVM | 1 | 1317 | 0.573 | 0.658 | 0.613 | 0.872 |
| Linear SVM | 2 | 1317 | 0.568 | 0.624 | 0.594 | 0.869 |
| Linear SVM | 3 | 1317 | 0.556 | 0.589 | 0.572 | 0.865 |
| Linear SVM | 4 | 1317 | 0.553 | 0.596 | 0.573 | 0.863 |
| Linear SVM | 5 | 1317 | 0.571 | 0.616 | 0.592 | 0.869 |
| Decision Tree | 1 | 1317 | 0.395 | 0.649 | 0.491 | 0.793 |
| Decision Tree | 2 | 1317 | 0.409 | 0.743 | 0.527 | 0.796 |
| Decision Tree | 3 | 1317 | 0.401 | 0.688 | 0.506 | 0.794 |
| Decision Tree | 4 | 1317 | 0.388 | 0.744 | 0.51 | 0.78 |
| Decision Tree | 5 | 1317 | 0.379 | 0.69 | 0.49 | 0.778 |
| LDA + PCA | 1 | 1317 | 0.61 | 0.465 | 0.528 | 0.872 |
| LDA + PCA | 2 | 1317 | 0.54 | 0.401 | 0.46 | 0.856 |
| LDA + PCA | 3 | 1317 | 0.567 | 0.396 | 0.466 | 0.861 |
| LDA + PCA | 4 | 1317 | 0.617 | 0.404 | 0.488 | 0.869 |
| LDA + PCA | 5 | 1317 | 0.619 | 0.473 | 0.536 | 0.874 |

## Reading and honest caveats

- **The rule baseline's 1.0 is self-consistency, not generalization**: the
  `sif_potential` labels in these CSVs were produced by the same
  deterministic engine, so evaluating the engine against its own labels
  trivially scores 1.0 (it proves the labels are reproducible, exactly
  like the golden-set evaluation). It does NOT mean the engine is perfect
  on real incidents — external hand-labelled data (the golden set is the
  seed) is the only true ground truth.
- **The classical models DO generalize**: they never see the held-out
  fold's text during training, so their scores measure how learnable the
  engine's SIF labels are from raw incident text. Best F1 here is the
  linear SVM (0.59 real / see synthetic section) — real signal exists,
  but generic text models stay well below the engine's consistency.
- Classical models are trained and cross-validated on the training split
  only; the held-out **test split is untouched** (that is the final
  evaluation set).
- F1 favours the model with the best precision/recall balance; with
  imbalanced SIF labels, accuracy alone can mislead — compare F1 and
  recall (the cost of a missed SIF precursor is high).


---

# Model comparison — Synthetic dataset/train.csv

- rows: **1204**  (SIF positive: **437**, 36.3%)
- cross-validation: **5-fold stratified** on the training set, seed 42
- feature pipeline: TF-IDF (1-2 word grams, 10k features, Latin + Indic scripts), fitted per fold only
- rule baseline: the existing deterministic engine's text-derived `sif_potential` verdicts, evaluated on each held-out fold

## Aggregate (mean over folds, std in parentheses)

| model | precision | recall | F1 | accuracy |
|---|---|---|---|---|
| Rule-based engine (ours) | 1.0 ± 0.0 | 1.0 ± 0.0 | 1.0 ± 0.0 | 1.0 ± 0.0 |
| Logistic Regression | 0.738 ± 0.023 | 0.803 ± 0.028 | 0.769 ± 0.016 | 0.825 ± 0.013 |
| Linear SVM | 0.788 ± 0.031 | 0.785 ± 0.017 | 0.786 ± 0.016 | 0.845 ± 0.014 |
| Decision Tree | 0.69 ± 0.042 | 0.746 ± 0.036 | 0.715 ± 0.016 | 0.784 ± 0.018 |
| LDA + PCA | 0.806 ± 0.027 | 0.737 ± 0.037 | 0.769 ± 0.024 | 0.84 ± 0.015 |

## Per-fold detail

| model | fold | n | precision | recall | F1 | accuracy |
| Rule-based engine (ours) | 1 | 241 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 2 | 241 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 3 | 241 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 4 | 241 | 1.0 | 1.0 | 1.0 | 1.0 |
| Rule-based engine (ours) | 5 | 240 | 1.0 | 1.0 | 1.0 | 1.0 |
| Logistic Regression | 1 | 241 | 0.753 | 0.77 | 0.761 | 0.826 |
| Logistic Regression | 2 | 241 | 0.766 | 0.828 | 0.796 | 0.846 |
| Logistic Regression | 3 | 241 | 0.747 | 0.807 | 0.776 | 0.83 |
| Logistic Regression | 4 | 241 | 0.723 | 0.773 | 0.747 | 0.809 |
| Logistic Regression | 5 | 240 | 0.702 | 0.839 | 0.764 | 0.812 |
| Linear SVM | 1 | 241 | 0.825 | 0.759 | 0.79 | 0.855 |
| Linear SVM | 2 | 241 | 0.77 | 0.77 | 0.77 | 0.834 |
| Linear SVM | 3 | 241 | 0.737 | 0.795 | 0.765 | 0.822 |
| Linear SVM | 4 | 241 | 0.805 | 0.795 | 0.8 | 0.855 |
| Linear SVM | 5 | 240 | 0.805 | 0.805 | 0.805 | 0.858 |
| Decision Tree | 1 | 241 | 0.677 | 0.77 | 0.72 | 0.784 |
| Decision Tree | 2 | 241 | 0.706 | 0.69 | 0.698 | 0.784 |
| Decision Tree | 3 | 241 | 0.642 | 0.795 | 0.711 | 0.763 |
| Decision Tree | 4 | 241 | 0.762 | 0.727 | 0.744 | 0.817 |
| Decision Tree | 5 | 240 | 0.663 | 0.747 | 0.703 | 0.771 |
| LDA + PCA | 1 | 241 | 0.806 | 0.667 | 0.73 | 0.822 |
| LDA + PCA | 2 | 241 | 0.842 | 0.736 | 0.785 | 0.855 |
| LDA + PCA | 3 | 241 | 0.776 | 0.75 | 0.763 | 0.83 |
| LDA + PCA | 4 | 241 | 0.829 | 0.773 | 0.8 | 0.859 |
| LDA + PCA | 5 | 240 | 0.776 | 0.759 | 0.767 | 0.833 |

## Reading and honest caveats

- **The rule baseline's 1.0 is self-consistency, not generalization**: the
  `sif_potential` labels in these CSVs were produced by the same
  deterministic engine, so evaluating the engine against its own labels
  trivially scores 1.0 (it proves the labels are reproducible, exactly
  like the golden-set evaluation). It does NOT mean the engine is perfect
  on real incidents — external hand-labelled data (the golden set is the
  seed) is the only true ground truth.
- **The classical models DO generalize**: they never see the held-out
  fold's text during training, so their scores measure how learnable the
  engine's SIF labels are from raw incident text. Best F1 here is the
  linear SVM (0.59 real / see synthetic section) — real signal exists,
  but generic text models stay well below the engine's consistency.
- Classical models are trained and cross-validated on the training split
  only; the held-out **test split is untouched** (that is the final
  evaluation set).
- F1 favours the model with the best precision/recall balance; with
  imbalanced SIF labels, accuracy alone can mislead — compare F1 and
  recall (the cost of a missed SIF precursor is high).
