"use client";

import { useEffect, useMemo } from "react";
import { IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { SwingPoint } from "@/lib/api";
import { Candle } from "@/lib/api";

interface SwingMarkersProps {
  chart: IChartApi | null;
  series: ISeriesApi<"Candlestick"> | null;
  swings: SwingPoint[];
  candles: Candle[];
}

export function SwingMarkers({
  chart,
  series,
  swings,
  candles,
}: SwingMarkersProps) {
  // Create a map of candles by timestamp for O(1) lookup instead of O(n) find
  const candleMap = useMemo(() => {
    const map = new Map<number, Candle>();
    candles.forEach(candle => {
      const timestamp = new Date(candle.timestamp).getTime();
      map.set(timestamp, candle);
    });
    return map;
  }, [candles]);

  // Memoize markers to avoid recreation on every render
  // Limit to last 200 swing points for performance
  const markers = useMemo(() => {
    if (!swings.length || !candles.length) {
      return [];
    }

    // Limit to last 200 swing points for performance (prevents too many markers)
    const limitedSwings = swings.slice(-200);

    return limitedSwings
      .map((swing) => {
        const swingTime = new Date(swing.timestamp).getTime();
        
        // Try exact match first (O(1))
        let candle = candleMap.get(swingTime);
        
        // If no exact match, find closest within 60 seconds (fallback)
        if (!candle) {
          candle = Array.from(candleMap.values()).find(
            (c) => Math.abs(new Date(c.timestamp).getTime() - swingTime) < 60000
          );
        }
        
        if (!candle) return null;

        return {
          time: (swingTime / 1000) as Time,
          position: swing.type === "high" ? ("aboveBar" as const) : ("belowBar" as const),
          color: swing.type === "high" ? "#10b981" : "#ef4444",
          // Use triangle shapes: arrowUp for swing highs, arrowDown for swing lows
          shape: swing.type === "high" ? ("arrowUp" as const) : ("arrowDown" as const),
          size: 1.5,
          text: swing.type === "high" ? "SH" : "SL",
        };
      })
      .filter(Boolean)
      // Sort markers by time in ascending order (required by lightweight-charts)
      .sort((a, b) => {
        if (!a || !b) return 0;
        return (a.time as number) - (b.time as number);
      });
  }, [swings, candleMap]);

  useEffect(() => {
    if (!chart || !series) {
      // Clear markers if chart/series are not available
      try {
        if (series && series.setMarkers) {
          series.setMarkers([]);
        }
      } catch (error) {
        // Series might be disposed, ignore
      }
      return;
    }

    try {
      // Check if chart/series are still valid (not disposed)
      if (!chart.timeScale || !series.setMarkers) return;

      if (markers.length === 0) {
        series.setMarkers([]);
        return;
      }

      series.setMarkers(markers as any);
    } catch (error) {
      // Chart or series might be disposed, ignore the error
      console.warn("SwingMarkers: Chart or series is disposed", error);
      return;
    }

    return () => {
      try {
        if (series && series.setMarkers) {
          series.setMarkers([]);
        }
      } catch (error) {
        // Series might be disposed, ignore
      }
    };
  }, [chart, series, markers]); // Only depend on markers, not candles

  return null;
}

