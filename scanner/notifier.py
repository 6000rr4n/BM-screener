"""Telegram notification sender for scan results."""

import os
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")


def send_scan_notification(signals: list[dict[str, Any]], scan_info: dict[str, Any]) -> bool:
    """Send scan summary to Telegram.

    Args:
        signals: List of signal dicts from the scanner.
        scan_info: Dict with total_tickers, scan_time, mode, etc.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info("Telegram not configured (no TELEGRAM_BOT_TOKEN/CHAT_ID), skipping notification")
        return False

    total = len(signals)
    if total == 0:
        text = (
            "📊 *Stock Scanner*\n"
            f"_{scan_info.get('mode', 'Aggressive')} mode | "
            f"{scan_info.get('total_tickers', 0)} tickers | "
            f"{scan_info.get('scan_time', 0):.0f}s_\n\n"
            "Nema signala danas."
        )
    else:
        bullish = sum(1 for s in signals if s.get("signal_direction") == "BULLISH")
        bearish = sum(1 for s in signals if s.get("signal_direction") == "BEARISH")
        breakout = sum(1 for s in signals if s.get("signal_type") == "BREAKOUT")
        meanrev = sum(1 for s in signals if s.get("signal_type") == "MEAN_REV")

        # Top 5 signals by score
        top = sorted(signals, key=lambda s: s.get("score", 0), reverse=True)[:5]
        top_lines = []
        for s in top:
            arrow = "🟢" if s.get("signal_direction") == "BULLISH" else "🔴"
            price = s.get("last_price", 0)
            rsi = s.get("rsi")
            rsi_str = f"{rsi:.0f}" if rsi is not None else "-"
            score = s.get("score", 0)
            top_lines.append(
                f"{arrow} *{s['ticker']}* ${price:.2f} | "
                f"{s.get('signal_type', '?')} | Score: {score:.0f} | RSI: {rsi_str}"
            )

        text = (
            f"📊 *Stock Scanner*\n"
            f"_{scan_info.get('mode', 'Aggressive')} mode | "
            f"{scan_info.get('total_tickers', 0)} tickers | "
            f"{scan_info.get('scan_time', 0):.0f}s_\n\n"
            f"*{total}* signala: {bullish} bullish, {bearish} bearish\n"
            f"Breakout: {breakout} | Mean Rev: {meanrev}\n\n"
            f"*Top signali:*\n" + "\n".join(top_lines)
        )

    if DASHBOARD_URL:
        text += f"\n\n[Otvori Dashboard]({DASHBOARD_URL})"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Telegram notification failed: {e}")
        return False
