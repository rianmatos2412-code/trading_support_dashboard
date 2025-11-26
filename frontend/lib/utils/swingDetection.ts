import { Candle, SwingPoint } from "@/lib/api";

export interface SwingDetectionOptions {
  window: number; // Number of bars to look back and forward (default: 2)
  excludeLatest?: number; // Number of latest candles to exclude (default: 1)
}

/**
 * Calculate swing highs and swing lows from candle data
 * Matches the Python implementation in services/strategy-engine/indicators/swing_points.py
 * 
 * A swing high is a high that is higher than 'window' bars before and after it.
 * A swing low is a low that is lower than 'window' bars before and after it.
 * 
 * Uses a rolling window approach: window of 2 means 2 bars before and 2 bars after (total 5 bars).
 * 
 * IMPORTANT: Excludes the latest candle(s) because they're still being updated in real-time.
 */
export function detectSwingPoints(
  candles: Candle[],
  symbol: string,
  timeframe: string,
  options: SwingDetectionOptions = { window: 2, excludeLatest: 1 }
): SwingPoint[] {
  // Input validation
  if (!candles || candles.length === 0) {
    return [];
  }

  const { window, excludeLatest = 1 } = options;
  
  // Validate window parameter
  if (!Number.isInteger(window) || window < 1) {
    return [];
  }

  // Check for minimum data requirement: need at least 2*window + 1 + excludeLatest candles
  const minRequired = 2 * window + 1 + excludeLatest;
  if (candles.length < minRequired) {
    return [];
  }

  // Sort candles by timestamp (ascending)
  const sortedCandles = [...candles].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Validate required fields
  if (!sortedCandles.every(c => 
    typeof c.high === 'number' && 
    typeof c.low === 'number' && 
    !isNaN(c.high) && 
    !isNaN(c.low)
  )) {
    return [];
  }

  // Exclude the latest candle(s) - they're still being updated
  // We need to exclude them from:
  // 1. Being checked as potential swing points
  // 2. Being used in the rolling window for other candles
  const excludeCount = Math.max(1, excludeLatest);
  const candlesForDetection = sortedCandles.slice(0, -excludeCount);
  
  // Also need to ensure we have enough candles after exclusion
  if (candlesForDetection.length < 2 * window + 1) {
    return [];
  }

  const swingPoints: SwingPoint[] = [];

  // Identify Swing Highs
  // A swing high must be the maximum in its rolling window (centered)
  // IMPORTANT: Only check candles that are NOT in the excluded latest candles
  // Also, don't use excluded candles in the rolling window
  for (let i = window; i < candlesForDetection.length - window; i++) {
    const currentHigh = candlesForDetection[i].high;
    
    // Check if current high is the maximum in the rolling window
    // Calculate the actual max in the window (only from candlesForDetection)
    let maxHigh = currentHigh;
    for (let j = i - window; j <= i + window; j++) {
      if (candlesForDetection[j].high > maxHigh) {
        maxHigh = candlesForDetection[j].high;
      }
    }
    
    // Swing high if current high equals the rolling max (matches Python logic)
    const isSwingHigh = currentHigh === maxHigh;
    
    // Also verify that we have valid neighbors (not NaN)
    const hasValidNeighbors = 
      candlesForDetection[i - window]?.high != null &&
      candlesForDetection[i + window]?.high != null &&
      !isNaN(candlesForDetection[i - window].high) &&
      !isNaN(candlesForDetection[i + window].high);
    
    // If it's a swing high and equals the rolling max, add it
    if (isSwingHigh && hasValidNeighbors && !isNaN(currentHigh)) {
      swingPoints.push({
        id: i * 2, // Use index-based ID for stability
        symbol,
        timeframe,
        type: "high",
        price: currentHigh,
        timestamp: candlesForDetection[i].timestamp,
      });
    }
  }

  // Identify Swing Lows
  // A swing low must be the minimum in its rolling window (centered)
  for (let i = window; i < candlesForDetection.length - window; i++) {
    const currentLow = candlesForDetection[i].low;
    
    // Check if current low is the minimum in the rolling window
    // Calculate the actual min in the window (only from candlesForDetection)
    let minLow = currentLow;
    for (let j = i - window; j <= i + window; j++) {
      if (candlesForDetection[j].low < minLow) {
        minLow = candlesForDetection[j].low;
      }
    }
    
    // Swing low if current low equals the rolling min (matches Python logic)
    const isSwingLow = currentLow === minLow;
    
    // Also verify that we have valid neighbors (not NaN)
    const hasValidNeighbors = 
      candlesForDetection[i - window]?.low != null &&
      candlesForDetection[i + window]?.low != null &&
      !isNaN(candlesForDetection[i - window].low) &&
      !isNaN(candlesForDetection[i + window].low);
    
    // If it's a swing low and equals the rolling min, add it
    if (isSwingLow && hasValidNeighbors && !isNaN(currentLow)) {
      swingPoints.push({
        id: i * 2 + 1,
        symbol,
        timeframe,
        type: "low",
        price: currentLow,
        timestamp: candlesForDetection[i].timestamp,
      });
    }
  }

  // Return sorted (should already be sorted by timestamp since candles are sorted)
  return swingPoints.sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

