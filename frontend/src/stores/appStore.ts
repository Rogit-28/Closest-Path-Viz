/**
 * Zustand store for the pathfinding visualization application.
 * Manages all state: map, algorithms, animation, WebSocket, metrics.
 */
import { create } from 'zustand';
import type {
  AlgorithmType,
  Coordinate,
  PathfindingConfig,
  AlgorithmResult,
  NodeCoord,
} from '../types';
import { warmCache, calculateCacheRegion } from '../utils/api';

type LocationSource = 'gps' | 'ip' | 'manual' | 'loading' | 'error';
export type RunPhase = 'idle' | 'running' | 'completed';

interface ExploredNode {
  node_id: string;
  lat: number;
  lon: number;
  cost: number;
  algorithm: string;
}

interface ExploredEdge {
  from_node_id: string;
  to_node_id: string;
  from_lat: number;
  from_lon: number;
  to_lat: number;
  to_lon: number;
  cost: number;
  algorithm: string;
  geometry?: number[][];
  metadata?: Record<string, unknown>;
}

interface AppState {
  // Map state
  startPoint: Coordinate | null;
  endPoint: Coordinate | null;
  mapCenter: Coordinate;
  mapZoom: number;

  // User location
  userLocation: Coordinate | null;
  userLocationSource: LocationSource;
  userLocationError: string | null;

  // Algorithm config
  selectedAlgorithms: AlgorithmType[];
  config: PathfindingConfig;

  // Animation state
  isRunning: boolean;
  isPaused: boolean;
  currentAlgorithm: string | null;
  runPhase: RunPhase;
  canEditCoordinates: boolean;

  // Results
  results: AlgorithmResult[];
  exploredNodes: Record<string, ExploredNode[]>;  // algorithm -> nodes
  exploredEdges: Record<string, ExploredEdge[]>;  // algorithm -> edge candidates
  frontierSize: Record<string, number>;
  pathNodes: Record<string, NodeCoord[]>;
  pathGeometry: Record<string, [number, number][]>;

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
  wsWarning: string | null;

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
  setRunPhase: (phase: RunPhase) => void;
  setPaused: (paused: boolean) => void;
  setCurrentAlgorithm: (algo: string | null) => void;
  addExploredNode: (algo: string, node: ExploredNode) => void;
  addExploredEdge: (algo: string, edge: ExploredEdge) => void;
  setFrontierSize: (algo: string, size: number) => void;
  addResult: (result: AlgorithmResult) => void;
  setPathNodes: (algo: string, nodes: NodeCoord[]) => void;
  setPathGeometry: (algo: string, coordinates: [number, number][]) => void;
  setGraphInfo: (info: AppState['graphInfo']) => void;
  setWsConnected: (connected: boolean) => void;
  setWsError: (error: string | null) => void;
  setWsWarning: (warning: string | null) => void;
  toggleSettings: () => void;
  setShowSettings: (show: boolean) => void;
  toggleMetrics: () => void;
  setComparisonMode: (mode: boolean) => void;
  setUserLocation: (location: Coordinate | null, source: LocationSource, error?: string | null) => void;
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
  floyd_warshall_node_limit: 1000,
};

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  startPoint: null,
  endPoint: null,
  mapCenter: { lat: 40.7128, lon: -74.006 },
  mapZoom: 13,

  // User location
  userLocation: null,
  userLocationSource: 'loading',
  userLocationError: null,

  selectedAlgorithms: ['astar'],
  config: defaultConfig,

  isRunning: false,
  isPaused: false,
  currentAlgorithm: null,
  runPhase: 'idle',
  canEditCoordinates: true,

  results: [],
  exploredNodes: {},
  exploredEdges: {},
  frontierSize: {},
  pathNodes: {},
  pathGeometry: {},

  graphInfo: null,

  wsConnected: false,
  wsError: null,
  wsWarning: null,

  showSettings: false,
  showMetrics: true,
  comparisonMode: false,

  // Actions
  setStartPoint: (point) => set({ startPoint: point }),
  setEndPoint: (point) => {
    set({ endPoint: point });
    // When Point B is set and we have Point A, warm cache for the combined region
    const state = get();
    if (point && state.startPoint) {
      const { centerLat, centerLon, radiusKm } = calculateCacheRegion(
        state.startPoint.lat,
        state.startPoint.lon,
        point.lat,
        point.lon,
        5 // 5km buffer
      );
      // Round to 4 decimal places to match backend cache key formatting
      warmCache(centerLat, centerLon, parseFloat(radiusKm.toFixed(4)));
    }
  },
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

  setRunning: (running) =>
    set({
      isRunning: running,
    }),
  setRunPhase: (phase) =>
    set({
      runPhase: phase,
      isRunning: phase === 'running',
      canEditCoordinates: phase === 'idle',
    }),
  setPaused: (paused) => set({ isPaused: paused }),
  setCurrentAlgorithm: (algo) => set({ currentAlgorithm: algo }),

  addExploredNode: (algo, node) =>
    set((state) => ({
      exploredNodes: {
        ...state.exploredNodes,
        [algo]: [...(state.exploredNodes[algo] || []), node],
      },
    })),

  addExploredEdge: (algo, edge) =>
    set((state) => ({
      exploredEdges: {
        ...state.exploredEdges,
        [algo]: [...(state.exploredEdges[algo] || []), edge],
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

  setPathGeometry: (algo, coordinates) =>
    set((state) => ({
      pathGeometry: { ...state.pathGeometry, [algo]: coordinates },
    })),

  setGraphInfo: (info) => set({ graphInfo: info }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setWsError: (error) => set({ wsError: error }),
  setWsWarning: (warning) => set({ wsWarning: warning }),
  toggleSettings: () => set((state) => ({ showSettings: !state.showSettings })),
  setShowSettings: (show) => set({ showSettings: show }),
  toggleMetrics: () => set((state) => ({ showMetrics: !state.showMetrics })),
  setComparisonMode: (mode) => set({ comparisonMode: mode }),
  
  setUserLocation: (location, source, error = null) => {
    set({ 
      userLocation: location, 
      userLocationSource: source, 
      userLocationError: error,
    });
    // If we have a new location, warm the cache
    if (location) {
      warmCache(location.lat, location.lon, 15);
    }
  },

  reset: () =>
    set({
      startPoint: null,
      endPoint: null,
      isRunning: false,
      isPaused: false,
      currentAlgorithm: null,
      runPhase: 'idle',
      canEditCoordinates: true,
      results: [],
      exploredNodes: {},
      exploredEdges: {},
      frontierSize: {},
      pathNodes: {},
      pathGeometry: {},
      graphInfo: null,
      wsError: null,
      wsWarning: null,
    }),

  clearResults: () =>
    set({
      results: [],
      exploredNodes: {},
      exploredEdges: {},
      frontierSize: {},
      pathNodes: {},
      pathGeometry: {},
      currentAlgorithm: null,
      isRunning: false,
      isPaused: false,
      runPhase: 'idle',
      canEditCoordinates: true,
      wsError: null,
      wsWarning: null,
    }),
}));
