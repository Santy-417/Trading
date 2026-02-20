import { create } from "zustand";
import type { AccountInfo, BotStatusResponse, PendingOrder, PerformanceMetrics, Position } from "@/types";

interface AppState {
  // Bot
  botStatus: BotStatusResponse | null;
  setBotStatus: (status: BotStatusResponse | null) => void;

  // Positions
  positions: Position[];
  setPositions: (positions: Position[]) => void;

  // Pending Orders
  pendingOrders: PendingOrder[];
  setPendingOrders: (orders: PendingOrder[]) => void;

  // Metrics
  metrics: PerformanceMetrics | null;
  setMetrics: (metrics: PerformanceMetrics | null) => void;

  // Account info (MT5 live data)
  accountInfo: AccountInfo | null;
  setAccountInfo: (info: AccountInfo | null) => void;

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

  pendingOrders: [],
  setPendingOrders: (orders) => set({ pendingOrders: orders }),

  metrics: null,
  setMetrics: (metrics) => set({ metrics }),

  accountInfo: null,
  setAccountInfo: (info) => set({ accountInfo: info }),

  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  activeSymbol: "EURUSD",
  setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),

  loading: {},
  setLoading: (key, value) =>
    set((s) => ({ loading: { ...s.loading, [key]: value } })),
}));
