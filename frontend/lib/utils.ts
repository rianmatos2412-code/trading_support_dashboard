import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 8,
  }).format(price);
}

export function formatTimestamp(timestamp: string | Date): string {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function getScoreColor(score: number): string {
  if (score >= 90) return "text-neon";
  if (score >= 75) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  return "text-gray-400";
}

export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined || num === 0) return "-";
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
  return `$${num.toFixed(2)}`;
}

export function formatSupply(num: number | null | undefined): string {
  if (num === null || num === undefined || num === 0) return "-";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatPercent(num: number | null | undefined): string {
  if (num === null || num === undefined) return "-";
  const sign = num >= 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
}

export function formatTimeDelta(timestamp: string | Date | null | undefined): string {
  if (!timestamp) return "-";
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  } else if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else if (diffDays < 7) {
    return `${diffDays}d ago`;
  } else {
    // For older than a week, show weeks, months, or years
    const diffWeeks = Math.floor(diffDays / 7);
    const diffMonths = Math.floor(diffDays / 30);
    const diffYears = Math.floor(diffDays / 365);

    if (diffYears > 0) {
      return `${diffYears}${diffYears === 1 ? " year" : " years"} ago`;
    } else if (diffMonths > 0) {
      return `${diffMonths}${diffMonths === 1 ? " month" : " months"} ago`;
    } else {
      return `${diffWeeks}${diffWeeks === 1 ? " week" : " weeks"} ago`;
    }
  }
}

