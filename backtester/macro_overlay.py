from dataclasses import dataclass
from enum import Enum


DISABLED_OVERLAY_CONFIG = "disabled"


class RiskScore(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    RISK_OFF = "risk_off"
    PANIC = "panic"


_RISK_ORDINALS = {
    RiskScore.NORMAL: 0,
    RiskScore.CAUTION: 1,
    RiskScore.RISK_OFF: 2,
    RiskScore.PANIC: 3,
}
_RISK_BY_ORDINAL = {value: key for key, value in _RISK_ORDINALS.items()}


@dataclass(frozen=True)
class MacroObservation:
    observation_date: str
    usable_from: str
    source: str
    series_id: str
    region: str
    value: float
    unit: str
    transform: str
    risk_bucket: RiskScore
    quality_flag: str = "ok"
    source_url: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class EventRiskObservation:
    event_date: str
    visible_at: str
    usable_from: str
    scope: str
    source: str
    event_type: str
    severity: str
    direction: str
    risk_bucket: RiskScore
    symbol: str = ""
    summary: str = ""
    source_id: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class SentimentObservation:
    collected_at: str
    visible_at: str
    usable_from: str
    source: str
    scope: str
    sentiment_score: float
    importance_score: float
    risk_bucket: RiskScore
    published_at: str = ""
    source_account: str = ""
    symbol: str = ""
    language: str = ""
    model_version: str = "manual_v1"
    text_hash: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class MacroOverlayRegimeReport:
    as_of_date: str
    usable_from: str
    candidate_label: str
    baseline_strategy: str
    macro_risk_score: RiskScore
    event_risk_score: RiskScore
    sentiment_risk_score: RiskScore
    overlay_config: str = DISABLED_OVERLAY_CONFIG
    combined_risk_score: RiskScore | None = None
    recommended_action: str = "observe_only"
    production_effect: str = "none"
    reason: str = ""
    source_reports: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.combined_risk_score is None:
            object.__setattr__(
                self,
                "combined_risk_score",
                combine_risk_scores(
                    [
                        self.macro_risk_score,
                        self.event_risk_score,
                        self.sentiment_risk_score,
                    ]
                ),
            )


def combine_risk_scores(scores: list[RiskScore | str | None]) -> RiskScore:
    observed = [_coerce_risk_score(score) for score in scores if score is not None]
    if not observed:
        return RiskScore.NORMAL

    max_ordinal = max(_RISK_ORDINALS[score] for score in observed)
    elevated_inputs = sum(1 for score in observed if _RISK_ORDINALS[score] >= _RISK_ORDINALS[RiskScore.CAUTION])
    if elevated_inputs >= 2:
        max_ordinal = min(max_ordinal + 1, _RISK_ORDINALS[RiskScore.PANIC])
    return _RISK_BY_ORDINAL[max_ordinal]


def _coerce_risk_score(score: RiskScore | str) -> RiskScore:
    if isinstance(score, RiskScore):
        return score
    try:
        return RiskScore(str(score))
    except ValueError as exc:
        raise ValueError(f"unknown risk score: {score}") from exc
