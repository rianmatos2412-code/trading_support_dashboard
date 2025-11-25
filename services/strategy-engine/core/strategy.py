"""
Trading Strategy Implementation

This module implements a trading strategy using the StrategyInterface class.
It orchestrates the complete workflow from data fetching to alert generation.
The strategy only executes when new 4H or 30M candles are detected.
"""
from core.strategy_interface import StrategyInterface
from alerts.database import AlertDatabase


class RunStrategy:
    """
    Trading strategy that combines swing highs/lows, support/resistance,
    and Fibonacci levels to generate trading signals.
    
    The strategy automatically checks for new candles and only executes
    when new 4H or 30M candles are detected.
    """
    
    def __init__(self):
        """Initialize the strategy with default StrategyInterface parameters."""
        self.strategy = StrategyInterface()
        # Initialize database manager
        self.db = AlertDatabase()
    
    def _get_latest_candle_timestamp(self, df):
        """
        Extract the latest candle timestamp from a DataFrame.
        
        Args:
            df: DataFrame with candle data (should have 'unix' column)
            
        Returns:
            Unix timestamp as integer, or None if not available
        """
        if df is None or len(df) == 0:
            return None
        
        try:
            # Get the latest candle (last row after get_candle reverses)
            latest_timestamp = int(df.iloc[-1]['unix'])
            return latest_timestamp
        except (KeyError, IndexError, ValueError, TypeError) as e:
            return None
    
    def execute_strategy(self, df_4h, df_30m, df_1h, asset_symbol="OTHER"):
        """
        Execute the complete trading strategy workflow.
        Only executes when new 4H or 30M candles are detected.
        
        Args:
            df_4h: DataFrame with 4H candle data
            df_30m: DataFrame with 30m candle data
            df_1h: DataFrame with 1H candle data
            asset_symbol: Asset symbol for pruning score (default: "OTHER")
            
        Returns:
            Dictionary containing:
            - 'executed': bool - True if strategy was executed, False if skipped
            - 'reason': str - Reason for execution or skip
            - 'new_candles': dict - Information about new candles detected
            - 'result': dict - Strategy results (alerts_4h, alerts_30m) if executed, None otherwise
            - 'db_summary': dict - Database save summary if executed, None otherwise
        """
        # Execute the strategy
        strategy_result = self.strategy.execute_strategy(
            df_4h, df_30m, df_1h, asset_symbol
        )
        
        # Get processed candles for timestamp extraction
        candles_4h_df = self.strategy.get_candle(df_4h, 200) if df_4h is not None else None
        candles_30m_df = self.strategy.get_candle(df_30m, 200) if df_30m is not None else None
        
        # Save results to database
        db_summary = self.save_strategy_results(
            strategy_result, asset_symbol, candles_4h_df, candles_30m_df
        )
        
        return {
            'executed': True,
            'reason': 'Strategy executed successfully',
            'new_candles': {},
            'result': strategy_result,
            'db_summary': db_summary
        }
    
    def save_strategy_results(self, result, asset_symbol, df_4h=None, df_30m=None):
        """
        Save strategy results (alerts) to database, checking for new candles and existing pairs.
        This is a convenience wrapper around AlertDatabase.save_strategy_results.
        
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
        return self.db.save_strategy_results(result, asset_symbol, df_4h, df_30m)

