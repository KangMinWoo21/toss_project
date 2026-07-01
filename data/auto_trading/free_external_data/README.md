# Free External Data Seed

This directory is a local CSV-only seed for the US paper-only auto-trading engine.

The rows are not investment-grade data. They exist to validate the data pipeline,
schema, audit logging, paper-only order plan columns, and local-only execution
contract. Replace them with refreshed exports from free sources before relying on
the risk features.

Expected source families:

- `factors.csv`: SEC EDGAR-derived or manually imported factor proxy fields.
- `short_sale_volume.csv`: FINRA Daily Short Sale Volume import.
- `news_sentiment.csv`: GDELT or Alpha Vantage news sentiment import.
- `listing_status.csv`: Alpha Vantage listing status or Nasdaq Trader symbol directory import.

`python -m backtester auto-paper-run --external-data-dir data/auto_trading/free_external_data`
must remain paper-only, dry-run, and local CSV only.

Refresh command:

```powershell
python scripts/fetch_us_free_external_data.py `
  --symbols SPY,QQQ,AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA `
  --output-dir data/auto_trading/free_external_data `
  --alpha-vantage-key YOUR_ALPHA_VANTAGE_KEY `
  --cik-map data/auto_trading/us_cik_map.csv `
  --finra-date 20260630
```
