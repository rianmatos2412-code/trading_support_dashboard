"""
Data Repository for Candle Data

This module provides a clean interface for accessing candle data from the database.
"""
import pandas as pd
from typing import Optional
from sqlalchemy import text
import sys
import os

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.database import SessionLocal


class CandleRepository:
    """Repository for accessing candle data from the database."""
    
    @staticmethod
    def get_candles(symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """
        Fetch candles from database and return as DataFrame.
        
        Args:
            symbol: Symbol name (e.g., "BTCUSDT")
            timeframe: Timeframe (e.g., "4h", "30m", "1h")
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with columns: unix, open, high, low, close, volume
        """
        try:
            db = SessionLocal()
            try:
                query = text("""
                    SELECT 
                        EXTRACT(EPOCH FROM oc.timestamp)::BIGINT as unix,
                        oc.open,
                        oc.high,
                        oc.low,
                        oc.close,
                        oc.volume
                    FROM ohlcv_candles oc
                    INNER JOIN symbols s ON oc.symbol_id = s.symbol_id
                    INNER JOIN timeframe t ON oc.timeframe_id = t.timeframe_id
                    WHERE s.symbol_name = :symbol
                    AND t.tf_name = :timeframe
                    ORDER BY oc.timestamp DESC
                    LIMIT :limit
                """)
                
                result = db.execute(query, {"symbol": symbol, "timeframe": timeframe, "limit": limit})
                rows = result.fetchall()
                
                if not rows:
                    return pd.DataFrame()
                
                # Convert to DataFrame
                df = pd.DataFrame(rows, columns=['unix', 'open', 'high', 'low', 'close', 'volume'])
                # Reverse to get chronological order (oldest first)
                df = df.iloc[::-1].reset_index(drop=True)
                
                return df
            finally:
                db.close()
        except Exception as e:
            # Return empty DataFrame on error
            return pd.DataFrame()

