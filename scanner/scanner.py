"""Scanner orchestrator: parallel ticker processing and full scan execution."""

import logging
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from scanner import config
from scanner.data_fetcher import get_all_tickers, fetch_ticker_data
from scanner.signals import detect_signals_for_ticker

logger = logging.getLogger(__name__)


def get_ticker_signal(
    ticker: str,
    mode: str = "Aggressive",
    use_ema_filter: bool = False,
) -> Optional[dict]:
    """Process a single ticker: fetch data → compute indicators → detect signals.

    Returns signal dict if found, else None.
    """
    data = fetch_ticker_data(ticker)
    if data is None:
        return None
    df_daily, df_weekly = data
    return detect_signals_for_ticker(ticker, df_daily, df_weekly, mode, use_ema_filter)


def run_scan(
    mode: str = "Aggressive",
    use_ema_filter: bool = False,
    use_sp500: bool = True,
    use_nasdaq: bool = True,
    use_dow: bool = True,
    use_custom: bool = True,
    max_workers: int = config.MAX_WORKERS,
) -> dict:
    """Run full scan across all enabled ticker lists.

    Returns dict with keys: signals, total_tickers, scan_time, errors.
    """
    start_time = time.time()
    errors: list[str] = []

    # Get ticker list
    logger.info(f"Fetching ticker lists (SP500={use_sp500}, NASDAQ={use_nasdaq}, DOW={use_dow}, Custom={use_custom})")
    tickers = get_all_tickers(use_sp500, use_nasdaq, use_dow, use_custom)
    total_tickers = len(tickers)
    if total_tickers == 0:
        logger.error("No tickers found! Check your internet connection and ticker sources.")
        return {"signals": [], "total_tickers": 0, "scan_time": 0, "errors": ["No tickers found"], "mode": mode, "use_ema_filter": use_ema_filter}
    logger.info(f"Scanning {total_tickers} tickers in {mode} mode (EMA filter: {use_ema_filter}, lookback: {config.SIGNAL_LOOKBACK} bars)")

    signals: list[dict] = []
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_ticker_signal, t, mode, use_ema_filter): t
            for t in tickers
        }
        for future in as_completed(futures):
            ticker = futures[future]
            done += 1
            try:
                result = future.result()
                if result is not None:
                    signals.append(result)
                if done % 100 == 0 or done == total_tickers:
                    logger.info(f"Processed {done}/{total_tickers} ({len(signals)} signals found)")
            except Exception as e:
                errors.append(f"{ticker}: {str(e)}")
                logger.error(f"{ticker}: scan error: {e}")

    # Sort by score descending
    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    scan_time = round(time.time() - start_time, 1)
    logger.info(f"Scan complete: {len(signals)} signals from {total_tickers} tickers in {scan_time}s")

    return {
        "signals": signals,
        "total_tickers": total_tickers,
        "scan_time": scan_time,
        "errors": errors,
        "mode": mode,
        "use_ema_filter": use_ema_filter,
    }
