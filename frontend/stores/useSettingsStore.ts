import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Settings, DEFAULT_SETTINGS } from "@/lib/types";

interface SettingsState {
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;
  resetSettings: () => void;
  saveSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      settings: DEFAULT_SETTINGS,

      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),

      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),

      saveSettings: async () => {
        // TODO: Implement API call to save settings to backend
        const { settings } = get();
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/settings`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(settings),
            }
          );
          if (!response.ok) throw new Error("Failed to save settings");
        } catch (error) {
          console.error("Error saving settings:", error);
          // Settings are persisted locally, so we can continue even if API fails
        }
      },
    }),
    {
      name: "trading-settings",
    }
  )
);

