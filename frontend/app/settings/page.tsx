"use client";

import { useEffect, useState } from "react";
import { useSettingsStore } from "@/stores/useSettingsStore";
import { Settings, DEFAULT_SETTINGS } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Save, RotateCcw } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  fetchStrategyConfig,
  updateStrategyConfigs,
  StrategyConfig,
} from "@/lib/api";

export default function SettingsPage() {
  const { settings, updateSettings, resetSettings, saveSettings } = useSettingsStore();
  const [localSettings, setLocalSettings] = useState<Settings>(settings);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleUpdate = (path: string, value: number) => {
    const keys = path.split(".");
    const newSettings = { ...localSettings };
    let current: any = newSettings;
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    
    setLocalSettings(newSettings);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    try {
      updateSettings(localSettings);
      await saveSettings();
      setSaveMessage("Settings saved successfully!");
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      console.error("Error saving settings:", error);
      setSaveMessage("Error saving settings. They are saved locally.");
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    resetSettings();
    setLocalSettings(DEFAULT_SETTINGS);
    setSaveMessage("Settings reset to defaults");
    setTimeout(() => setSaveMessage(null), 3000);
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="max-w-4xl mx-auto space-y-4">
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
              <h1 className="text-2xl font-bold text-foreground">Settings</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Configure trading parameters and indicators
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleReset}>
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              <Save className="h-4 w-4 mr-2" />
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>

        {saveMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 bg-primary/10 border border-primary/20 rounded-lg text-sm text-primary"
          >
            {saveMessage}
          </motion.div>
        )}

        <Tabs defaultValue="strategy" className="space-y-4">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="strategy">Strategy Config</TabsTrigger>
            <TabsTrigger value="fib">Fibonacci</TabsTrigger>
            <TabsTrigger value="tp">Take Profit</TabsTrigger>
            <TabsTrigger value="confluence">Confluence</TabsTrigger>
            <TabsTrigger value="swing">Swing Detection</TabsTrigger>
          </TabsList>

          {/* Strategy Configuration */}
          <TabsContent value="strategy" className="space-y-4">
            <StrategyConfigTab />
          </TabsContent>

          {/* Fibonacci Levels */}
          <TabsContent value="fib" className="space-y-4">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Fibonacci Levels</h3>
              
              <div className="space-y-6">
                {/* Long Settings */}
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-green-400">Long Position</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="long-entry1">Entry 1</Label>
                      <Input
                        id="long-entry1"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.long.entry1}
                        onChange={(e) =>
                          handleUpdate("fibLevels.long.entry1", parseFloat(e.target.value))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="long-entry2">Entry 2</Label>
                      <Input
                        id="long-entry2"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.long.entry2}
                        onChange={(e) =>
                          handleUpdate("fibLevels.long.entry2", parseFloat(e.target.value))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="long-sl">Stop Loss</Label>
                      <Input
                        id="long-sl"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.long.sl}
                        onChange={(e) =>
                          handleUpdate("fibLevels.long.sl", parseFloat(e.target.value))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="long-approaching">Approaching</Label>
                      <Input
                        id="long-approaching"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.long.approaching}
                        onChange={(e) =>
                          handleUpdate("fibLevels.long.approaching", parseFloat(e.target.value))
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* Short Settings */}
                <div className="space-y-4 pt-4 border-t">
                  <h4 className="text-sm font-medium text-red-400">Short Position</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="short-entry1">Entry 1</Label>
                      <Input
                        id="short-entry1"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.short.entry1}
                        onChange={(e) =>
                          handleUpdate("fibLevels.short.entry1", parseFloat(e.target.value))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="short-entry2">Entry 2</Label>
                      <Input
                        id="short-entry2"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.short.entry2}
                        onChange={(e) =>
                          handleUpdate("fibLevels.short.entry2", parseFloat(e.target.value))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="short-sl">Stop Loss</Label>
                      <Input
                        id="short-sl"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.short.sl}
                        onChange={(e) =>
                          handleUpdate("fibLevels.short.sl", parseFloat(e.target.value))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="short-approaching">Approaching</Label>
                      <Input
                        id="short-approaching"
                        type="number"
                        step="0.001"
                        min="0"
                        max="1"
                        value={localSettings.fibLevels.short.approaching}
                        onChange={(e) =>
                          handleUpdate("fibLevels.short.approaching", parseFloat(e.target.value))
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* Pullback Start */}
                <div className="space-y-2 pt-4 border-t">
                  <Label htmlFor="pullback-start">Pullback Start</Label>
                  <Input
                    id="pullback-start"
                    type="number"
                    step="0.001"
                    min="0"
                    max="1"
                    value={localSettings.fibLevels.pullbackStart}
                    onChange={(e) =>
                      handleUpdate("fibLevels.pullbackStart", parseFloat(e.target.value))
                    }
                  />
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Take Profit Multipliers */}
          <TabsContent value="tp" className="space-y-4">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Take Profit Multipliers</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tp1">TP1 Multiplier</Label>
                  <Input
                    id="tp1"
                    type="number"
                    step="0.1"
                    min="0"
                    value={localSettings.slMultipliers.tp1}
                    onChange={(e) =>
                      handleUpdate("slMultipliers.tp1", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tp2">TP2 Multiplier</Label>
                  <Input
                    id="tp2"
                    type="number"
                    step="0.1"
                    min="0"
                    value={localSettings.slMultipliers.tp2}
                    onChange={(e) =>
                      handleUpdate("slMultipliers.tp2", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tp3">TP3 Multiplier</Label>
                  <Input
                    id="tp3"
                    type="number"
                    step="0.1"
                    min="0"
                    value={localSettings.slMultipliers.tp3}
                    onChange={(e) =>
                      handleUpdate("slMultipliers.tp3", parseFloat(e.target.value))
                    }
                  />
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">General</h3>
              <div className="space-y-2">
                <Label htmlFor="min-score">Minimum Score</Label>
                <Input
                  id="min-score"
                  type="number"
                  min="0"
                  max="100"
                  value={localSettings.minScore}
                  onChange={(e) =>
                    handleUpdate("minScore", parseFloat(e.target.value))
                  }
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Minimum market score required for signal generation (0-100)
                </p>
              </div>
            </Card>
          </TabsContent>

          {/* Confluence Weights */}
          <TabsContent value="confluence" className="space-y-4">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Confluence Indicator Weights</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Adjust the weight of each confluence indicator in the scoring system.
              </p>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="weight-ob">Order Block (OB)</Label>
                  <Input
                    id="weight-ob"
                    type="number"
                    min="0"
                    max="100"
                    value={localSettings.confluenceWeights.ob}
                    onChange={(e) =>
                      handleUpdate("confluenceWeights.ob", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight-sr">Support/Resistance (SR)</Label>
                  <Input
                    id="weight-sr"
                    type="number"
                    min="0"
                    max="100"
                    value={localSettings.confluenceWeights.sr}
                    onChange={(e) =>
                      handleUpdate("confluenceWeights.sr", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight-rsi">RSI</Label>
                  <Input
                    id="weight-rsi"
                    type="number"
                    min="0"
                    max="100"
                    value={localSettings.confluenceWeights.rsi}
                    onChange={(e) =>
                      handleUpdate("confluenceWeights.rsi", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight-cvd">CVD</Label>
                  <Input
                    id="weight-cvd"
                    type="number"
                    min="0"
                    max="100"
                    value={localSettings.confluenceWeights.cvd}
                    onChange={(e) =>
                      handleUpdate("confluenceWeights.cvd", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight-fib">Fibonacci (FIB)</Label>
                  <Input
                    id="weight-fib"
                    type="number"
                    min="0"
                    max="100"
                    value={localSettings.confluenceWeights.fib}
                    onChange={(e) =>
                      handleUpdate("confluenceWeights.fib", parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight-trend">Trend</Label>
                  <Input
                    id="weight-trend"
                    type="number"
                    min="0"
                    max="100"
                    value={localSettings.confluenceWeights.trend}
                    onChange={(e) =>
                      handleUpdate("confluenceWeights.trend", parseFloat(e.target.value))
                    }
                  />
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Swing Detection */}
          <TabsContent value="swing" className="space-y-4">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Swing Detection Parameters</h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="lookback">Lookback Periods</Label>
                  <Input
                    id="lookback"
                    type="number"
                    min="1"
                    max="50"
                    value={localSettings.swingDetection.lookbackPeriods}
                    onChange={(e) =>
                      handleUpdate("swingDetection.lookbackPeriods", parseInt(e.target.value))
                    }
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Number of periods to look back when detecting swing points
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="strength">Strength</Label>
                  <Input
                    id="strength"
                    type="number"
                    min="1"
                    max="20"
                    value={localSettings.swingDetection.strength}
                    onChange={(e) =>
                      handleUpdate("swingDetection.strength", parseInt(e.target.value))
                    }
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Minimum strength required for a swing point to be detected
                  </p>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// Strategy Configuration Component
function StrategyConfigTab() {
  const [config, setConfig] = useState<StrategyConfig>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    try {
      const data = await fetchStrategyConfig();
      setConfig(data);
    } catch (error) {
      console.error("Error loading strategy config:", error);
      setSaveMessage("Error loading configuration");
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdate = (key: string, value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    try {
      // Convert all values to strings for API
      const configsToSave: Record<string, string> = {};
      for (const [key, value] of Object.entries(config)) {
        if (key === "swing_high_low_pruning_score") {
          // Keep JSON as string
          configsToSave[key] =
            typeof value === "string" ? value : JSON.stringify(value);
        } else {
          configsToSave[key] = String(value);
        }
      }
      await updateStrategyConfigs(configsToSave);
      setSaveMessage("Strategy configuration saved successfully!");
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      console.error("Error saving strategy config:", error);
      setSaveMessage("Error saving configuration");
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <p className="text-muted-foreground">Loading configuration...</p>
      </Card>
    );
  }

  return (
    <>
      {saveMessage && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-primary/10 border border-primary/20 rounded-lg text-sm text-primary"
        >
          {saveMessage}
        </motion.div>
      )}

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Strategy Configuration</h3>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
        </div>

        <div className="space-y-6">
          {/* Market Data Limits */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium">Market Data Limits</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="market_data_limit">Market Data Limit</Label>
                <Input
                  id="market_data_limit"
                  type="number"
                  value={config.market_data_limit || ""}
                  onChange={(e) =>
                    handleUpdate("market_data_limit", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="symbol_limit">Symbol Limit</Label>
                <Input
                  id="symbol_limit"
                  type="number"
                  value={config.symbol_limit || ""}
                  onChange={(e) => handleUpdate("symbol_limit", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="limit_market_cap">Min Market Cap (USD)</Label>
                <Input
                  id="limit_market_cap"
                  type="number"
                  value={config.limit_market_cap || ""}
                  onChange={(e) =>
                    handleUpdate("limit_market_cap", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="limit_volume_up">Min 24h Volume (USD)</Label>
                <Input
                  id="limit_volume_up"
                  type="number"
                  value={config.limit_volume_up || ""}
                  onChange={(e) =>
                    handleUpdate("limit_volume_up", e.target.value)
                  }
                />
              </div>
            </div>
          </div>

          {/* Fibonacci Levels */}
          <div className="space-y-4 pt-4 border-t">
            <h4 className="text-sm font-medium">Fibonacci Levels</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="bullish_fib_level_lower">
                  Bullish Fib Lower
                </Label>
                <Input
                  id="bullish_fib_level_lower"
                  type="number"
                  step="0.001"
                  value={config.bullish_fib_level_lower || ""}
                  onChange={(e) =>
                    handleUpdate("bullish_fib_level_lower", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bullish_fib_level_higher">
                  Bullish Fib Higher
                </Label>
                <Input
                  id="bullish_fib_level_higher"
                  type="number"
                  step="0.001"
                  value={config.bullish_fib_level_higher || ""}
                  onChange={(e) =>
                    handleUpdate("bullish_fib_level_higher", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bullish_sl_fib_level">
                  Bullish SL Fib Level
                </Label>
                <Input
                  id="bullish_sl_fib_level"
                  type="number"
                  step="0.001"
                  value={config.bullish_sl_fib_level || ""}
                  onChange={(e) =>
                    handleUpdate("bullish_sl_fib_level", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bearish_fib_level">Bearish Fib Level</Label>
                <Input
                  id="bearish_fib_level"
                  type="number"
                  step="0.001"
                  value={config.bearish_fib_level || ""}
                  onChange={(e) =>
                    handleUpdate("bearish_fib_level", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bearish_sl_fib_level">
                  Bearish SL Fib Level
                </Label>
                <Input
                  id="bearish_sl_fib_level"
                  type="number"
                  step="0.001"
                  value={config.bearish_sl_fib_level || ""}
                  onChange={(e) =>
                    handleUpdate("bearish_sl_fib_level", e.target.value)
                  }
                />
              </div>
            </div>
          </div>

          {/* Take Profit Levels */}
          <div className="space-y-4 pt-4 border-t">
            <h4 className="text-sm font-medium">Take Profit Levels</h4>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tp1_fib_level">TP1 Fib Level</Label>
                <Input
                  id="tp1_fib_level"
                  type="number"
                  step="0.001"
                  value={config.tp1_fib_level || ""}
                  onChange={(e) => handleUpdate("tp1_fib_level", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tp2_fib_level">TP2 Fib Level</Label>
                <Input
                  id="tp2_fib_level"
                  type="number"
                  step="0.001"
                  value={config.tp2_fib_level || ""}
                  onChange={(e) => handleUpdate("tp2_fib_level", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tp3_fib_level">TP3 Fib Level</Label>
                <Input
                  id="tp3_fib_level"
                  type="number"
                  step="0.001"
                  value={config.tp3_fib_level || ""}
                  onChange={(e) => handleUpdate("tp3_fib_level", e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Swing Detection */}
          <div className="space-y-4 pt-4 border-t">
            <h4 className="text-sm font-medium">Swing Detection</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="candle_counts_for_swing_high_low">
                  Candle Counts for Swing High/Low
                </Label>
                <Input
                  id="candle_counts_for_swing_high_low"
                  type="number"
                  value={config.candle_counts_for_swing_high_low || ""}
                  onChange={(e) =>
                    handleUpdate(
                      "candle_counts_for_swing_high_low",
                      e.target.value
                    )
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sensible_window">Sensible Window</Label>
                <Input
                  id="sensible_window"
                  type="number"
                  value={config.sensible_window || ""}
                  onChange={(e) =>
                    handleUpdate("sensible_window", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="swing_window">Swing Window</Label>
                <Input
                  id="swing_window"
                  type="number"
                  value={config.swing_window || ""}
                  onChange={(e) => handleUpdate("swing_window", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="swing_high_low_pruning_score">
                  Pruning Scores (JSON)
                </Label>
                <Input
                  id="swing_high_low_pruning_score"
                  type="text"
                  value={
                    typeof config.swing_high_low_pruning_score === "string"
                      ? config.swing_high_low_pruning_score
                      : JSON.stringify(
                          config.swing_high_low_pruning_score || {},
                          null,
                          2
                        )
                  }
                  onChange={(e) =>
                    handleUpdate(
                      "swing_high_low_pruning_score",
                      e.target.value
                    )
                  }
                />
                <p className="text-xs text-muted-foreground">
                  JSON format: {"{"}"BTCUSDT": 0.015, "ETHUSDT": 0.015{"}"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </>
  );
}

