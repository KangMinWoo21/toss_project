from dataclasses import dataclass


@dataclass(frozen=True)
class KisUsConfig:
    app_key: str
    app_secret: str
    account_no: str
    account_product_code: str
    mock_base_url: str


@dataclass(frozen=True)
class KisUsPosition:
    symbol: str
    exchange: str
    quantity: int
    market_value: float
    average_price: float = 0.0


@dataclass(frozen=True)
class KisUsQuote:
    symbol: str
    exchange: str
    price: float


@dataclass(frozen=True)
class KisUsTarget:
    symbol: str
    exchange: str
    target_weight: float


@dataclass(frozen=True)
class ProtectedPosition:
    symbol: str
    reason: str


@dataclass(frozen=True)
class KisUsPlannedOrder:
    plan_id: str
    as_of: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    current_quantity: int
    target_weight: float
    current_weight: float
    reference_price: float
    estimated_value: float
    risk_status: str
    risk_reasons: str
    execution_allowed: bool
    created_at: str
    paper_only: bool = True
    dry_run: bool = True
    production_effect: str = "none"
