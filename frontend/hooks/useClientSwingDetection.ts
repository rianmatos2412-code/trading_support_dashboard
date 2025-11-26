import { useEffect, useMemo, useRef } from "react";
import { useMarketStore } from "@/stores/useMarketStore";
import { detectSwingPoints } from "@/lib/utils/swingDetection";
import { SwingPoint } from "@/lib/api";

/**
 * Hook to detect swing points from candles on the client side
 * Automatically updates swing points in the store when candles change
 * Uses the same algorithm as the Python backend (window=2 by default)
 * Excludes the latest candle(s) because they're still being updated
 * Includes debouncing to prevent excessive recalculations on WebSocket updates
 */
export function useClientSwingDetection() {
  const { candles, selectedSymbol, selectedTimeframe, setSwingPoints } = useMarketStore();
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

  // Calculate swing points with debouncing for frequent updates
  // Exclude latest candle because it's still being updated
  useEffect(() => {
    // Clear any pending calculation
    if (calculationTimeoutRef.current) {
      clearTimeout(calculationTimeoutRef.current);
    }

    // Debounce calculation - wait 100ms after last candle update
    // This prevents excessive recalculations when WebSocket sends frequent updates
    calculationTimeoutRef.current = setTimeout(() => {
      if (sortedCandles.length === 0) {
        setSwingPoints([]);
        return;
      }

      const window = 3;
      // Exclude the latest candle (excludeLatest: 1) because it's still changing
      const calculatedSwings = detectSwingPoints(
        sortedCandles,
        selectedSymbol,
        selectedTimeframe,
        { window, excludeLatest: 1 }
      );

      setSwingPoints(calculatedSwings);
    }, 100); // 100ms debounce

    return () => {
      if (calculationTimeoutRef.current) {
        clearTimeout(calculationTimeoutRef.current);
      }
    };
  }, [sortedCandles, selectedSymbol, selectedTimeframe, setSwingPoints]);

  return {
    swingPoints: [],
    candleCount: relevantCandles.length,
  };
}

