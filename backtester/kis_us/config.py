import os
from urllib.parse import urlparse

from .models import KisUsConfig


DEFAULT_KIS_MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"
KIS_MOCK_HOST = "openapivts.koreainvestment.com"
REQUIRED_ENV_KEYS = (
    "KIS_APP_KEY",
    "KIS_APP_SECRET",
    "KIS_ACCOUNT_NO",
    "KIS_ACCOUNT_PRODUCT_CODE",
)


class KisUsConfigError(ValueError):
    pass


def load_kis_us_config(env: dict[str, str] | None = None) -> KisUsConfig:
    values = env if env is not None else os.environ
    missing = [key for key in REQUIRED_ENV_KEYS if not str(values.get(key, "")).strip()]
    if missing:
        raise KisUsConfigError(f"missing {', '.join(missing)} for KIS US mock configuration")
    base_url = str(values.get("KIS_MOCK_BASE_URL", DEFAULT_KIS_MOCK_BASE_URL)).strip().rstrip("/")
    _validate_mock_base_url(base_url)
    account_no = str(values["KIS_ACCOUNT_NO"]).strip()
    account_product_code = str(values["KIS_ACCOUNT_PRODUCT_CODE"]).strip()
    if not (account_no.isdigit() and len(account_no) == 8):
        raise KisUsConfigError("KIS_ACCOUNT_NO must be the 8 digit KIS account number without hyphen")
    if not (account_product_code.isdigit() and len(account_product_code) == 2):
        raise KisUsConfigError("KIS_ACCOUNT_PRODUCT_CODE must be the 2 digit KIS account product code")
    return KisUsConfig(
        app_key=str(values["KIS_APP_KEY"]).strip(),
        app_secret=str(values["KIS_APP_SECRET"]).strip(),
        account_no=account_no,
        account_product_code=account_product_code,
        mock_base_url=base_url,
    )


def _validate_mock_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname != KIS_MOCK_HOST:
        raise KisUsConfigError("KIS_MOCK_BASE_URL must use https and the exact KIS mock trading host")


def redact_secret(value: str) -> str:
    text = str(value)
    if len(text) <= 4:
        return "****"
    return f"{text[:2]}****{text[-2:]}"
