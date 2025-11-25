"""
Data models for strategy engine.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class FibResult:
    """Container for raw Fibonacci calculations derived from swing points."""
    timeframe: str
    low_center: Tuple[int, float]  # (datetime, price)
    left_high: Optional[Tuple[int, float]] = None  # (datetime, price) - earlier in time
    right_high: Optional[Tuple[int, float]] = None  # (datetime, price) - later in time
    fib_bear_level: Optional[float] = None
    fib_bull_lower: Optional[float] = None
    fib_bull_higher: Optional[float] = None


@dataclass
class ConfirmedFibResult(FibResult):
    """Fibonacci result enriched with support/resistance matches and confluence metadata."""
    match_4h: bool = False
    match_1h: bool = False
    match_both: bool = False
    additional_matches: Dict[str, bool] = field(default_factory=dict)
    confluence_mark: str = "none"
    confluence_count: int = 0

