"""Data fetching module: ticker lists from Wikipedia + OHLCV data via yfinance."""

import ssl
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import numpy as np
import yfinance as yf

from scanner import config

# Fix SSL for macOS Python 3.13 (missing certificates)
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

# Fallback ticker lists when Wikipedia scraping fails
_FALLBACK_SP500 = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEP",
    "AIG", "ALL", "AMAT", "AMD", "AMGN", "AMP", "AMZN", "ANET", "ANSS", "AON",
    "APD", "APH", "AVGO", "AXP", "BA", "BAC", "BDX", "BK", "BKNG", "BLK",
    "BMY", "BRK-B", "BSX", "C", "CAT", "CB", "CCI", "CDNS", "CEG", "CHTR",
    "CI", "CL", "CMCSA", "CME", "CMG", "COP", "COST", "CRM", "CSCO", "CTAS",
    "CVS", "CVX", "D", "DE", "DHR", "DIS", "DLR", "DOW", "DUK", "ECL",
    "EL", "EMR", "EOG", "EQR", "ETN", "EW", "EXC", "F", "FCX", "FDX",
    "FI", "FICO", "GD", "GE", "GILD", "GM", "GOOG", "GOOGL", "GPN", "GS",
    "HD", "HON", "HSY", "HUM", "IBM", "ICE", "INTC", "INTU", "ISRG", "ITW",
    "JNJ", "JPM", "KHC", "KLAC", "KO", "LIN", "LLY", "LMT", "LOW", "LRCX",
    "MA", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MMC",
    "MMM", "MO", "MPC", "MRK", "MS", "MSCI", "MSFT", "MSI", "MU", "NEE",
    "NFLX", "NKE", "NOC", "NOW", "NSC", "NVDA", "ORCL", "ORLY", "OXY", "PANW",
    "PCAR", "PEP", "PFE", "PG", "PGR", "PH", "PLTR", "PM", "PNC", "PSA",
    "PSX", "PYPL", "QCOM", "REGN", "ROP", "ROST", "RTX", "SBUX", "SCHW", "SHW",
    "SLB", "SMCI", "SNPS", "SO", "SPG", "SRE", "SYK", "SYY", "T", "TDG",
    "TGT", "TJX", "TMO", "TMUS", "TRV", "TSLA", "TSN", "TT", "TXN", "UNH",
    "UNP", "UPS", "URI", "USB", "V", "VLO", "VRTX", "VZ", "WBA", "WFC",
    "WM", "WMT", "XEL", "XOM", "ZTS",
]

_FALLBACK_NASDAQ100 = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN",
    "AMZN", "ANSS", "APP", "ARM", "ASML", "AVGO", "AZN", "BIIB", "BKNG", "BKR",
    "CDNS", "CDW", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CTAS",
    "CTSH", "DASH", "DDOG", "DLTR", "DXCM", "EA", "EXC", "FANG", "FAST", "FTNT",
    "GEHC", "GFS", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "ILMN", "INTC", "INTU",
    "ISRG", "KDP", "KHC", "KLAC", "LRCX", "LULU", "MAR", "MCHP", "MDB", "MDLZ",
    "MELI", "META", "MNST", "MRVL", "MSFT", "MU", "NFLX", "NVDA", "NXPI", "ODFL",
    "ON", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PYPL", "QCOM", "REGN",
    "ROP", "ROST", "SBUX", "SMCI", "SNPS", "TEAM", "TMUS", "TSLA", "TTD", "TTWO",
    "TXN", "VRSK", "VRTX", "WBD", "WDAY", "XEL", "ZS",
]

_FALLBACK_DOW30 = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "DOW", "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "WMT",
]


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance DataFrame: fix MultiIndex, lowercase columns, flatten."""
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns and isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    return df


def fetch_sp500_tickers() -> list[str]:
    """Fetch S&P 500 ticker list from Wikipedia, with fallback to hardcoded list."""
    try:
        tables = pd.read_html(config.SP500_URL)
        df = tables[0]
        tickers = df["Symbol"].dropna().astype(str).str.strip().tolist()
        # Fix tickers with dots (BRK.B -> BRK-B for yfinance)
        tickers = [t.replace(".", "-") for t in tickers]
        if len(tickers) > 50:
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers from Wikipedia")
            return tickers
        logger.warning(f"Wikipedia returned only {len(tickers)} S&P 500 tickers, using fallback")
    except Exception as e:
        logger.warning(f"Wikipedia S&P 500 fetch failed: {e}")
    logger.info(f"Using fallback S&P 500 list ({len(_FALLBACK_SP500)} tickers)")
    return list(_FALLBACK_SP500)


def fetch_nasdaq100_tickers() -> list[str]:
    """Fetch Nasdaq 100 ticker list from Wikipedia, with fallback to hardcoded list."""
    try:
        tables = pd.read_html(config.NASDAQ100_URL)
        for table in tables:
            if "Ticker" in table.columns:
                tickers = table["Ticker"].dropna().astype(str).str.strip().tolist()
                tickers = [t.replace(".", "-") for t in tickers]
                if len(tickers) > 20:
                    logger.info(f"Fetched {len(tickers)} Nasdaq 100 tickers from Wikipedia")
                    return tickers
        logger.warning("Nasdaq 100: no valid table found, using fallback")
    except Exception as e:
        logger.warning(f"Wikipedia Nasdaq 100 fetch failed: {e}")
    logger.info(f"Using fallback Nasdaq 100 list ({len(_FALLBACK_NASDAQ100)} tickers)")
    return list(_FALLBACK_NASDAQ100)


def fetch_dow30_tickers() -> list[str]:
    """Fetch Dow Jones 30 ticker list from Wikipedia, with fallback to hardcoded list."""
    try:
        tables = pd.read_html(config.DOW30_URL)
        for table in tables:
            if "Symbol" in table.columns:
                tickers = table["Symbol"].dropna().astype(str).str.strip().tolist()
                tickers = [t.replace(".", "-") for t in tickers]
                if len(tickers) > 10:
                    logger.info(f"Fetched {len(tickers)} Dow 30 tickers from Wikipedia")
                    return tickers
        logger.warning("Dow 30: no valid table found, using fallback")
    except Exception as e:
        logger.warning(f"Wikipedia Dow 30 fetch failed: {e}")
    logger.info(f"Using fallback Dow 30 list ({len(_FALLBACK_DOW30)} tickers)")
    return list(_FALLBACK_DOW30)


def load_custom_tickers(filepath: str = "tickers_custom.txt") -> list[str]:
    """Load custom tickers from file, supporting inline comments."""
    tickers: list[str] = []
    if not os.path.exists(filepath):
        logger.warning(f"Custom tickers file not found: {filepath}")
        return tickers
    try:
        with open(filepath, "r") as f:
            for line in f:
                ticker = line.split("#")[0].strip()
                if ticker:
                    tickers.append(ticker.upper())
        logger.info(f"Loaded {len(tickers)} custom tickers")
    except Exception as e:
        logger.error(f"Failed to load custom tickers: {e}")
    return tickers


def get_all_tickers(
    use_sp500: bool = True,
    use_nasdaq: bool = True,
    use_dow: bool = True,
    use_custom: bool = True,
) -> list[str]:
    """Combine and deduplicate tickers from all enabled sources."""
    all_tickers: list[str] = []
    if use_sp500:
        all_tickers.extend(fetch_sp500_tickers())
    if use_nasdaq:
        all_tickers.extend(fetch_nasdaq100_tickers())
    if use_dow:
        all_tickers.extend(fetch_dow30_tickers())
    if use_custom:
        all_tickers.extend(load_custom_tickers())
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in all_tickers:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    logger.info(f"Total unique tickers: {len(unique)}")
    return unique


def fetch_ohlcv(
    ticker: str, period: str = "1y", interval: str = "1d"
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a single ticker via yfinance."""
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df = _normalize_df(df)
        min_bars = 60 if interval == "1d" else 20
        if len(df) < min_bars:
            logger.warning(f"{ticker}: only {len(df)} bars ({interval}), need {min_bars}")
            return None
        return df
    except Exception as e:
        logger.error(f"{ticker}: fetch error ({interval}): {e}")
        return None


def fetch_ticker_data(ticker: str) -> Optional[tuple[pd.DataFrame, Optional[pd.DataFrame]]]:
    """Fetch both daily and weekly data for a single ticker."""
    df_daily = fetch_ohlcv(ticker, period="1y", interval="1d")
    if df_daily is None:
        return None
    df_weekly = fetch_ohlcv(ticker, period="2y", interval="1wk")
    return (df_daily, df_weekly)


def fetch_all_ohlcv(
    tickers: list[str], max_workers: int = 20
) -> dict[str, tuple[pd.DataFrame, Optional[pd.DataFrame]]]:
    """Fetch OHLCV data for all tickers in parallel using ThreadPoolExecutor."""
    results: dict[str, tuple[pd.DataFrame, Optional[pd.DataFrame]]] = {}
    total = len(tickers)
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_ticker_data, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            done += 1
            try:
                result = future.result()
                if result is not None:
                    results[ticker] = result
                    if done % 50 == 0 or done == total:
                        logger.info(f"Fetched {done}/{total} tickers ({len(results)} valid)")
            except Exception as e:
                logger.error(f"{ticker}: unexpected error: {e}")

    logger.info(f"Fetch complete: {len(results)}/{total} tickers with valid data")
    return results
