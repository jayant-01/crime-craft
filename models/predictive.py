from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FeatureContribution(BaseModel):
    """One feature's contribution to the score. SHAP value + human-readable note."""
    name: str
    value: float | int | str
    contribution: float        # signed SHAP value (positive = increases risk)
    explanation: str


class RecidivismRequest(BaseModel):
    """Score a known offender. `subject` is a free-text key — typically the
    `suspect_names` value found across cases. The route audit-logs everything
    so we can review who was scored, by whom, and why."""
    subject: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=4, max_length=500,
                        description="Why this scoring was requested. Logged.")


class RecidivismResponse(BaseModel):
    # `model_version` collides with Pydantic v2's protected "model_" namespace;
    # opt out so the field name (part of our API contract) doesn't emit a warning.
    model_config = ConfigDict(protected_namespaces=())

    subject: str
    score: float                            # 0..1
    band: RiskBand
    case_count: int                         # number of cases linking to subject
    features: dict[str, float | int | str]  # extracted features (transparent)
    top_contributions: list[FeatureContribution]
    model_version: str
    is_stub: bool = False                   # true when the real model isn't loaded
    decision_note: str                      # "advisory only, human-in-the-loop required"
