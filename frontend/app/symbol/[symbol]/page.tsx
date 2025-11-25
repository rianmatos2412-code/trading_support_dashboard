"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMarketStore } from "@/stores/useMarketStore";
import { fetchSignals, TradingSignal, fetchCandles, Candle, fetchSymbolDetails, SymbolDetails } from "@/lib/api";
import { ChartContainer } from "@/components/chart/ChartContainer";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConfluenceBadges } from "@/components/ui/ConfluenceBadge";
import { formatPrice, formatTimestamp, formatNumber, formatSupply, formatPercent } from "@/lib/utils";
import { ArrowLeft, TrendingUp, TrendingDown, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useWebSocket } from "@/hooks/useWebSocket";
import { subscribeToSymbolUpdates } from "@/hooks/useSymbolData";
import { TimeframeSelector } from "@/components/ui/TimeframeSelector";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export default function SymbolDetailPage() {
  const params = useParams();
  const router = useRouter();
  // Get symbol from URL and ensure it ends with USDT
  let symbolParam = (params.symbol as string).toUpperCase().replace("/", "");
  const symbol = symbolParam.endsWith("USDT") ? symbolParam : symbolParam + "USDT";
  const { 
    setSelectedSymbol, 
    setLatestSignal, 
    setCandles: setStoreCandles, 
    setSelectedTimeframe,
    selectedTimeframe,
    chartSettings,
    updateChartSettings
  } = useMarketStore();

  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbolDetails, setSymbolDetails] = useState<SymbolDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [priceChange24h, setPriceChange24h] = useState<number | null>(null);
  const [stats, setStats] = useState({
    total: 0,
    long: 0,
    short: 0,
  });
  const [sortField, setSortField] = useState<"price_score" | "direction" | "timestamp">("price_score");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // WebSocket connection for real-time updates
  useWebSocket(symbol, selectedTimeframe);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        // Set symbol first to ensure ChartContainer is ready
        setSelectedSymbol(symbol);
        // Use current timeframe from store, default to "1h" if not set
        const timeframe = selectedTimeframe || "1h";
        if (!selectedTimeframe) {
          setSelectedTimeframe("1h");
        }
        
        const [fetchedSignals, fetchedCandles, fetchedDetails] = await Promise.all([
          fetchSignals({ symbol, limit: 100 }),
          fetchCandles(symbol, timeframe, 200),
          fetchSymbolDetails(symbol).catch(() => null), // Don't fail if details not available
        ]);

        setSignals(fetchedSignals);
        setCandles(fetchedCandles);
        setSymbolDetails(fetchedDetails);
        
        // Set symbol and timeframe in store first, then update candles
        // This ensures ChartContainer can properly filter candles
        setSelectedSymbol(symbol);
        setSelectedTimeframe("1h");
        
        // Also update store candles so ChartContainer can display them
        // Only set if we have candles
        if (fetchedCandles && fetchedCandles.length > 0) {
          setStoreCandles(fetchedCandles);
        }
        if (fetchedSignals.length > 0) {
          setLatestSignal(fetchedSignals[0]);
        }

        // Calculate 24h price change from candles
        if (fetchedCandles.length >= 24) {
          const currentPrice = fetchedCandles[0]?.close;
          const price24hAgo = fetchedCandles[23]?.close;
          if (currentPrice && price24hAgo && price24hAgo > 0) {
            const change = ((currentPrice - price24hAgo) / price24hAgo) * 100;
            setPriceChange24h(change);
          }
        }

        // Calculate statistics
        const total = fetchedSignals.length;
        const long = fetchedSignals.filter((s) => s.direction === "long").length;
        const short = fetchedSignals.filter((s) => s.direction === "short").length;

        setStats({
          total,
          long,
          short,
        });
      } catch (error) {
        console.error("Error loading symbol data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [symbol, setSelectedSymbol, setLatestSignal, setStoreCandles, setSelectedTimeframe]);

  // Reload candles when timeframe changes (but not on initial load)
  useEffect(() => {
    if (!selectedTimeframe || isLoading) return;
    
    const reloadCandles = async () => {
      try {
        const fetchedCandles = await fetchCandles(symbol, selectedTimeframe, 200);
        setCandles(fetchedCandles);
        setStoreCandles(fetchedCandles);
      } catch (error) {
        console.error("Error reloading candles:", error);
      }
    };

    reloadCandles();
  }, [selectedTimeframe, symbol, setStoreCandles, isLoading]);

  // Subscribe to real-time symbol updates
  useEffect(() => {
    const unsubscribe = subscribeToSymbolUpdates((update) => {
      if (update.symbol === symbol) {
        setSymbolDetails((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            price: update.price ?? prev.price,
            volume_24h: update.volume_24h ?? prev.volume_24h,
            market_cap: update.marketcap ?? prev.market_cap,
          };
        });
      }
    });

    return unsubscribe;
  }, [symbol]);

  // Sort signals based on sortField and sortDirection
  const sortedSignals = useMemo(() => {
    const sorted = [...signals].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case "price_score":
          const aEntryPrice = a.entry1 || a.price || 0;
          const aCurrentPrice = symbolDetails?.price ?? 0;
          const bEntryPrice = b.entry1 || b.price || 0;
          const bCurrentPrice = symbolDetails?.price ?? 0;
          aValue = aEntryPrice > 0 ? Math.abs(aCurrentPrice - aEntryPrice) / aEntryPrice : 0;
          bValue = bEntryPrice > 0 ? Math.abs(bCurrentPrice - bEntryPrice) / bEntryPrice : 0;
          break;
        case "direction":
          aValue = a.direction;
          bValue = b.direction;
          break;
        case "timestamp":
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
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
  }, [signals, sortField, sortDirection, symbolDetails?.price]);

  const handleSort = (field: "price_score" | "direction" | "timestamp") => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const SortIcon = ({ field }: { field: "price_score" | "direction" | "timestamp" }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }
    return sortDirection === "asc" ? <ArrowUp className="h-3 w-3 ml-1" /> : <ArrowDown className="h-3 w-3 ml-1" />;
  };

  const displaySymbol = symbol.replace("USDT", "/USDT");
  const priceChangeColor = priceChange24h !== null && priceChange24h >= 0 ? "text-green-400" : "text-red-400";
  const priceChangeIcon = priceChange24h !== null && priceChange24h >= 0 ? ArrowUp : ArrowDown;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-4 md:p-6">
        <div className="max-w-[1920px] mx-auto">
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading symbol data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="mx-auto max-w-[1920px] space-y-6">
        {/* Symbol Information Header */}
        <Card className="p-6 shadow-sm border-border/60">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-4">
              <Link href="/dashboard">
                <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
              </Link>
              {symbolDetails?.image_path ? (
                <img
                  src={symbolDetails.image_path}
                  alt={displaySymbol}
                  className="w-16 h-16 rounded-full object-cover shadow-inner"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center shadow-inner">
                  <span className="text-lg font-medium text-muted-foreground">
                    {symbolDetails?.base_asset?.charAt(0) || displaySymbol.charAt(0)}
                  </span>
                </div>
              )}
              <div>
                <p className="text-sm uppercase tracking-wide text-muted-foreground">Symbol Overview</p>
                <h1 className="text-3xl font-bold leading-tight text-foreground">{displaySymbol}</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  {symbolDetails?.base_asset || ""} / {symbolDetails?.quote_asset || "USDT"}
                </p>
              </div>
            </div>
            <div className="space-y-2 text-right">
              <div className="text-4xl font-semibold text-foreground">
                {formatPrice(symbolDetails?.price)}
              </div>
              {priceChange24h !== null && (
                <div className={`flex items-center justify-end gap-2 text-base font-semibold ${priceChangeColor}`}>
                  {priceChange24h >= 0 ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
                  {formatPercent(priceChange24h)}
                  <span className="text-xs text-muted-foreground">(24h)</span>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Responsive layout with primary focus on chart */}
        <div className="grid gap-6 xl:grid-cols-[minmax(0,2.1fr)_minmax(280px,1fr)]">
          {/* Chart + controls */}
          <Card className="p-6 shadow-md border-border/60">
            <div className="flex flex-wrap gap-4 items-center justify-between border-b pb-4">
              <div className="flex items-center gap-3">
                <Label htmlFor="timeframe" className="text-sm text-muted-foreground">Timeframe</Label>
                <TimeframeSelector />
              </div>
              <div className="flex flex-wrap gap-3">
                {[
                  { id: "show-swings", label: "Swings", value: chartSettings.showSwings, key: "showSwings" },
                  { id: "show-entry", label: "Entry/SL/TP", value: chartSettings.showEntrySLTP, key: "showEntrySLTP" },
                  { id: "show-rsi", label: "RSI", value: chartSettings.showRSI, key: "showRSI" },
                  { id: "show-tooltip", label: "Tooltip", value: chartSettings.showTooltip, key: "showTooltip" },
                  { id: "show-ma7", label: "MA(7)", value: chartSettings.showMA7, key: "showMA7" },
                  { id: "show-ma25", label: "MA(25)", value: chartSettings.showMA25, key: "showMA25" },
                  { id: "show-ma99", label: "MA(99)", value: chartSettings.showMA99, key: "showMA99" },
                ].map((setting) => (
                  <div className="flex items-center gap-2" key={setting.id}>
                    <Switch
                      id={setting.id}
                      checked={setting.value}
                      onCheckedChange={(checked: boolean) =>
                        updateChartSettings({ [setting.key]: checked } as Partial<typeof chartSettings>)
                      }
                    />
                    <Label htmlFor={setting.id} className="text-xs md:text-sm text-muted-foreground cursor-pointer">
                      {setting.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
            <div className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-foreground">Price Action</h2>
                  <p className="text-xs text-muted-foreground">
                    Live candles for {displaySymbol} • Timeframe {selectedTimeframe?.toUpperCase()}
                  </p>
                </div>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/50 p-2 shadow-inner">
                <ChartContainer height={520} />
              </div>
            </div>
          </Card>

          {/* Supporting cards */}
          <div className="space-y-6">
            {symbolDetails && (
              <Card className="p-5 shadow-sm border-border/60">
                <p className="text-sm font-medium text-muted-foreground mb-4">Market Metrics</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Market Cap</p>
                    <p className="text-lg font-semibold mt-1">{formatNumber(symbolDetails.market_cap)}</p>
                  </div>
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">24h Volume</p>
                    <p className="text-lg font-semibold mt-1">{formatNumber(symbolDetails.volume_24h)}</p>
                  </div>
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Circulating Supply</p>
                    <p className="text-lg font-semibold mt-1">{formatSupply(symbolDetails.circulating_supply)}</p>
                  </div>
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">24h Change</p>
                    <p className={`text-lg font-semibold mt-1 ${priceChangeColor}`}>
                      {priceChange24h !== null ? formatPercent(priceChange24h) : "-"}
                    </p>
                  </div>
                </div>
              </Card>
            )}

            <Card className="p-5 shadow-sm border-border/60">
              <p className="text-sm font-medium text-muted-foreground mb-4">Signal Snapshot</p>
              <div className="flex flex-col gap-4">
                <div className="rounded-lg border border-border/50 bg-muted/10 p-4">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Total Signals</p>
                  <p className="text-3xl font-semibold text-foreground mt-1">{stats.total}</p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/10 p-4">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Bias</p>
                  <div className="mt-2 flex items-center gap-3 text-sm">
                    <span className="font-semibold text-emerald-400">Long {stats.long}</span>
                    <span className="text-muted-foreground">/</span>
                    <span className="font-semibold text-rose-400">Short {stats.short}</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Signal History Table */}
        <Card className="p-6 shadow-md border-border/60">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <h2 className="text-xl font-semibold text-foreground">Signal History</h2>
              <p className="text-xs text-muted-foreground">Latest {signals.length} strategy signals</p>
            </div>
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => router.push("/dashboard")}>
              View on Dashboard
            </Button>
          </div>
          <div className="rounded-xl border border-border/50 overflow-hidden">
            <div className="hidden md:grid md:grid-cols-[110px_120px_1fr_160px_120px] bg-muted/40 px-4 py-3 text-xs font-semibold text-muted-foreground">
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 font-semibold text-muted-foreground hover:text-foreground justify-start"
                onClick={() => handleSort("direction")}
              >
                Direction
                <SortIcon field="direction" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 font-semibold text-muted-foreground hover:text-foreground justify-start"
                onClick={() => handleSort("price_score")}
              >
                Score
                <SortIcon field="price_score" />
              </Button>
              <span>Entries / Targets</span>
              <span>Confluence</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 font-semibold text-muted-foreground hover:text-foreground justify-end"
                onClick={() => handleSort("timestamp")}
              >
                Timestamp
                <SortIcon field="timestamp" />
              </Button>
            </div>
            <div className="divide-y divide-border/60 max-h-[640px] overflow-y-auto">
              {sortedSignals.map((signal, index) => (
                <motion.div
                  key={signal.id || index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className="grid gap-3 px-4 py-4 text-sm md:grid-cols-[110px_120px_1fr_160px_120px] items-start md:items-center hover:bg-muted/30"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant={signal.direction === "long" ? "long" : "short"} className="px-2 py-1 text-xs">
                      {signal.direction === "long" ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {signal.direction.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="font-semibold">
                    {(() => {
                      const entryPrice = signal.entry1 || signal.price || 0;
                      const currentPrice = symbolDetails?.price ?? null;

                      if (currentPrice !== null && entryPrice > 0) {
                        const priceScore = Math.abs(currentPrice - entryPrice) / entryPrice;
                        const percentage = (priceScore * 100).toFixed(2);
                        const colorClass =
                          priceScore < 0.01
                            ? "text-green-400"
                            : priceScore < 0.03
                            ? "text-yellow-400"
                            : "text-red-400";

                        return <span className={colorClass}>{percentage}%</span>;
                      }

                      return <span className="text-muted-foreground">-</span>;
                    })()}
                  </div>
                  <div className="space-y-1 text-xs text-muted-foreground">
                    <div className="flex flex-wrap gap-4 text-foreground">
                      <span>Entry {formatPrice(signal.entry1 || signal.price)}</span>
                      {signal.sl && <span>SL {formatPrice(signal.sl)}</span>}
                      {signal.tp1 && <span>TP1 {formatPrice(signal.tp1)}</span>}
                      {signal.tp2 && <span>TP2 {formatPrice(signal.tp2)}</span>}
                      {signal.tp3 && <span>TP3 {formatPrice(signal.tp3)}</span>}
                    </div>
                    {signal.swing_high && signal.swing_low && (
                      <div className="flex flex-wrap gap-4">
                        <span>Swing High {formatPrice(signal.swing_high)}</span>
                        <span>Swing Low {formatPrice(signal.swing_low)}</span>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {signal.confluence ? <ConfluenceBadges confluence={signal.confluence} /> : "—"}
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    {formatTimestamp(signal.timestamp)}
                  </div>
                </motion.div>
              ))}
              {signals.length === 0 && (
                <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                  No signals found for this symbol
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

