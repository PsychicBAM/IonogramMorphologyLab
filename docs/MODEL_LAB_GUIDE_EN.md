# Model Lab Guide

## Scope
Model Lab is an optional development workspace for training and comparing classifiers from labeled feature CSV files. It is not a diagnostic product and its models are development/research use only unless externally validated for the stated population, instrument, labels, and intended use.

## Workflow
Prepare a CSV with numeric feature columns, a `label` column, and preferably a `date` or sequence grouping field. Import it in Model Lab, inspect class counts and feature names, choose a model, train, then inspect the generated model card. Supported families are logistic regression, linear/RBF SVM, random forest, gradient boosting, k-nearest neighbors, and a calibrated ensemble configuration.

## Leakage control
The default split is `by_date`; neighboring frames from a date/sequence must not be casually split between train and test. A held-out score is evidence about that split, not universal accuracy. Record the data source, seed, class counts, split policy, and preprocessing in the model card.

## Model card and uncertainty
New model cards are marked `development`, record limitations, and state that Article 3 blinded labels were not used. Calibration status may be `uncalibrated`. A score may be absent (`confidence_score: null`), which means there is no calibrated probability to interpret. Below the abstention threshold the model returns `abstain`, a valid output requiring review.

## Responsible use
Do not use a model result as final morphology, causal mechanism, or clinical/operational decision. Compare it with quality flags, interpretable features, rule output, reference context, and expert review. External validation must be independent and documented before changing the model's claim status.

## Troubleshooting
Use at least two viable classes and enough groups for a split. Remove nonnumeric feature cells or provide explicit feature columns. If a model cannot estimate probabilities, preserve null confidence instead of substituting a score. Archive the CSV, card, and environment details with research outputs.
