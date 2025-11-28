"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { TradingSignal } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Filter, Search, ArrowUpDown, ArrowUp, ArrowDown, Lock, Unlock, Plus, X } from "lucide-react";
import { SignalList } from "@/components/signals/SignalList";
import { useSignalsStore } from "@/stores/useSignalsStore";
import { useSignalFeed } from "@/hooks/useSignalFeed";
import { useSymbolData } from "@/hooks/useSymbolData";
import { cn } from "@/lib/utils";

interface SignalsClientProps {
  initialSignals: TradingSignal[];
}

const statusStyles: Record<string, string> = {
  connected: "bg-emerald-400",
  connecting: "bg-amber-400",
  disconnected: "bg-red-400",
  idle: "bg-muted-foreground",
};

const formatRelative = (timestamp: number | null) => {
  if (!timestamp) return "Waiting for live data";
  const diffSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (diffSeconds < 1) return "Just now";
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60); 
  return `${diffHours}h ago`;
};

type SortField = "swing_timestamp" | "price_score" | "confluence" | "symbol" | "entry_price" | "timestamp";
type SortDirection = "asc" | "desc";

interface SortOption {
  field: SortField;
  direction: SortDirection;
}

const calculatePriceScore = (currentPrice: number | null | undefined, entryPrice: number): number => {
  if (!currentPrice || currentPrice <= 0 || entryPrice <= 0) return Infinity; // Put missing prices at end
  return Math.abs(currentPrice - entryPrice) / currentPrice * 100;
};

export function SignalsClient({ initialSignals }: SignalsClientProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [directionFilter, setDirectionFilter] = useState<"all" | "long" | "short">("all");
  const [sortOptions, setSortOptions] = useState<SortOption[]>([
    { field: "swing_timestamp", direction: "desc" },
    { field: "price_score", direction: "asc" },
    { field: "confluence", direction: "desc" },
  ]);
  const [appliedSortOptions, setAppliedSortOptions] = useState<SortOption[]>([
    { field: "swing_timestamp", direction: "desc" },
    { field: "price_score", direction: "asc" },
    { field: "confluence", direction: "desc" },
  ]);
  const MAX_SORT_OPTIONS = 3;
  const [isFixed, setIsFixed] = useState(false);
  const [fixedOrder, setFixedOrder] = useState<string[]>([]);
  const setInitialSignals = useSignalsStore((state) => state.setInitialSignals);
  const signalIds = useSignalsStore((state) => state.signalIds);
  const { status, lastMessageAt } = useSignalFeed();
  const { symbols } = useSymbolData();

  useEffect(() => {
    setInitialSignals(initialSignals ?? []);
  }, [initialSignals, setInitialSignals]);

  const filteredAndSortedIds = useMemo(() => {
    const lookup = useSignalsStore.getState().signalMap;
    const query = searchTerm.trim().toLowerCase();

    // Filter signals
    const filtered = signalIds.filter((id) => {
      const signal = lookup[id];
      if (!signal) return false;
      if (query && !signal.symbol.toLowerCase().includes(query)) return false;
      if (directionFilter !== "all" && signal.direction !== directionFilter) return false;
      
      return true;
    });

    // If fixed, maintain the fixed order for filtered items
    if (isFixed && fixedOrder.length > 0) {
      // Create a set for fast lookup of filtered items
      const filteredSet = new Set(filtered);
      // Return items in fixed order that are still in the filtered set
      return fixedOrder.filter(id => filteredSet.has(id));
    }

    // Multi-sort signals using configurable sort options
    const sorted = [...filtered].sort((aId, bId) => {
      const a = lookup[aId];
      const b = lookup[bId];
      if (!a || !b) return 0;

      // Helper functions to get values for sorting
      const getMaxSwingTimestamp = (signal: typeof a): number => {
        const highTs = signal.swing_high_timestamp ? new Date(signal.swing_high_timestamp).getTime() : 0;
        const lowTs = signal.swing_low_timestamp ? new Date(signal.swing_low_timestamp).getTime() : 0;
        return Math.max(highTs, lowTs);
      };

      const getPriceScore = (signal: typeof a): number => {
        const entryPrice = signal.entry1 ?? signal.price ?? 0;
        const currentPrice = symbols.find((s) => s.symbol === signal.symbol)?.price ?? null;
        return calculatePriceScore(currentPrice, entryPrice);
      };

      const getConfluenceValue = (signal: typeof a): number => {
        if (!signal.confluence || typeof signal.confluence !== "string") return 0;
        const value = parseInt(signal.confluence, 10);
        return isNaN(value) ? 0 : value;
      };

      const getValue = (signal: typeof a, field: SortField): number | string => {
        switch (field) {
          case "swing_timestamp":
            return getMaxSwingTimestamp(signal);
          case "price_score":
            return getPriceScore(signal);
          case "confluence":
            return getConfluenceValue(signal);
          case "symbol":
            return signal.symbol.toLowerCase();
          case "entry_price":
            return signal.entry1 ?? signal.price ?? 0;
          case "timestamp":
            return new Date(signal.timestamp).getTime();
          default:
            return 0;
        }
      };

      // Apply each sort option in order
      for (const sortOption of appliedSortOptions) {
        const aValue = getValue(a, sortOption.field);
        const bValue = getValue(b, sortOption.field);

        if (aValue !== bValue) {
          if (typeof aValue === "string" && typeof bValue === "string") {
            const comparison = aValue.localeCompare(bValue);
            return sortOption.direction === "asc" ? comparison : -comparison;
          } else {
            const comparison = (aValue as number) - (bValue as number);
            return sortOption.direction === "asc" ? comparison : -comparison;
          }
        }
      }

      return 0; // All sort criteria are equal
    });

    return sorted;
  }, [signalIds, searchTerm, directionFilter, appliedSortOptions, symbols, isFixed, fixedOrder]);

  const totalSignals = signalIds.length;

  // Calculate current order for fixing
  const calculateCurrentOrder = useMemo(() => {
    const lookup = useSignalsStore.getState().signalMap;
    const query = searchTerm.trim().toLowerCase();

    // Filter signals
    const filtered = signalIds.filter((id) => {
      const signal = lookup[id];
      if (!signal) return false;
      if (query && !signal.symbol.toLowerCase().includes(query)) return false;
      if (directionFilter !== "all" && signal.direction !== directionFilter) return false;
      
      return true;
    });

    // Multi-sort using configurable sort options (same logic as filteredAndSortedIds)
    const sorted = [...filtered].sort((aId, bId) => {
      const a = lookup[aId];
      const b = lookup[bId];
      if (!a || !b) return 0;

      const getMaxSwingTimestamp = (signal: typeof a): number => {
        const highTs = signal.swing_high_timestamp ? new Date(signal.swing_high_timestamp).getTime() : 0;
        const lowTs = signal.swing_low_timestamp ? new Date(signal.swing_low_timestamp).getTime() : 0;
        return Math.max(highTs, lowTs);
      };

      const getPriceScore = (signal: typeof a): number => {
        const entryPrice = signal.entry1 ?? signal.price ?? 0;
        const currentPrice = symbols.find((s) => s.symbol === signal.symbol)?.price ?? null;
        return calculatePriceScore(currentPrice, entryPrice);
      };

      const getConfluenceValue = (signal: typeof a): number => {
        if (!signal.confluence || typeof signal.confluence !== "string") return 0;
        const value = parseInt(signal.confluence, 10);
        return isNaN(value) ? 0 : value;
      };

      const getValue = (signal: typeof a, field: SortField): number | string => {
        switch (field) {
          case "swing_timestamp":
            return getMaxSwingTimestamp(signal);
          case "price_score":
            return getPriceScore(signal);
          case "confluence":
            return getConfluenceValue(signal);
          case "symbol":
            return signal.symbol.toLowerCase();
          case "entry_price":
            return signal.entry1 ?? signal.price ?? 0;
          case "timestamp":
            return new Date(signal.timestamp).getTime();
          default:
            return 0;
        }
      };

      for (const sortOption of appliedSortOptions) {
        const aValue = getValue(a, sortOption.field);
        const bValue = getValue(b, sortOption.field);

        if (aValue !== bValue) {
          if (typeof aValue === "string" && typeof bValue === "string") {
            const comparison = aValue.localeCompare(bValue);
            return sortOption.direction === "asc" ? comparison : -comparison;
          } else {
            const comparison = (aValue as number) - (bValue as number);
            return sortOption.direction === "asc" ? comparison : -comparison;
          }
        }
      }

      return 0;
    });

    return sorted;
  }, [signalIds, searchTerm, directionFilter, appliedSortOptions, symbols]);

  // Handle apply sort button
  const handleApplySort = () => {
    setAppliedSortOptions([...sortOptions]);
  };

  // Handle fixed button toggle
  const handleFixedToggle = () => {
    if (!isFixed) {
      // When enabling fixed, capture the current order
      setFixedOrder(calculateCurrentOrder);
    } else {
      // When disabling fixed, clear the fixed order
      setFixedOrder([]);
    }
    setIsFixed(!isFixed);
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="mx-auto flex max-w-[1920px] flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Real-time Signals</h1>
              <p className="text-sm text-muted-foreground">
                Rendering {filteredAndSortedIds.length} / {totalSignals} signals
              </p>
            </div>
          </div>
          <Card className="flex items-center gap-6 px-4 py-2 text-sm">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  statusStyles[status] ?? statusStyles.idle
                )}
              />
              <span className="capitalize">{status}</span>
            </div>
            <div className="text-muted-foreground">
              Last update: <span className="text-foreground">{formatRelative(lastMessageAt)}</span>
            </div>
          </Card>
        </div>

        <Card className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="min-w-[220px] flex-1">
              <Label htmlFor="search" className="sr-only">
                Search
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by symbol..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Label className="text-sm">Direction</Label>
              <Select value={directionFilter} onValueChange={(value) => setDirectionFilter(value as any)}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="long">Long</SelectItem>
                  <SelectItem value="short">Short</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Multi-Sort Options */}
            <div className="flex items-center gap-2 flex-wrap">
              <Label className="text-sm">Sort:</Label>
              <div className="flex items-center gap-2 flex-wrap">
                {sortOptions.map((option, index) => (
                  <div key={index} className="flex items-center gap-1 border rounded-md px-2 py-1 bg-card">
                    <span className="text-xs text-muted-foreground">{index + 1}.</span>
                    <Select
                      value={option.field}
                      onValueChange={(value) => {
                        const newOptions = [...sortOptions];
                        newOptions[index].field = value as SortField;
                        setSortOptions(newOptions);
                      }}
                      disabled={isFixed}
                    >
                      <SelectTrigger className="w-[140px] h-7 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="swing_timestamp">Swing Timestamp</SelectItem>
                        <SelectItem value="price_score">Price Score</SelectItem>
                        <SelectItem value="confluence">Confluence</SelectItem>
                        <SelectItem value="symbol">Symbol</SelectItem>
                        <SelectItem value="entry_price">Entry Price</SelectItem>
                        <SelectItem value="timestamp">Signal Timestamp</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select
                      value={option.direction}
                      onValueChange={(value) => {
                        const newOptions = [...sortOptions];
                        newOptions[index].direction = value as SortDirection;
                        setSortOptions(newOptions);
                      }}
                      disabled={isFixed}
                    >
                      <SelectTrigger className="w-[80px] h-7 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="asc">
                          <div className="flex items-center gap-1">
                            <ArrowUp className="h-3 w-3" />
                            <span>Asc</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="desc">
                          <div className="flex items-center gap-1">
                            <ArrowDown className="h-3 w-3" />
                            <span>Desc</span>
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setSortOptions(sortOptions.filter((_, i) => i !== index));
                      }}
                      disabled={isFixed || sortOptions.length === 1}
                      className="h-7 w-7 p-0"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSortOptions([...sortOptions, { field: "swing_timestamp", direction: "desc" }]);
                  }}
                  disabled={isFixed || sortOptions.length >= MAX_SORT_OPTIONS}
                  className="h-7 gap-1"
                >
                  <Plus className="h-3 w-3" />
                  <span className="text-xs">Add</span>
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleApplySort}
                  disabled={isFixed}
                  className="h-7 gap-1"
                >
                  Apply
                </Button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant={isFixed ? "default" : "outline"}
                size="sm"
                onClick={handleFixedToggle}
                className="gap-2"
              >
                {isFixed ? (
                  <>
                    <Lock className="h-4 w-4" />
                    <span>Fixed</span>
                  </>
                ) : (
                  <>
                    <Unlock className="h-4 w-4" />
                    <span>Unfixed</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </Card>

        <SignalList signalIds={filteredAndSortedIds} symbols={symbols} />
      </div>
    </div>
  );
}

