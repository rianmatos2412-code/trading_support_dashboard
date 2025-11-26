"use client";

import { memo, useMemo } from "react";
import { TradingSignal } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { formatPrice, formatTimestamp, cn } from "@/lib/utils";
import { TrendingDown, TrendingUp } from "lucide-react";

interface SignalRowProps {
  signal: TradingSignal;
}

const clampScore = (score: number) => Math.max(0, Math.min(100, score));

export const SignalRow = memo(
  ({ signal }: SignalRowProps) => {
    const directionIsLong = signal.direction === "long";
    const entryPrice = signal.entry1 ?? signal.price ?? 0;
    const score = clampScore(signal.market_score ?? 0);
    const lastUpdated = formatTimestamp(signal.timestamp);

    const scoreStyles = useMemo(() => {
      if (score >= 85) return "text-emerald-400";
      if (score >= 65) return "text-amber-400";
      return "text-muted-foreground";
    }, [score]);

    const priceTargets = useMemo(
      () =>
        [signal.tp1, signal.tp2, signal.tp3]
          .filter((value): value is number => typeof value === "number")
          .slice(0, 2),
      [signal.tp1, signal.tp2, signal.tp3]
    );

    return (
      <div
        className={cn(
          "flex w-full items-center justify-between gap-4 rounded-lg border border-border/60 bg-card/70 px-4 py-3 transition",
          directionIsLong ? "hover:border-emerald-500/50" : "hover:border-red-500/50"
        )}
      >
        <div className="flex min-w-[220px] items-center gap-3">
          <div className="font-semibold tracking-tight text-foreground">
            {signal.symbol.replace("USDT", "/USDT")}
          </div>
          <Badge variant={directionIsLong ? "long" : "short"} className="px-2 py-1 text-[11px]">
            {directionIsLong ? (
              <TrendingUp className="mr-1 h-3 w-3" />
            ) : (
              <TrendingDown className="mr-1 h-3 w-3" />
            )}
            {signal.direction?.toUpperCase()}
          </Badge>
          {signal.timeframe && (
            <span className="text-xs uppercase text-muted-foreground">{signal.timeframe}</span>
          )}
        </div>

        <div className="flex flex-1 items-center justify-end gap-8 text-sm">
          <div className="text-right">
            <p className="font-mono text-base text-foreground">{formatPrice(entryPrice)}</p>
            <p className="text-xs text-muted-foreground">Entry</p>
          </div>
          <div className="text-right">
            <p className={cn("font-semibold text-lg", scoreStyles)}>{score.toFixed(1)}</p>
            <div className="mt-1 h-1.5 w-24 rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  directionIsLong ? "bg-emerald-400" : "bg-red-400"
                )}
                style={{ width: `${score}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">Score</p>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {priceTargets.map((target, index) => (
              <div key={`${signal.id}-target-${index}`} className="text-right">
                <p className="font-mono text-sm text-foreground">{formatPrice(target)}</p>
                <p className="text-[11px] uppercase">TP{index + 1}</p>
              </div>
            ))}
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <p className="font-medium text-foreground">{formatPrice(signal.price)}</p>
            <p>Last update</p>
            <p>{lastUpdated}</p>
          </div>
        </div>
      </div>
    );
  },
  (prev, next) => prev.signal === next.signal
);

SignalRow.displayName = "SignalRow";


