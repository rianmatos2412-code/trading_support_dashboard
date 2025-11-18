"""
Confluence Engine - Scores trading signals based on multiple factors
"""
import sys
import os
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import (
    ConfluenceFactor, SupportResistance, SwingPoint, OHLCVCandle
)
from shared.logger import setup_logger
from shared.config import CONFLUENCE_WEIGHTS
from shared.redis_client import publish_event

logger = setup_logger(__name__)


class ConfluenceEngine:
    """Engine for calculating confluence scores"""
    
    def __init__(self, weights: Dict[str, int] = CONFLUENCE_WEIGHTS):
        self.weights = weights
        self.max_score = sum(weights.values())
    
    def calculate_rsi(self, prices: List[Decimal], period: int = 14) -> Optional[Decimal]:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(Decimal("0"))
            else:
                gains.append(Decimal("0"))
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return Decimal("100")
        
        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
        
        return rsi
    
    def check_order_block(
        self,
        candles: List[OHLCVCandle],
        current_price: Decimal,
        direction: str
    ) -> bool:
        """Check if current price is near an order block"""
        # Simplified: check if there's a strong candle in recent history
        if len(candles) < 10:
            return False
        
        recent_candles = candles[-10:]
        
        for candle in recent_candles:
            body_size = abs(Decimal(str(candle.close)) - Decimal(str(candle.open)))
            candle_range = Decimal(str(candle.high)) - Decimal(str(candle.low))
            
            if candle_range > 0:
                body_ratio = body_size / candle_range
                
                # Strong bullish candle for long
                if direction == "long" and candle.close > candle.open and body_ratio > 0.7:
                    if abs(current_price - Decimal(str(candle.low))) / current_price < 0.01:
                        return True
                
                # Strong bearish candle for short
                if direction == "short" and candle.close < candle.open and body_ratio > 0.7:
                    if abs(current_price - Decimal(str(candle.high))) / current_price < 0.01:
                        return True
        
        return False
    
    def check_sr_confluence(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        current_price: Decimal,
        direction: str
    ) -> bool:
        """Check if price is near support/resistance level"""
        tolerance = Decimal("0.005")  # 0.5%
        
        if direction == "long":
            # Check for support
            sr_levels = db.query(SupportResistance).filter(
                and_(
                    SupportResistance.symbol == symbol,
                    SupportResistance.timeframe == timeframe,
                    SupportResistance.type == "support",
                    SupportResistance.is_active == True
                )
            ).all()
            
            for level in sr_levels:
                level_price = Decimal(str(level.level))
                if abs(current_price - level_price) / current_price <= tolerance:
                    return True
        else:
            # Check for resistance
            sr_levels = db.query(SupportResistance).filter(
                and_(
                    SupportResistance.symbol == symbol,
                    SupportResistance.timeframe == timeframe,
                    SupportResistance.type == "resistance",
                    SupportResistance.is_active == True
                )
            ).all()
            
            for level in sr_levels:
                level_price = Decimal(str(level.level))
                if abs(current_price - level_price) / current_price <= tolerance:
                    return True
        
        return False
    
    def check_swing_confluence(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        current_price: Decimal,
        direction: str
    ) -> bool:
        """Check if price is near swing point"""
        tolerance = Decimal("0.005")
        
        if direction == "long":
            swing_lows = db.query(SwingPoint).filter(
                and_(
                    SwingPoint.symbol == symbol,
                    SwingPoint.timeframe == timeframe,
                    SwingPoint.type == "swing_low"
                )
            ).order_by(desc(SwingPoint.timestamp)).limit(5).all()
            
            for swing in swing_lows:
                swing_price = Decimal(str(swing.price))
                if abs(current_price - swing_price) / current_price <= tolerance:
                    return True
        else:
            swing_highs = db.query(SwingPoint).filter(
                and_(
                    SwingPoint.symbol == symbol,
                    SwingPoint.timeframe == timeframe,
                    SwingPoint.type == "swing_high"
                )
            ).order_by(desc(SwingPoint.timestamp)).limit(5).all()
            
            for swing in swing_highs:
                swing_price = Decimal(str(swing.price))
                if abs(current_price - swing_price) / current_price <= tolerance:
                    return True
        
        return False
    
    def calculate_confluence_score(
        self,
        symbol: str,
        timeframe: str,
        current_price: Decimal,
        direction: str,
        candles: List[OHLCVCandle]
    ) -> Dict[str, any]:
        """Calculate overall confluence score"""
        db = SessionLocal()
        try:
            factors = []
            score = 0
            
            # RSI
            prices = [Decimal(str(c.close)) for c in candles[-50:]]
            rsi = self.calculate_rsi(prices)
            if rsi:
                if direction == "long" and rsi < 30:  # Oversold
                    factors.append("RSI")
                    score += self.weights.get("RSI", 0)
                elif direction == "short" and rsi > 70:  # Overbought
                    factors.append("RSI")
                    score += self.weights.get("RSI", 0)
            
            # Order Block
            if self.check_order_block(candles, current_price, direction):
                factors.append("OB")
                score += self.weights.get("OB", 0)
            
            # Support/Resistance
            if self.check_sr_confluence(db, symbol, timeframe, current_price, direction):
                factors.append("SR")
                score += self.weights.get("SR", 0)
            
            # Swing Points
            if self.check_swing_confluence(db, symbol, timeframe, current_price, direction):
                factors.append("SWING")
                score += self.weights.get("SWING", 0)
            
            # Fibonacci (will be checked separately, but add placeholder)
            factors.append("FIB")
            score += self.weights.get("FIB", 0)
            
            # Calculate percentage score
            percentage_score = int((score / self.max_score) * 100)
            
            return {
                "factors": factors,
                "score": score,
                "max_score": self.max_score,
                "percentage_score": percentage_score
            }
        finally:
            db.close()
    
    def save_confluence_factors(
        self,
        db: Session,
        symbol: str,
        timestamp: datetime,
        factors: List[str],
        score: int
    ):
        """Save confluence factors to database"""
        try:
            for factor in factors:
                confluence = ConfluenceFactor(
                    symbol=symbol,
                    timestamp=timestamp,
                    factor_type=factor,
                    factor_score=self.weights.get(factor, 0)
                )
                db.add(confluence)
            
            db.commit()
        except Exception as e:
            logger.error(f"Error saving confluence factors: {e}")
            db.rollback()


def calculate_confluence(
    symbol: str,
    timeframe: str,
    current_price: Decimal,
    direction: str,
    candles: List[OHLCVCandle]
) -> Dict[str, any]:
    """Calculate confluence for a symbol"""
    engine = ConfluenceEngine()
    return engine.calculate_confluence_score(symbol, timeframe, current_price, direction, candles)


if __name__ == "__main__":
    if not init_db():
        logger.error("Database initialization failed")
    else:
        # Example usage would require candles
        pass

