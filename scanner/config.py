"""Configuration constants for the stock scanner."""

# ── Ticker Lists ──────────────────────────────────────────────────────────────
USE_SP500: bool = True
USE_NASDAQ100: bool = True
USE_DOW: bool = True
USE_CUSTOM: bool = True

# ── Scanner Defaults ──────────────────────────────────────────────────────────
DEFAULT_MODE: str = "Aggressive"
USE_EMA_FILTER: bool = False
MAX_WORKERS: int = 20
SIGNAL_LOOKBACK: int = 3  # Check last N bars for signals (not just the last bar)

# ── Bollinger Bands ───────────────────────────────────────────────────────────
BB_LENGTH: int = 20
BB_STD: float = 2.0
BBW_LOOKBACK: int = 100

# ── ATR ───────────────────────────────────────────────────────────────────────
ATR_LENGTH: int = 14

# ── RSI ───────────────────────────────────────────────────────────────────────
RSI_LENGTH: int = 14
RSI_BREAK_UP: int = 52
RSI_BREAK_DN: int = 48
RSI_OVERBOUGHT: int = 65
RSI_OVERSOLD: int = 35

# ── EMA ───────────────────────────────────────────────────────────────────────
EMA_FAST: int = 50
EMA_SLOW: int = 200

# ── Stochastic ────────────────────────────────────────────────────────────────
STOCH_K: int = 14
STOCH_D: int = 3

# ── MACD ──────────────────────────────────────────────────────────────────────
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9

# ── Combo Score Weights ───────────────────────────────────────────────────────
ATR_WEIGHT: float = 0.5
BBW_WEIGHT: float = 0.5
STOCH_WEIGHT: float = 0.33
RSI_WEIGHT: float = 0.33
MACD_WEIGHT: float = 0.33
COMBO_NORM_PERIOD: int = 100
SIGNAL_MA_FAST: int = 5
SIGNAL_MA_SLOW: int = 9

# ── Options DTE ───────────────────────────────────────────────────────────────
DTE_DEBIT_MIN: int = 30
DTE_DEBIT_MAX: int = 60
DTE_CREDIT_MIN: int = 7
DTE_CREDIT_MAX: int = 21

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR: str = "output"
DASHBOARD_FILE: str = "output/dashboard.html"
EXCEL_FILE: str = "output/scanner_results.xlsx"

# ── Wikipedia URLs ────────────────────────────────────────────────────────────
SP500_URL: str = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL: str = "https://en.wikipedia.org/wiki/Nasdaq-100"
DOW30_URL: str = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_PORT: int = 5050

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_REPO: str = "6000rr4n/BM-screener-mobile"
DASHBOARD_URL: str = "https://6000rr4n.github.io/BM-screener-mobile/"
