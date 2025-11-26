"use client";

import { useMarketStore } from "@/stores/useMarketStore";
import { TimeframeSelector } from "@/components/ui/TimeframeSelector";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

// Swings are now auto-calculated from candles, no refresh button needed
export function ChartControls() {
  const { chartSettings, updateChartSettings } = useMarketStore();

  return (
    <div className="flex flex-wrap items-center gap-4 p-4 bg-card rounded-lg border">
      <div className="flex items-center gap-2">
        <Label htmlFor="timeframe">Timeframe:</Label>
        <TimeframeSelector />
      </div>
      <div className="flex-1" />

      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Switch
            id="show-swings"
            checked={chartSettings.showSwings}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showSwings: checked })
            }
          />
          <Label htmlFor="show-swings" className="text-sm cursor-pointer">
            Swings
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="show-entry"
            checked={chartSettings.showEntrySLTP}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showEntrySLTP: checked })
            }
          />
          <Label htmlFor="show-entry" className="text-sm cursor-pointer">
            Entry/SL/TP
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="show-rsi"
            checked={chartSettings.showRSI}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showRSI: checked })
            }
          />
          <Label htmlFor="show-rsi" className="text-sm cursor-pointer">
            RSI
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="show-tooltip"
            checked={chartSettings.showTooltip}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showTooltip: checked })
            }
          />
          <Label htmlFor="show-tooltip" className="text-sm cursor-pointer">
            Tooltip
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="show-ma7"
            checked={chartSettings.showMA7}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showMA7: checked })
            }
          />
          <Label htmlFor="show-ma7" className="text-sm cursor-pointer">
            MA(7)
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="show-ma25"
            checked={chartSettings.showMA25}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showMA25: checked })
            }
          />
          <Label htmlFor="show-ma25" className="text-sm cursor-pointer">
            MA(25)
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="show-ma99"
            checked={chartSettings.showMA99}
            onCheckedChange={(checked: boolean) =>
              updateChartSettings({ showMA99: checked })
            }
          />
          <Label htmlFor="show-ma99" className="text-sm cursor-pointer">
            MA(99)
          </Label>
        </div>
      </div>
    </div>
  );
}

