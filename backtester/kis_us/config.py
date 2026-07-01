import os

from .models import KisUsConfig


DEFAULT_KIS_MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"
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
    if "openapivts.koreainvestment.com" not in base_url:
        raise KisUsConfigError("KIS_MOCK_BASE_URL must point to the KIS mock trading host")
    return KisUsConfig(
        app_key=str(values["KIS_APP_KEY"]).strip(),
        app_secret=str(values["KIS_APP_SECRET"]).strip(),
        account_no=str(values["KIS_ACCOUNT_NO"]).strip(),
        account_product_code=str(values["KIS_ACCOUNT_PRODUCT_CODE"]).strip(),
        mock_base_url=base_url,
    )


def redact_secret(value: str) -> str:
    text = str(value)
    if len(text) <= 4:
        return "****"
    return f"{text[:2]}****{text[-2:]}"
