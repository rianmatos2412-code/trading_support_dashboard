"""
Support/Resistance Engine - Detects support and resistance levels
"""
import sys
import os
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.models import OHLCVCandle, SupportResistance, SwingPoint
from shared.logger import setup_logger
from shared.config import SR_PRICE_TOLERANCE, SR_TOUCH_THRESHOLD
from shared.redis_client import publish_event

logger = setup_logger(__name__)


class SREngine:
    """Engine for detecting support and resistance levels"""
    
    def __init__(self, price_tolerance: Decimal = SR_PRICE_TOLERANCE, touch_threshold: int = SR_TOUCH_THRESHOLD):
        self.price_tolerance = price_tolerance
        self.touch_threshold = touch_threshold
    
    def find_price_clusters(self, prices: List[Decimal], tolerance: Decimal) -> Dict[Decimal, List[Decimal]]:
        """Group prices into clusters based on tolerance"""
        clusters = {}
        
        for price in prices:
            # Find existing cluster within tolerance
            found_cluster = False
            for cluster_key in clusters.keys():
                if abs(price - cluster_key) / cluster_key <= tolerance:
                    clusters[cluster_key].append(price)
                    found_cluster = True
                    break
            
            if not found_cluster:
                clusters[price] = [price]
        
        return clusters
    
    def detect_sr_from_swings(
        self, 
        swing_highs: List[Decimal], 
        swing_lows: List[Decimal]
    ) -> Tuple[List[Decimal], List[Decimal]]:
        """Detect S/R levels from swing points"""
        # Cluster swing highs (resistance) and swing lows (support)
        resistance_clusters = self.find_price_clusters(swing_highs, self.price_tolerance)
        support_clusters = self.find_price_clusters(swing_lows, self.price_tolerance)
        
        # Filter clusters by touch threshold
        resistance_levels = [
            sum(prices) / len(prices) 
            for prices in resistance_clusters.values() 
            if len(prices) >= self.touch_threshold
        ]
        
        support_levels = [
            sum(prices) / len(prices) 
            for prices in support_clusters.values() 
            if len(prices) >= self.touch_threshold
        ]
        
        return sorted(support_levels), sorted(resistance_levels)
    
    def detect_sr_from_candles(self, candles: List[OHLCVCandle]) -> Tuple[List[Decimal], List[Decimal]]:
        """Detect S/R levels from candle highs and lows"""
        highs = [Decimal(str(c.high)) for c in candles]
        lows = [Decimal(str(c.low)) for c in candles]
        
        # Cluster highs and lows
        high_clusters = self.find_price_clusters(highs, self.price_tolerance)
        low_clusters = self.find_price_clusters(lows, self.price_tolerance)
        
        # Filter by touch threshold
        resistance_levels = [
            sum(prices) / len(prices)
            for prices in high_clusters.values()
            if len(prices) >= self.touch_threshold
        ]
        
        support_levels = [
            sum(prices) / len(prices)
            for prices in low_clusters.values()
            if len(prices) >= self.touch_threshold
        ]
        
        return sorted(support_levels), sorted(resistance_levels)
    
    def save_sr_levels(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        support_levels: List[Decimal],
        resistance_levels: List[Decimal]
    ):
        """Save support and resistance levels to database"""
        try:
            # Get existing active levels
            existing = db.query(SupportResistance).filter(
                and_(
                    SupportResistance.symbol == symbol,
                    SupportResistance.timeframe == timeframe,
                    SupportResistance.is_active == True
                )
            ).all()
            
            # Deactivate old levels that are no longer relevant
            for existing_level in existing:
                existing_price = Decimal(str(existing_level.level))
                is_still_relevant = False
                
                # Check if it's close to any new level
                all_levels = support_levels + resistance_levels
                for new_level in all_levels:
                    if abs(existing_price - new_level) / existing_price <= self.price_tolerance:
                        is_still_relevant = True
                        break
                
                if not is_still_relevant:
                    existing_level.is_active = False
                    existing_level.updated_at = datetime.now()
            
            # Add new support levels
            for level in support_levels:
                # Check if similar level exists
                existing_level = db.query(SupportResistance).filter(
                    and_(
                        SupportResistance.symbol == symbol,
                        SupportResistance.timeframe == timeframe,
                        SupportResistance.type == "support",
                        SupportResistance.is_active == True
                    )
                ).first()
                
                if existing_level:
                    existing_price = Decimal(str(existing_level.level))
                    if abs(existing_price - level) / existing_price <= self.price_tolerance:
                        # Update existing
                        existing_level.strength += 1
                        existing_level.last_touch = datetime.now()
                        existing_level.updated_at = datetime.now()
                    else:
                        # Create new
                        sr = SupportResistance(
                            symbol=symbol,
                            timeframe=timeframe,
                            level=float(level),
                            type="support",
                            strength=1,
                            first_touch=datetime.now(),
                            last_touch=datetime.now()
                        )
                        db.add(sr)
                else:
                    sr = SupportResistance(
                        symbol=symbol,
                        timeframe=timeframe,
                        level=float(level),
                        type="support",
                        strength=1,
                        first_touch=datetime.now(),
                        last_touch=datetime.now()
                    )
                    db.add(sr)
            
            # Add new resistance levels
            for level in resistance_levels:
                existing_level = db.query(SupportResistance).filter(
                    and_(
                        SupportResistance.symbol == symbol,
                        SupportResistance.timeframe == timeframe,
                        SupportResistance.type == "resistance",
                        SupportResistance.is_active == True
                    )
                ).first()
                
                if existing_level:
                    existing_price = Decimal(str(existing_level.level))
                    if abs(existing_price - level) / existing_price <= self.price_tolerance:
                        existing_level.strength += 1
                        existing_level.last_touch = datetime.now()
                        existing_level.updated_at = datetime.now()
                    else:
                        sr = SupportResistance(
                            symbol=symbol,
                            timeframe=timeframe,
                            level=float(level),
                            type="resistance",
                            strength=1,
                            first_touch=datetime.now(),
                            last_touch=datetime.now()
                        )
                        db.add(sr)
                else:
                    sr = SupportResistance(
                        symbol=symbol,
                        timeframe=timeframe,
                        level=float(level),
                        type="resistance",
                        strength=1,
                        first_touch=datetime.now(),
                        last_touch=datetime.now()
                    )
                    db.add(sr)
            
            db.commit()
            logger.info(f"Saved {len(support_levels)} support and {len(resistance_levels)} resistance levels for {symbol}")
        except Exception as e:
            logger.error(f"Error saving S/R levels: {e}")
            db.rollback()
            raise
    
    def process_sr_detection(self, symbol: str, timeframe: str, candles: List[OHLCVCandle]):
        """Process S/R detection for candles"""
        if len(candles) < 50:
            logger.warning(f"Not enough candles for S/R detection: {len(candles)}")
            return
        
        # Get swing points
        db = SessionLocal()
        try:
            swing_highs_data = db.query(SwingPoint).filter(
                and_(
                    SwingPoint.symbol == symbol,
                    SwingPoint.timeframe == timeframe,
                    SwingPoint.type == "swing_high"
                )
            ).order_by(desc(SwingPoint.timestamp)).limit(50).all()
            
            swing_lows_data = db.query(SwingPoint).filter(
                and_(
                    SwingPoint.symbol == symbol,
                    SwingPoint.timeframe == timeframe,
                    SwingPoint.type == "swing_low"
                )
            ).order_by(desc(SwingPoint.timestamp)).limit(50).all()
            
            swing_highs = [Decimal(str(sp.price)) for sp in swing_highs_data]
            swing_lows = [Decimal(str(sp.price)) for sp in swing_lows_data]
            
            # Detect from swings
            support_levels, resistance_levels = self.detect_sr_from_swings(swing_highs, swing_lows)
            
            # Also detect from candles as backup
            candle_support, candle_resistance = self.detect_sr_from_candles(candles[-100:])
            
            # Merge results
            all_support = list(set(support_levels + candle_support))
            all_resistance = list(set(resistance_levels + candle_resistance))
            
            if all_support or all_resistance:
                self.save_sr_levels(db, symbol, timeframe, all_support, all_resistance)
                
                # Publish event
                publish_event("sr_detected", {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "support_levels": [float(s) for s in all_support],
                    "resistance_levels": [float(r) for r in all_resistance]
                })
        finally:
            db.close()


def process_sr_detection(symbol: str, timeframe: str):
    """Process S/R detection for a symbol"""
    db = SessionLocal()
    try:
        candles = db.query(OHLCVCandle).filter(
            and_(
                OHLCVCandle.symbol == symbol,
                OHLCVCandle.timeframe == timeframe
            )
        ).order_by(desc(OHLCVCandle.timestamp)).limit(200).all()
        candles.reverse()
        
        if len(candles) < 50:
            return
        
        engine = SREngine()
        engine.process_sr_detection(symbol, timeframe, candles)
    except Exception as e:
        logger.error(f"Error in S/R detection: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if not init_db():
        logger.error("Database initialization failed")
    else:
        process_sr_detection("BTCUSDT", "1h")

