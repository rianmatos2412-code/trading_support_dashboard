"use client";

import { useMarketStore } from "@/stores/useMarketStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"];

export function SymbolSelector() {
  const { selectedSymbol, setSelectedSymbol } = useMarketStore();

  return (
    <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
      <SelectTrigger className="w-[140px]">
        <SelectValue placeholder="Select symbol" />
      </SelectTrigger>
      <SelectContent>
        {SYMBOLS.map((symbol) => (
          <SelectItem key={symbol} value={symbol}>
            {symbol.replace("USDT", "/USDT")}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

