import { create } from "zustand";
import type { BotStatusResponse, PerformanceMetrics, Position } from "@/types";

interface AppState {
  // Bot
  botStatus: BotStatusResponse | null;
  setBotStatus: (status: BotStatusResponse | null) => void;

  // Positions
  positions: Position[];
  setPositions: (positions: Position[]) => void;

  // Metrics
  metrics: PerformanceMetrics | null;
  setMetrics: (metrics: PerformanceMetrics | null) => void;

  // UI
  sidebarOpen: boolean;
  toggleSidebar: () => void;

  // Active Symbol
  activeSymbol: string;
  setActiveSymbol: (symbol: string) => void;

  // Loading
  loading: Record<string, boolean>;
  setLoading: (key: string, value: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  botStatus: null,
  setBotStatus: (status) => set({ botStatus: status }),

  positions: [],
  setPositions: (positions) => set({ positions }),

  metrics: null,
  setMetrics: (metrics) => set({ metrics }),

  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  activeSymbol: "EURUSD",
  setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),

  loading: {},
  setLoading: (key, value) =>
    set((s) => ({ loading: { ...s.loading, [key]: value } })),
}));
