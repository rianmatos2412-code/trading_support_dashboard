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

    const markers = swings.map((swing) => {
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
    }).filter(Boolean);

    series.setMarkers(markers as any);

    return () => {
      series.setMarkers([]);
    };
  }, [chart, series, swings, candles]);

  return null;
}

