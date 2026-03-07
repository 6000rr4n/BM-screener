"""Flask server + CLI entry point for the stock scanner."""

import argparse
import logging
import os
import sys
import webbrowser

from flask import Flask, request, jsonify, send_file, Response

from scanner import config
from scanner.scanner import run_scan, get_ticker_signal
from scanner.dashboard_generator import generate_dashboard
from scanner.excel_exporter import export_to_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global state for last scan results
_last_scan: dict = {"signals": [], "total_tickers": 0, "scan_time": 0, "mode": "Aggressive", "use_ema_filter": False}
_last_html: str = ""


def _run_and_store(
    mode: str = "Aggressive",
    use_ema: bool = False,
    use_sp500: bool = True,
    use_nasdaq: bool = True,
    use_dow: bool = True,
    use_custom: bool = True,
) -> dict:
    """Run scan and store results globally."""
    global _last_scan, _last_html
    result = run_scan(
        mode=mode,
        use_ema_filter=use_ema,
        use_sp500=use_sp500,
        use_nasdaq=use_nasdaq,
        use_dow=use_dow,
        use_custom=use_custom,
    )
    _last_scan = result
    _last_html = generate_dashboard(result["signals"], result)

    # Export to Excel
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    export_to_excel(result["signals"], config.EXCEL_FILE)

    return result


@app.route("/")
def index() -> Response:
    """Serve the dashboard HTML."""
    return Response(_last_html, mimetype="text/html")


@app.route("/health")
def health() -> Response:
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/run_scan", methods=["POST"])
def run_scan_endpoint() -> Response:
    """Run a new scan with parameters from request JSON."""
    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode", config.DEFAULT_MODE)
    use_ema = data.get("use_ema", config.USE_EMA_FILTER)
    use_sp500 = data.get("use_sp500", config.USE_SP500)
    use_nasdaq = data.get("use_nasdaq", config.USE_NASDAQ100)
    use_dow = data.get("use_dow", config.USE_DOW)
    use_custom = data.get("use_custom", config.USE_CUSTOM)

    logger.info(f"POST /run_scan: mode={mode}, ema={use_ema}")
    result = _run_and_store(mode, use_ema, use_sp500, use_nasdaq, use_dow, use_custom)
    return jsonify({
        "status": "ok",
        "total_signals": len(result["signals"]),
        "total_tickers": result["total_tickers"],
        "scan_time": result["scan_time"],
    })


@app.route("/scan_single")
def scan_single() -> Response:
    """Scan a single ticker."""
    ticker = request.args.get("ticker", "").strip().upper()
    mode = request.args.get("mode", config.DEFAULT_MODE)
    use_ema = request.args.get("use_ema", "false").lower() == "true"

    if not ticker:
        return jsonify({"error": "ticker required"}), 400

    logger.info(f"GET /scan_single: {ticker} mode={mode}")
    result = get_ticker_signal(ticker, mode, use_ema)
    if result is None:
        return jsonify({"error": f"No signal for {ticker}"}), 404

    # Add to current signals and regenerate
    global _last_scan, _last_html
    # Remove old entry for same ticker if exists
    _last_scan["signals"] = [s for s in _last_scan["signals"] if s["ticker"] != ticker]
    _last_scan["signals"].insert(0, result)
    _last_html = generate_dashboard(_last_scan["signals"], _last_scan)

    return jsonify({"status": "ok", "signal": result})


@app.route("/download_excel")
def download_excel() -> Response:
    """Download the Excel file."""
    if os.path.exists(config.EXCEL_FILE):
        return send_file(
            os.path.abspath(config.EXCEL_FILE),
            as_attachment=True,
            download_name="scanner_results.xlsx",
        )
    return jsonify({"error": "No Excel file available"}), 404


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Stock Scanner")
    parser.add_argument("--static", action="store_true", help="Generate static HTML only (no server)")
    parser.add_argument("--mode", default=config.DEFAULT_MODE, choices=["Aggressive", "Normal"])
    parser.add_argument("--ema", action="store_true", default=config.USE_EMA_FILTER)
    parser.add_argument("--port", type=int, default=config.FLASK_PORT)
    args = parser.parse_args()

    logger.info("Starting stock scanner...")
    result = _run_and_store(mode=args.mode, use_ema=args.ema)
    logger.info(f"Found {len(result['signals'])} signals")

    # Save dashboard HTML
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(config.DASHBOARD_FILE, "w") as f:
        f.write(_last_html)
    logger.info(f"Dashboard saved to {config.DASHBOARD_FILE}")

    if args.static:
        logger.info("Static mode: exiting without starting server")
        sys.exit(0)

    # Start Flask server
    logger.info(f"Starting Flask server on http://localhost:{args.port}")
    webbrowser.open(f"http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
