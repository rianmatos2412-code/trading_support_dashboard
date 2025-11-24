"use client";

import { useEffect, useState } from "react";
import { useSymbolData } from "@/hooks/useSymbolData";
import { SymbolItem } from "@/components/ui/SymbolManager";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SymbolsTable } from "@/components/table/SymbolsTable";

export default function SymbolsPage() {
  const router = useRouter();
  const { symbols, isLoading } = useSymbolData();
  const [filteredSymbols, setFilteredSymbols] = useState<SymbolItem[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  // Filter symbols by search term
  useEffect(() => {
    let filtered = [...symbols];

    // Search filter
    if (searchTerm) {
      const query = searchTerm.toLowerCase().trim();
      filtered = filtered.filter(
        (item) =>
          item.symbol.toLowerCase().includes(query) ||
          item.base.toLowerCase().includes(query) ||
          item.quote.toLowerCase().includes(query)
      );
    }

    setFilteredSymbols(filtered);
  }, [symbols, searchTerm]);

  const handleRowClick = (symbol: string) => {
    router.push(`/symbol/${symbol}`);
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="max-w-[1920px] mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Symbols</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {filteredSymbols.length} symbol{filteredSymbols.length !== 1 ? "s" : ""} found
                {searchTerm && ` (out of ${symbols.length} total)`}
                {!searchTerm && ` (${symbols.length} total)`}
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <Card className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[200px]">
              <Label htmlFor="search" className="sr-only">
                Search
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by symbol or base asset..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

          </div>
        </Card>

        {/* Symbols Table */}
        {isLoading ? (
          <Card className="p-12">
            <div className="text-center">
              <p className="text-muted-foreground">Loading symbols...</p>
            </div>
          </Card>
        ) : (
          <SymbolsTable symbols={filteredSymbols} onRowClick={handleRowClick} />
        )}
      </div>
    </div>
  );
}

