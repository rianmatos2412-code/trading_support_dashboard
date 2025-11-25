"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface MarketScoreProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
  currentPrice?: number | null;
  entryPrice?: number | null;
}

export function MarketScore({ 
  score, 
  size = "md", 
  showLabel = true,
  className,
  currentPrice,
  entryPrice,
}: MarketScoreProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const percentage = clampedScore / 100;

  const sizeClasses = {
    sm: "w-16 h-16 text-xs",
    md: "w-24 h-24 text-base",
    lg: "w-32 h-32 text-xl",
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-400 fill-emerald-400";
    if (score >= 75) return "text-green-400 fill-green-400";
    if (score >= 60) return "text-yellow-400 fill-yellow-400";
    if (score >= 45) return "text-orange-400 fill-orange-400";
    return "text-red-400 fill-red-400";
  };

  // Calculate price score (same logic as SignalsTable)
  let priceScore: number | null = null;
  if (currentPrice !== undefined && currentPrice !== null && entryPrice !== undefined && entryPrice !== null && entryPrice > 0) {
    priceScore = Math.abs(currentPrice - entryPrice) / entryPrice;
  }

  // Get color for price score
  const getPriceScoreColor = (score: number) => {
    if (score < 0.01) return "text-green-400 fill-green-400"; // < 1%
    if (score < 0.03) return "text-yellow-400 fill-yellow-400"; // 1-3%
    return "text-red-400 fill-red-400"; // > 3%
  };

  // Use price score color if available, otherwise use market score color
  const circleColor = priceScore !== null 
    ? getPriceScoreColor(priceScore)
    : getScoreColor(clampedScore);

  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - percentage);

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <div className={cn("relative", sizeClasses[size])}>
        <svg 
          className="transform -rotate-90 w-full h-full" 
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid meet"
        >
          <circle
            cx="50"
            cy="50"
            r="36"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            className="text-gray-700"
          />
          <motion.circle
            cx="50"
            cy="50"
            r="36"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={circleColor}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn("font-bold", circleColor)}>
            {Math.round(clampedScore)}
          </span>
        </div>
      </div>
      {showLabel && (
        <div className="flex flex-col items-center gap-1">
          {priceScore !== null && (
            <span className={cn("text-xs font-medium", priceScore < 0.01 ? "text-green-400" : priceScore < 0.03 ? "text-yellow-400" : "text-red-400")}>
              Price Score: {(priceScore * 100).toFixed(2)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}

