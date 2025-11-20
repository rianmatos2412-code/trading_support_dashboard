import { create } from "zustand";
import { Candle, SwingPoint, SRLevel, TradingSignal } from "@/lib/api";
import { Timeframe, Symbol, ChartSettings } from "@/lib/types";

interface MarketState {
  selectedSymbol: Symbol;
  selectedTimeframe: Timeframe;
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
  setSwingPoints: (swings) => set({ swingPoints: swings }),
  addSwingPoint: (swing) =>
    set((state) => ({
      swingPoints: [...state.swingPoints, swing].filter(
        (s) => s.symbol === swing.symbol && s.timeframe === swing.timeframe
      ),
    })),
  setSRLevels: (levels) => set({ srLevels: levels }),
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

