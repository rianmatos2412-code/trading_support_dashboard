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
import { ArrowLeft, Filter, Search } from "lucide-react";
import { SignalList } from "@/components/signals/SignalList";
import { useSignalsStore } from "@/stores/useSignalsStore";
import { useSignalFeed } from "@/hooks/useSignalFeed";
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

export function SignalsClient({ initialSignals }: SignalsClientProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [directionFilter, setDirectionFilter] = useState<"all" | "long" | "short">("all");
  const [minScore, setMinScore] = useState<number>(0);
  const setInitialSignals = useSignalsStore((state) => state.setInitialSignals);
  const signalIds = useSignalsStore((state) => state.signalIds);
  const revision = useSignalsStore((state) => state.revision);
  const { status, lastMessageAt } = useSignalFeed();

  useEffect(() => {
    setInitialSignals(initialSignals ?? []);
  }, [initialSignals, setInitialSignals]);

  const filteredIds = useMemo(() => {
    const lookup = useSignalsStore.getState().signalMap;
    const query = searchTerm.trim().toLowerCase();

    return signalIds.filter((id) => {
      const signal = lookup[id];
      if (!signal) return false;
      if (query && !signal.symbol.toLowerCase().includes(query)) return false;
      if (directionFilter !== "all" && signal.direction !== directionFilter) return false;
      if (minScore > 0 && (signal.market_score ?? 0) < minScore) return false;
      return true;
    });
  }, [signalIds, searchTerm, directionFilter, minScore, revision]);

  const totalSignals = signalIds.length;

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
                Rendering {filteredIds.length} / {totalSignals} signals
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

            <div className="flex items-center gap-2">
              <Label htmlFor="min-score">Min Score</Label>
              <Input
                id="min-score"
                type="number"
                min={0}
                max={100}
                value={minScore}
                onChange={(event) => setMinScore(Number(event.target.value) || 0)}
                className="w-[100px]"
              />
            </div>
          </div>
        </Card>

        <SignalList signalIds={filteredIds} />
      </div>
    </div>
  );
}

