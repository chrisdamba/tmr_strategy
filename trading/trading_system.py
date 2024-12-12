import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pandas as pd
import requests
import json
import os
from urllib.parse import urljoin

from tmr_strategy.trading.position_manager import PositionManager
from tmr_strategy.trading.risk_manager import RiskManager
from tmr_strategy.trading.stock_screener import StockScreener

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


############################################
# Config Manager
############################################

class ConfigManager:
    def __init__(self, config_path: str):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def get(self, key: str, default=None):
        return self.config.get(key, default)


############################################
# Rate Limiter
############################################

class RateLimiter:
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = threading.Lock()

    def wait(self):
        now = time.time()
        with self._lock:
            self.requests = [req for req in self.requests if now - req < self.time_window]
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
            self.requests.append(now)


class IBWebClient:
    def __init__(self, base_url: str, session_token: Optional[str] = None):
        self.base_url = base_url
        self.session = requests.Session()
        if session_token:
            self.session.headers.update({"Authorization": f"Bearer {session_token}"})
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

        self.authenticated = False
        self.last_auth_check = None
        self.auth_check_interval = timedelta(minutes=30)

        # Rate limiters
        self.global_limiter = RateLimiter(max_requests=50, time_window=1.0)
        self.endpoint_limiters = {
            "/iserver/marketdata/history": RateLimiter(max_requests=10, time_window=1.0),
            "/iserver/secdef/search": RateLimiter(max_requests=5, time_window=1.0)
        }

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                      data: Optional[Dict] = None, check_auth: bool = True) -> Dict:
        self.global_limiter.wait()
        if endpoint in self.endpoint_limiters:
            self.endpoint_limiters[endpoint].wait()

        if check_auth:
            self._ensure_authenticated()
        url = urljoin(self.base_url, endpoint)
        response = None
        try:
            response = self.session.request(method, url, params=params, json=data if data else None)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response is not None and response.status_code == 401:
                self.authenticated = False
            raise

    def _ensure_authenticated(self):
        now = datetime.now()
        if (not self.authenticated or not self.last_auth_check or (
                now - self.last_auth_check > self.auth_check_interval)):
            try:
                self._make_request("GET", "/tickle", check_auth=False)
                self.authenticated = True
                self.last_auth_check = now
            except:
                self._authenticate()

    def _authenticate(self):
        # Implement actual authentication if needed
        pass

    def get_historical_data(self, conid: str, duration="1Y", bar_size="1d") -> pd.DataFrame:
        endpoint = "/iserver/marketdata/history"
        params = {"conid": conid, "period": duration, "bar": bar_size, "outsideRth": True}
        data = self._make_request("GET", endpoint, params=params)
        df = pd.DataFrame(data.get('data', []))
        if not df.empty:
            df['Date'] = pd.to_datetime(df['t'], unit='ms')
            df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
            df = df.set_index('Date')
        return df

    def get_positions(self, account_id: str) -> List[Dict]:
        endpoint = f"/portfolio/{account_id}/positions"
        return self._make_request("GET", endpoint)

    def get_account_summary(self, account_id: str) -> Dict:
        endpoint = f"/portfolio/{account_id}/summary"
        return self._make_request("GET", endpoint)

    def place_order(self, account_id: str, order_data: Dict) -> Dict:
        endpoint = f"/iserver/account/{account_id}/orders"
        return self._make_request("POST", endpoint, data=order_data)

    def get_executions(self, account_id: str, from_date: Optional[str] = None) -> List[Dict]:
        endpoint = f"/iserver/account/{account_id}/executions"
        params = {"from": from_date} if from_date else None
        return self._make_request("GET", endpoint, params=params)

    def search_symbol(self, symbol: str) -> List[Dict]:
        endpoint = "/iserver/secdef/search"
        data = {"symbol": symbol}
        return self._make_request("POST", endpoint, data=data)


############################################
# Symbol Resolver
############################################

class SymbolResolver:
    def __init__(self, ib_client: IBWebClient):
        self.ib_client = ib_client
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = timedelta(days=1)
        self._lock = threading.Lock()

    def get_conid(self, symbol: str) -> str:
        with self._lock:
            now = datetime.now()
            if symbol in self.cache and (now - self.cache_time[symbol] < self.cache_duration):
                return self.cache[symbol]

            try:
                response = self.ib_client.search_symbol(symbol)
                for contract in response:
                    if (contract.get('type') == 'STK' and
                            contract.get('currency') == 'USD' and
                            contract.get('exchange') in ['SMART', 'NYSE', 'NASDAQ']):
                        self.cache[symbol] = contract['conid']
                        self.cache_time[symbol] = now
                        return contract['conid']
                raise ValueError(f"Could not find suitable conid for symbol: {symbol}")
            except Exception as e:
                logger.error(f"Error resolving symbol {symbol}: {str(e)}")
                raise


def log_metrics(metrics, cycle_duration):
    logger.info(f"Metrics: {metrics}, cycle_duration={cycle_duration:.2f}s")


def run_trading_cycle(screener, risk_manager, position_manager, ib_client, account_id, tickers):
    cycle_start = time.time()
    metrics = {
        'signals_generated': 0,
        'orders_placed': 0,
        'errors': 0
    }

    # Placeholder: Fetch market data for each ticker
    universe_data = {}
    for ticker in tickers:
        try:
            conid = ib_client.search_symbol(ticker)
            if conid:
                # assuming first returned conid is correct
                conid_val = conid[0]['conid']
                df = ib_client.get_historical_data(conid_val)
                if not df.empty:
                    universe_data[ticker] = df
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            metrics['errors'] += 1

    # Screen for signals
    signals = screener.screen_universe(universe_data)
    # Count signals
    total_signals = 0
    for (buy, sell) in signals.values():
        total_signals += len(buy) + len(sell)
    metrics['signals_generated'] = total_signals

    # Risk checks and placing orders
    # This is placeholder logic, actual order placement should be done
    # similarly to execute_trades function from previous code
    # Just updating metrics['orders_placed'] as an example
    # You would integrate execute_trades logic here
    metrics['orders_placed'] = 0  # once orders placed, increment this

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

    # Load config.json
    with open("/app/config.json", "r") as f:
        config = json.load(f)
    screener_params = config.get("screener_params", {})
    screener_params["profit_threshold"] = profit_threshold
    screener_params["min_price"] = min_price

    risk_manager = RiskManager(max_drawdown, max_position_size)
    position_manager = PositionManager(max_positions, allocation_per_trade)
    screener = StockScreener(params=screener_params)

    # Setup IBWebClient and environment
    ib_base_url = "https://localhost:5055/v1/api"  # gateway endpoint
    ib_client = IBWebClient(base_url=ib_base_url)

    retry_count = 1
    while True:
        try:
            run_trading_cycle(screener, risk_manager, position_manager, ib_client, account_id, tickers)
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
