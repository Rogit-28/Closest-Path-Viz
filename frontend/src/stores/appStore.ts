/**
 * Zustand store for the pathfinding visualization application.
 * Manages all state: map, algorithms, animation, WebSocket, metrics.
 */
import { create } from 'zustand';
import type {
  AlgorithmType,
  HeuristicType,
  WeightFunction,
  Coordinate,
  PathfindingConfig,
  AlgorithmResult,
  NodeCoord,
  WsMessage,
} from '../types';

interface ExploredNode {
  node_id: string;
  lat: number;
  lon: number;
  cost: number;
  algorithm: string;
}

interface AppState {
  // Map state
  startPoint: Coordinate | null;
  endPoint: Coordinate | null;
  mapCenter: Coordinate;
  mapZoom: number;

  // Algorithm config
  selectedAlgorithms: AlgorithmType[];
  config: PathfindingConfig;

  // Animation state
  isRunning: boolean;
  isPaused: boolean;
  currentAlgorithm: string | null;

  // Results
  results: AlgorithmResult[];
  exploredNodes: Record<string, ExploredNode[]>;  // algorithm -> nodes
  frontierSize: Record<string, number>;
  pathNodes: Record<string, NodeCoord[]>;

  // Graph info
  graphInfo: {
    node_count: number;
    edge_count: number;
    fallback_speed_pct: number;
    source: string;
  } | null;

  // WebSocket
  wsConnected: boolean;
  wsError: string | null;

  // UI
  showSettings: boolean;
  showMetrics: boolean;
  comparisonMode: boolean;

  // Actions
  setStartPoint: (point: Coordinate | null) => void;
  setEndPoint: (point: Coordinate | null) => void;
  setMapCenter: (center: Coordinate) => void;
  setMapZoom: (zoom: number) => void;
  toggleAlgorithm: (algo: AlgorithmType) => void;
  setSelectedAlgorithms: (algos: AlgorithmType[]) => void;
  updateConfig: (partial: Partial<PathfindingConfig>) => void;
  setRunning: (running: boolean) => void;
  setPaused: (paused: boolean) => void;
  setCurrentAlgorithm: (algo: string | null) => void;
  addExploredNode: (algo: string, node: ExploredNode) => void;
  setFrontierSize: (algo: string, size: number) => void;
  addResult: (result: AlgorithmResult) => void;
  setPathNodes: (algo: string, nodes: NodeCoord[]) => void;
  setGraphInfo: (info: AppState['graphInfo']) => void;
  setWsConnected: (connected: boolean) => void;
  setWsError: (error: string | null) => void;
  toggleSettings: () => void;
  toggleMetrics: () => void;
  setComparisonMode: (mode: boolean) => void;
  reset: () => void;
  clearResults: () => void;
}

const defaultConfig: PathfindingConfig = {
  astar_heuristic: 'haversine',
  weight_function: 'distance',
  hybrid_weights: { alpha: 0.6, beta: 0.4 },
  k_paths: 1,
  animation_speed: 1,
  show_all_explored: true,
  animation_granularity: 'every_node',
};

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  startPoint: null,
  endPoint: null,
  mapCenter: { lat: 40.7128, lon: -74.006 },
  mapZoom: 13,

  selectedAlgorithms: ['astar'],
  config: defaultConfig,

  isRunning: false,
  isPaused: false,
  currentAlgorithm: null,

  results: [],
  exploredNodes: {},
  frontierSize: {},
  pathNodes: {},

  graphInfo: null,

  wsConnected: false,
  wsError: null,

  showSettings: false,
  showMetrics: true,
  comparisonMode: false,

  // Actions
  setStartPoint: (point) => set({ startPoint: point }),
  setEndPoint: (point) => set({ endPoint: point }),
  setMapCenter: (center) => set({ mapCenter: center }),
  setMapZoom: (zoom) => set({ mapZoom: zoom }),

  toggleAlgorithm: (algo) => {
    const current = get().selectedAlgorithms;
    if (current.includes(algo)) {
      if (current.length > 1) {
        set({ selectedAlgorithms: current.filter((a) => a !== algo) });
      }
    } else {
      set({ selectedAlgorithms: [...current, algo] });
    }
  },
  setSelectedAlgorithms: (algos) => set({ selectedAlgorithms: algos }),

  updateConfig: (partial) =>
    set((state) => ({ config: { ...state.config, ...partial } })),

  setRunning: (running) => set({ isRunning: running }),
  setPaused: (paused) => set({ isPaused: paused }),
  setCurrentAlgorithm: (algo) => set({ currentAlgorithm: algo }),

  addExploredNode: (algo, node) =>
    set((state) => ({
      exploredNodes: {
        ...state.exploredNodes,
        [algo]: [...(state.exploredNodes[algo] || []), node],
      },
    })),

  setFrontierSize: (algo, size) =>
    set((state) => ({
      frontierSize: { ...state.frontierSize, [algo]: size },
    })),

  addResult: (result) =>
    set((state) => ({ results: [...state.results, result] })),

  setPathNodes: (algo, nodes) =>
    set((state) => ({
      pathNodes: { ...state.pathNodes, [algo]: nodes },
    })),

  setGraphInfo: (info) => set({ graphInfo: info }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setWsError: (error) => set({ wsError: error }),
  toggleSettings: () => set((state) => ({ showSettings: !state.showSettings })),
  toggleMetrics: () => set((state) => ({ showMetrics: !state.showMetrics })),
  setComparisonMode: (mode) => set({ comparisonMode: mode }),

  reset: () =>
    set({
      startPoint: null,
      endPoint: null,
      isRunning: false,
      isPaused: false,
      currentAlgorithm: null,
      results: [],
      exploredNodes: {},
      frontierSize: {},
      pathNodes: {},
      graphInfo: null,
      wsError: null,
    }),

  clearResults: () =>
    set({
      results: [],
      exploredNodes: {},
      frontierSize: {},
      pathNodes: {},
      currentAlgorithm: null,
      isRunning: false,
      isPaused: false,
    }),
}));
