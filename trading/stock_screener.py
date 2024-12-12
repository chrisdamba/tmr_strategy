import logging
import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional, Tuple


class StockScreener:
    def __init__(self, params: Optional[Dict] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.params = params or {
            'channel_period': 252,
            'channel_break_window': 10,
            'atr_period': 5,
            'atr_multiple': 1,
            'min_volume': 100000,
            'profit_threshold': 2.0,
            'min_price': 5.0
        }

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        if len(df) < self.params['channel_period']:
            raise ValueError(f"Insufficient data length: need at least {self.params['channel_period']} bars.")
        if df[required_columns].isnull().any().any():
            self.logger.warning("Data contains NaNs, forward-filling.")
            df = df.ffill()
        return df

    def compute_bars_since(self, condition: pd.Series) -> np.ndarray:
        condition = condition.fillna(False)
        bars_since = np.full(len(condition), np.nan)
        last_true = -1
        for i, val in enumerate(condition):
            if val:
                last_true = i
                bars_since[i] = 0
            else:
                if last_true != -1:
                    bars_since[i] = i - last_true
        return bars_since

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_index()
        df['HHV_252'] = df['Close'].rolling(self.params['channel_period']).max()
        df['LLV_252'] = df['Close'].rolling(self.params['channel_period']).min()
        df['ATR_5'] = ta.atr(df['High'], df['Low'], df['Close'], length=self.params['atr_period'])
        df['ROC_1'] = (df['Close'] / df['Close'].shift(1) - 1) * 100
        df['Diff'] = (df['HHV_252'] - df['LLV_252']) / 4.0
        df['BuyZone'] = df['LLV_252'] + (df['Diff'] * 3)
        breakout_condition = df['Close'] > df['HHV_252'].shift(1)
        df['BarsSinceBreakout'] = self.compute_bars_since(breakout_condition)
        df['Vol_MA_20'] = df['Volume'].rolling(20).mean()
        df['NoGapDown'] = df['Open'] > df['Low'].shift(1)
        df['PriceFilter'] = df['Close'] > self.params['min_price']
        df['LimitPrice'] = df['Low'].shift(1) - df['ATR_5'].shift(1) * self.params['atr_multiple']
        df['StopLoss'] = df['LimitPrice'] - df['ATR_5']
        return df

    def check_buy_conditions(self, df: pd.DataFrame) -> pd.Series:
        return ((df['ROC_1'] < -2) &
                (df['Close'] < df['BuyZone']) &
                (df['BarsSinceBreakout'] < self.params['channel_break_window']) &
                (df['NoGapDown']) &
                (df['Vol_MA_20'] > self.params['min_volume']) &
                (df['PriceFilter']))

    def check_sell_conditions(self, df: pd.DataFrame) -> pd.Series:
        sell_trigger_price = df['BuyZone'] * (1 + self.params['profit_threshold'] / 100.0)
        return ((df['Close'] > sell_trigger_price) | (df['Close'] < df['StopLoss']))

    def process_single_stock(self, ticker: str, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        try:
            df = self.validate_data(df)
            df = self.compute_indicators(df)
            buy_signals = df[self.check_buy_conditions(df)].copy()
            sell_signals = df[self.check_sell_conditions(df)].copy()
            return buy_signals, sell_signals
        except Exception as e:
            self.logger.error(f"Error processing {ticker}: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    def screen_universe(self, universe_data: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
        results = {}
        for ticker, df in universe_data.items():
            buy_signals, sell_signals = self.process_single_stock(ticker, df)
            results[ticker] = (buy_signals, sell_signals)
        return results

