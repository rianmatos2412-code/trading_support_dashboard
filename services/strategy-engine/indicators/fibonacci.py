"""
Fibonacci Level Calculation

This module provides functions to calculate Fibonacci retracement and extension levels
from swing highs and lows.
"""
from typing import List, Tuple, Optional
from core.models import FibResult
from config.settings import StrategyConfig


def calculate_fibonacci_levels(
    swing_highs: List[Tuple[int, float]], 
    swing_lows: List[Tuple[int, float]], 
    timeframe: str,
    config: StrategyConfig
) -> List[FibResult]:
    """
    Calculate Fibonacci levels from swing highs and lows.
    
    Args:
        swing_highs: List of (datetime, price) tuples for swing highs
        swing_lows: List of (datetime, price) tuples for swing lows
        timeframe: Timeframe string (e.g., "4h", "30m")
        config: StrategyConfig instance with Fibonacci level parameters
        
    Returns:
        List of FibResult objects with calculated Fibonacci levels
    """
    output: List[FibResult] = []
    
    # Input validation
    if not isinstance(swing_lows, (list, tuple)) or not swing_lows:
        return output
    
    if not isinstance(swing_highs, (list, tuple)):
        swing_highs = []
    
    if not isinstance(timeframe, str):
        timeframe = ""
    
    # Pre-validate and filter swing highs for efficiency
    valid_highs = []
    for swing_high in swing_highs:
        if not isinstance(swing_high, (list, tuple)) or len(swing_high) < 2:
            continue
        try:
            h_dt, h_price = swing_high[0], swing_high[1]
            # Validate datetime and price are numeric and price is positive
            if isinstance(h_dt, (int, float)) and isinstance(h_price, (int, float)) and h_price > 0:
                valid_highs.append((int(h_dt), float(h_price)))
        except (IndexError, TypeError, ValueError):
            continue
    
    # Sort valid highs by datetime for efficient searching
    valid_highs.sort(key=lambda x: x[0])
    
    # Process each swing low
    for swing_low in swing_lows:
        # Validate swing_low structure
        if not isinstance(swing_low, (list, tuple)) or len(swing_low) < 2:
            continue
        
        try:
            low_dt, low_price = swing_low[0], swing_low[1]
        except (IndexError, TypeError):
            continue
        
        # Validate datetime and price
        if not isinstance(low_dt, (int, float)) or not isinstance(low_price, (int, float)):
            continue
        
        low_dt = int(low_dt)
        low_price = float(low_price)
        
        # Validate price is positive
        if low_price <= 0:
            continue
        
        # Find RIGHT HIGH (later in time - after this low)
        # This is the first swing high that occurs after this low
        right_high = None
        for h_dt, h_price in valid_highs:
            if h_dt > low_dt:  # Compare datetime, not index
                right_high = (h_dt, h_price)
                # Found the first high after the low, can break
                break
        
        # Find LEFT HIGH (earlier in time - before this low)
        # This is the last swing high that occurs before this low (nearest to the low)
        left_high = None
        for h_dt, h_price in valid_highs:
            if h_dt < low_dt:  # Compare datetime, not index
                left_high = (h_dt, h_price)
                # Keep updating until we find one >= low_dt (since list is sorted ascending)
            else:
                # Since valid_highs is sorted, we can break once we pass the low datetime
                break
        
        # Initialize Fibonacci levels
        fib_bear_level = None
        fib_bull_lower_level = None
        fib_bull_higher_level = None
        
        # Calculate Bullish Fibonacci levels (extension from low to right high)
        if right_high is not None:
            rh_dt, rh_price = right_high
            
            # Validate price relationship (high should be above low)
            if rh_price > low_price:
                try:
                    price_diff = rh_price - low_price
                    
                    # Calculate bullish extension levels
                    # These extend beyond the right high
                    fib_bull_lower_level = rh_price - price_diff * config.bullish_fib_level_lower
                    fib_bull_higher_level = rh_price - price_diff * config.bullish_fib_level_higher
                    
                    # Ensure fib levels are above the low (safety check)
                    fib_bull_lower_level = max(low_price, fib_bull_lower_level)
                    fib_bull_higher_level = max(low_price, fib_bull_higher_level)
                except (TypeError, ValueError, OverflowError):
                    # Skip if calculation fails
                    pass
        
        # Calculate Bearish Fibonacci level (retracement from left high to low)
        if left_high is not None:
            lh_dt, lh_price = left_high
            
            # Validate price relationship (high should be above low)
            if lh_price > low_price:
                try:
                    price_diff = lh_price - low_price
                    
                    # Calculate bearish retracement level
                    # This is a retracement from the high back toward the low
                    fib_bear_level = low_price + price_diff * config.bearish_fib_level
                    
                    # Ensure the fib level is between low and high (safety check)
                    fib_bear_level = max(low_price, min(lh_price, fib_bear_level))
                except (TypeError, ValueError, OverflowError):
                    # Skip if calculation fails
                    pass
        
        # Build dataclass result
        output.append(
            FibResult(
                timeframe=timeframe,
                low_center=(low_dt, low_price),  # (datetime, price)
                left_high=left_high,  # (datetime, price) or None
                right_high=right_high,  # (datetime, price) or None
                fib_bear_level=float(fib_bear_level) if fib_bear_level is not None else None,
                fib_bull_lower=float(fib_bull_lower_level) if fib_bull_lower_level is not None else None,
                fib_bull_higher=float(fib_bull_higher_level) if fib_bull_higher_level is not None else None,
            )
        )
    
    return output

