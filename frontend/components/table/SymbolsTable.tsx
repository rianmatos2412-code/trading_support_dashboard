"use client";

import { useState, useMemo, useEffect } from "react";
import { SymbolItem } from "@/components/ui/SymbolManager";
import { Button } from "@/components/ui/button";
import { formatPrice, formatNumber, formatPercent } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

type SortField = "name" | "price" | "marketcap" | "volume_24h" | "change24h";
type SortDirection = "asc" | "desc";

interface SymbolsTableProps {
  symbols: SymbolItem[];
  onRowClick?: (symbol: string) => void;
}

export function SymbolsTable({ symbols, onRowClick }: SymbolsTableProps) {
  const router = useRouter();
  const [sortField, setSortField] = useState<SortField>("marketcap");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());

  const sortedSymbols = useMemo(() => {
    const sorted = [...symbols].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case "name":
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        case "price":
          aValue = a.price || 0;
          bValue = b.price || 0;
          break;
        case "marketcap":
          aValue = a.marketcap || 0;
          bValue = b.marketcap || 0;
          break;
        case "volume_24h":
          aValue = a.volume_24h || 0;
          bValue = b.volume_24h || 0;
          break;
        case "change24h":
          aValue = a.change24h || 0;
          bValue = b.change24h || 0;
          break;
        default:
          return 0;
      }

      // Handle missing values - put them at the end
      if (aValue === 0 && bValue !== 0) return 1;
      if (aValue !== 0 && bValue === 0) return -1;

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
  }, [symbols, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const handleRowClick = (symbol: string) => {
    if (onRowClick) {
      onRowClick(symbol);
    } else {
      router.push(`/symbol/${symbol}`);
    }
  };

  const handleImageOrNameClick = (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation();
    router.push(`/symbol/${symbol}`);
  };

  const handleImageError = (symbol: string) => {
    setImageErrors((prev) => new Set(prev).add(symbol));
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }
    return sortDirection === "asc"
      ? <ArrowUp className="h-3 w-3 ml-1" />
      : <ArrowDown className="h-3 w-3 ml-1" />;
  };

  if (symbols.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No symbols available</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-3 text-left min-w-[200px]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("name")}
                >
                  Name
                  <SortIcon field="name" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right min-w-[120px]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("price")}
                >
                  Price
                  <SortIcon field="price" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right min-w-[140px]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("marketcap")}
                >
                  Market Cap
                  <SortIcon field="marketcap" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right min-w-[140px]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("volume_24h")}
                >
                  Volume (24h)
                  <SortIcon field="volume_24h" />
                </Button>
              </th>
              <th className="px-4 py-3 text-right min-w-[120px]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 font-semibold"
                  onClick={() => handleSort("change24h")}
                >
                  Change (24h)
                  <SortIcon field="change24h" />
                </Button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedSymbols.map((symbol, index) => {
              const changeColor = symbol.change24h >= 0 ? "text-green-500" : "text-red-500";
              const hasImage = symbol.image_url && !imageErrors.has(symbol.symbol);

              return (
                <motion.tr
                  key={symbol.symbol}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className="border-b transition-colors hover:bg-muted/50 cursor-pointer"
                  onClick={() => handleRowClick(symbol.symbol)}
                >
                  {/* Name Column with Image */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {hasImage ? (
                        <img
                          src={symbol.image_url!}
                          alt={symbol.symbol}
                          className="w-8 h-8 rounded-full flex-shrink-0 object-cover cursor-pointer hover:opacity-80 transition-opacity"
                          onClick={(e) => handleImageOrNameClick(e, symbol.symbol)}
                          onError={() => handleImageError(symbol.symbol)}
                        />
                      ) : (
                        <div
                          className="w-8 h-8 rounded-full flex-shrink-0 bg-muted flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity"
                          onClick={(e) => handleImageOrNameClick(e, symbol.symbol)}
                        >
                          <span className="text-xs font-medium text-muted-foreground">
                            {symbol.base.charAt(0)}
                          </span>
                        </div>
                      )}
                      <div className="flex flex-col min-w-0">
                        <span
                          className="text-sm font-medium text-foreground cursor-pointer hover:underline"
                          onClick={(e) => handleImageOrNameClick(e, symbol.symbol)}
                        >
                          {symbol.base}/{symbol.quote}
                        </span>
                        <span className="text-xs text-muted-foreground truncate">
                          {symbol.symbol}
                        </span>
                      </div>
                    </div>
                  </td>

                  {/* Price Column */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm font-medium text-foreground">
                      ${formatPrice(symbol.price)}
                    </div>
                  </td>

                  {/* Market Cap Column */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm font-medium text-foreground">
                      {formatNumber(symbol.marketcap)}
                    </div>
                  </td>

                  {/* Volume (24h) Column */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm font-medium text-foreground">
                      {formatNumber(symbol.volume_24h)}
                    </div>
                  </td>

                  {/* Change (24h) Column */}
                  <td className="px-4 py-3 text-right">
                    <div className={`text-sm font-semibold ${changeColor}`}>
                      {formatPercent(symbol.change24h)}
                    </div>
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

