/**
 * Playback store for client-side animation control.
 * 
 * Manages visualization event playback with real-time speed control,
 * pause/resume, and scrubbing capabilities.
 */
import { create } from 'zustand';

// Event types that come from the SSE stream
export interface PlaybackNodeEvent {
  type: 'node_visit';
  algorithm: string;
  node_id: string;
  lat: number;
  lon: number;
  cost: number;
  nodes_explored: number;
  metadata?: Record<string, unknown>;
}

export interface PlaybackEdgeEvent {
  type: 'edge_explore';
  algorithm: string;
  from_node_id: string;
  to_node_id: string;
  from_lat: number;
  from_lon: number;
  to_lat: number;
  to_lon: number;
  cost: number;
  nodes_explored: number;
  geometry?: number[][];
  metadata?: Record<string, unknown>;
}

export interface PlaybackFrontierEvent {
  type: 'frontier_update';
  algorithm: string;
  frontier_size: number;
  nodes_explored: number;
}

export type PlaybackEvent = PlaybackNodeEvent | PlaybackEdgeEvent | PlaybackFrontierEvent;

interface PlaybackState {
  // Per-algorithm event storage
  events: Record<string, PlaybackEvent[]>;
  playbackIndex: Record<string, number>;
  streamComplete: Record<string, boolean>;
  
  // Global playback state
  isPlaying: boolean;
  speed: number;  // 0.25, 0.5, 1, 2, 5, 10, 50, 0 (instant)
  activeAlgorithm: string | null;  // Which algo is being animated
  
  // Timing metrics
  renderStartTime: Record<string, number | null>;
  renderEndTime: Record<string, number | null>;
  
  // Actions
  addEvent: (event: PlaybackEvent) => void;
  addEvents: (events: PlaybackEvent[]) => void;
  markStreamComplete: (algo: string) => void;
  play: () => void;
  pause: () => void;
  togglePlayPause: () => void;
  setSpeed: (speed: number) => void;
  seekTo: (algo: string, index: number) => void;
  advancePlayback: (algo: string, count: number) => void;
  setActiveAlgorithm: (algo: string | null) => void;
  markRenderStart: (algo: string) => void;
  markRenderEnd: (algo: string) => void;
  reset: () => void;
  resetAlgorithm: (algo: string) => void;
  restartAlgorithmPlayback: (algo: string) => void;
  
  // Selectors (computed helpers)
  getVisibleNodeEvents: (algo: string) => PlaybackNodeEvent[];
  getVisibleEdgeEvents: (algo: string) => PlaybackEdgeEvent[];
  getProgress: (algo: string) => number;
  getTotalEvents: (algo: string) => number;
  getCurrentIndex: (algo: string) => number;
  isAlgoComplete: (algo: string) => boolean;
  getRenderTime: (algo: string) => number | null;
}

export const usePlaybackStore = create<PlaybackState>((set, get) => ({
  // Initial state
  events: {},
  playbackIndex: {},
  streamComplete: {},
  isPlaying: false,
  speed: 1,
  activeAlgorithm: null,
  renderStartTime: {},
  renderEndTime: {},

  // Add a single event
  addEvent: (event) => {
    const algo = event.algorithm;
    set((state) => ({
      events: {
        ...state.events,
        [algo]: [...(state.events[algo] || []), event],
      },
    }));
  },

  // Add multiple events at once (for batching)
  addEvents: (newEvents) => {
    if (newEvents.length === 0) return;
    
    set((state) => {
      const updated = { ...state.events };
      for (const event of newEvents) {
        const algo = event.algorithm;
        if (!updated[algo]) {
          updated[algo] = [];
        }
        updated[algo] = [...updated[algo], event];
      }
      return { events: updated };
    });
  },

  // Mark that all events for an algorithm have been received
  markStreamComplete: (algo) => {
    set((state) => ({
      streamComplete: { ...state.streamComplete, [algo]: true },
    }));
  },

  // Playback controls
  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  togglePlayPause: () => set((state) => ({ isPlaying: !state.isPlaying })),

  setSpeed: (speed) => {
    const state = get();
    set({ speed });
    
    // If speed is 0 (instant), jump all active algorithms to end
    if (speed === 0 && state.activeAlgorithm) {
      const algo = state.activeAlgorithm;
      const total = state.events[algo]?.length || 0;
      set((s) => ({
        playbackIndex: { ...s.playbackIndex, [algo]: total },
      }));
    }
  },

  // Seek to a specific position (for scrubber)
  seekTo: (algo, index) => {
    const total = get().events[algo]?.length || 0;
    const clampedIndex = Math.max(0, Math.min(index, total));
    set((state) => ({
      playbackIndex: { ...state.playbackIndex, [algo]: clampedIndex },
      isPlaying: false,  // Auto-pause when seeking
    }));
  },

  // Advance playback by N events (called by playback loop)
  advancePlayback: (algo, count) => {
    const state = get();
    const currentIndex = state.playbackIndex[algo] || 0;
    const total = state.events[algo]?.length || 0;
    const newIndex = Math.min(currentIndex + count, total);
    
    set((s) => ({
      playbackIndex: { ...s.playbackIndex, [algo]: newIndex },
    }));
    
    // Check if playback completed
    if (newIndex >= total && state.streamComplete[algo]) {
      // Mark render end time if not already set
      if (!state.renderEndTime[algo]) {
        get().markRenderEnd(algo);
      }
    }
  },

  setActiveAlgorithm: (algo) => {
    set({ activeAlgorithm: algo });
    // Start render timing when algorithm becomes active
    if (algo && !get().renderStartTime[algo]) {
      get().markRenderStart(algo);
    }
  },

  markRenderStart: (algo) => {
    set((state) => ({
      renderStartTime: { ...state.renderStartTime, [algo]: performance.now() },
    }));
  },

  markRenderEnd: (algo) => {
    set((state) => ({
      renderEndTime: { ...state.renderEndTime, [algo]: performance.now() },
    }));
  },

  // Reset all playback state
  reset: () => {
    set({
      events: {},
      playbackIndex: {},
      streamComplete: {},
      isPlaying: false,
      activeAlgorithm: null,
      renderStartTime: {},
      renderEndTime: {},
    });
  },

  // Reset a single algorithm (for re-running)
  resetAlgorithm: (algo) => {
    set((state) => {
      const newEvents = { ...state.events };
      const newPlaybackIndex = { ...state.playbackIndex };
      const newStreamComplete = { ...state.streamComplete };
      const newRenderStart = { ...state.renderStartTime };
      const newRenderEnd = { ...state.renderEndTime };
      
      delete newEvents[algo];
      delete newPlaybackIndex[algo];
      delete newStreamComplete[algo];
      delete newRenderStart[algo];
      delete newRenderEnd[algo];
      
      return {
        events: newEvents,
        playbackIndex: newPlaybackIndex,
        streamComplete: newStreamComplete,
        renderStartTime: newRenderStart,
        renderEndTime: newRenderEnd,
        activeAlgorithm: state.activeAlgorithm === algo ? null : state.activeAlgorithm,
      };
    });
  },

  restartAlgorithmPlayback: (algo) => {
    set((state) => {
      const hasAlgo = Boolean(state.events[algo]);
      if (!hasAlgo) {
        return { isPlaying: false };
      }

      return {
        playbackIndex: { ...state.playbackIndex, [algo]: 0 },
        renderStartTime: { ...state.renderStartTime, [algo]: null },
        renderEndTime: { ...state.renderEndTime, [algo]: null },
        activeAlgorithm: algo,
        isPlaying: false,
      };
    });
  },

  // Selectors
  getVisibleNodeEvents: (algo) => {
    const state = get();
    const events = state.events[algo] || [];
    const index = state.playbackIndex[algo] || 0;
    return events.slice(0, index).filter((e): e is PlaybackNodeEvent => e.type === 'node_visit');
  },

  getVisibleEdgeEvents: (algo) => {
    const state = get();
    const events = state.events[algo] || [];
    const index = state.playbackIndex[algo] || 0;
    return events.slice(0, index).filter((e): e is PlaybackEdgeEvent => e.type === 'edge_explore');
  },

  getProgress: (algo) => {
    const state = get();
    const total = state.events[algo]?.length || 0;
    if (total === 0) return 0;
    const index = state.playbackIndex[algo] || 0;
    return Math.round((index / total) * 100);
  },

  getTotalEvents: (algo) => {
    return get().events[algo]?.length || 0;
  },

  getCurrentIndex: (algo) => {
    return get().playbackIndex[algo] || 0;
  },

  isAlgoComplete: (algo) => {
    const state = get();
    const total = state.events[algo]?.length || 0;
    const index = state.playbackIndex[algo] || 0;
    return total > 0 && index >= total && state.streamComplete[algo];
  },

  getRenderTime: (algo) => {
    const state = get();
    const start = state.renderStartTime[algo];
    const end = state.renderEndTime[algo];
    if (start == null) return null;
    if (end == null) {
      // Still rendering, return elapsed time
      return performance.now() - start;
    }
    return end - start;
  },
}));
