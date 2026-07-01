from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REQUIRED_UNIVERSE_COLUMNS = {
    "symbol",
    "name",
    "asset_type",
    "universe_start",
    "universe_end",
    "source",
    "active_flag",
    "survivorship_warning",
}
REQUIRED_PIT_UNIVERSE_COLUMNS = {
    "symbol",
    "name",
    "asset_type",
    "exchange",
    "effective_from",
    "effective_to",
    "status",
    "source",
    "survivorship_warning",
}
ACTIVE_PIT_STATUSES = {"active", "listed", "included"}


@dataclass(frozen=True)
class UniverseMember:
    symbol: str
    name: str
    asset_type: str
    exchange: str
    universe_start: str
    universe_end: str
    source: str
    active_flag: bool
    survivorship_warning: str
    target_weight: float


def load_universe(path: Path | str) -> list[UniverseMember]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = REQUIRED_UNIVERSE_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")
        members: list[UniverseMember] = []
        for row in reader:
            symbol = str(row.get("symbol", "")).strip().upper()
            warning = str(row.get("survivorship_warning", "")).strip()
            active_flag = str(row.get("active_flag", "")).strip().lower() in {"true", "1", "yes", "y"}
            if not symbol:
                raise ValueError(f"{csv_path} contains an empty symbol")
            if not active_flag:
                raise ValueError(f"{csv_path} contains inactive row for {symbol}; v1 fails closed")
            if not warning:
                raise ValueError(f"{csv_path} missing survivorship_warning for {symbol}")
            raw_weight = str(row.get("target_weight", "")).strip()
            target_weight = float(raw_weight) if raw_weight else 0.0
            members.append(
                UniverseMember(
                    symbol=symbol,
                    name=str(row.get("name", "")).strip(),
                    asset_type=str(row.get("asset_type", "")).strip(),
                    exchange=str(row.get("exchange", "")).strip().upper(),
                    universe_start=str(row.get("universe_start", "")).strip(),
                    universe_end=str(row.get("universe_end", "")).strip(),
                    source=str(row.get("source", "")).strip(),
                    active_flag=active_flag,
                    survivorship_warning=warning,
                    target_weight=target_weight,
                )
            )
    if not members:
        raise ValueError(f"{csv_path} has no active universe rows")
    if all(member.target_weight == 0.0 for member in members):
        equal_weight = 1.0 / len(members)
        members = [
            UniverseMember(
                symbol=member.symbol,
                name=member.name,
                asset_type=member.asset_type,
                exchange=member.exchange,
                universe_start=member.universe_start,
                universe_end=member.universe_end,
                source=member.source,
                active_flag=member.active_flag,
                survivorship_warning=member.survivorship_warning,
                target_weight=equal_weight,
            )
            for member in members
        ]
    return members


def load_point_in_time_universe(path: Path | str, *, as_of: str) -> list[UniverseMember]:
    csv_path = Path(path)
    as_of_date = date.fromisoformat(as_of)
    with csv_path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no header")
        missing = REQUIRED_PIT_UNIVERSE_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(sorted(missing))}")
        members: list[UniverseMember] = []
        for row in reader:
            member = _pit_member_from_row(csv_path, row, as_of_date)
            if member is not None:
                members.append(member)
    if not members:
        raise ValueError(f"{csv_path} has no point-in-time universe rows for as_of={as_of}")
    if all(member.target_weight == 0.0 for member in members):
        equal_weight = 1.0 / len(members)
        members = [
            UniverseMember(
                symbol=member.symbol,
                name=member.name,
                asset_type=member.asset_type,
                exchange=member.exchange,
                universe_start=member.universe_start,
                universe_end=member.universe_end,
                source=member.source,
                active_flag=member.active_flag,
                survivorship_warning=member.survivorship_warning,
                target_weight=equal_weight,
            )
            for member in members
        ]
    return sorted(members, key=lambda member: member.symbol)


def universe_survivorship_warning_flag(members: list[UniverseMember]) -> bool:
    return any(_warning_is_survivorship_related(member.survivorship_warning) for member in members)


def _pit_member_from_row(csv_path: Path, row: dict[str, str], as_of_date: date) -> UniverseMember | None:
    symbol = str(row.get("symbol", "")).strip().upper()
    source = str(row.get("source", "")).strip()
    warning = str(row.get("survivorship_warning", "")).strip()
    if not symbol:
        raise ValueError(f"{csv_path} contains an empty symbol")
    if not source:
        raise ValueError(f"{csv_path} missing source for {symbol}")
    if not warning:
        raise ValueError(f"{csv_path} missing survivorship_warning for {symbol}")
    effective_from = date.fromisoformat(str(row.get("effective_from", "")).strip())
    effective_to_text = str(row.get("effective_to", "")).strip()
    effective_to = date.fromisoformat(effective_to_text) if effective_to_text else None
    if effective_to is not None and effective_to < effective_from:
        raise ValueError(f"{csv_path} invalid effective period for {symbol}")
    status = str(row.get("status", "")).strip().lower()
    in_effect = effective_from <= as_of_date and (effective_to is None or as_of_date <= effective_to)
    if not in_effect or status not in ACTIVE_PIT_STATUSES:
        return None
    raw_weight = str(row.get("target_weight", "")).strip()
    target_weight = float(raw_weight) if raw_weight else 0.0
    return UniverseMember(
        symbol=symbol,
        name=str(row.get("name", "")).strip(),
        asset_type=str(row.get("asset_type", "")).strip(),
        exchange=str(row.get("exchange", "")).strip().upper(),
        universe_start=effective_from.isoformat(),
        universe_end=effective_to.isoformat() if effective_to else "",
        source=source,
        active_flag=True,
        survivorship_warning=warning,
        target_weight=target_weight,
    )


def _warning_is_survivorship_related(warning: str) -> bool:
    normalized = str(warning).strip().lower()
    return normalized in {"true", "yes", "1"} or "survivorship" in normalized or "current" in normalized
