"""Recidivism model.

Two modes:
  - stub        : deterministic heuristic from the same feature vector,
                  with synthetic "SHAP-style" contributions so the UI shape
                  is identical to the live path. No external deps.
  - live        : XGBoost classifier + real SHAP explanations. Model file
                  lives at MODEL_PATH; train with `python -m services.predictive.train`.

The route always returns the same RecidivismResponse shape. `is_stub: true`
in the response makes it obvious to callers (and the audit log) when a real
model wasn't used.

Ethics notes — kept here, not in a separate doc, so anyone modifying this
file sees them:
  1. The output is advisory. The route enforces human-in-the-loop language
     in the response.
  2. Score is on KNOWN OFFENDERS only — subject must appear in suspect_names
     of at least one case.
  3. Every call is audit-logged with the requester's reason. A score view
     with no logged reason should be treated as a bug.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from models import FeatureContribution, RecidivismResponse, RiskBand
from services.datastore import case_repo
from .features import FEATURE_ORDER, cases_for_subject, extract_features, feature_vector

log = logging.getLogger("predictive")

MODEL_PATH = Path(os.environ.get("RECIDIVISM_MODEL_PATH", "services/predictive/models/recidivism.json"))
MODEL_VERSION_FALLBACK = "stub-v0.1"

_loaded_model = None
_loaded_explainer = None
_loaded_version: str | None = None


def _try_load_model():
    global _loaded_model, _loaded_explainer, _loaded_version
    if _loaded_model is not None:
        return _loaded_model
    if not MODEL_PATH.exists():
        return None
    try:
        import xgboost as xgb  # lazy
        import shap  # lazy

        model = xgb.XGBClassifier()
        model.load_model(str(MODEL_PATH))
        _loaded_model = model
        _loaded_explainer = shap.TreeExplainer(model)
        _loaded_version = _read_version_marker() or "live-v1"
        log.info("loaded recidivism model from %s (%s)", MODEL_PATH, _loaded_version)
        return model
    except Exception:
        log.exception("recidivism model load failed; falling back to stub")
        return None


def _read_version_marker() -> str | None:
    marker = MODEL_PATH.with_suffix(".version")
    if marker.exists():
        return marker.read_text().strip()
    return None


def model_version() -> str:
    _try_load_model()
    return _loaded_version or MODEL_VERSION_FALLBACK


def is_stub() -> bool:
    return _try_load_model() is None


# --- public API -----------------------------------------------------------

def score_subject(subject: str) -> RecidivismResponse:
    """Score `subject` and return a structured response. Always returns —
    never raises — so the route's audit-log entry can record outcomes even
    for empty or stub paths."""
    all_cases = case_repo().list(limit=100_000)
    subject_cases = cases_for_subject(subject, list(all_cases))
    features = extract_features(subject_cases)

    if not subject_cases:
        return RecidivismResponse(
            subject=subject,
            score=0.0,
            band=RiskBand.LOW,
            case_count=0,
            features=features,
            top_contributions=[],
            model_version=model_version(),
            is_stub=True,
            decision_note=_DECISION_NOTE_NO_HISTORY,
        )

    model = _try_load_model()
    if model is None:
        return _stub_score(subject, features, subject_cases)

    return _live_score(subject, features, subject_cases, model)


# --- stub path ------------------------------------------------------------

def _stub_score(subject: str, features: dict[str, Any], subject_cases) -> RecidivismResponse:
    """Deterministic synthetic score — same shape as the live response so the
    UI can render it. Weights are simple and explainable."""
    weights = {
        "prior_count": 0.18,
        "unique_localities": 0.05,
        "unique_crime_types": 0.07,
        "has_violent_crime": 0.30,
        "has_property_crime": 0.10,
        "open_or_investigating": 0.15,
    }
    # Recency reduces risk: long gap → lower score.
    days = features.get("days_since_last_case", 365)
    recency_factor = max(0.0, 1.0 - min(days, 365) / 365.0) * 0.20

    raw = sum(weights.get(k, 0.0) * float(features.get(k, 0)) for k in weights) + recency_factor
    score = max(0.0, min(1.0, _sigmoid(raw - 1.0)))

    contributions: list[FeatureContribution] = []
    for name, w in weights.items():
        v = features.get(name, 0)
        contribution = w * float(v)
        if contribution == 0:
            continue
        contributions.append(
            FeatureContribution(
                name=name,
                value=v,
                contribution=contribution,
                explanation=_explanation_for(name, v, contribution),
            )
        )
    contributions.append(
        FeatureContribution(
            name="recency",
            value=days,
            contribution=recency_factor,
            explanation=_explanation_for("days_since_last_case", days, recency_factor),
        )
    )
    contributions.sort(key=lambda c: abs(c.contribution), reverse=True)

    return RecidivismResponse(
        subject=subject,
        score=score,
        band=_band(score),
        case_count=len(subject_cases),
        features=features,
        top_contributions=contributions[:5],
        model_version=MODEL_VERSION_FALLBACK,
        is_stub=True,
        decision_note=_DECISION_NOTE,
    )


# --- live path ------------------------------------------------------------

def _live_score(subject: str, features: dict[str, Any], subject_cases, model) -> RecidivismResponse:
    import numpy as np

    vec = np.array([feature_vector(features)], dtype=float)
    prob = float(model.predict_proba(vec)[0][1])
    shap_vals = _loaded_explainer.shap_values(vec)[0]

    contributions = [
        FeatureContribution(
            name=name,
            value=features[name],
            contribution=float(shap_vals[idx]),
            explanation=_explanation_for(name, features[name], float(shap_vals[idx])),
        )
        for idx, name in enumerate(FEATURE_ORDER)
    ]
    contributions.sort(key=lambda c: abs(c.contribution), reverse=True)

    return RecidivismResponse(
        subject=subject,
        score=prob,
        band=_band(prob),
        case_count=len(subject_cases),
        features=features,
        top_contributions=contributions[:5],
        model_version=model_version(),
        is_stub=False,
        decision_note=_DECISION_NOTE,
    )


# --- helpers --------------------------------------------------------------

def _band(score: float) -> RiskBand:
    if score < 0.33:
        return RiskBand.LOW
    if score < 0.66:
        return RiskBand.MEDIUM
    return RiskBand.HIGH


def _sigmoid(x: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-x))


def _explanation_for(feature: str, value, contribution: float) -> str:
    direction = "increases" if contribution > 0 else "decreases"
    if feature == "prior_count":
        return f"{value} prior cases linked to subject — {direction} risk."
    if feature == "unique_localities":
        return f"Activity in {value} distinct localities — {direction} risk."
    if feature == "unique_crime_types":
        return f"{value} distinct crime types in history — {direction} risk."
    if feature == "has_violent_crime":
        return f"{'Violent crime present' if value else 'No violent crime'} in history — {direction} risk."
    if feature == "has_property_crime":
        return f"{'Property crime present' if value else 'No property crime'} in history — {direction} risk."
    if feature in ("days_since_last_case", "recency"):
        return f"Last case was {value} days ago — {direction} risk."
    if feature == "open_or_investigating":
        return f"{'Has an active case' if value else 'No active case'} — {direction} risk."
    return f"{feature}={value} — {direction} risk."


_DECISION_NOTE = (
    "ADVISORY ONLY. This score is a decision aid for senior officers — "
    "never the basis for action by itself. Human review and existing "
    "investigative procedures remain mandatory."
)

_DECISION_NOTE_NO_HISTORY = (
    "No prior cases found for this subject. Score is not computed — recidivism "
    "scoring is restricted to KNOWN offenders only."
)


def reset_for_tests() -> None:
    global _loaded_model, _loaded_explainer, _loaded_version
    _loaded_model = None
    _loaded_explainer = None
    _loaded_version = None
