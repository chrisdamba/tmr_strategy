import os
import time
import logging
from trading.risk_manager import RiskManager
from trading.position_manager import PositionManager
from trading.stock_screener import StockScreener

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/trading.log')
    ]
)

logger = logging.getLogger(__name__)


def log_metrics(metrics, cycle_duration):
    # Log metrics and cycle duration
    logger.info(f"Metrics: {metrics}, cycle_duration={cycle_duration:.2f}s")


def run_trading_cycle(screener, risk_manager, position_manager):
    cycle_start = time.time()
    metrics = {
        'signals_generated': 0,
        'orders_placed': 0,
        'errors': 0
    }

    # TODO: implement actual trading logic here
    # Fetch market data via gateway
    signals = screener.screen_universe(data)
    metrics['signals_generated'] = len(...) # count signals
    # risk checks with risk_manager
    # place orders with position_manager
    metrics['orders_placed'] = number_of_orders

    cycle_duration = time.time() - cycle_start
    log_metrics(metrics, cycle_duration)


def main():
    account_id = os.environ.get("IBKR_ACCOUNT_ID")
    check_interval = int(os.environ.get("TRADING_CHECK_INTERVAL", "60"))
    max_positions = int(os.environ.get("MAX_POSITIONS", "10"))
    allocation_per_trade = float(os.environ.get("ALLOCATION_PER_TRADE", "1000"))
    max_drawdown = float(os.environ.get("MAX_DRAWDOWN", "0.2"))
    max_position_size = float(os.environ.get("MAX_POSITION_SIZE", "0.1"))
    tickers = os.environ.get("TICKERS", "AAPL,MSFT").split(",")
    profit_threshold = float(os.environ.get("PROFIT_THRESHOLD", "2.0"))
    min_price = float(os.environ.get("MIN_PRICE", "5.0"))

    import json
    with open("/app/config.json", "r") as f:
        config = json.load(f)
    screener_params = config.get("screener_params", {})
    screener_params["profit_threshold"] = profit_threshold
    screener_params["min_price"] = min_price

    risk_manager = RiskManager(max_drawdown, max_position_size)
    position_manager = PositionManager(max_positions, allocation_per_trade)
    screener = StockScreener(params=screener_params)

    retry_count = 1
    while True:
        try:
            run_trading_cycle(screener, risk_manager, position_manager)
            retry_count = 1  # reset on success
        except Exception as e:
            logger.error(f"Trading cycle failed: {str(e)}", exc_info=True)
            # Exponential backoff with max 300s
            backoff = min(300, retry_count * 30)
            time.sleep(backoff)
            retry_count += 1

        time.sleep(check_interval)


if __name__ == "__main__":
    main()
