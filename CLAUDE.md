# BM-screener

Stock scanner that detects breakout and mean reversion signals across S&P 500, Nasdaq 100, DOW 30 and custom tickers.

## Project structure

```
scanner/
  main.py            # Flask server + CLI entry point (port 5050)
  scanner.py          # Orchestrator, parallel scanning with ThreadPoolExecutor
  data_fetcher.py     # Ticker lists (Wikipedia + fallback) + yfinance OHLCV
  indicators.py       # Technical indicators (BB, ATR, RSI, EMA, Stochastic, MACD, TTM Squeeze)
  signals.py          # Signal detection (Breakout/MeanRev) + IV rank + option strategy mapping
  dashboard_generator.py  # Single-file HTML dashboard generation (embedded CSS/JS)
  excel_exporter.py   # XLSX export with formatting
  notifier.py         # Telegram notifications
  config.py           # All tunable parameters (thresholds, periods, paths)
tickers_custom.txt    # Custom ticker list (supports # comments)
docs/manifest.json    # PWA manifest
```

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Run with web server
python -m scanner.main

# Static HTML generation only
python -m scanner.main --static

# Options
python -m scanner.main --mode Aggressive --ema --port 5050
```

Always use `python -m scanner.main` (not `python scanner/main.py`) to avoid circular import issues.

## Key API routes

- `GET /` — Serve dashboard HTML
- `POST /run_scan` — Execute scan (params: mode, ema, lists)
- `GET /scan_single?ticker=AAPL` — Scan single ticker
- `GET /download_excel` — Download XLSX results
- `GET /health` — Health check

## Environment variables

See `.env.example`. Key vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DASHBOARD_URL`.

## Conventions

- Language: Python 3.11+
- Web framework: Flask
- Data: pandas DataFrames, yfinance for market data
- Config: All magic numbers and thresholds live in `config.py`
- Dashboard: Single self-contained HTML file with inline CSS/JS
- Git: Never commit `.env`. Output files in `output/` are gitignored but `docs/index.html` is force-added for GitHub Pages.
- GitHub Actions: Automated scans commit results to `docs/index.html`
