import { useEffect, useMemo, useRef } from "react";
import { useMarketStore } from "@/stores/useMarketStore";
import { detectSupportResistanceLevels } from "@/lib/utils/supportResistance";
import { SRLevel } from "@/lib/api";

/**
 * Hook to detect support and resistance levels from candles on the client side
 * Automatically updates SR levels in the store when candles change
 * Uses the same algorithm as the Python backend
 * Excludes the latest candle(s) because they're still being updated
 * Includes debouncing to prevent excessive recalculations on WebSocket updates
 */
export function useClientSupportResistance() {
  const { candles, selectedSymbol, selectedTimeframe, setSRLevels } = useMarketStore();
  const calculationTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Filter candles for current symbol and timeframe
  const relevantCandles = useMemo(() => {
    return candles.filter(
      (c) => c.symbol === selectedSymbol && c.timeframe === selectedTimeframe
    );
  }, [candles, selectedSymbol, selectedTimeframe]);

  // Memoize sorted candles to avoid re-sorting on every render
  const sortedCandles = useMemo(() => {
    return [...relevantCandles].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [relevantCandles]);

  // Calculate support/resistance levels with debouncing for frequent updates
  // Exclude latest candle because it's still being updated
  useEffect(() => {
    // Clear any pending calculation
    if (calculationTimeoutRef.current) {
      clearTimeout(calculationTimeoutRef.current);
    }

    // Debounce calculation - wait 150ms after last candle update
    // Slightly longer than swing detection since SR calculation is more complex
    calculationTimeoutRef.current = setTimeout(() => {
      if (sortedCandles.length === 0) {
        setSRLevels([]);
        return;
      }

      // Determine if this is a high timeframe (4h, 1d, etc.)
      // For now, treat all as low timeframe (use low/high)
      const isHighTimeframe = false; // Can be made configurable later
      
      const calculatedSR = detectSupportResistanceLevels(
        sortedCandles,
        selectedSymbol,
        selectedTimeframe,
        {
          beforeCandleCount: 3, // Match Python default
          afterCandleCount: 2, // Match Python sensible_window default
          highTimeframeFlag: isHighTimeframe,
          excludeLatest: 1, // Exclude latest candle
        }
      );

      setSRLevels(calculatedSR);
    }, 150); // 150ms debounce

    return () => {
      if (calculationTimeoutRef.current) {
        clearTimeout(calculationTimeoutRef.current);
      }
    };
  }, [sortedCandles, selectedSymbol, selectedTimeframe, setSRLevels]);

  return {
    srLevels: [],
    candleCount: relevantCandles.length,
  };
}

