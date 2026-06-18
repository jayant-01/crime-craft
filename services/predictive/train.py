"""Train the recidivism model on the indexed corpus.

Usage:
    python -m services.predictive.train

We don't have real recidivism labels yet — until KSP provides them, we
generate a synthetic supervised signal from the case history itself
(`recidivated = prior_count >= 2`). This is enough to wire the pipeline
end-to-end; replace the label generation with real ground truth before
this model goes anywhere near a production decision.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from services.datastore import case_repo
from .features import FEATURE_ORDER, cases_for_subject, extract_features, feature_vector
from .model import MODEL_PATH

log = logging.getLogger("predictive.train")


def _build_dataset():
    all_cases = list(case_repo().list(limit=100_000))
    subjects: dict[str, list] = {}
    for c in all_cases:
        for name in c.suspect_names:
            if not name or name.lower() in ("unknown", "redacted"):
                continue
            subjects.setdefault(name.strip(), []).append(c)

    X, y = [], []
    for name, cases in subjects.items():
        feats = extract_features(cases)
        X.append(feature_vector(feats))
        # SYNTHETIC LABEL — replace with real recidivism ground truth.
        y.append(int(feats["prior_count"] >= 2))
    return X, y, len(subjects)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        import xgboost as xgb
        import numpy as np
    except ImportError:
        log.error("xgboost / numpy not installed. Install requirements first.")
        return 2

    X, y, subjects = _build_dataset()
    if not X:
        log.error("no eligible subjects (need >=1 named suspect across cases)")
        return 1

    log.info("training on %d subjects, %d features", subjects, len(FEATURE_ORDER))

    model = xgb.XGBClassifier(
        n_estimators=80,
        max_depth=3,
        learning_rate=0.1,
        objective="binary:logistic",
        eval_metric="logloss",
    )
    model.fit(np.array(X), np.array(y))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))
    MODEL_PATH.with_suffix(".version").write_text("live-v1\n")
    log.info("saved model to %s", MODEL_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
