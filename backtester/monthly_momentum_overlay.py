import csv
import re
from dataclasses import dataclass
from pathlib import Path


CHAMPION_CANDIDATE_ID = "proxy_guard_exit_short_minus5_neutral_loss_guard55_min_history244"

REPORT_COLUMNS = [
    "candidate_id",
    "champion_candidate_id",
    "status",
    "adoption_status",
    "overlay_cap",
    "validation_evidence",
    "required_failures",
    "required_failures_delta",
    "min_required_excess_pct",
    "min_required_excess_delta",
    "worst_max_drawdown_pct",
    "worst_max_drawdown_delta",
    "full_excess_pct",
    "full_excess_delta",
    "median_walk_forward_excess_pct",
    "median_walk_forward_excess_delta",
    "return_concentration_ratio",
    "return_concentration_delta",
    "reasons",
    "trading_allowed",
    "production_effect",
    "research_only_note",
]


@dataclass(frozen=True)
class ChampionMetrics:
    candidate_id: str
    required_failures: int
    min_required_excess_pct: float
    worst_max_drawdown_pct: float
    full_excess_pct: float
    median_walk_forward_excess_pct: float
    return_concentration_ratio: float


@dataclass(frozen=True)
class OverlayTrial:
    candidate_id: str
    overlay_cap: float
    validation_evidence: str
    required_failures: int
    min_required_excess_pct: float
    worst_max_drawdown_pct: float
    full_excess_pct: float
    median_walk_forward_excess_pct: float
    return_concentration_ratio: float


@dataclass(frozen=True)
class OverlayEvaluation:
    trial: OverlayTrial
    status: str
    adoption_status: str
    reasons: str
    trading_allowed: str = "False"
    production_effect: str = "none"


def load_champion_metrics(path: Path | str) -> ChampionMetrics:
    rows = _read_csv(path)
    by_name = {row["name"]: row for row in rows}
    return ChampionMetrics(
        candidate_id=CHAMPION_CANDIDATE_ID,
        required_failures=_extract_int(by_name["required_scenarios"]["detail"], r"(\d+) failed"),
        min_required_excess_pct=_extract_float(by_name["required_excess"]["detail"], "min_required_excess_pct"),
        worst_max_drawdown_pct=_extract_float(by_name["drawdown_buffer"]["detail"], "worst_max_drawdown_pct"),
        full_excess_pct=_extract_float(by_name["return_concentration"]["detail"], "full_excess_pct"),
        median_walk_forward_excess_pct=_extract_float(
            by_name["return_concentration"]["detail"],
            "median_walk_forward_excess_pct",
        ),
        return_concentration_ratio=_extract_float(by_name["return_concentration"]["detail"], "ratio"),
    )


def evaluate_overlay_trial(champion: ChampionMetrics, trial: OverlayTrial) -> OverlayEvaluation:
    reasons: list[str] = []
    validated = trial.validation_evidence == "validated"
    if not validated:
        reasons.append("validation_evidence_not_validated")
    if trial.required_failures > champion.required_failures:
        reasons.append("new_required_failures")
    if trial.required_failures != 0:
        reasons.append("required_failures_not_zero")
    if trial.worst_max_drawdown_pct < champion.worst_max_drawdown_pct:
        reasons.append("worse_drawdown")
    if trial.median_walk_forward_excess_pct <= champion.median_walk_forward_excess_pct:
        reasons.append("median_walk_forward_not_improved")
    if trial.return_concentration_ratio > champion.return_concentration_ratio:
        reasons.append("worse_concentration")

    if reasons and not (len(reasons) == 1 and reasons[0] == "validation_evidence_not_validated"):
        return OverlayEvaluation(trial=trial, status="REJECT", adoption_status="REJECTED", reasons=";".join(reasons))
    if not validated:
        return OverlayEvaluation(
            trial=trial,
            status="NEEDS_VALIDATION",
            adoption_status="FULL_VALIDATION_REQUIRED",
            reasons=";".join(reasons),
        )
    return OverlayEvaluation(
        trial=trial,
        status="PAPER_DIAGNOSTIC_PASS",
        adoption_status="FULL_VALIDATION_REQUIRED",
        reasons="beats_champion_thresholds_without_trading_authorization",
    )


def build_monthly_momentum_overlay_report(
    champion: ChampionMetrics,
    trials: list[OverlayTrial],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for trial in trials:
        evaluation = evaluate_overlay_trial(champion, trial)
        rows.append(
            {
                "candidate_id": trial.candidate_id,
                "champion_candidate_id": champion.candidate_id,
                "status": evaluation.status,
                "adoption_status": evaluation.adoption_status,
                "overlay_cap": _format_float(trial.overlay_cap),
                "validation_evidence": trial.validation_evidence,
                "required_failures": str(trial.required_failures),
                "required_failures_delta": str(trial.required_failures - champion.required_failures),
                "min_required_excess_pct": _format_float(trial.min_required_excess_pct),
                "min_required_excess_delta": _format_float(
                    trial.min_required_excess_pct - champion.min_required_excess_pct
                ),
                "worst_max_drawdown_pct": _format_float(trial.worst_max_drawdown_pct),
                "worst_max_drawdown_delta": _format_float(
                    trial.worst_max_drawdown_pct - champion.worst_max_drawdown_pct
                ),
                "full_excess_pct": _format_float(trial.full_excess_pct),
                "full_excess_delta": _format_float(trial.full_excess_pct - champion.full_excess_pct),
                "median_walk_forward_excess_pct": _format_float(trial.median_walk_forward_excess_pct),
                "median_walk_forward_excess_delta": _format_float(
                    trial.median_walk_forward_excess_pct - champion.median_walk_forward_excess_pct
                ),
                "return_concentration_ratio": _format_float(trial.return_concentration_ratio),
                "return_concentration_delta": _format_float(
                    trial.return_concentration_ratio - champion.return_concentration_ratio
                ),
                "reasons": evaluation.reasons,
                "trading_allowed": evaluation.trading_allowed,
                "production_effect": evaluation.production_effect,
                "research_only_note": "Paper-only diagnostic; no order, broker, promotion, or production effect.",
            }
        )
    return rows


def save_monthly_momentum_overlay_report(rows: list[dict[str, str]], output: Path | str) -> int:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def load_overlay_trials(path: Path | str) -> list[OverlayTrial]:
    trials: list[OverlayTrial] = []
    for row in _read_csv(path):
        trials.append(
            OverlayTrial(
                candidate_id=row["candidate_id"],
                overlay_cap=float(row["overlay_cap"]),
                validation_evidence=row.get("validation_evidence", "trial_input_only"),
                required_failures=int(row["required_failures"]),
                min_required_excess_pct=float(row["min_required_excess_pct"]),
                worst_max_drawdown_pct=float(row["worst_max_drawdown_pct"]),
                full_excess_pct=float(row["full_excess_pct"]),
                median_walk_forward_excess_pct=float(row["median_walk_forward_excess_pct"]),
                return_concentration_ratio=float(row["return_concentration_ratio"]),
            )
        )
    return trials


def save_monthly_momentum_overlay_markdown(rows: list[dict[str, str]], output: Path | str) -> int:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Monthly Momentum Overlay Report",
        "",
        "Paper-only research diagnostic. `trading_allowed=False`; `production_effect=none`.",
        "",
        "| Candidate | Status | Overlay Cap | Median WF Excess | Worst MDD | Concentration | Reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {candidate_id} | {status} | {overlay_cap} | {median_walk_forward_excess_pct} | "
            "{worst_max_drawdown_pct} | {return_concentration_ratio} | {reasons} |".format(**row)
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


def _read_csv(path: Path | str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _extract_float(text: str, key: str) -> float:
    match = re.search(rf"{re.escape(key)}=(-?\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"missing {key} in {text!r}")
    return float(match.group(1))


def _extract_int(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"missing integer pattern {pattern!r} in {text!r}")
    return int(match.group(1))


def _format_float(value: float) -> str:
    return f"{value:.4f}"
