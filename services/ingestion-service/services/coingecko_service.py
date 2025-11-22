"""
CoinGecko ingestion service for fetching market data from CoinGecko API
"""
import sys
import os
import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import text
import structlog

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.database import DatabaseManager
from shared.redis_client import publish_event

# Import from local modules (relative to ingestion-service root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.circuit_breaker import AsyncCircuitBreaker
from utils.rate_limiter import COINGECKO_RATE_LIMIT, COINGECKO_MINUTE_LIMIT
from config.settings import COINGECKO_API_URL, COINGECKO_MIN_MARKET_CAP, COINGECKO_MIN_VOLUME_24H
from database.repository import get_or_create_symbol_record, get_strategy_config_value
from services.binance_service import BinanceIngestionService

logger = structlog.get_logger(__name__)

# Path to local mapping file
MAPPING_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ticker_to_coingecko_mapping.json')

class CoinGeckoIngestionService:
    """Service for ingesting market data from CoinGecko API"""
    
    def __init__(self):
        self.base_url = COINGECKO_API_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError, Exception)
        )
        self._mapping_cache: Optional[Dict[str, str]] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _fetch_top_market_metrics_impl(self, limit: int = 200) -> List[Dict]:
        """Internal implementation of fetch_top_market_metrics"""
        # Calculate pages needed (CoinGecko allows max 250 per page)
        per_page = min(limit, 250)
        pages_needed = (limit + per_page - 1) // per_page
        
        all_coins = []
        for page in range(1, pages_needed + 1):
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false"
            }
            
            async with COINGECKO_RATE_LIMIT:
                async with COINGECKO_MINUTE_LIMIT:
                    async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            data = await response.json()
                            all_coins.extend(data)
                            logger.info(f"Fetched page {page}: {len(data)} coins")
                        else:
                            logger.error(f"Failed to fetch CoinGecko data: {response.status}")
                            if response.status == 429:
                                logger.warning("Rate limited by CoinGecko, waiting 60 seconds...")
                                await asyncio.sleep(60)
                                continue
                            response.raise_for_status()
                            break
        
        # Limit to requested number
        return all_coins[:limit]
    
    async def fetch_top_market_metrics(self, limit: int = 200) -> List[Dict]:
        """Fetch top market metrics from CoinGecko with circuit breaker protection"""
        try:
            return await self.circuit_breaker.call(self._fetch_top_market_metrics_impl, limit)
        except Exception as e:
            logger.error("coingecko_market_metrics_error", error=str(e), exc_info=True)
            return []
    
    def map_coin_to_symbol(self, coin_data: Dict) -> Optional[str]:
        """Map CoinGecko coin data to trading symbol (e.g., BTCUSDT)"""
        try:
            symbol = coin_data.get("symbol", "").upper()
            if symbol:
                return f"{symbol}USDT"
            return None
        except Exception as e:
            logger.error(f"Error mapping coin to symbol: {e}")
            return None
    
    def get_or_create_symbol_id(self, db: Session, symbol: str, image_path: Optional[str] = None) -> Optional[int]:
        """Get or create symbol_id for a given symbol with optional image path"""
        return get_or_create_symbol_record(db, symbol, image_path=image_path)
    
    def get_symbol_id(self, db: Session, symbol: str) -> Optional[int]:
        """Get symbol_id for an existing symbol only (does not create new symbols)"""
        try:
            result = db.execute(
                text("SELECT symbol_id FROM symbols WHERE symbol_name = :symbol"),
                {"symbol": symbol}
            ).scalar()
            return result
        except Exception as e:
            logger.error(f"Error getting symbol_id for {symbol}: {e}")
            return None
    
    async def save_market_metrics(
        self, 
        db: Session, 
        coins_data: List[Dict], 
        binance_service: Optional[BinanceIngestionService] = None,
        create_symbols: bool = True
    ):
        """Save market metrics to database using CoinGecko data
        
        Args:
            create_symbols: If True, creates new symbols if they don't exist.
                           If False, only updates existing symbols (skips new ones).
        """
        try:
            saved_count = 0
            skipped_count = 0
            current_timestamp = datetime.now()
            
            for coin in coins_data:
                try:
                    # Use Binance symbol if available (from new ingestion flow), otherwise map from coin data
                    symbol = coin.get("_binance_symbol")
                    if not symbol:
                        symbol = self.map_coin_to_symbol(coin)
                    if not symbol:
                        skipped_count += 1
                        continue
                    
                    # Extract image path from CoinGecko data
                    image_path = coin.get("image")
                    
                    # Get symbol_id - create if allowed, otherwise only get existing
                    if create_symbols:
                        symbol_id = self.get_or_create_symbol_id(db, symbol, image_path=image_path)
                        if not symbol_id:
                            logger.warning(f"Could not get/create symbol_id for {symbol}")
                            skipped_count += 1
                            continue
                    else:
                        # Only update existing symbols, skip new ones
                        symbol_id = self.get_symbol_id(db, symbol)
                        if not symbol_id:
                            skipped_count += 1
                            continue  # Skip symbols that don't exist
                    
                    # Extract market data from CoinGecko
                    market_cap = coin.get("market_cap")
                    volume_24h = coin.get("total_volume")
                    circulating_supply = coin.get("circulating_supply")
                    price = coin.get("current_price")
                    
                    # Skip if essential data is missing
                    if market_cap is None and volume_24h is None and circulating_supply is None and price is None:
                        skipped_count += 1
                        continue
                    
                    # Use INSERT ... ON CONFLICT DO UPDATE for upsert
                    stmt = text("""
                        INSERT INTO market_data 
                        (symbol_id, timestamp, market_cap, volume_24h, circulating_supply, price)
                        VALUES (:symbol_id, :timestamp, :market_cap, :volume_24h, :circulating_supply, :price)
                        ON CONFLICT (symbol_id, timestamp) 
                        DO UPDATE SET
                            market_cap = EXCLUDED.market_cap,
                            volume_24h = EXCLUDED.volume_24h,
                            circulating_supply = EXCLUDED.circulating_supply,
                            price = EXCLUDED.price
                    """)
                    db.execute(stmt, {
                        "symbol_id": symbol_id,
                        "timestamp": current_timestamp,
                        "market_cap": float(market_cap) if market_cap else None,
                        "volume_24h": float(volume_24h) if volume_24h else None,
                        "circulating_supply": float(circulating_supply) if circulating_supply else None,
                        "price": float(price) if price else None
                    })
                    saved_count += 1
                    
                    # Publish marketcap_update event for real-time market cap and volume updates
                    try:
                        publish_event("marketcap_update", {
                            "symbol": symbol,
                            "marketcap": float(market_cap) if market_cap else None,
                            "volume_24h": float(volume_24h) if volume_24h else None,
                            "timestamp": current_timestamp.isoformat()
                        })
                    except Exception as e:
                        logger.debug(f"Failed to publish marketcap_update event for {symbol}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error saving market data for {coin.get('id', 'unknown')}: {e}")
                    skipped_count += 1
                    continue
            
            db.commit()
            logger.info(f"Saved {saved_count} market metrics, skipped {skipped_count}")
            
            # Publish event
            if saved_count > 0:
                publish_event("market_metrics_update", {
                    "count": saved_count,
                    "timestamp": current_timestamp.isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error saving market metrics: {e}")
            db.rollback()
            raise
    
    async def _fetch_market_data_by_symbols_impl(self, symbols: List[str]) -> List[Dict]:
        """Internal implementation of fetch_market_data_by_symbols"""
        # Convert symbols to coin IDs (remove USDT suffix and lowercase)
        coin_ids = []
        symbol_to_coin_id = {}
        for symbol in symbols:
            if symbol.endswith("USDT"):
                coin_id = symbol[:-4].lower()
                coin_ids.append(coin_id)
                symbol_to_coin_id[symbol] = coin_id
        
        if not coin_ids:
            return []
        
        # CoinGecko API allows up to 250 coin IDs per request
        all_coins = []
        batch_size = 250
        for i in range(0, len(coin_ids), batch_size):
            batch = coin_ids[i:i + batch_size]
            coin_ids_str = ",".join(batch)
            
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": "usd",
                "ids": coin_ids_str,
                "order": "market_cap_desc",
                "per_page": len(batch),
                "page": 1,
                "sparkline": "false"
            }
            
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    data = await response.json()
                    all_coins.extend(data)
                    logger.info(f"Fetched market data for {len(data)} coins")
                else:
                    logger.error(f"Failed to fetch CoinGecko data: {response.status}")
                    if response.status == 429:
                        logger.warning("Rate limited by CoinGecko, waiting 60 seconds...")
                        await asyncio.sleep(60)
                        continue
                    response.raise_for_status()
                    break
        
        return all_coins
    
    async def fetch_market_data_by_symbols(self, symbols: List[str]) -> List[Dict]:
        """Fetch market data from CoinGecko for specific symbols with circuit breaker protection"""
        try:
            return await self.circuit_breaker.call(self._fetch_market_data_by_symbols_impl, symbols)
        except Exception as e:
            logger.error(f"Error fetching market data by symbols: {e}")
            return []
    
    async def update_market_data_for_symbols(self, symbols: List[str], binance_service: Optional[BinanceIngestionService] = None):
        """Update market data (price, market_cap, volume_24h) for existing symbols only"""
        logger.info(f"Updating market data for {len(symbols)} existing symbols")
        
        # Fetch market data from CoinGecko
        coins_data = await self.fetch_market_data_by_symbols(symbols)
        if not coins_data:
            logger.warning("No market data fetched from CoinGecko")
            return
        
        # Update database (create_symbols=False means only update existing symbols)
        with DatabaseManager() as db:
            await self.save_market_metrics(
                db, 
                coins_data, 
                binance_service=binance_service,
                create_symbols=False  # Only update existing symbols, don't create new ones
            )
            logger.info(f"Successfully updated market data for {len(coins_data)} symbols")
    
    async def ingest_top_market_metrics(self, limit: int = 200, binance_service: Optional[BinanceIngestionService] = None):
        """Ingest top market metrics from CoinGecko, filtered to only Binance perpetual contracts"""
        logger.info(f"Starting CoinGecko ingestion for top {limit} coins")
        
        # Fetch market metrics
        coins_data = await self.fetch_top_market_metrics(limit)
        if not coins_data:
            logger.warning("No market metrics fetched from CoinGecko")
            return
        
        # Filter to only include symbols available on Binance perpetual contracts
        if binance_service:
            available_symbols = await binance_service.get_available_perpetual_symbols()
            if available_symbols:
                filtered_coins = []
                for coin in coins_data:
                    symbol = self.map_coin_to_symbol(coin)
                    if symbol and symbol in available_symbols:
                        filtered_coins.append(coin)
                    else:
                        logger.debug(f"Filtered out {coin.get('id', 'unknown')} - not available as perpetual on Binance")
                
                coins_data = filtered_coins
                logger.info(f"Filtered to {len(coins_data)} coins available as Binance perpetual contracts")
            else:
                logger.warning("Could not fetch Binance perpetual symbols, saving all CoinGecko data")
        
        # Save to database
        with DatabaseManager() as db:
            await self.save_market_metrics(db, coins_data, binance_service=binance_service)
    
    def extract_base_asset(self, symbol: str) -> Optional[str]:
        """Extract base asset from Binance symbol (e.g., BTC from BTCUSDT)"""
        if symbol.endswith("USDT"):
            return symbol[:-4]
        return None
    
    def normalize_base_asset(self, base_asset: str) -> str:
        """Normalize base asset by removing common multiplier prefixes.
        
        Binance often uses multiplier prefixes (1000, 100, 10) for tokens with small unit prices.
        This function removes these prefixes to match with CoinGecko ticker symbols.
        
        Examples:
            "1000PEPE" -> "PEPE"
            "100SHIB" -> "SHIB"
            "10LUNC" -> "LUNC"
            "BTC" -> "BTC" (no change)
        
        Args:
            base_asset: Base asset string, may contain multiplier prefix
            
        Returns:
            Normalized base asset without multiplier prefix
        """
        base_upper = base_asset.upper()
        
        # Common multiplier prefixes used by Binance
        multipliers = ["1000000", "1000",  "10"]
        
        for multiplier in multipliers:
            if base_upper.startswith(multiplier):
                # Check if the rest is a valid ticker (at least 2 chars)
                remaining = base_upper[len(multiplier):]
                if len(remaining) >= 2:
                    return remaining
        
        return base_upper
    
    def load_ticker_mapping(self) -> Dict[str, str]:
        """Load ticker to CoinGecko coin ID mapping from local file"""
        if self._mapping_cache is not None:
            return self._mapping_cache
        
        try:
            if os.path.exists(MAPPING_FILE_PATH):
                with open(MAPPING_FILE_PATH, 'r') as f:
                    data = json.load(f)
                    self._mapping_cache = data.get("mappings", {})
                    return self._mapping_cache
            else:
                # Create empty mapping file if it doesn't exist
                os.makedirs(os.path.dirname(MAPPING_FILE_PATH), exist_ok=True)
                with open(MAPPING_FILE_PATH, 'w') as f:
                    json.dump({"mappings": {}}, f, indent=2)
                self._mapping_cache = {}
                return {}
        except Exception as e:
            logger.error(f"Error loading ticker mapping: {e}")
            self._mapping_cache = {}
            return {}
    
    def save_ticker_mapping(self, ticker: str, coin_id: str):
        """Save ticker to CoinGecko coin ID mapping to local file"""
        try:
            mapping = self.load_ticker_mapping()
            mapping[ticker.upper()] = coin_id
            self._mapping_cache = mapping
            
            os.makedirs(os.path.dirname(MAPPING_FILE_PATH), exist_ok=True)
            with open(MAPPING_FILE_PATH, 'w') as f:
                json.dump({"mappings": mapping}, f, indent=2)
            
            logger.info(f"Updated mapping: {ticker.upper()} -> {coin_id}")
        except Exception as e:
            logger.error(f"Error saving ticker mapping: {e}")
    
    async def _search_coin_by_ticker_impl(self, ticker: str) -> Optional[Dict]:
        """Search for coin by ticker using CoinGecko search endpoint"""
        url = f"{self.base_url}/search"
        params = {"query": ticker}
        
        try:
            async with COINGECKO_RATE_LIMIT:
                async with COINGECKO_MINUTE_LIMIT:
                    async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            data = await response.json()
                            coins = data.get("coins", [])
                            
                            # Try to find exact match by ticker (case-insensitive)
                            ticker_upper = ticker.upper()
                            for coin in coins:
                                if coin.get("symbol", "").upper() == ticker_upper:
                                    return coin
                            
                            # If no exact match, return first result if available
                            if coins:
                                return coins[0]
                            
                            return None
                        elif response.status == 429:
                            logger.warning("Rate limited by CoinGecko search, waiting 60 seconds...")
                            await asyncio.sleep(60)
                            return None
                        else:
                            logger.debug(f"CoinGecko search failed for {ticker}: {response.status}")
                            return None
        except Exception as e:
            logger.debug(f"Error searching CoinGecko for {ticker}: {e}")
            return None
    
    async def search_coin_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Search for coin by ticker with circuit breaker protection"""
        try:
            return await self.circuit_breaker.call(self._search_coin_by_ticker_impl, ticker)
        except Exception as e:
            logger.debug(f"Error searching coin by ticker {ticker}: {e}")
            return None
    
    async def _fetch_coin_by_id_impl(self, coin_id: str) -> Optional[Dict]:
        """Fetch coin market data by CoinGecko ID"""
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
            "sparkline": "false"
        }
        
        try:
            async with COINGECKO_RATE_LIMIT:
                async with COINGECKO_MINUTE_LIMIT:
                    async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and len(data) > 0:
                                return data[0]
                            return None
                        elif response.status == 429:
                            logger.warning("Rate limited by CoinGecko, waiting 60 seconds...")
                            await asyncio.sleep(60)
                            return None
                        else:
                            logger.debug(f"CoinGecko fetch failed for {coin_id}: {response.status}")
                            return None
        except Exception as e:
            logger.debug(f"Error fetching coin by ID {coin_id}: {e}")
            return None
    
    async def fetch_coin_by_id(self, coin_id: str) -> Optional[Dict]:
        """Fetch coin market data by CoinGecko ID with circuit breaker protection"""
        try:
            return await self.circuit_breaker.call(self._fetch_coin_by_id_impl, coin_id)
        except Exception as e:
            logger.debug(f"Error fetching coin by ID {coin_id}: {e}")
            return None
    
    async def enrich_asset_with_coingecko(self, ticker: str) -> Optional[Dict]:
        """Enrich asset with CoinGecko data using multiple strategies:
        1. Use local mapping file (most reliable, already confirmed)
        2. Use CoinGecko search endpoint (comprehensive search)
        3. Try direct match by ticker (fallback, rarely works)
        4. If new mapping is confirmed from search, update mapping file
        """
        ticker_upper = ticker.upper()
        
        # Strategy 1: Use local mapping file (most reliable)
        mapping = self.load_ticker_mapping()
        coin_id_from_mapping = mapping.get(ticker_upper)
        if coin_id_from_mapping:
            coin_data = await self.fetch_coin_by_id(coin_id_from_mapping)
            if coin_data:
                # Verify the symbol matches
                if coin_data.get("symbol", "").upper() == ticker_upper:
                    logger.debug(f"Mapping match found for {ticker}: {coin_id_from_mapping}")
                    return coin_data
        
        # Strategy 2: Use CoinGecko search endpoint
        search_result = await self.search_coin_by_ticker(ticker)
        if search_result:
            # Fetch full market data using the coin ID from search
            coin_id_from_search = search_result.get("id")
            if coin_id_from_search:
                coin_data = await self.fetch_coin_by_id(coin_id_from_search)
                if coin_data:
                    # Verify the symbol matches
                    if coin_data.get("symbol", "").upper() == ticker_upper:
                        logger.debug(f"Search match found for {ticker}: {coin_id_from_search}")
                        # Update mapping file with confirmed mapping
                        self.save_ticker_mapping(ticker, coin_id_from_search)
                        return coin_data
        
        # Strategy 3: Try direct match by ticker (coin ID is usually lowercase ticker, rarely works)
        coin_id_direct = ticker_upper.lower()
        coin_data = await self.fetch_coin_by_id(coin_id_direct)
        if coin_data:
            # Verify the symbol matches
            if coin_data.get("symbol", "").upper() == ticker_upper:
                logger.debug(f"Direct match found for {ticker}: {coin_id_direct}")
                # Update mapping file with confirmed mapping
                self.save_ticker_mapping(ticker, coin_id_direct)
                return coin_data
        
        logger.debug(f"No CoinGecko data found for {ticker}")
        return None
    
    async def ingest_from_binance_perpetuals(
        self, 
        binance_service: BinanceIngestionService,
        min_binance_volume: Optional[float] = None,
        min_market_cap: Optional[float] = None
    ) -> List[Dict]:
        """New ingestion flow:
        1. Fetch Binance USDT perpetual futures (primary universe)
        2. Fetch top 200-300 coins from CoinGecko ordered by market cap
        3. Match CoinGecko coins to Binance symbols
        4. Apply filters (Binance 24h volume > threshold, CoinGecko market cap > threshold)
        5. Return final asset universe
        
        Args:
            binance_service: Binance service instance
            min_binance_volume: Minimum Binance 24h volume (USD). If None, fetched from database.
            min_market_cap: Minimum CoinGecko market cap (USD). If None, fetched from database.
        """
        logger.info("Starting new ingestion flow: Binance perpetuals -> CoinGecko enrichment")
        
        # Get filter thresholds and limits from database if not provided
        with DatabaseManager() as db:
            if min_binance_volume is None:
                db_value = get_strategy_config_value(
                    db, 
                    "limit_volume_up", 
                    default_value=COINGECKO_MIN_VOLUME_24H
                )
                min_binance_volume = db_value if db_value is not None else COINGECKO_MIN_VOLUME_24H
                logger.info(f"Loaded min_binance_volume from database: {min_binance_volume}")
            
            if min_market_cap is None:
                db_value = get_strategy_config_value(
                    db,
                    "limit_market_cap",
                    default_value=COINGECKO_MIN_MARKET_CAP
                )
                min_market_cap = db_value if db_value is not None else COINGECKO_MIN_MARKET_CAP
                logger.info(f"Loaded min_market_cap from database: {min_market_cap}")
            
            # Get CoinGecko limit from database
            db_value = get_strategy_config_value(
                db,
                "coingecko_limit",
                default_value=250.0
            )
            coingecko_limit = int(db_value) if db_value is not None else 250
            logger.info(f"Loaded coingecko_limit from database: {coingecko_limit}")
        
        # Step 1: Fetch Binance USDT perpetual futures
        perpetual_symbols = await binance_service.get_available_perpetual_symbols()
        if not perpetual_symbols:
            logger.warning("No Binance perpetual symbols found")
            return []
        
        # Filter to only USDT pairs
        usdt_symbols = [s for s in perpetual_symbols if s.endswith("USDT")]
        logger.info(f"Found {len(usdt_symbols)} USDT perpetual symbols on Binance")
        
        # Step 2: Fetch Binance ticker data for volume filtering
        binance_tickers = await binance_service.fetch_all_tickers_24h()
        logger.info(f"Retrieved {len(binance_tickers)} tickers from Binance")
        
        # Create a mapping of normalized base asset to Binance symbol for quick lookup
        # This handles cases like "1000PEPE" (Binance) matching "PEPE" (CoinGecko)
        base_asset_to_symbol = {}
        for symbol in usdt_symbols:
            base_asset = self.extract_base_asset(symbol)
            if base_asset:
                normalized = self.normalize_base_asset(base_asset)
                # Store normalized key (primary lookup)
                base_asset_to_symbol[normalized] = symbol
                # Also store original in case it's needed for exact matches
                if normalized != base_asset.upper():
                    base_asset_to_symbol[base_asset.upper()] = symbol
        
        logger.info(f"Created base asset mapping: {len(base_asset_to_symbol)} entries")
        
        # Step 3: Fetch top coins from CoinGecko ordered by market cap
        # coingecko_limit is already loaded from database above
        logger.info(f"Fetching top {coingecko_limit} coins from CoinGecko by market cap")
        top_coins = await self.fetch_top_market_metrics(limit=coingecko_limit)
        
        if not top_coins:
            logger.warning("No coins fetched from CoinGecko")
            return []
        
        logger.info(f"Fetched {len(top_coins)} coins from CoinGecko")
        
        # Step 4: Match CoinGecko coins to Binance symbols and apply filters
        enriched_assets = []
        skipped_no_binance_match = 0
        skipped_volume_filter = 0
        skipped_market_cap_filter = 0
        
        for coin_data in top_coins:
            try:
                # Get ticker symbol from CoinGecko data
                coin_symbol = coin_data.get("symbol", "").upper()
                if not coin_symbol:
                    continue
                
                # Normalize CoinGecko symbol for matching (handles multiplier prefix cases)
                normalized_coin_symbol = self.normalize_base_asset(coin_symbol)
                
                # Find matching Binance symbol (try normalized first, then original)
                binance_symbol = base_asset_to_symbol.get(normalized_coin_symbol)
                if not binance_symbol:
                    # Fallback to original symbol in case of exact match
                    binance_symbol = base_asset_to_symbol.get(coin_symbol)
                
                if not binance_symbol:
                    skipped_no_binance_match += 1
                    continue
                
                # Get Binance ticker data for volume check
                ticker_data = binance_tickers.get(binance_symbol)
                if not ticker_data:
                    skipped_no_binance_match += 1
                    continue
                
                # Apply Binance volume filter
                quote_volume = ticker_data.get("quoteVolume")
                if quote_volume is None or float(quote_volume) < min_binance_volume:
                    skipped_volume_filter += 1
                    continue
                
                # Apply CoinGecko market cap filter
                market_cap = coin_data.get("market_cap")
                if market_cap is None or float(market_cap) < min_market_cap:
                    skipped_market_cap_filter += 1
                    continue
                
                # Add symbol to coin_data for mapping
                coin_data["_binance_symbol"] = binance_symbol
                coin_data["_base_asset"] = coin_symbol
                
                enriched_assets.append(coin_data)
                
            except Exception as e:
                logger.error(f"Error processing coin {coin_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(
            "ingestion_completed",
            total_binance_symbols=len(usdt_symbols),
            coingecko_coins_fetched=len(top_coins),
            enriched_count=len(enriched_assets),
            skipped_no_binance_match=skipped_no_binance_match,
            skipped_volume_filter=skipped_volume_filter,
            skipped_market_cap_filter=skipped_market_cap_filter
        )
        
        return enriched_assets
    
    async def ingest_from_binance_perpetuals_and_save(
        self,
        binance_service: BinanceIngestionService,
        min_binance_volume: Optional[float] = None,
        min_market_cap: Optional[float] = None
    ):
        """Ingest from Binance perpetuals, enrich with CoinGecko, and save to database"""
        logger.info("Starting new ingestion flow with database save")
        
        # Get enriched assets
        enriched_assets = await self.ingest_from_binance_perpetuals(
            binance_service=binance_service,
            min_binance_volume=min_binance_volume,
            min_market_cap=min_market_cap
        )
        
        if not enriched_assets:
            logger.warning("No enriched assets to save")
            return
        
        # Save to database
        with DatabaseManager() as db:
            await self.save_market_metrics(
                db, 
                enriched_assets, 
                binance_service=binance_service,
                create_symbols=True
            )
            
            # Extract symbols from enriched assets
            enriched_symbols = set()
            for asset in enriched_assets:
                symbol = asset.get("_binance_symbol")
                if symbol:
                    enriched_symbols.add(symbol)
            
            # Get all active symbols from database
            active_symbols_result = db.execute(
                text("SELECT symbol_name FROM symbols WHERE is_active = TRUE")
            ).fetchall()
            db_active_symbols = {row[0] for row in active_symbols_result}
            
            # Find symbols in database that are not in enriched assets
            symbols_to_deactivate = db_active_symbols - enriched_symbols
            
            if symbols_to_deactivate:
                # Deactivate symbols not in enriched assets
                current_timestamp = datetime.now(timezone.utc)
                db.execute(
                    text("""
                        UPDATE symbols
                        SET is_active = FALSE,
                            removed_at = :removed_at,
                            updated_at = :updated_at
                        WHERE symbol_name = ANY(:symbol_names)
                        AND is_active = TRUE
                    """),
                    {
                        "removed_at": current_timestamp,
                        "updated_at": current_timestamp,
                        "symbol_names": list(symbols_to_deactivate)
                    }
                )
                db.commit()
                logger.info(f"Deactivated {len(symbols_to_deactivate)} symbols not in enriched assets")
            else:
                logger.info("All active symbols are present in enriched assets, no deactivation needed")
        
        logger.info(f"Successfully saved {len(enriched_assets)} assets to database")

