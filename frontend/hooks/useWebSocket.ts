import { useEffect, useRef, useCallback } from "react";
import { useMarketStore } from "@/stores/useMarketStore";
import { TradingSignal, Candle, SwingPoint } from "@/lib/api";
import { notifySymbolUpdate } from "@/hooks/useSymbolData";
import { SymbolItem } from "@/components/ui/SymbolManager";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export type WebSocketEvent =
  | { type: "signal"; data: TradingSignal }
  | { type: "candle"; data: Candle }
  | { type: "swing"; data: SwingPoint }
  | { type: "symbol_update"; data: Partial<SymbolItem> }
  | { type: "marketcap_update"; data: Partial<SymbolItem> }
  | { type: "indicator"; data: any }
  | { type: "connected" | "subscribed" | "error"; message?: string; symbol?: string; timeframe?: string };

export function useWebSocket(symbol?: string, timeframe?: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;
  const reconnectDelay = useRef(1000); // Start with 1 second
  const isConnectingRef = useRef(false);
  const isMountedRef = useRef(true);

  const {
    addSignal,
    addCandle,
    addSwingPoint,
    selectedSymbol,
    selectedTimeframe,
    setError,
  } = useMarketStore();

  const connect = useCallback(() => {
    // Prevent multiple connection attempts
    if (isConnectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    // Close existing connection if it exists
    if (wsRef.current) {
      const currentState = wsRef.current.readyState;
      if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }

    try {
      isConnectingRef.current = true;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) {
          ws.close();
          return;
        }
        console.log("WebSocket connected to:", WS_URL);
        isConnectingRef.current = false;
        reconnectAttempts.current = 0;
        reconnectDelay.current = 1000;
        setError(null);

        // Subscribe to symbol and timeframe
        const currentSymbol = symbol || selectedSymbol;
        const currentTimeframe = timeframe || selectedTimeframe;
        const subscribeMessage = {
          type: "subscribe",
          symbol: currentSymbol,
          timeframe: currentTimeframe,
        };
        console.log("Subscribing to:", subscribeMessage);
        ws.send(JSON.stringify(subscribeMessage));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "symbol_update") {
            // if (message.data.symbol === "BTCUSDT") {
            //   console.log("current time:", new Date().toISOString());
            //   console.log("timestamp:", message.data.timestamp);
            //   console.log("BTCUSDT price updated:", message.data.price);
            // }
          }
          // console.log("WebSocket message received:", message);
          handleMessage(message);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        if (!isMountedRef.current) return;
        console.error("WebSocket error:", error);
        isConnectingRef.current = false;
        setError("WebSocket connection error");
      };

      ws.onclose = (event) => {
        if (!isMountedRef.current) return;
        console.log("WebSocket disconnected", event.code, event.reason);
        isConnectingRef.current = false;
        wsRef.current = null;

        // Only attempt reconnection if it wasn't a manual close (code 1000)
        if (event.code !== 1000 && isMountedRef.current) {
          // Attempt reconnection
          if (reconnectAttempts.current < maxReconnectAttempts) {
            reconnectAttempts.current++;
            reconnectTimeoutRef.current = setTimeout(() => {
              if (isMountedRef.current) {
                connect();
              }
            }, reconnectDelay.current);
            reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000); // Max 30 seconds
          } else {
            setError("WebSocket connection lost. Please refresh the page.");
          }
        }
      };
    } catch (error) {
      console.error("Error connecting WebSocket:", error);
      isConnectingRef.current = false;
      if (isMountedRef.current) {
        setError("Failed to connect to WebSocket");
      }
    }
  }, [symbol, timeframe, selectedSymbol, selectedTimeframe, setError]);

  const handleMessage = useCallback(
    (message: WebSocketEvent) => {
      switch (message.type) {
        case "signal":
          addSignal(message.data);
          
          // Extract swing high/low points from strategy_alert signal
          // and add them as swing points to the store
          if (message.data.swing_high && message.data.swing_high_timestamp) {
            const swingHigh: SwingPoint = {
              id: Date.now(), // Generate unique ID
              symbol: message.data.symbol,
              timeframe: message.data.timeframe || "unknown",
              type: "high",
              price: message.data.swing_high,
              timestamp: message.data.swing_high_timestamp,
            };
            addSwingPoint(swingHigh);
          }
          
          if (message.data.swing_low && message.data.swing_low_timestamp) {
            const swingLow: SwingPoint = {
              id: Date.now() + 1, // Generate unique ID
              symbol: message.data.symbol,
              timeframe: message.data.timeframe || "unknown",
              type: "low",
              price: message.data.swing_low,
              timestamp: message.data.swing_low_timestamp,
            };
            addSwingPoint(swingLow);
          }
          break;
        case "candle":
          addCandle(message.data);
          break;
        case "swing":
          addSwingPoint(message.data);
          break;
        case "symbol_update":
          // Notify symbol data subscribers about the update
          notifySymbolUpdate(message.data);
          break;
        case "marketcap_update":
          // Notify symbol data subscribers about market cap/volume update
          notifySymbolUpdate(message.data);
          break;
        case "connected":
        case "subscribed":
          // Handle connection/subscription confirmations
          console.log("WebSocket:", message.type, message.message);
          break;
        case "indicator":
          // Handle indicator updates
          console.log("Indicator update:", message.data);
          break;
        default:
          console.warn("Unknown WebSocket message type:", message);
      }
    },
    [addSignal, addCandle, addSwingPoint]
  );

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      const currentState = wsRef.current.readyState;
      // Only close if not already closed or closing
      if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) {
        wsRef.current.close(1000, "Component unmounting"); // 1000 = normal closure
      }
      wsRef.current = null;
    }
    isConnectingRef.current = false;
  }, []);

  useEffect(() => {
    isMountedRef.current = true;

    // Disconnect previous connection
    disconnect();

    // Small delay to ensure previous connection is fully closed
    const connectTimeout = setTimeout(() => {
      if (isMountedRef.current && WS_URL) {
        connect();
      } else if (!WS_URL) {
        // Fallback to polling if WebSocket is not available
        console.log("WebSocket not configured, using REST API polling");
      }
    }, 100);

    return () => {
      isMountedRef.current = false;
      clearTimeout(connectTimeout);
      disconnect();
    };
  }, [symbol, timeframe, selectedSymbol, selectedTimeframe, connect, disconnect]);

  return { connect, disconnect };
}

