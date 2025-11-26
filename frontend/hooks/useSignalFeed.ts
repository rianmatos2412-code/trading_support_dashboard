"use client";

import { useEffect, useRef, useState } from "react";
import { TradingSignal } from "@/lib/api";
import { useSignalsStore } from "@/stores/useSignalsStore";

const SIGNALS_WS_URL =
  process.env.NEXT_PUBLIC_SIGNALS_WS_URL || "ws://localhost:8000/ws";
const FLUSH_INTERVAL_MS = 300;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 15_000;

type FeedStatus = "idle" | "connecting" | "connected" | "disconnected";

const isTradingSignal = (value: unknown): value is TradingSignal => {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return "id" in record && "symbol" in record;
};

const normalizeSignalPayload = (payload: unknown): TradingSignal[] => {
  if (!payload) return [];
  if (Array.isArray(payload)) {
    return payload.filter(isTradingSignal);
  }
  if (isTradingSignal(payload)) {
    return [payload];
  }
  if (typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (Array.isArray(record.signals)) {
      return record.signals.filter(isTradingSignal);
    }
    if (record.type === "signal" && record.data && isTradingSignal(record.data)) {
      return [record.data];
    }
    if (
      record.type === "signals" &&
      Array.isArray(record.data)
    ) {
      return record.data.filter(isTradingSignal);
    }
  }
  return [];
};

export function useSignalFeed() {
  const updateBatch = useSignalsStore((state) => state.updateBatch);
  const [status, setStatus] = useState<FeedStatus>("idle");
  const [lastMessageAt, setLastMessageAt] = useState<number | null>(null);
  const queueRef = useRef<TradingSignal[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const flushIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const isUnmountedRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    isUnmountedRef.current = false;

    const flushQueue = () => {
      if (!queueRef.current.length) return;
      const batch = queueRef.current.splice(0, queueRef.current.length);
      updateBatch(batch);
    };

    const cleanupSocket = () => {
      const socket = socketRef.current;
      if (socket) {
        socket.onopen = null;
        socket.onclose = null;
        socket.onerror = null;
        socket.onmessage = null;
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
          socket.close(1000, "component unmount");
        }
      }
      socketRef.current = null;
    };

    const scheduleReconnect = () => {
      if (isUnmountedRef.current) return;
      if (reconnectTimeoutRef.current) return;
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectTimeoutRef.current = null;
        connect();
      }, backoffRef.current);
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
    };

    const connect = () => {
      if (isUnmountedRef.current) return;
      cleanupSocket();
      setStatus("connecting");
      try {
        socketRef.current = new WebSocket(SIGNALS_WS_URL);
      } catch (error) {
        console.warn("Failed to establish signals WebSocket", error);
        setStatus("disconnected");
        scheduleReconnect();
        return;
      }

      const socket = socketRef.current;
      if (!socket) return;

      socket.onopen = () => {
        if (isUnmountedRef.current) return;
        setStatus("connected");
        backoffRef.current = INITIAL_BACKOFF_MS;
      };

      socket.onmessage = (event) => {
        if (isUnmountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data);
          const signals = normalizeSignalPayload(parsed);
          if (signals.length) {
            queueRef.current.push(...signals);
            setLastMessageAt(Date.now());
          }
        } catch (error) {
          console.error("Unable to parse WebSocket payload", error);
        }
      };

      socket.onerror = () => {
        if (isUnmountedRef.current) return;
        setStatus("disconnected");
      };

      socket.onclose = () => {
        if (isUnmountedRef.current) return;
        setStatus("disconnected");
        scheduleReconnect();
      };
    };

    flushIntervalRef.current = setInterval(flushQueue, FLUSH_INTERVAL_MS);
    connect();

    return () => {
      isUnmountedRef.current = true;
      if (flushIntervalRef.current) {
        clearInterval(flushIntervalRef.current);
        flushIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      flushQueue();
      cleanupSocket();
      setStatus("idle");
    };
  }, [updateBatch]);

  return { status, lastMessageAt };
}

export type { FeedStatus };


