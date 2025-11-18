"""
Fibonacci Entry Engine - Calculates Fibonacci levels and entry points
"""
import sys
import os
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import (
    SwingPoint, FibonacciLevel, FibConfig, TradingSignal
)
from shared.logger import setup_logger
from shared.config import (
    FIB_LONG_ENTRY1, FIB_LONG_ENTRY2, FIB_LONG_SL, FIB_LONG_APPROACHING,
    FIB_SHORT_ENTRY1, FIB_SHORT_ENTRY2, FIB_SHORT_SL, FIB_SHORT_APPROACHING,
    FIB_PULLBACK_START
)
from shared.redis_client import publish_event

logger = setup_logger(__name__)


class FibonacciEngine:
    """Engine for calculating Fibonacci levels and entry points"""
    
    def __init__(self):
        self.fib_levels = {
            0.0: "fib_0",
            0.236: "fib_0_236",
            0.382: "fib_0_382",
            0.5: "fib_0_5",
            0.618: "fib_0_618",
            0.70: "fib_0_70",
            0.72: "fib_0_72",
            0.789: "fib_0_789",
            0.90: "fib_0_90",
            1.0: "fib_1"
        }
    
    def get_fib_config(self, db: Session, setup_type: str) -> Optional[FibConfig]:
        """Get Fibonacci configuration from database"""
        return db.query(FibConfig).filter(
            FibConfig.setup_type == setup_type,
            FibConfig.is_active == True
        ).first()
    
    def calculate_fib_levels(
        self, 
        swing_high: Decimal, 
        swing_low: Decimal, 
        direction: str
    ) -> Dict[str, Decimal]:
        """Calculate Fibonacci retracement levels"""
        diff = swing_high - swing_low
        
        if direction == "long":
            # For long: swing_low is 0, swing_high is 1
            base = swing_low
        else:
            # For short: swing_high is 0, swing_low is 1
            base = swing_high
            diff = -diff
        
        levels = {}
        for fib_ratio, level_name in self.fib_levels.items():
            if direction == "long":
                levels[level_name] = base + (diff * Decimal(str(fib_ratio)))
            else:
                levels[level_name] = base + (diff * Decimal(str(fib_ratio)))
        
        return levels
    
    def get_latest_swings(
        self, 
        db: Session, 
        symbol: str, 
        timeframe: str
    ) -> tuple[Optional[SwingPoint], Optional[SwingPoint]]:
        """Get latest swing high and swing low"""
        swing_high = db.query(SwingPoint).filter(
            and_(
                SwingPoint.symbol == symbol,
                SwingPoint.timeframe == timeframe,
                SwingPoint.type == "swing_high"
            )
        ).order_by(desc(SwingPoint.timestamp)).first()
        
        swing_low = db.query(SwingPoint).filter(
            and_(
                SwingPoint.symbol == symbol,
                SwingPoint.timeframe == timeframe,
                SwingPoint.type == "swing_low"
            )
        ).order_by(desc(SwingPoint.timestamp)).first()
        
        return swing_high, swing_low
    
    def determine_direction(
        self, 
        swing_high: Optional[SwingPoint], 
        swing_low: Optional[SwingPoint],
        current_price: Decimal
    ) -> str:
        """Determine trading direction based on swing points and current price"""
        if not swing_high or not swing_low:
            return "long"  # Default
        
        high_price = Decimal(str(swing_high.price))
        low_price = Decimal(str(swing_low.price))
        
        # If price is closer to swing low, potential long
        # If price is closer to swing high, potential short
        distance_to_low = abs(current_price - low_price)
        distance_to_high = abs(current_price - high_price)
        
        if distance_to_low < distance_to_high:
            return "long"
        else:
            return "short"
    
    def calculate_entry_levels(
        self,
        fib_levels: Dict[str, Decimal],
        config: FibConfig,
        direction: str
    ) -> Dict[str, Decimal]:
        """Calculate entry, SL, and TP levels based on Fibonacci config"""
        entry_levels = {}
        
        if direction == "long":
            entry_levels["entry1"] = fib_levels.get("fib_0_70", Decimal("0"))
            entry_levels["entry2"] = fib_levels.get("fib_0_72", Decimal("0"))
            entry_levels["sl"] = fib_levels.get("fib_0_90", Decimal("0"))
            entry_levels["approaching"] = fib_levels.get("fib_0_618", Decimal("0"))
        else:
            entry_levels["entry1"] = fib_levels.get("fib_0_618", Decimal("0"))
            entry_levels["entry2"] = fib_levels.get("fib_0_69", Decimal("0"))
            entry_levels["sl"] = fib_levels.get("fib_0_789", Decimal("0"))
            entry_levels["approaching"] = fib_levels.get("fib_0_5", Decimal("0"))
        
        return entry_levels
    
    def calculate_tp_levels(
        self,
        entry: Decimal,
        sl: Decimal,
        direction: str
    ) -> Dict[str, Decimal]:
        """Calculate take profit levels"""
        risk = abs(entry - sl)
        
        if direction == "long":
            tp1 = entry + (risk * Decimal("1.0"))
            tp2 = entry + (risk * Decimal("1.618"))
            tp3 = entry + (risk * Decimal("2.618"))
        else:
            tp1 = entry - (risk * Decimal("1.0"))
            tp2 = entry - (risk * Decimal("1.618"))
            tp3 = entry - (risk * Decimal("2.618"))
        
        return {
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3
        }
    
    def detect_pullback(
        self,
        current_price: Decimal,
        swing_high: Decimal,
        swing_low: Decimal,
        direction: str
    ) -> tuple[bool, Optional[Decimal]]:
        """Detect if price is in pullback zone (starting at 0.382)"""
        diff = swing_high - swing_low
        pullback_start_level = swing_low + (diff * FIB_PULLBACK_START)
        
        if direction == "long":
            # Pullback detected if price is between pullback_start and swing_low
            if swing_low <= current_price <= pullback_start_level:
                return True, pullback_start_level
        else:
            pullback_start_level = swing_high - (diff * FIB_PULLBACK_START)
            if pullback_start_level <= current_price <= swing_high:
                return True, pullback_start_level
        
        return False, None
    
    def process_fibonacci(
        self,
        symbol: str,
        timeframe: str,
        current_price: Decimal
    ):
        """Process Fibonacci calculations for a symbol"""
        db = SessionLocal()
        try:
            swing_high, swing_low = self.get_latest_swings(db, symbol, timeframe)
            
            if not swing_high or not swing_low:
                logger.warning(f"No swing points found for {symbol}")
                return
            
            high_price = Decimal(str(swing_high.price))
            low_price = Decimal(str(swing_low.price))
            
            # Determine direction
            direction = self.determine_direction(swing_high, swing_low, current_price)
            
            # Calculate Fibonacci levels
            fib_levels = self.calculate_fib_levels(high_price, low_price, direction)
            
            # Get config
            config = self.get_fib_config(db, direction)
            if not config:
                logger.warning(f"No Fibonacci config found for {direction}")
                return
            
            # Calculate entry levels
            entry_levels = self.calculate_entry_levels(fib_levels, config, direction)
            
            # Calculate TP levels
            tp_levels = self.calculate_tp_levels(
                entry_levels["entry1"],
                entry_levels["sl"],
                direction
            )
            
            # Detect pullback
            pullback_detected, pullback_level = self.detect_pullback(
                current_price, high_price, low_price, direction
            )
            
            # Save Fibonacci levels
            fib_record = FibonacciLevel(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(),
                swing_high=float(high_price),
                swing_low=float(low_price),
                fib_0=float(fib_levels["fib_0"]),
                fib_0_236=float(fib_levels.get("fib_0_236", 0)),
                fib_0_382=float(fib_levels.get("fib_0_382", 0)),
                fib_0_5=float(fib_levels.get("fib_0_5", 0)),
                fib_0_618=float(fib_levels.get("fib_0_618", 0)),
                fib_0_70=float(fib_levels.get("fib_0_70", 0)),
                fib_0_72=float(fib_levels.get("fib_0_72", 0)),
                fib_0_789=float(fib_levels.get("fib_0_789", 0)),
                fib_0_90=float(fib_levels.get("fib_0_90", 0)),
                fib_1=float(fib_levels["fib_1"]),
                direction=direction
            )
            db.add(fib_record)
            db.commit()
            
            # Publish event
            publish_event("fib_calculated", {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction,
                "entry1": float(entry_levels["entry1"]),
                "entry2": float(entry_levels["entry2"]),
                "sl": float(entry_levels["sl"]),
                "tp1": float(tp_levels["tp1"]),
                "tp2": float(tp_levels["tp2"]),
                "tp3": float(tp_levels["tp3"]),
                "pullback_detected": pullback_detected
            })
            
            return {
                "direction": direction,
                "entry_levels": entry_levels,
                "tp_levels": tp_levels,
                "swing_high": high_price,
                "swing_low": low_price,
                "pullback_detected": pullback_detected,
                "pullback_level": pullback_level
            }
            
        except Exception as e:
            logger.error(f"Error processing Fibonacci: {e}")
            db.rollback()
            return None
        finally:
            db.close()


def process_fibonacci(symbol: str, timeframe: str, current_price: Decimal):
    """Process Fibonacci for a symbol"""
    engine = FibonacciEngine()
    return engine.process_fibonacci(symbol, timeframe, current_price)


if __name__ == "__main__":
    if not init_db():
        logger.error("Database initialization failed")
    else:
        process_fibonacci("BTCUSDT", "1h", Decimal("50000"))

