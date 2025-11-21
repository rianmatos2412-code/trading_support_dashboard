"use client";

import { useEffect } from "react";
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
  useEffect(() => {
    if (!chart || !series || !swings.length || !candles.length) return;

    // Deduplicate swing points by timestamp + type to avoid duplicate markers
    const seen = new Set<string>();
    const uniqueSwings = swings.filter((swing) => {
      const key = `${swing.timestamp}-${swing.type}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });

    const markers = uniqueSwings
      .map((swing) => {
        const candle = candles.find(
          (c) => Math.abs(new Date(c.timestamp).getTime() - new Date(swing.timestamp).getTime()) < 60000
        );
        
        if (!candle) return null;

        return {
          time: (new Date(swing.timestamp).getTime() / 1000) as Time,
          position: swing.type === "high" ? ("aboveBar" as const) : ("belowBar" as const),
          color: swing.type === "high" ? "#10b981" : "#ef4444",
          shape: swing.type === "high" ? ("circle" as const) : ("circle" as const),
          size: 1.5,
          text: swing.type === "high" ? "SH" : "SL",
        };
      })
      .filter(Boolean)
      .sort((a, b) => {
        // Sort by time in ascending order (required by lightweight-charts)
        const timeA = typeof a.time === "number" ? a.time : new Date(a.time as string).getTime() / 1000;
        const timeB = typeof b.time === "number" ? b.time : new Date(b.time as string).getTime() / 1000;
        return timeA - timeB;
      });

    series.setMarkers(markers as any);

    return () => {
      series.setMarkers([]);
    };
  }, [chart, series, swings, candles]);

  return null;
}

