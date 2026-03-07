"""Signal detection: breakout & mean reversion signals with option strategy mapping."""

import logging
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import yfinance as yf

from scanner import config
from scanner.indicators import compute_all_indicators, calc_weekly_trend

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def crossover(series: pd.Series, level: pd.Series) -> pd.Series:
    """Detect crossover: series crosses above level."""
    return (series > level) & (series.shift(1) <= level)


def crossunder(series: pd.Series, level: pd.Series) -> pd.Series:
    """Detect crossunder: series crosses below level."""
    return (series < level) & (series.shift(1) >= level)


# ── Signal Detection ──────────────────────────────────────────────────────────

def detect_breakout_signals(df: pd.DataFrame, mode: str = "Aggressive") -> pd.DataFrame:
    """Detect breakout signals (squeeze → debit strategy)."""
    df = df.copy()

    if mode == "Aggressive":
        df["bull_breakout"] = (
            df["is_squeeze"]
            & df["bull_trend"]
            & df["bbw_rising"]
            & crossover(df["close"], df["bb_basis"])
            & (df["rsi"] > config.RSI_BREAK_UP)
        )
        df["bear_breakout"] = (
            df["is_squeeze"]
            & df["bear_trend"]
            & df["bbw_rising"]
            & crossunder(df["close"], df["bb_basis"])
            & (df["rsi"] < config.RSI_BREAK_DN)
        )
    else:  # Normal
        df["bull_breakout"] = (
            df["is_squeeze"]
            & df["bull_trend"]
            & crossover(df["close"], df["bb_upper"])
            & (df["rsi"] > config.RSI_BREAK_UP)
        )
        df["bear_breakout"] = (
            df["is_squeeze"]
            & df["bear_trend"]
            & crossunder(df["close"], df["bb_lower"])
            & (df["rsi"] < config.RSI_BREAK_DN)
        )
    return df


def detect_meanrev_signals(df: pd.DataFrame, mode: str = "Aggressive") -> pd.DataFrame:
    """Detect mean reversion signals (expansion → credit strategy)."""
    df = df.copy()

    if mode == "Aggressive":
        df["bull_mean_rev"] = (
            df["is_expansion"]
            & df["bull_trend"]
            & (~df["bbw_rising"])
            & (df["rsi"] < 40)
        )
        df["bear_mean_rev"] = (
            df["is_expansion"]
            & df["bear_trend"]
            & (~df["bbw_rising"])
            & (df["rsi"] > 60)
        )
    else:  # Normal
        df["bull_mean_rev"] = (
            df["is_expansion"]
            & df["bull_trend"]
            & crossover(df["close"], df["bb_lower"])
            & (df["rsi"] < config.RSI_OVERSOLD)
        )
        df["bear_mean_rev"] = (
            df["is_expansion"]
            & df["bear_trend"]
            & crossunder(df["close"], df["bb_upper"])
            & (df["rsi"] > config.RSI_OVERBOUGHT)
        )
    return df


# ── IV Rank ───────────────────────────────────────────────────────────────────

def get_iv_rank(ticker: str, df: pd.DataFrame) -> tuple[Optional[float], Optional[float]]:
    """Get IV rank from options chain, fallback to HV rank.

    Returns:
        (iv_percent, iv_rank) or (hv_percent, hv_rank) as fallback.
    """
    # Try real IV from options chain
    try:
        stock = yf.Ticker(ticker)
        price = stock.fast_info.last_price
        expirations = stock.options
        if expirations:
            target_date = datetime.now() + timedelta(days=25)
            valid_exp = None
            for exp in expirations:
                exp_date = datetime.strptime(exp, "%Y-%m-%d")
                if exp_date >= target_date:
                    valid_exp = exp
                    break
            if valid_exp:
                chain = stock.option_chain(valid_exp)
                ivs = []
                for opt_df in [chain.calls, chain.puts]:
                    if "impliedVolatility" in opt_df.columns and "strike" in opt_df.columns:
                        opt_df = opt_df.copy()
                        opt_df["dist"] = (opt_df["strike"] - price).abs()
                        atm = opt_df.nsmallest(3, "dist")
                        for iv in atm["impliedVolatility"].dropna():
                            if 0.01 < iv < 10.0:
                                ivs.append(iv)
                if ivs:
                    iv_pct = float(np.median(ivs)) * 100
                    return (round(iv_pct, 1), None)  # IV rank needs historical data
    except Exception:
        pass

    # Fallback: HV Rank (always available)
    try:
        returns = df["close"].pct_change().dropna()
        if len(returns) < 30:
            return (None, None)
        hv = returns.rolling(30).std() * (252 ** 0.5) * 100
        hv_current = hv.iloc[-1]
        hv_min = hv.min()
        hv_max = hv.max()
        if hv_max == hv_min:
            return (round(float(hv_current), 1), 50.0)
        hv_rank = (hv_current - hv_min) / (hv_max - hv_min) * 100
        return (round(float(hv_current), 1), round(float(hv_rank), 1))
    except Exception:
        return (None, None)


# ── Confirmation Logic ────────────────────────────────────────────────────────

def get_confirmation(
    signal_type: str,
    signal_direction: str,
    last_row: pd.Series,
) -> tuple[bool, list[str]]:
    """Check TTM squeeze + momentum alignment for signal confirmation.

    Returns:
        (is_confirmed, detail_list) where detail_list has items like '✓ squeeze' or '✗ momentum'.
    """
    details: list[str] = []
    squeeze_ok = False
    momentum_ok = False

    ttm_squeeze_on = bool(last_row.get("ttm_squeeze_on", False))
    ttm_squeeze_off = bool(last_row.get("ttm_squeeze_off", False))
    ttm_dir = str(last_row.get("ttm_momentum_dir", "FLAT"))

    if signal_type == "BREAKOUT":
        squeeze_ok = ttm_squeeze_on or ttm_squeeze_off
        if signal_direction == "BULLISH":
            momentum_ok = ttm_dir == "UP"
        else:
            momentum_ok = ttm_dir == "DOWN"
        details.append(f"{'✓' if squeeze_ok else '✗'} squeeze")
        details.append(f"{'✓' if momentum_ok else '✗'} momentum")
        return (squeeze_ok and momentum_ok, details)
    else:  # MEAN_REV
        if signal_direction == "BULLISH":
            momentum_ok = ttm_dir == "UP"
        else:
            momentum_ok = ttm_dir == "DOWN"
        details.append(f"{'✓' if momentum_ok else '✗'} momentum")
        return (momentum_ok, details)


# ── Option Strategy Mapping ───────────────────────────────────────────────────

OPTION_STRATEGIES = {
    ("BREAKOUT", "BULLISH"): ("Debit Call", f"{config.DTE_DEBIT_MIN}-{config.DTE_DEBIT_MAX} DTE"),
    ("BREAKOUT", "BEARISH"): ("Debit Put", f"{config.DTE_DEBIT_MIN}-{config.DTE_DEBIT_MAX} DTE"),
    ("MEAN_REV", "BULLISH"): ("Credit Put", f"{config.DTE_CREDIT_MIN}-{config.DTE_CREDIT_MAX} DTE"),
    ("MEAN_REV", "BEARISH"): ("Credit Call", f"{config.DTE_CREDIT_MIN}-{config.DTE_CREDIT_MAX} DTE"),
}


# ── Build Signal Dict ─────────────────────────────────────────────────────────

def detect_signals_for_ticker(
    ticker: str,
    df: pd.DataFrame,
    df_weekly: Optional[pd.DataFrame],
    mode: str = "Aggressive",
    use_ema_filter: bool = False,
) -> Optional[dict]:
    """Process a single ticker: compute indicators, detect signals, build output dict.

    Returns signal dict if a signal is found on the last bar, else None.
    """
    try:
        df = compute_all_indicators(df, use_ema_filter)
        df = detect_breakout_signals(df, mode)
        df = detect_meanrev_signals(df, mode)

        last = df.iloc[-1]

        # Determine which signal fired on the last bar
        signal_type: Optional[str] = None
        signal_direction: Optional[str] = None

        if last.get("bull_breakout", False):
            signal_type, signal_direction = "BREAKOUT", "BULLISH"
        elif last.get("bear_breakout", False):
            signal_type, signal_direction = "BREAKOUT", "BEARISH"
        elif last.get("bull_mean_rev", False):
            signal_type, signal_direction = "MEAN_REV", "BULLISH"
        elif last.get("bear_mean_rev", False):
            signal_type, signal_direction = "MEAN_REV", "BEARISH"

        if signal_type is None:
            return None

        # Weekly trend
        weekly_info = calc_weekly_trend(df_weekly)

        # IV Rank
        iv, iv_rank = get_iv_rank(ticker, df)

        # Confirmation
        confirmed, confirm_details = get_confirmation(signal_type, signal_direction, last)

        # Option strategy
        opt_strategy, dte_range = OPTION_STRATEGIES.get(
            (signal_type, signal_direction), ("N/A", "N/A")
        )

        # Regime
        if last.get("is_squeeze", False):
            regime = "SQUEEZE"
        elif last.get("is_expansion", False):
            regime = "EXPANSION"
        else:
            regime = "NEUTRAL"

        # Score
        score = float(last["score_breakout"]) if signal_type == "BREAKOUT" else float(last["score_meanrev"])

        # Patterns
        patterns: list[str] = []
        if last.get("ttm_squeeze_on", False):
            patterns.append("TTM Squeeze")
        if last.get("ttm_squeeze_off", False):
            patterns.append("Squeeze Fired")
        if last.get("combo_diverge", False):
            patterns.append("Divergence")
        if last.get("bbw_rising", False) and last.get("is_squeeze", False):
            patterns.append("Squeeze Expanding")

        # Sparkline: last 30 close prices
        sparkline = df["close"].tail(30).tolist()

        return {
            "ticker": ticker,
            "signal_type": signal_type,
            "signal_direction": signal_direction,
            "option_strategy": opt_strategy,
            "dte_range": dte_range,
            "regime": regime,
            "score": round(score, 1),
            "last_price": round(float(last["close"]), 2),
            "rsi": round(float(last["rsi"]), 1) if not np.isnan(last["rsi"]) else None,
            "bbw_pct": round(float(last["bbw_pct"]), 1) if not np.isnan(last["bbw_pct"]) else None,
            "atr_pct": round(float(last["atr_pct"]), 2) if not np.isnan(last["atr_pct"]) else None,
            "iv": iv,
            "iv_rank": iv_rank,
            "bull_trend": bool(last.get("bull_trend", False)),
            "patterns": ", ".join(patterns) if patterns else "",
            "divergence": bool(last.get("combo_diverge", False)),
            "ttm_squeeze_on": bool(last.get("ttm_squeeze_on", False)),
            "ttm_squeeze_off": bool(last.get("ttm_squeeze_off", False)),
            "ttm_momentum_dir": str(last.get("ttm_momentum_dir", "FLAT")),
            "ttm_hist_color": str(last.get("ttm_hist_color", "flat")),
            "weekly_trend": weekly_info["weekly_trend"],
            "weekly_rsi": weekly_info["weekly_rsi"],
            "sparkline": sparkline,
            "confirmed": confirmed,
            "confirm_details": confirm_details,
        }
    except Exception as e:
        logger.error(f"{ticker}: signal detection error: {e}")
        return None
