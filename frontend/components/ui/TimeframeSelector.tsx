"use client";

import { useMarketStore } from "@/stores/useMarketStore";
import { Timeframe } from "@/lib/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m", "1h", "4h"];

export function TimeframeSelector() {
  const { selectedTimeframe, setSelectedTimeframe } = useMarketStore();

  return (
    <Select value={selectedTimeframe} onValueChange={(value) => setSelectedTimeframe(value as Timeframe)}>
      <SelectTrigger className="w-[100px]">
        <SelectValue placeholder="Timeframe" />
      </SelectTrigger>
      <SelectContent>
        {TIMEFRAMES.map((tf) => (
          <SelectItem key={tf} value={tf}>
            {tf}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

