"""
Storage Service - Database operations and data access layer
"""
import sys
import os
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import (
    OHLCVCandle, MarketData, TradingSignal, SwingPoint,
    SupportResistance, FibonacciLevel, ConfluenceFactor
)
from shared.logger import setup_logger

logger = setup_logger(__name__)


class StorageService:
    """Service for database operations"""
    
    def __init__(self):
        self.db: Optional[Session] = None
    
    def __enter__(self):
        self.db = SessionLocal()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def save_trading_signal(self, signal_data: Dict) -> Optional[TradingSignal]:
        """Save trading signal to database"""
        try:
            signal = TradingSignal(
                symbol=signal_data["symbol"],
                timestamp=signal_data.get("timestamp", datetime.now()),
                market_score=signal_data["market_score"],
                direction=signal_data["direction"],
                price=signal_data["price"],
                entry1=signal_data.get("entry1"),
                entry2=signal_data.get("entry2"),
                sl=signal_data.get("sl"),
                tp1=signal_data.get("tp1"),
                tp2=signal_data.get("tp2"),
                tp3=signal_data.get("tp3"),
                swing_high=signal_data.get("swing_high"),
                swing_low=signal_data.get("swing_low"),
                support_level=signal_data.get("support_level"),
                resistance_level=signal_data.get("resistance_level"),
                confluence=signal_data.get("confluence"),
                risk_reward_ratio=signal_data.get("risk_reward_ratio"),
                pullback_detected=signal_data.get("pullback_detected", False),
                pullback_start_level=signal_data.get("pullback_start_level"),
                approaching_fib_level=signal_data.get("approaching_fib_level"),
                confidence_score=signal_data.get("confidence_score")
            )
            
            # Use merge to handle conflicts
            self.db.merge(signal)
            self.db.commit()
            
            logger.info(f"Saved trading signal for {signal_data['symbol']}")
            return signal
        except Exception as e:
            logger.error(f"Error saving trading signal: {e}")
            self.db.rollback()
            return None
    
    def get_latest_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Get latest trading signal for a symbol"""
        try:
            return self.db.query(TradingSignal).filter(
                TradingSignal.symbol == symbol
            ).order_by(desc(TradingSignal.timestamp)).first()
        except Exception as e:
            logger.error(f"Error getting latest signal: {e}")
            return None
    
    def get_signals(
        self,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100
    ) -> List[TradingSignal]:
        """Get trading signals with filters"""
        try:
            query = self.db.query(TradingSignal)
            
            if symbol:
                query = query.filter(TradingSignal.symbol == symbol)
            
            if direction:
                query = query.filter(TradingSignal.direction == direction)
            
            return query.order_by(desc(TradingSignal.timestamp)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return []
    
    def get_latest_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[OHLCVCandle]:
        """Get latest candles for a symbol"""
        try:
            return self.db.query(OHLCVCandle).filter(
                and_(
                    OHLCVCandle.symbol == symbol,
                    OHLCVCandle.timeframe == timeframe
                )
            ).order_by(desc(OHLCVCandle.timestamp)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting candles: {e}")
            return []
    
    def get_active_sr_levels(
        self,
        symbol: str,
        timeframe: str
    ) -> Dict[str, List[float]]:
        """Get active support and resistance levels"""
        try:
            support = self.db.query(SupportResistance).filter(
                and_(
                    SupportResistance.symbol == symbol,
                    SupportResistance.timeframe == timeframe,
                    SupportResistance.type == "support",
                    SupportResistance.is_active == True
                )
            ).all()
            
            resistance = self.db.query(SupportResistance).filter(
                and_(
                    SupportResistance.symbol == symbol,
                    SupportResistance.timeframe == timeframe,
                    SupportResistance.type == "resistance",
                    SupportResistance.is_active == True
                )
            ).all()
            
            return {
                "support": [float(s.level) for s in support],
                "resistance": [float(r.level) for r in resistance]
            }
        except Exception as e:
            logger.error(f"Error getting S/R levels: {e}")
            return {"support": [], "resistance": []}
    
    def get_latest_swings(
        self,
        symbol: str,
        timeframe: str
    ) -> Dict[str, Optional[float]]:
        """Get latest swing high and low"""
        try:
            swing_high = self.db.query(SwingPoint).filter(
                and_(
                    SwingPoint.symbol == symbol,
                    SwingPoint.timeframe == timeframe,
                    SwingPoint.type == "swing_high"
                )
            ).order_by(desc(SwingPoint.timestamp)).first()
            
            swing_low = self.db.query(SwingPoint).filter(
                and_(
                    SwingPoint.symbol == symbol,
                    SwingPoint.timeframe == timeframe,
                    SwingPoint.type == "swing_low"
                )
            ).order_by(desc(SwingPoint.timestamp)).first()
            
            return {
                "swing_high": float(swing_high.price) if swing_high else None,
                "swing_low": float(swing_low.price) if swing_low else None
            }
        except Exception as e:
            logger.error(f"Error getting swings: {e}")
            return {"swing_high": None, "swing_low": None}


def save_signal(signal_data: Dict) -> Optional[TradingSignal]:
    """Save trading signal"""
    with StorageService() as storage:
        return storage.save_trading_signal(signal_data)


def get_latest_signal(symbol: str) -> Optional[TradingSignal]:
    """Get latest signal"""
    with StorageService() as storage:
        return storage.get_latest_signal(symbol)


if __name__ == "__main__":
    if not init_db():
        logger.error("Database initialization failed")
    else:
        # Example usage
        signal = get_latest_signal("BTCUSDT")
        if signal:
            logger.info(f"Latest signal: {signal.symbol} - {signal.direction} - Score: {signal.market_score}")

