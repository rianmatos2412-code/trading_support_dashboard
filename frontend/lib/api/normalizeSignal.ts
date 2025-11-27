import type { TradingSignal } from "@/lib/api";

const toNumber = (value: unknown): number | undefined => {
  if (value === null || value === undefined) return undefined;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

const toBoolean = (value: unknown): boolean => {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.toLowerCase();
    return normalized === "true" || normalized === "1";
  }
  return Boolean(value);
};

const toTimestamp = (value: unknown): string | undefined => {
  if (!value) return undefined;
  if (typeof value === "string") return value;
  if (value instanceof Date) return value.toISOString();
  return undefined;
};

const normalizeDirection = (value: unknown): "long" | "short" => {
  if (typeof value === "string") {
    return value.toLowerCase() === "short" ? "short" : "long";
  }
  return "long";
};

export function normalizeSignalPayload(payload: Record<string, any>): TradingSignal {
  const entry =
    toNumber(payload.entry1) ??
    toNumber(payload.entry_price) ??
    toNumber(payload.price) ??
    0;

  const timestamp =
    toTimestamp(payload.timestamp) ??
    toTimestamp(payload.created_at) ??
    new Date().toISOString();

  return {
    id: Number(
      payload.id ??
        payload.signal_id ??
        payload.alert_id ??
        Date.now()
    ),
    symbol: payload.symbol ?? payload.ticker ?? "UNKNOWN",
    timeframe: payload.timeframe ?? payload.time_frame ?? payload.interval,
    timestamp,
    market_score:
      toNumber(payload.market_score ?? payload.confidence_score) ?? 0,
    direction: normalizeDirection(payload.direction),
    price: toNumber(payload.price) ?? entry,
    entry1: entry,
    entry2: toNumber(payload.entry2 ?? payload.entry_2),
    sl: toNumber(payload.sl ?? payload.stop_loss),
    tp1: toNumber(payload.tp1 ?? payload.take_profit_1),
    tp2: toNumber(payload.tp2 ?? payload.take_profit_2),
    tp3: toNumber(payload.tp3 ?? payload.take_profit_3),
    swing_high: toNumber(payload.swing_high ?? payload.swing_high_price),
    swing_high_timestamp: toTimestamp(
      payload.swing_high_timestamp ?? payload.swingHighTimestamp
    ),
    swing_low: toNumber(payload.swing_low ?? payload.swing_low_price),
    swing_low_timestamp: toTimestamp(
      payload.swing_low_timestamp ?? payload.swingLowTimestamp
    ),
    support_level: toNumber(payload.support_level),
    resistance_level: toNumber(payload.resistance_level),
    confluence: payload.confluence ?? payload.risk_score ?? undefined,
    risk_reward_ratio: toNumber(payload.risk_reward_ratio),
    pullback_detected: toBoolean(payload.pullback_detected ?? false),
    confidence_score: toNumber(payload.confidence_score),
  };
}

export function mapAlertRecordToSignal(alert: Record<string, any>): TradingSignal {
  return normalizeSignalPayload({
    ...alert,
    price: alert.price ?? alert.entry_price,
    entry1: alert.entry_price,
    sl: alert.stop_loss,
    tp1: alert.take_profit_1,
    tp2: alert.take_profit_2,
    tp3: alert.take_profit_3,
    swing_high: alert.swing_high_price,
    swing_low: alert.swing_low_price,
  });
}

export function mapSignalResponseToSignal(signal: Record<string, any>): TradingSignal {
  return normalizeSignalPayload(signal);
}


