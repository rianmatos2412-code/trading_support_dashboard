"""
Support and Resistance Level Detection

This module provides functions to detect support and resistance levels in price data.
Support levels are price points where the price tends to bounce upward.
Resistance levels are price points where the price tends to bounce downward.
"""
from typing import List, Tuple
import pandas as pd
import sys
import os

# Import the original support_resistance module from parent directory
# We need to import from the root level support_resistance.py
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)
import support_resistance as sr_module


def get_support_resistance_levels(
    timeframe_ticker_df: pd.DataFrame, 
    high_timeframe_flag: bool,
    sensible_window: int = 2
) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Calculate support and resistance levels from the DataFrame.
    
    Args:
        timeframe_ticker_df: pandas DataFrame with OHLC data
        high_timeframe_flag: If True, uses open/close for HTF analysis. If False, uses low/high for LTF analysis.
        sensible_window: Number of candles to check after the candidate level (default: 2)
            
    Returns:
        Tuple of (support_level_list, resistance_level_list) where each list contains
        tuples of (index, price)
    """
    support_level_list = []
    resistance_level_list = []
    
    # Input validation
    if timeframe_ticker_df is None or not hasattr(timeframe_ticker_df, '__len__'):
        return support_level_list, resistance_level_list
    
    if len(timeframe_ticker_df) < 4:  # Need at least 4 rows for range(3, len-1) to work
        return support_level_list, resistance_level_list
    
    # Check required columns exist
    required_columns = ['low', 'high']
    if not all(col in timeframe_ticker_df.columns for col in required_columns):
        return support_level_list, resistance_level_list
            
    # backward 3, forward sensible_window
    for sens_row in range(3, len(timeframe_ticker_df) - 1):
        try:
            # Check for support level
            support_result = sr_module.support(
                timeframe_ticker_df, 
                sens_row, 
                3,  # before_candle_count
                sensible_window,  # after_candle_count
                high_timeframe_flag
            )
            if support_result is True:
                support_level_list.append((sens_row, float(timeframe_ticker_df.low[sens_row])))
            
            # Check for resistance level
            resistance_result = sr_module.resistance(
                timeframe_ticker_df, 
                sens_row, 
                3,  # before_candle_count
                sensible_window,  # after_candle_count
                high_timeframe_flag
            )
            if resistance_result is True:
                resistance_level_list.append((sens_row, float(timeframe_ticker_df.high[sens_row])))
                
        except (KeyError, IndexError, TypeError) as e:
            # Skip this row if there's an error accessing the data
            continue
        
    return support_level_list, resistance_level_list
