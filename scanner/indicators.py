"""Technical indicators: BB, ATR, RSI, EMA, Stochastic, MACD, TTM Squeeze, combo scores."""

import logging
from typing import Optional

import pandas as pd
import numpy as np

from scanner import config

logger = logging.getLogger(__name__)


# ── Utilities ─────────────────────────────────────────────────────────────────

def rolling_percentile(series: pd.Series, window: int = 100) -> pd.Series:
    """Fast rolling percentile using numpy loop (NOT rolling().apply())."""
    arr = series.to_numpy(dtype=float)
    result = np.full(len(arr), np.nan)
    for i in range(window - 1, len(arr)):
        window_data = arr[i - window + 1 : i + 1]
        valid = window_data[~np.isnan(window_data)]
        if len(valid) > 0 and not np.isnan(arr[i]):
            result[i] = (np.sum(valid <= arr[i]) / len(valid)) * 100
    return pd.Series(result, index=series.index)


def normalize_minmax(series: pd.Series, window: int = 100) -> pd.Series:
    """Rolling min-max normalization to [-50, +50] range."""
    roll_min = series.rolling(window, min_periods=1).min()
    roll_max = series.rolling(window, min_periods=1).max()
    denom = roll_max - roll_min
    denom = denom.replace(0, np.nan)
    normalized = ((series - roll_min) / denom - 0.5) * 100
    return normalized.fillna(0.0)


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def calc_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Bollinger Bands, BBW%, percentile, squeeze/expansion flags."""
    df = df.copy()
    close = df["close"]
    df["bb_basis"] = close.rolling(config.BB_LENGTH).mean()
    std = close.rolling(config.BB_LENGTH).std()
    df["bb_upper"] = df["bb_basis"] + config.BB_STD * std
    df["bb_lower"] = df["bb_basis"] - config.BB_STD * std
    df["bbw"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_basis"] * 100
    df["bbw_pct"] = rolling_percentile(df["bbw"], config.BBW_LOOKBACK)
    df["is_squeeze"] = df["bbw_pct"] < 20
    df["is_expansion"] = df["bbw_pct"] > 80
    df["bbw_rising"] = df["bbw"] > df["bbw"].shift(1)
    return df


# ── ATR ───────────────────────────────────────────────────────────────────────

def calc_atr(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate ATR, ATR% of price, and ATR percentile."""
    df = df.copy()
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(span=config.ATR_LENGTH, adjust=False).mean()
    df["atr_pct"] = df["atr"] / close * 100
    df["atr_pct_rank"] = rolling_percentile(df["atr_pct"], config.BBW_LOOKBACK)
    return df


# ── RSI ───────────────────────────────────────────────────────────────────────

def calc_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate RSI using Wilder's smoothing (EMA with com=period-1)."""
    df = df.copy()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=config.RSI_LENGTH - 1, min_periods=config.RSI_LENGTH).mean()
    avg_loss = loss.ewm(com=config.RSI_LENGTH - 1, min_periods=config.RSI_LENGTH).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


# ── EMA Trend Filter ─────────────────────────────────────────────────────────

def calc_ema_trend(df: pd.DataFrame, use_ema_filter: bool = True) -> pd.DataFrame:
    """Calculate EMA 50/200 trend filter."""
    df = df.copy()
    close = df["close"]
    df["ema_fast"] = close.ewm(span=config.EMA_FAST, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=config.EMA_SLOW, adjust=False).mean()
    if use_ema_filter:
        df["bull_trend"] = close > df["ema_slow"]
        df["bear_trend"] = close < df["ema_slow"]
    else:
        df["bull_trend"] = True
        df["bear_trend"] = True
    return df


# ── Stochastic ────────────────────────────────────────────────────────────────

def calc_stochastic(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Stochastic %K and %D."""
    df = df.copy()
    low_min = df["low"].rolling(config.STOCH_K).min()
    high_max = df["high"].rolling(config.STOCH_K).max()
    denom = high_max - low_min
    denom = denom.replace(0, np.nan)
    raw_k = (df["close"] - low_min) / denom * 100
    df["stoch_k"] = raw_k.rolling(config.STOCH_D).mean()
    df["stoch_d"] = df["stoch_k"].rolling(config.STOCH_D).mean()
    return df


# ── MACD ──────────────────────────────────────────────────────────────────────

def calc_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate MACD line, signal line, and histogram."""
    df = df.copy()
    ema_fast = df["close"].ewm(span=config.MACD_FAST, adjust=False).mean()
    ema_slow = df["close"].ewm(span=config.MACD_SLOW, adjust=False).mean()
    df["macd_line"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd_line"].ewm(span=config.MACD_SIGNAL, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]
    return df


# ── Combo Scores ──────────────────────────────────────────────────────────────

def calc_combo_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate volatility/momentum sub-scores and breakout/meanrev scores."""
    df = df.copy()

    # Sub1: volatility
    atr_norm = normalize_minmax(df["atr_pct"], config.COMBO_NORM_PERIOD)
    bbw_norm = normalize_minmax(df["bbw"], config.COMBO_NORM_PERIOD)
    df["sub1_volatility"] = atr_norm * config.ATR_WEIGHT + bbw_norm * config.BBW_WEIGHT

    # Sub2: momentum
    stoch_norm = (df["stoch_k"] - 50) / 100 * 100
    rsi_norm = (df["rsi"] - 50) / 100 * 100
    macd_norm = normalize_minmax(df["macd_hist"], config.COMBO_NORM_PERIOD)
    df["sub2_momentum"] = (
        stoch_norm * config.STOCH_WEIGHT
        + rsi_norm * config.RSI_WEIGHT
        + macd_norm * config.MACD_WEIGHT
    )

    # Normalize momentum to 0-100 for score formulas
    mom_min = df["sub2_momentum"].rolling(config.COMBO_NORM_PERIOD, min_periods=1).min()
    mom_max = df["sub2_momentum"].rolling(config.COMBO_NORM_PERIOD, min_periods=1).max()
    mom_range = mom_max - mom_min
    mom_range = mom_range.replace(0, np.nan)
    momentum_0_100 = ((df["sub2_momentum"] - mom_min) / mom_range * 100).fillna(50)

    # Breakout Score: deep squeeze + strong momentum = better breakout candidate
    bbw_pct = df["bbw_pct"].fillna(50)
    atr_pct = df["atr_pct_rank"].fillna(50)
    df["score_breakout"] = (
        (100 - bbw_pct) * 0.40
        + (100 - atr_pct) * 0.30
        + momentum_0_100 * 0.30
    ).clip(0, 100)

    # MeanRev Score: expansion + reversal
    df["score_meanrev"] = (
        bbw_pct * 0.35
        + atr_pct * 0.25
        + momentum_0_100 * 0.40
    ).clip(0, 100)

    # Divergence: volatility rising but momentum not following
    sub1_rising = df["sub1_volatility"] > df["sub1_volatility"].shift(1)
    sub2_rising = df["sub2_momentum"] > df["sub2_momentum"].shift(1)
    df["combo_diverge"] = sub1_rising & ~sub2_rising

    return df


# ── TTM Squeeze ───────────────────────────────────────────────────────────────

def calc_ttm_squeeze(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate TTM Squeeze (John Carter): BB vs Keltner Channel comparison."""
    df = df.copy()
    close, high, low = df["close"], df["high"], df["low"]

    # Keltner Channel: EMA(20) ± 1.5 * ATR(20)
    kc_mid = close.ewm(span=20, adjust=False).mean()
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    kc_atr = tr.ewm(span=20, adjust=False).mean()
    kc_upper = kc_mid + 1.5 * kc_atr
    kc_lower = kc_mid - 1.5 * kc_atr

    # Squeeze detection: BB inside KC
    squeeze_on = (df["bb_lower"] > kc_lower) & (df["bb_upper"] < kc_upper)
    df["ttm_squeeze_on"] = squeeze_on

    # Squeeze fired: previous bar was squeeze, current is not
    # IMPORTANT: use numpy concatenate, NOT shift().fillna(False) on bool
    squeeze_on_prev = pd.Series(
        np.concatenate([[False], squeeze_on.values[:-1]]),
        index=squeeze_on.index, dtype=bool
    )
    df["ttm_squeeze_off"] = (~squeeze_on) & squeeze_on_prev

    # Momentum histogram
    highest_high = high.rolling(20).max()
    lowest_low = low.rolling(20).min()
    mid_val = (highest_high + lowest_low) / 2
    delta = close - (mid_val + kc_mid) / 2
    momentum = delta.ewm(span=20, adjust=False).mean()
    df["ttm_momentum"] = momentum

    # Momentum direction
    mom_prev = pd.Series(
        np.concatenate([[np.nan], momentum.values[:-1]]),
        index=momentum.index
    )
    conditions = [
        momentum > mom_prev,
        momentum < mom_prev,
    ]
    choices = ["UP", "DOWN"]
    df["ttm_momentum_dir"] = np.select(conditions, choices, default="FLAT")

    # Histogram color
    mom_rising = momentum > mom_prev
    mom_falling = momentum <= mom_prev
    colors = np.where(
        momentum > 0,
        np.where(mom_rising, "lime", "green"),
        np.where(mom_falling, "red", "maroon")
    )
    df["ttm_hist_color"] = colors

    return df


# ── Weekly Trend ──────────────────────────────────────────────────────────────

def calc_weekly_trend(df_weekly: Optional[pd.DataFrame]) -> dict:
    """Calculate weekly RSI and EMA(200) trend from weekly DataFrame."""
    result = {"weekly_trend": "N/A", "weekly_rsi": None}
    if df_weekly is None or len(df_weekly) < 30:
        return result

    df_weekly = df_weekly.copy()

    # Weekly RSI
    delta = df_weekly["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=config.RSI_LENGTH - 1, min_periods=config.RSI_LENGTH).mean()
    avg_loss = loss.ewm(com=config.RSI_LENGTH - 1, min_periods=config.RSI_LENGTH).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    weekly_rsi = 100 - (100 / (1 + rs))
    result["weekly_rsi"] = round(float(weekly_rsi.iloc[-1]), 1) if not np.isnan(weekly_rsi.iloc[-1]) else None

    # Weekly EMA(200) trend with ±1% buffer
    if len(df_weekly) >= 200:
        ema200 = df_weekly["close"].ewm(span=200, adjust=False).mean()
        last_close = df_weekly["close"].iloc[-1]
        last_ema = ema200.iloc[-1]
        pct_diff = (last_close - last_ema) / last_ema * 100
        if pct_diff > 1:
            result["weekly_trend"] = "Bullish"
        elif pct_diff < -1:
            result["weekly_trend"] = "Bearish"
        else:
            result["weekly_trend"] = "Neutral"
    else:
        # Not enough data for EMA 200, use shorter-term assessment
        ema50 = df_weekly["close"].ewm(span=min(50, len(df_weekly)), adjust=False).mean()
        last_close = df_weekly["close"].iloc[-1]
        last_ema = ema50.iloc[-1]
        if last_close > last_ema * 1.01:
            result["weekly_trend"] = "Bullish"
        elif last_close < last_ema * 0.99:
            result["weekly_trend"] = "Bearish"
        else:
            result["weekly_trend"] = "Neutral"

    return result


# ── Master Function ───────────────────────────────────────────────────────────

def compute_all_indicators(df: pd.DataFrame, use_ema_filter: bool = True) -> pd.DataFrame:
    """Compute all technical indicators on a daily OHLCV DataFrame."""
    df = calc_bollinger_bands(df)
    df = calc_atr(df)
    df = calc_rsi(df)
    df = calc_ema_trend(df, use_ema_filter)
    df = calc_stochastic(df)
    df = calc_macd(df)
    df = calc_combo_scores(df)
    df = calc_ttm_squeeze(df)
    return df
