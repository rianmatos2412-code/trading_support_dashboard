import { create } from "zustand";
import { Candle, SwingPoint, SRLevel, TradingSignal, MarketMetadata } from "@/lib/api";
import {
  Timeframe,
  Symbol,
  ChartSettings,
  DEFAULT_SYMBOLS,
  DEFAULT_TIMEFRAMES,
} from "@/lib/types";

interface MarketState {
  selectedSymbol: Symbol;
  selectedTimeframe: Timeframe;
  availableSymbols: Symbol[];
  availableTimeframes: Timeframe[];
  symbolTimeframes: Record<string, Timeframe[]>;
  candles: Candle[];
  swingPoints: SwingPoint[];
  srLevels: SRLevel[];
  signals: TradingSignal[];
  latestSignal: TradingSignal | null;
  chartSettings: ChartSettings;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSelectedSymbol: (symbol: Symbol) => void;
  setSelectedTimeframe: (timeframe: Timeframe) => void;
  setCandles: (candles: Candle[]) => void;
  addCandle: (candle: Candle) => void;
  updateCandle: (candle: Candle) => void;
  setSwingPoints: (swings: SwingPoint[]) => void;
  addSwingPoint: (swing: SwingPoint) => void;
  setSRLevels: (levels: SRLevel[]) => void;
  setSignals: (signals: TradingSignal[]) => void;
  addSignal: (signal: TradingSignal) => void;
  setLatestSignal: (signal: TradingSignal | null) => void;
  updateChartSettings: (settings: Partial<ChartSettings>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setMarketMetadata: (metadata: MarketMetadata) => void;
  reset: () => void;
}

const defaultChartSettings: ChartSettings = {
  showFibs: true,
  showOrderBlocks: true,
  showSR: true,
  showSwings: true,
  showEntrySLTP: true,
};

export const useMarketStore = create<MarketState>((set) => ({
  selectedSymbol: "BTCUSDT",
  selectedTimeframe: "1h",
  availableSymbols: DEFAULT_SYMBOLS,
  availableTimeframes: DEFAULT_TIMEFRAMES,
  symbolTimeframes: DEFAULT_SYMBOLS.reduce<Record<string, Timeframe[]>>((acc, symbol) => {
    acc[symbol] = [...DEFAULT_TIMEFRAMES];
    return acc;
  }, {}),
  candles: [],
  swingPoints: [],
  srLevels: [],
  signals: [],
  latestSignal: null,
  chartSettings: defaultChartSettings,
  isLoading: false,
  error: null,

  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setSelectedTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),
  setCandles: (candles) => set({ candles }),
  addCandle: (candle) =>
    set((state) => {
      const existing = state.candles.findIndex(
        (c) => c.timestamp === candle.timestamp && c.symbol === candle.symbol
      );
      if (existing >= 0) {
        const updated = [...state.candles];
        updated[existing] = candle;
        return { candles: updated };
      }
      return { candles: [...state.candles, candle].sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      ) };
    }),
  updateCandle: (candle) =>
    set((state) => {
      const index = state.candles.findIndex(
        (c) => c.timestamp === candle.timestamp && c.symbol === candle.symbol
      );
      if (index >= 0) {
        const updated = [...state.candles];
        updated[index] = candle;
        return { candles: updated };
      }
      return state;
    }),
  setSwingPoints: (swings) => set({ swingPoints: Array.isArray(swings) ? swings : [] }),
  addSwingPoint: (swing) =>
    set((state) => {
      // Filter to only keep swing points for the same symbol/timeframe
      const filtered = state.swingPoints.filter(
        (s) => s.symbol === swing.symbol && s.timeframe === swing.timeframe
      );
      
      // Check if this swing point already exists (deduplicate by ID or timestamp+type)
      const exists = filtered.some(
        (s) => 
          (s.id && swing.id && s.id === swing.id) || 
          (s.timestamp === swing.timestamp && s.type === swing.type)
      );
      
      // Only add if it doesn't already exist
      if (exists) {
        return { swingPoints: filtered };
      }
      
      // Add the new swing point
      return { swingPoints: [...filtered, swing] };
    }),
  setSRLevels: (levels) => set({ srLevels: Array.isArray(levels) ? levels : [] }),
  setSignals: (signals) => set({ signals }),
  addSignal: (signal) =>
    set((state) => ({
      signals: [signal, ...state.signals].slice(0, 1000), // Keep last 1000
      latestSignal: signal.symbol === state.selectedSymbol ? signal : state.latestSignal,
    })),
  setLatestSignal: (signal) => set({ latestSignal: signal }),
  updateChartSettings: (settings) =>
    set((state) => ({
      chartSettings: { ...state.chartSettings, ...settings },
    })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setMarketMetadata: (metadata) =>
    set((state) => {
      const nextSymbolTimeframes =
        metadata.symbolTimeframes &&
        Object.keys(metadata.symbolTimeframes).length > 0
          ? Object.entries(metadata.symbolTimeframes).reduce<Record<string, Timeframe[]>>(
              (acc, [symbol, timeframes]) => {
                acc[symbol] = [...timeframes];
                return acc;
              },
              {}
            )
          : state.symbolTimeframes;

      return {
        availableSymbols:
          metadata.symbols && metadata.symbols.length
            ? metadata.symbols
            : state.availableSymbols,
        availableTimeframes:
          metadata.timeframes && metadata.timeframes.length
            ? metadata.timeframes
            : state.availableTimeframes,
        symbolTimeframes: nextSymbolTimeframes,
      };
    }),
  reset: () =>
    set({
      candles: [],
      swingPoints: [],
      srLevels: [],
      signals: [],
      latestSignal: null,
      isLoading: false,
      error: null,
    }),
}));

