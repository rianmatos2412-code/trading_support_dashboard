"""
Swing Engine - Detects swing highs and swing lows
"""
import sys
import os
from typing import List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import OHLCVCandle, SwingPoint
from shared.logger import setup_logger
from shared.config import SWING_LOOKBACK_PERIODS
from shared.redis_client import publish_event

logger = setup_logger(__name__)


class SwingEngine:
    """Engine for detecting swing highs and swing lows"""
    
    def __init__(self, lookback_periods: int = SWING_LOOKBACK_PERIODS):
        self.lookback_periods = lookback_periods
    
    def detect_swing_high(
        self, 
        candles: List[OHLCVCandle], 
        index: int
    ) -> Optional[Tuple[int, Decimal]]:
        """
        Detect swing high at index
        A swing high is when the high is higher than N periods on both sides
        """
        if index < self.lookback_periods or index >= len(candles) - self.lookback_periods:
            return None
        
        current_high = Decimal(str(candles[index].high))
        
        # Check left side
        for i in range(index - self.lookback_periods, index):
            if Decimal(str(candles[i].high)) >= current_high:
                return None
        
        # Check right side
        for i in range(index + 1, index + self.lookback_periods + 1):
            if Decimal(str(candles[i].high)) >= current_high:
                return None
        
        return (index, current_high)
    
    def detect_swing_low(
        self, 
        candles: List[OHLCVCandle], 
        index: int
    ) -> Optional[Tuple[int, Decimal]]:
        """
        Detect swing low at index
        A swing low is when the low is lower than N periods on both sides
        """
        if index < self.lookback_periods or index >= len(candles) - self.lookback_periods:
            return None
        
        current_low = Decimal(str(candles[index].low))
        
        # Check left side
        for i in range(index - self.lookback_periods, index):
            if Decimal(str(candles[i].low)) <= current_low:
                return None
        
        # Check right side
        for i in range(index + 1, index + self.lookback_periods + 1):
            if Decimal(str(candles[i].low)) <= current_low:
                return None
        
        return (index, current_low)
    
    def find_swing_points(self, candles: List[OHLCVCandle]) -> Tuple[List[Tuple[int, Decimal]], List[Tuple[int, Decimal]]]:
        """Find all swing highs and lows in the candle series"""
        swing_highs = []
        swing_lows = []
        
        # Start from lookback_periods and end before the last lookback_periods
        start_idx = self.lookback_periods
        end_idx = len(candles) - self.lookback_periods
        
        for i in range(start_idx, end_idx):
            swing_high = self.detect_swing_high(candles, i)
            if swing_high:
                swing_highs.append(swing_high)
            
            swing_low = self.detect_swing_low(candles, i)
            if swing_low:
                swing_lows.append(swing_low)
        
        return swing_highs, swing_lows
    
    def save_swing_points(
        self, 
        db: Session, 
        symbol: str, 
        timeframe: str, 
        candles: List[OHLCVCandle],
        swing_highs: List[Tuple[int, Decimal]],
        swing_lows: List[Tuple[int, Decimal]]
    ):
        """Save swing points to database"""
        try:
            # Save swing highs
            for idx, price in swing_highs:
                candle = candles[idx]
                swing_point = SwingPoint(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=candle.timestamp,
                    price=float(price),
                    type="swing_high",
                    strength=self.lookback_periods
                )
                # Use merge to handle conflicts
                db.merge(swing_point)
            
            # Save swing lows
            for idx, price in swing_lows:
                candle = candles[idx]
                swing_point = SwingPoint(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=candle.timestamp,
                    price=float(price),
                    type="swing_low",
                    strength=self.lookback_periods
                )
                db.merge(swing_point)
            
            db.commit()
            logger.info(f"Saved {len(swing_highs)} swing highs and {len(swing_lows)} swing lows for {symbol}")
        except Exception as e:
            logger.error(f"Error saving swing points: {e}")
            db.rollback()
            raise
    
    def process_candles(self, symbol: str, timeframe: str, candles: List[OHLCVCandle]):
        """Process candles and detect swing points"""
        if len(candles) < self.lookback_periods * 2 + 1:
            logger.warning(f"Not enough candles for swing detection: {len(candles)}")
            return
        
        swing_highs, swing_lows = self.find_swing_points(candles)
        
        if swing_highs or swing_lows:
            db = SessionLocal()
            try:
                self.save_swing_points(db, symbol, timeframe, candles, swing_highs, swing_lows)
                
                # Get latest swing points
                latest_high = swing_highs[-1] if swing_highs else None
                latest_low = swing_lows[-1] if swing_lows else None
                
                # Publish event
                publish_event("swing_detected", {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "swing_high": float(latest_high[1]) if latest_high else None,
                    "swing_low": float(latest_low[1]) if latest_low else None,
                    "swing_high_count": len(swing_highs),
                    "swing_low_count": len(swing_lows)
                })
            finally:
                db.close()


def process_swing_detection(symbol: str, timeframe: str):
    """Process swing detection for a symbol"""
    db = SessionLocal()
    try:
        # Get recent candles
        candles = db.query(OHLCVCandle).filter(
            and_(
                OHLCVCandle.symbol == symbol,
                OHLCVCandle.timeframe == timeframe
            )
        ).order_by(desc(OHLCVCandle.timestamp)).limit(200).all()
        candles.reverse()  # Oldest first
        
        if len(candles) < 50:
            logger.warning(f"Not enough candles for {symbol}")
            return
        
        engine = SwingEngine()
        engine.process_candles(symbol, timeframe, candles)
        
    except Exception as e:
        logger.error(f"Error in swing detection: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if not init_db():
        logger.error("Database initialization failed")
    else:
        # Example usage
        process_swing_detection("BTCUSDT", "1h")

