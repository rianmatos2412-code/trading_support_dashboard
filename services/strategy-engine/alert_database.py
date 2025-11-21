"""
Database Manager for Trading Alerts

This module handles all database operations for storing and retrieving trading alerts.
It checks for duplicate swing high/low pairs and tracks candle timestamps to detect new candles.
"""

import sqlite3
import os
from typing import List, Dict, Optional, Tuple


class AlertDatabase:
    """
    Manages database operations for trading alerts.
    Handles storage, retrieval, and duplicate detection for swing high/low pairs.
    """
    
    def __init__(self, db_path: str = "trading_alerts.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file (default: "trading_alerts.db")
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """
        Initialize the database and create tables if they don't exist.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                swing_low_idx INTEGER NOT NULL,
                swing_low_price REAL NOT NULL,
                swing_high_idx INTEGER NOT NULL,
                swing_high_price REAL NOT NULL,
                current_price REAL NOT NULL,
                entry_level REAL NOT NULL,
                sl REAL NOT NULL,
                tp1 REAL NOT NULL,
                tp2 REAL NOT NULL,
                tp3 REAL NOT NULL,
                approaching REAL NOT NULL,
                risk_score TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset, timeframe, swing_low_idx, swing_low_price, swing_high_idx, swing_high_price)
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_swing_pair 
            ON alerts(asset, timeframe, swing_low_idx, swing_low_price, swing_high_idx, swing_high_price)
        ''')
        
        # Create table to track last processed candle timestamps
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candle_timestamps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                last_candle_timestamp INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset, timeframe)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def swing_pair_exists(self, asset: str, timeframe: str, swing_low: Tuple, swing_high: Tuple) -> bool:
        """
        Check if a swing high/low pair already exists in the database.
        
        Args:
            asset: Asset symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "4h", "30m")
            swing_low: Tuple of (index, price) for swing low
            swing_high: Tuple of (index, price) for swing high
            
        Returns:
            True if the pair exists, False otherwise
        """
        if swing_low is None or swing_high is None:
            return False
        
        try:
            low_idx, low_price = swing_low[0], swing_low[1]
            high_idx, high_price = swing_high[0], swing_high[1]
        except (IndexError, TypeError):
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM alerts
            WHERE asset = ? 
            AND timeframe = ?
            AND swing_low_idx = ?
            AND ABS(swing_low_price - ?) < 0.01
            AND swing_high_idx = ?
            AND ABS(swing_high_price - ?) < 0.01
        ''', (asset, timeframe, int(low_idx), float(low_price), int(high_idx), float(high_price)))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def save_alerts(self, alerts: List[Dict], asset_symbol: str) -> Dict[str, int]:
        """
        Save alerts to database, skipping those that already exist.
        
        Args:
            alerts: List of alert dictionaries from _generate_alerts
            asset_symbol: Asset symbol (e.g., "BTCUSDT")
            
        Returns:
            Dictionary with counts: {'saved': int, 'skipped': int, 'errors': int}
        """
        if not alerts:
            return {'saved': 0, 'skipped': 0, 'errors': 0}
        
        saved_count = 0
        skipped_count = 0
        error_count = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for alert in alerts:
            try:
                timeframe = alert.get('timeframe', 'unknown')
                swing_low = alert.get('swing_low')
                swing_high = alert.get('swing_high')
                
                # Check if pair already exists
                if self.swing_pair_exists(asset_symbol, timeframe, swing_low, swing_high):
                    skipped_count += 1
                    continue
                
                # Extract swing low/high data
                if swing_low is None or swing_high is None:
                    error_count += 1
                    continue
                
                low_idx, low_price = swing_low[0], swing_low[1]
                high_idx, high_price = swing_high[0], swing_high[1]
                
                # Insert alert
                cursor.execute('''
                    INSERT INTO alerts (
                        asset, timeframe, alert_type,
                        swing_low_idx, swing_low_price,
                        swing_high_idx, swing_high_price,
                        current_price, entry_level,
                        sl, tp1, tp2, tp3,
                        approaching, risk_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    asset_symbol,
                    timeframe,
                    alert.get('type', 'unknown'),
                    int(low_idx),
                    float(low_price),
                    int(high_idx),
                    float(high_price),
                    float(alert.get('current_price', 0)),
                    float(alert.get('entry_level', 0)),
                    float(alert.get('sl', 0)),
                    float(alert.get('tp1', 0)),
                    float(alert.get('tp2', 0)),
                    float(alert.get('tp3', 0)),
                    float(alert.get('approaching', 0)),
                    str(alert.get('risk_score', 'none'))
                ))
                
                saved_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Error saving alert to database: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return {
            'saved': saved_count,
            'skipped': skipped_count,
            'errors': error_count
        }
    
    def update_candle_timestamp(self, asset: str, timeframe: str, candle_timestamp: int) -> bool:
        """
        Update the last processed candle timestamp for a given asset and timeframe.
        This helps track when new candles are generated.
        
        Args:
            asset: Asset symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "4h", "30m")
            candle_timestamp: Unix timestamp of the candle
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO candle_timestamps 
                (asset, timeframe, last_candle_timestamp, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (asset, timeframe, candle_timestamp))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating candle timestamp: {e}")
            return False
    
    def get_last_candle_timestamp(self, asset: str, timeframe: str) -> Optional[int]:
        """
        Get the last processed candle timestamp for a given asset and timeframe.
        
        Args:
            asset: Asset symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "4h", "30m")
            
        Returns:
            Unix timestamp of last processed candle, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_candle_timestamp 
                FROM candle_timestamps
                WHERE asset = ? AND timeframe = ?
            ''', (asset, timeframe))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting candle timestamp: {e}")
            return None
    
    def is_new_candle(self, asset: str, timeframe: str, current_candle_timestamp: int) -> bool:
        """
        Check if the current candle is new (hasn't been processed yet).
        
        Args:
            asset: Asset symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "4h", "30m")
            current_candle_timestamp: Unix timestamp of the current candle
            
        Returns:
            True if this is a new candle, False otherwise
        """
        last_timestamp = self.get_last_candle_timestamp(asset, timeframe)
        
        if last_timestamp is None:
            return True  # First time processing, consider it new
        
        return current_candle_timestamp > last_timestamp
    
    def save_strategy_results(self, result: Dict, asset_symbol: str, 
                             df_4h=None, df_30m=None) -> Dict[str, Dict[str, int]]:
        """
        Save strategy results (alerts) to database, checking for new candles and existing pairs.
        This is the main function to call after executing the strategy.
        
        Args:
            result: Result dictionary from execute_strategy containing 'alerts_4h' and 'alerts_30m'
            asset_symbol: Asset symbol (e.g., "BTCUSDT")
            df_4h: Optional DataFrame with 4H candles (to extract latest timestamp)
            df_30m: Optional DataFrame with 30M candles (to extract latest timestamp)
            
        Returns:
            Dictionary with summary: {
                '4h': {'saved': int, 'skipped': int, 'errors': int},
                '30m': {'saved': int, 'skipped': int, 'errors': int}
            }
        """
        summary = {
            '4h': {'saved': 0, 'skipped': 0, 'errors': 0},
            '30m': {'saved': 0, 'skipped': 0, 'errors': 0}
        }
        
        # Process 4H alerts
        alerts_4h = result.get('alerts_4h', [])
        if alerts_4h:
            # Check if we have a new 4H candle
            should_process_4h = True
            if df_4h is not None and len(df_4h) > 0:
                try:
                    # Get the latest candle timestamp (after get_candle, latest is at iloc[-1])
                    # get_candle reverses the dataframe, so the last row is the most recent
                    latest_4h_timestamp = int(df_4h.iloc[-1]['unix'])
                    should_process_4h = self.is_new_candle(asset_symbol, '4h', latest_4h_timestamp)
                    
                    if should_process_4h:
                        self.update_candle_timestamp(asset_symbol, '4h', latest_4h_timestamp)
                except (KeyError, IndexError, ValueError) as e:
                    print(f"Warning: Could not extract 4H candle timestamp: {e}")
            
            if should_process_4h:
                summary['4h'] = self.save_alerts(alerts_4h, asset_symbol)
            else:
                summary['4h'] = {'saved': 0, 'skipped': len(alerts_4h), 'errors': 0}
        
        # Process 30M alerts
        alerts_30m = result.get('alerts_30m', [])
        if alerts_30m:
            # Check if we have a new 30M candle
            should_process_30m = True
            if df_30m is not None and len(df_30m) > 0:
                try:
                    # Get the latest candle timestamp (after get_candle, latest is at iloc[-1])
                    # get_candle reverses the dataframe, so the last row is the most recent
                    latest_30m_timestamp = int(df_30m.iloc[-1]['unix'])
                    should_process_30m = self.is_new_candle(asset_symbol, '30m', latest_30m_timestamp)
                    
                    if should_process_30m:
                        self.update_candle_timestamp(asset_symbol, '30m', latest_30m_timestamp)
                except (KeyError, IndexError, ValueError) as e:
                    print(f"Warning: Could not extract 30M candle timestamp: {e}")
            
            if should_process_30m:
                summary['30m'] = self.save_alerts(alerts_30m, asset_symbol)
            else:
                summary['30m'] = {'saved': 0, 'skipped': len(alerts_30m), 'errors': 0}
        
        return summary

