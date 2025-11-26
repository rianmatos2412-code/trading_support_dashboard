"use client";

import { useEffect, useRef, useMemo } from "react";
import { IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { SRLevel, Candle } from "@/lib/api";

interface SupportResistanceLinesProps {
  chart: IChartApi | null;
  series: ISeriesApi<"Candlestick"> | null;
  srLevels: SRLevel[];
  candles: Candle[]; // Need candles to determine the end of the chart
}

export function SupportResistanceLines({
  chart,
  series,
  srLevels,
  candles,
}: SupportResistanceLinesProps) {
  const seriesRef = useRef<ISeriesApi<"Line">[]>([]);

  // Limit to last 50 SR levels for performance and remove duplicates
  const limitedSRLevels = useMemo(() => {
    if (!srLevels.length) return [];

    // Remove duplicate levels (same price within 0.1% tolerance)
    const uniqueLevels: SRLevel[] = [];
    const seenPrices = new Set<number>();

    for (const level of srLevels.slice(-50)) {
      // Round to nearest 0.1% to group similar levels
      const roundedPrice = Math.round(level.level * 1000) / 1000;
      
      if (!seenPrices.has(roundedPrice)) {
        seenPrices.add(roundedPrice);
        uniqueLevels.push(level);
      }
    }

    return uniqueLevels;
  }, [srLevels]);

  useEffect(() => {
    if (!chart || !series) {
      // Cleanup if chart/series not available
      seriesRef.current.forEach((lineSeries) => {
        try {
          chart?.removeSeries(lineSeries);
        } catch (e) {
          // Ignore
        }
      });
      seriesRef.current = [];
      return;
    }

    if (!limitedSRLevels.length) {
      // Cleanup if no levels
      seriesRef.current.forEach((lineSeries) => {
        try {
          chart.removeSeries(lineSeries);
        } catch (e) {
          // Ignore
        }
      });
      seriesRef.current = [];
      return;
    }

    try {
      // Cleanup previous series
      seriesRef.current.forEach((lineSeries) => {
        try {
          chart.removeSeries(lineSeries);
        } catch (e) {
          // Series might already be removed
        }
      });
      seriesRef.current = [];

      // Get the latest candle timestamp to extend lines to the end of the chart
      // Sort candles by timestamp to find the latest one
      const sortedCandles = [...candles].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
      
      // Use the latest candle timestamp, or current time if no candles
      const latestCandleTime = sortedCandles.length > 0
        ? (new Date(sortedCandles[sortedCandles.length - 1].timestamp).getTime() / 1000) as Time
        : (Math.floor(Date.now() / 1000) as Time);

      // Add some buffer (e.g., 24 hours) to extend beyond the latest candle
      const endTime = (latestCandleTime as number + 24 * 60 * 60) as Time;

      limitedSRLevels.forEach((level) => {
        // Start line from the detection candle timestamp
        if (!level.timestamp) return; // Skip if no timestamp
        
        const startTime = (new Date(level.timestamp).getTime() / 1000) as Time;

        const color = level.type === "support" ? "#10b981" : "#ef4444";
        const opacity = Math.min(level.strength / 10, 0.6); // Cap opacity at 60%
        
        const lineSeries = chart.addLineSeries({
          color: `${color}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}`,
          lineWidth: level.type === "support" ? 2 : 1,
          lineStyle: level.touches >= 3 ? 0 : 2, // Solid for strong levels, dashed for weak
        });

        // Draw line from detection candle timestamp to end of chart (latest candle + buffer)
        lineSeries.setData([
          { time: startTime, value: level.level },
          { time: endTime, value: level.level },
        ]);
        
        seriesRef.current.push(lineSeries);
      });
    } catch (error) {
      console.warn("SupportResistanceLines: Error rendering lines", error);
    }

    return () => {
      // Cleanup series on unmount
      seriesRef.current.forEach((lineSeries) => {
        try {
          chart?.removeSeries(lineSeries);
        } catch (e) {
          // Series might already be removed
        }
      });
      seriesRef.current = [];
    };
  }, [chart, series, limitedSRLevels]);

  return null;
}

