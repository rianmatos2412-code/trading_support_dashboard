"""
Candle Service

This module provides services for processing candle data.
"""
import pandas as pd
from typing import Optional
from data.repository import CandleRepository
from shared.config import STRATEGY_CANDLE_COUNT


class CandleService:
    """Service for processing candle data."""
    
    def __init__(self):
        """Initialize the candle service."""
        self.repository = CandleRepository()
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = None) -> Optional[pd.DataFrame]:
        """
        Get candles for a symbol and timeframe.
        
        Args:
            symbol: Symbol name (e.g., "BTCUSDT")
            timeframe: Timeframe (e.g., "4h", "30m", "1h")
            limit: Number of candles to fetch (defaults to STRATEGY_CANDLE_COUNT)
            
        Returns:
            DataFrame with candle data or None if not available
        """
        if limit is None:
            limit = STRATEGY_CANDLE_COUNT
        
        df = self.repository.get_candles(symbol, timeframe, limit)
        
        if df is None or len(df) == 0:
            return None
        
        return df
    
    def prepare_candles(self, df: Optional[pd.DataFrame], candle_count: int) -> Optional[pd.DataFrame]:
        """
        Extract and prepare the last N candles from a DataFrame.
        
        Args:
            df: DataFrame with OHLC data (newest first), or None
            candle_count: Number of candles to extract
            
        Returns:
            DataFrame with candles in chronological order (oldest first), or None if insufficient data
        """
        if df is None or len(df) == 0:
            return None
        
        if len(df) < candle_count:
            return None
        
        df_copy = df.copy()
        # Add the last row again (for processing)
        df_copy = pd.concat([df_copy, df_copy.tail(1)], axis=0, ignore_index=True)
        df_copy.dropna(inplace=True)
        df_copy = df_copy.iloc[:candle_count+1]
        return df_copy

