import unittest

from backtester.kis_us.config import KisUsConfigError, load_kis_us_config, redact_secret


class KisUsConfigTests(unittest.TestCase):
    def test_missing_required_env_fails_closed_without_leaking_values(self):
        env = {
            "KIS_APP_KEY": "live_app_key_value",
            "KIS_APP_SECRET": "live_secret_value",
            "KIS_ACCOUNT_NO": "",
            "KIS_ACCOUNT_PRODUCT_CODE": "01",
        }

        with self.assertRaises(KisUsConfigError) as raised:
            load_kis_us_config(env)

        message = str(raised.exception)
        self.assertIn("missing KIS_ACCOUNT_NO", message)
        self.assertNotIn("live_app_key_value", message)
        self.assertNotIn("live_secret_value", message)

    def test_loads_mock_only_config_with_default_base_url(self):
        cfg = load_kis_us_config(
            {
                "KIS_APP_KEY": "app",
                "KIS_APP_SECRET": "secret",
                "KIS_ACCOUNT_NO": "12345678",
                "KIS_ACCOUNT_PRODUCT_CODE": "01",
            }
        )

        self.assertEqual(cfg.mock_base_url, "https://openapivts.koreainvestment.com:29443")
        self.assertEqual(cfg.account_no, "12345678")

    def test_rejects_non_mock_base_url(self):
        with self.assertRaises(KisUsConfigError):
            load_kis_us_config(
                {
                    "KIS_APP_KEY": "app",
                    "KIS_APP_SECRET": "secret",
                    "KIS_ACCOUNT_NO": "12345678",
                    "KIS_ACCOUNT_PRODUCT_CODE": "01",
                    "KIS_MOCK_BASE_URL": "https://openapi.koreainvestment.com:9443",
                }
            )

    def test_rejects_spoofed_or_non_https_mock_base_url(self):
        base_env = {
            "KIS_APP_KEY": "app",
            "KIS_APP_SECRET": "secret",
            "KIS_ACCOUNT_NO": "12345678",
            "KIS_ACCOUNT_PRODUCT_CODE": "01",
        }
        for unsafe_url in [
            "http://openapivts.koreainvestment.com:29443",
            "https://openapivts.koreainvestment.com.evil.example",
            "https://evil.example/openapivts.koreainvestment.com",
        ]:
            with self.subTest(unsafe_url=unsafe_url):
                env = dict(base_env, KIS_MOCK_BASE_URL=unsafe_url)
                with self.assertRaises(KisUsConfigError):
                    load_kis_us_config(env)

    def test_rejects_hyphenated_account_or_product_code(self):
        base_env = {
            "KIS_APP_KEY": "app",
            "KIS_APP_SECRET": "secret",
            "KIS_ACCOUNT_NO": "1234-5678",
            "KIS_ACCOUNT_PRODUCT_CODE": "01",
        }
        with self.assertRaises(KisUsConfigError):
            load_kis_us_config(base_env)

        env = dict(base_env, KIS_ACCOUNT_NO="12345678", KIS_ACCOUNT_PRODUCT_CODE="1")
        with self.assertRaises(KisUsConfigError):
            load_kis_us_config(env)

    def test_redact_secret_masks_middle(self):
        self.assertEqual(redact_secret("abcdefgh"), "ab****gh")


if __name__ == "__main__":
    unittest.main()
