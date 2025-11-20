"use client";

import { useState, useMemo } from "react";
import { TradingSignal } from "@/lib/api";
import { ConfluenceBadges } from "@/components/ui/ConfluenceBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatPrice, formatTimestamp } from "@/lib/utils";
import { TrendingUp, TrendingDown, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useMarketStore } from "@/stores/useMarketStore";

type SortField = 
  | "timestamp" 
  | "market_score" 
  | "symbol" 
  | "direction" 
  | "entry"
  | "sl"
  | "tp1";
type SortDirection = "asc" | "desc";

interface SignalsTableProps {
  signals: TradingSignal[];
  onRowClick?: (signal: TradingSignal) => void;
}

export function SignalsTable({ signals, onRowClick }: SignalsTableProps) {
  const router = useRouter();
  const { setSelectedSymbol, setLatestSignal } = useMarketStore();
  const [sortField, setSortField] = useState<SortField>("timestamp");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const sortedSignals = useMemo(() => {
    const sorted = [...signals].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case "timestamp":
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        case "market_score":
          aValue = a.market_score || 0;
          bValue = b.market_score || 0;
          break;
        case "symbol":
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        case "direction":
          aValue = a.direction;
          bValue = b.direction;
          break;
        case "entry":
          aValue = a.entry1 || a.price || 0;
          bValue = b.entry1 || b.price || 0;
          break;
        case "sl":
          aValue = a.sl || 0;
          bValue = b.sl || 0;
          break;
        case "tp1":
          aValue = a.tp1 || 0;
          bValue = b.tp1 || 0;
          break;
        default:
          return 0;
      }

      if (typeof aValue === "string" && typeof bValue === "string") {
        return sortDirection === "asc"
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortDirection === "asc" 
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });

    return sorted;
  }, [signals, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const handleRowClick = (signal: TradingSignal) => {
    setSelectedSymbol(signal.symbol);
    setLatestSignal(signal);
    if (onRowClick) {
      onRowClick(signal);
    } else {
      router.push(`/dashboard`);
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }
    return sortDirection === "asc" 
      ? <ArrowUp className="h-3 w-3 ml-1" />
      : <ArrowDown className="h-3 w-3 ml-1" />;
  };

  if (signals.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No signals available</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("symbol")}
                >
                  Symbol
                  <SortIcon field="symbol" />
                </Button>
              </th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("market_score")}
                >
                  Score
                  <SortIcon field="market_score" />
                </Button>
              </th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("direction")}
                >
                  Direction
                  <SortIcon field="direction" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("entry")}
                >
                  Entry
                  <SortIcon field="entry" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("sl")}
                >
                  SL
                  <SortIcon field="sl" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right">TP1</th>
              <th className="px-4 py-3 text-right">TP2</th>
              <th className="px-4 py-3 text-right">TP3</th>
              <th className="px-4 py-3 text-right">Swing High</th>
              <th className="px-4 py-3 text-right">Swing Low</th>
              <th className="px-4 py-3 text-left">Confluence</th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("timestamp")}
                >
                  Timestamp
                  <SortIcon field="timestamp" />
                </Button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedSignals.map((signal, index) => {
              const isHighScore = (signal.market_score || 0) >= 90;
              return (
                <motion.tr
                  key={signal.id || index}
                  className={`
                    border-b transition-colors hover:bg-muted/50 cursor-pointer
                    ${isHighScore ? "bg-emerald-500/10" : ""}
                    ${signal.direction === "long" ? "hover:bg-green-500/5" : "hover:bg-red-500/5"}
                  `}
                  onClick={() => handleRowClick(signal)}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                >
                  <td className="px-4 py-3 font-medium">
                    {signal.symbol.replace("USDT", "/USDT")}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`
                        font-semibold
                        ${isHighScore ? "text-emerald-400" : ""}
                        ${(signal.market_score || 0) >= 75 && (signal.market_score || 0) < 90 ? "text-green-400" : ""}
                        ${(signal.market_score || 0) >= 60 && (signal.market_score || 0) < 75 ? "text-yellow-400" : ""}
                        ${(signal.market_score || 0) < 60 ? "text-gray-400" : ""}
                      `}
                    >
                      {signal.market_score || 0}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={signal.direction === "long" ? "long" : "short"}
                      className="flex items-center gap-1 w-fit"
                    >
                      {signal.direction === "long" ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {signal.direction.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {formatPrice(signal.entry1 || signal.price)}
                  </td>
                  <td className="px-4 py-3 text-right text-red-400">
                    {signal.sl ? formatPrice(signal.sl) : "-"}
                  </td>
                  <td className="px-4 py-3 text-right text-green-400">
                    {signal.tp1 ? formatPrice(signal.tp1) : "-"}
                  </td>
                  <td className="px-4 py-3 text-right text-green-400">
                    {signal.tp2 ? formatPrice(signal.tp2) : "-"}
                  </td>
                  <td className="px-4 py-3 text-right text-green-400">
                    {signal.tp3 ? formatPrice(signal.tp3) : "-"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {signal.swing_high ? formatPrice(signal.swing_high) : "-"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {signal.swing_low ? formatPrice(signal.swing_low) : "-"}
                  </td>
                  <td className="px-4 py-3">
                    {signal.confluence ? (
                      <ConfluenceBadges confluence={signal.confluence} />
                    ) : (
                      <span className="text-muted-foreground text-sm">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatTimestamp(signal.timestamp)}
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

