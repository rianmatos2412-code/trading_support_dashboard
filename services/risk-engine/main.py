"""
Risk Engine - Calculates risk-reward ratios and risk metrics
"""
import sys
import os
from typing import Dict, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.database import SessionLocal, init_db
from shared.logger import setup_logger
from shared.config import MIN_RISK_REWARD_RATIO, MAX_RISK_PERCENT
from shared.redis_client import publish_event

logger = setup_logger(__name__)


class RiskEngine:
    """Engine for calculating risk-reward metrics"""
    
    def __init__(
        self,
        min_rr: Decimal = MIN_RISK_REWARD_RATIO,
        max_risk_pct: Decimal = MAX_RISK_PERCENT
    ):
        self.min_rr = min_rr
        self.max_risk_pct = max_risk_pct
    
    def calculate_risk_reward(
        self,
        entry: Decimal,
        sl: Decimal,
        tp1: Decimal,
        tp2: Optional[Decimal] = None,
        tp3: Optional[Decimal] = None
    ) -> Dict[str, Decimal]:
        """Calculate risk-reward ratios"""
        risk = abs(entry - sl)
        
        if risk == 0:
            return {
                "risk": Decimal("0"),
                "reward_tp1": Decimal("0"),
                "reward_tp2": Decimal("0"),
                "reward_tp3": Decimal("0"),
                "rr_tp1": Decimal("0"),
                "rr_tp2": Decimal("0"),
                "rr_tp3": Decimal("0"),
                "is_valid": False
            }
        
        reward_tp1 = abs(tp1 - entry)
        rr_tp1 = reward_tp1 / risk
        
        reward_tp2 = abs(tp2 - entry) if tp2 else Decimal("0")
        rr_tp2 = reward_tp2 / risk if tp2 else Decimal("0")
        
        reward_tp3 = abs(tp3 - entry) if tp3 else Decimal("0")
        rr_tp3 = reward_tp3 / risk if tp3 else Decimal("0")
        
        # Check if meets minimum RR requirement
        is_valid = rr_tp1 >= self.min_rr
        
        return {
            "risk": risk,
            "reward_tp1": reward_tp1,
            "reward_tp2": reward_tp2,
            "reward_tp3": reward_tp3,
            "rr_tp1": rr_tp1,
            "rr_tp2": rr_tp2,
            "rr_tp3": rr_tp3,
            "is_valid": is_valid
        }
    
    def calculate_position_size(
        self,
        account_balance: Decimal,
        risk_percent: Decimal,
        entry: Decimal,
        sl: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate position size based on risk percentage"""
        if risk_percent > self.max_risk_pct:
            risk_percent = self.max_risk_pct
        
        risk_amount = account_balance * (risk_percent / Decimal("100"))
        risk_per_unit = abs(entry - sl)
        
        if risk_per_unit == 0:
            return {
                "position_size": Decimal("0"),
                "risk_amount": Decimal("0"),
                "risk_percent": Decimal("0")
            }
        
        position_size = risk_amount / risk_per_unit
        
        return {
            "position_size": position_size,
            "risk_amount": risk_amount,
            "risk_percent": risk_percent
        }
    
    def calculate_confidence_score(
        self,
        market_score: int,
        rr_ratio: Decimal,
        confluence_factors: int
    ) -> Decimal:
        """Calculate confidence score based on multiple factors"""
        # Market score (0-100) contributes 50%
        market_component = Decimal(str(market_score)) * Decimal("0.5")
        
        # RR ratio contributes 30% (normalized to 0-100)
        rr_component = min(rr_ratio * Decimal("20"), Decimal("30"))
        
        # Confluence factors contribute 20% (each factor = 4%)
        confluence_component = Decimal(str(confluence_factors)) * Decimal("4")
        confluence_component = min(confluence_component, Decimal("20"))
        
        confidence = market_component + rr_component + confluence_component
        
        return min(confidence, Decimal("100"))
    
    def validate_setup(
        self,
        entry: Decimal,
        sl: Decimal,
        tp1: Decimal,
        current_price: Decimal
    ) -> Dict[str, any]:
        """Validate if setup meets risk criteria"""
        rr_metrics = self.calculate_risk_reward(entry, sl, tp1)
        
        # Check if current price is between entry and SL (invalid)
        if entry > sl:
            # Long setup
            if sl <= current_price <= entry:
                price_valid = True
            else:
                price_valid = False
        else:
            # Short setup
            if entry <= current_price <= sl:
                price_valid = True
            else:
                price_valid = False
        
        is_valid = rr_metrics["is_valid"] and price_valid
        
        return {
            "is_valid": is_valid,
            "rr_ratio": rr_metrics["rr_tp1"],
            "price_valid": price_valid,
            "risk": rr_metrics["risk"]
        }


def calculate_risk_reward(
    entry: Decimal,
    sl: Decimal,
    tp1: Decimal,
    tp2: Optional[Decimal] = None,
    tp3: Optional[Decimal] = None
) -> Dict[str, Decimal]:
    """Calculate risk-reward for a setup"""
    engine = RiskEngine()
    return engine.calculate_risk_reward(entry, sl, tp1, tp2, tp3)


if __name__ == "__main__":
    if not init_db():
        logger.error("Database initialization failed")
    else:
        # Example
        result = calculate_risk_reward(
            Decimal("50000"),
            Decimal("49000"),
            Decimal("52000"),
            Decimal("54000"),
            Decimal("56000")
        )
        logger.info(f"Risk-Reward: {result}")

