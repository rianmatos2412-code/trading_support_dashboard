import { Candle, SRLevel } from "@/lib/api";

export interface SupportResistanceOptions {
  beforeCandleCount?: number; // Number of candles to check before (default: 3)
  afterCandleCount?: number; // Number of candles to check after (default: 2)
  highTimeframeFlag?: boolean; // If true, use open/close for HTF. If false, use low/high for LTF (default: false)
  excludeLatest?: number; // Number of latest candles to exclude (default: 1)
}

/**
 * Check if a candle at the given index forms a support level.
 * Matches the Python implementation in services/strategy-engine/indicators/support_resistance.py
 * 
 * A support level is identified when:
 * - The price (low for LTF, open for HTF) at candle_index is the lowest point
 * - In the window of before_candle_count candles before and after_candle_count candles after
 */
function isSupport(
  candles: Candle[],
  candleIndex: number,
  beforeCandleCount: number,
  afterCandleCount: number,
  highTimeframeFlag: boolean
): boolean | null {
  try {
    // Validate inputs
    if (!candles || candles.length === 0) {
      return null;
    }

    if (candleIndex < beforeCandleCount || candleIndex >= candles.length - afterCandleCount) {
      return null;
    }

    // Determine which price to use
    const supportPrice = highTimeframeFlag 
      ? candles[candleIndex].open 
      : candles[candleIndex].low;

    if (typeof supportPrice !== 'number' || isNaN(supportPrice)) {
      return null;
    }

    // Check all candles in the before window
    for (let i = candleIndex - beforeCandleCount; i < candleIndex; i++) {
      const price = highTimeframeFlag ? candles[i].open : candles[i].low;
      if (typeof price === 'number' && !isNaN(price) && price < supportPrice) {
        return false; // Found a lower price before, not a support
      }
    }

    // Check all candles in the after window
    for (let i = candleIndex + 1; i <= candleIndex + afterCandleCount; i++) {
      const price = highTimeframeFlag ? candles[i].open : candles[i].low;
      if (typeof price === 'number' && !isNaN(price) && price < supportPrice) {
        return false; // Found a lower price after, not a support
      }
    }

    // If we get here, this candle has the lowest price in the window
    return true;
  } catch (error) {
    return null;
  }
}

/**
 * Check if a candle at the given index forms a resistance level.
 * Matches the Python implementation in services/strategy-engine/indicators/support_resistance.py
 * 
 * A resistance level is identified when:
 * - The price (high for LTF, close for HTF) at candle_index is the highest point
 * - In the window of before_candle_count candles before and after_candle_count candles after
 */
function isResistance(
  candles: Candle[],
  candleIndex: number,
  beforeCandleCount: number,
  afterCandleCount: number,
  highTimeframeFlag: boolean
): boolean | null {
  try {
    // Validate inputs
    if (!candles || candles.length === 0) {
      return null;
    }

    if (candleIndex < beforeCandleCount || candleIndex >= candles.length - afterCandleCount) {
      return null;
    }

    // Determine which price to use
    const resistancePrice = highTimeframeFlag 
      ? candles[candleIndex].close 
      : candles[candleIndex].high;

    if (typeof resistancePrice !== 'number' || isNaN(resistancePrice)) {
      return null;
    }

    // Check all candles in the before window
    for (let i = candleIndex - beforeCandleCount; i < candleIndex; i++) {
      const price = highTimeframeFlag ? candles[i].close : candles[i].high;
      if (typeof price === 'number' && !isNaN(price) && price > resistancePrice) {
        return false; // Found a higher price before, not a resistance
      }
    }

    // Check all candles in the after window
    for (let i = candleIndex + 1; i <= candleIndex + afterCandleCount; i++) {
      const price = highTimeframeFlag ? candles[i].close : candles[i].high;
      if (typeof price === 'number' && !isNaN(price) && price > resistancePrice) {
        return false; // Found a higher price after, not a resistance
      }
    }

    // If we get here, this candle has the highest price in the window
    return true;
  } catch (error) {
    return null;
  }
}

/**
 * Calculate support and resistance levels from candle data.
 * Matches the Python implementation in services/strategy-engine/indicators/support_resistance.py
 * 
 * Loops from index 3 to len-1 (excluding latest candle)
 * Uses before_candle_count=3 and after_candle_count=sensible_window (default 2)
 */
export function detectSupportResistanceLevels(
  candles: Candle[],
  symbol: string,
  timeframe: string,
  options: SupportResistanceOptions = {}
): SRLevel[] {
  // Input validation
  if (!candles || candles.length === 0) {
    return [];
  }

  const {
    beforeCandleCount = 3,
    afterCandleCount = 2,
    highTimeframeFlag = false,
    excludeLatest = 1,
  } = options;

  // Validate parameters
  if (!Number.isInteger(beforeCandleCount) || beforeCandleCount < 1) {
    return [];
  }
  if (!Number.isInteger(afterCandleCount) || afterCandleCount < 1) {
    return [];
  }

  // Need at least beforeCandleCount + afterCandleCount + 1 + excludeLatest candles
  const minRequired = beforeCandleCount + afterCandleCount + 1 + excludeLatest;
  if (candles.length < minRequired) {
    return [];
  }

  // Sort candles by timestamp (ascending)
  const sortedCandles = [...candles].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Validate required fields
  const requiredFields = highTimeframeFlag 
    ? ['open', 'close'] 
    : ['low', 'high'];
  
  if (!sortedCandles.every(c => 
    requiredFields.every(field => 
      typeof c[field as keyof Candle] === 'number' && 
      !isNaN(c[field as keyof Candle] as number)
    )
  )) {
    return [];
  }

  // Exclude the latest candle(s) - they're still being updated
  const excludeCount = Math.max(1, excludeLatest);
  const candlesForDetection = sortedCandles.slice(0, -excludeCount);

  // Need at least beforeCandleCount + afterCandleCount + 1 candles after exclusion
  if (candlesForDetection.length < beforeCandleCount + afterCandleCount + 1) {
    return [];
  }

  const srLevels: SRLevel[] = [];
  let levelId = 0;

  // Loop from index 3 to len-1 (matching Python: range(3, len-1))
  // But we need to account for beforeCandleCount, so start from beforeCandleCount
  const startIndex = Math.max(beforeCandleCount, 3);
  const endIndex = candlesForDetection.length - 1; // Exclude last candle (len-1)

  for (let i = startIndex; i < endIndex; i++) {
    try {
      // Check for support level
      const supportResult = isSupport(
        candlesForDetection,
        i,
        beforeCandleCount,
        afterCandleCount,
        highTimeframeFlag
      );
      
      if (supportResult === true) {
        const supportPrice = highTimeframeFlag 
          ? candlesForDetection[i].open 
          : candlesForDetection[i].low;
        
        srLevels.push({
          id: levelId++,
          symbol,
          timeframe,
          level: supportPrice,
          type: "support",
          strength: 1, // Can be enhanced later with touch counting
          touches: 1, // Can be enhanced later
          timestamp: candlesForDetection[i].timestamp, // Store the detection candle timestamp
        });
      }

      // Check for resistance level
      const resistanceResult = isResistance(
        candlesForDetection,
        i,
        beforeCandleCount,
        afterCandleCount,
        highTimeframeFlag
      );
      
      if (resistanceResult === true) {
        const resistancePrice = highTimeframeFlag 
          ? candlesForDetection[i].close 
          : candlesForDetection[i].high;
        
        srLevels.push({
          id: levelId++,
          symbol,
          timeframe,
          level: resistancePrice,
          type: "resistance",
          strength: 1, // Can be enhanced later with touch counting
          touches: 1, // Can be enhanced later
          timestamp: candlesForDetection[i].timestamp, // Store the detection candle timestamp
        });
      }
    } catch (error) {
      // Skip this candle if there's an error
      continue;
    }
  }

  // Sort by timestamp (most recent first)
  return srLevels.sort((a, b) => {
    if (a.timestamp && b.timestamp) {
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    }
    return 0;
  });
}

