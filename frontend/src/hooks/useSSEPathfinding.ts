import { useCallback, useEffect, useRef } from 'react';
import { useAppStore } from '../stores/appStore';
import { usePlaybackStore, type PlaybackEvent } from '../stores/playbackStore';
import type { PathfindingConfig, AlgorithmType, Coordinate, WsMessage } from '../types';
import { calculateCacheRegion } from '../utils/api';

/**
 * SSE-based pathfinding hook with client-side playback control.
 * 
 * Events are pushed to the playback store for client-controlled animation.
 * The playback loop (usePlaybackLoop) handles rendering based on speed settings.
 */
export function useSSEPathfinding() {
  const esRef = useRef<EventSource | null>(null);
  const streamCompletedRef = useRef<boolean>(false);

  // Get store actions (these are stable references)
  const appStore = useAppStore;
  const playbackStore = usePlaybackStore;

  const buildUrl = (
    startPoint: Coordinate,
    endPoint: Coordinate,
    algorithms: AlgorithmType[],
    config: PathfindingConfig
  ) => {
    const params = new URLSearchParams();
    params.set('start_lat', String(startPoint.lat));
    params.set('start_lon', String(startPoint.lon));
    params.set('end_lat', String(endPoint.lat));
    params.set('end_lon', String(endPoint.lon));
    if (algorithms && algorithms.length > 0) params.set('algorithms', algorithms.join(','));

    // Calculate and pass radius_km to match cache warming
    const { radiusKm } = calculateCacheRegion(
      startPoint.lat,
      startPoint.lon,
      endPoint.lat,
      endPoint.lon,
      5 // 5km buffer, same as appStore
    );
    // Round to 4 decimal places to match backend cache key formatting
    params.set('radius_km', radiusKm.toFixed(4));

    // Add config params. Hybrid weights are expanded if present.
    params.set('astar_heuristic', config.astar_heuristic);
    params.set('weight_function', config.weight_function);
    if (config.hybrid_weights) {
      params.set('hybrid_weights_alpha', String(config.hybrid_weights.alpha));
      params.set('hybrid_weights_beta', String(config.hybrid_weights.beta));
    }
    params.set('k_paths', String(config.k_paths));
    // Animation speed is now handled client-side, but still pass for potential server-side use
    params.set('animation_speed', String(config.animation_speed));
    params.set('show_all_explored', String(config.show_all_explored));
    params.set('animation_granularity', config.animation_granularity);

    return `/api/pathfinding/stream?${params.toString()}`;
  };

  const startPathfinding = useCallback(
    (
      startPoint: Coordinate,
      endPoint: Coordinate,
      algorithms: AlgorithmType[],
      config: PathfindingConfig
    ) => {
      // Close any existing connection first
      if (esRef.current) {
        streamCompletedRef.current = true;
        try {
          esRef.current.close();
        } catch {
          // no-op
        }
        esRef.current = null;
      }

      // Reset state for new pathfinding run
      streamCompletedRef.current = false;
      appStore.getState().clearResults();
      playbackStore.getState().reset();

      const url = buildUrl(startPoint, endPoint, algorithms, config);

      const es = new EventSource(url);
      if (import.meta.env.DEV) console.log('SSE: Connecting to', url);

      // Open handler
      es.onopen = () => {
        if (import.meta.env.DEV) console.log('SSE: Connection opened');
        appStore.getState().setWsConnected(true);
        appStore.getState().setWsError(null);
        appStore.getState().setWsWarning(null);
        appStore.getState().setRunPhase('running');
      };

      // Error handler
      es.onerror = (ev) => {
        // When server closes the stream the readyState becomes CLOSED (2)
        const readyState = (es && (es as EventSource).readyState) ?? null;
        
        // If stream completed normally (all_complete received), this is not an error
        if (streamCompletedRef.current) {
          if (import.meta.env.DEV) console.log('SSE: Connection closed after successful completion');
          return;
        }
        
        if (import.meta.env.DEV) {
          console.error('SSE: Connection error', ev);
          console.log('SSE: readyState =', readyState);
        }
        
        // Only show error if stream didn't complete normally
        appStore.getState().setWsError('EventSource connection error.');
        
        // If closed, update connection state
        if (readyState === 2) {
          appStore.getState().setWsConnected(false);
          if (appStore.getState().runPhase === 'running') {
            appStore.getState().setRunPhase('completed');
          }
          appStore.getState().setCurrentAlgorithm(null);
        }
      };

      // Helper to parse and dispatch messages
      const handleMessage = (eventData: string) => {
        let data: WsMessage | null = null;
        try {
          data = JSON.parse(eventData) as WsMessage;
        } catch {
          appStore.getState().setWsError('Received malformed SSE message from backend.');
          return;
        }

        if (!data) return;

        // Handle loading event (just log for now, could show UI feedback)
        if (data.type === 'loading') {
          if (import.meta.env.DEV) console.log('SSE: Loading -', data.message);
          return;
        }

        // Visual events go to playback store
        if (data.type === 'node_visit') {
          const event: PlaybackEvent = {
            type: 'node_visit',
            algorithm: data.algorithm,
            node_id: data.node_id,
            lat: data.lat,
            lon: data.lon,
            cost: data.cost,
            nodes_explored: data.nodes_explored,
            metadata: data.metadata,
          };
          playbackStore.getState().addEvent(event);
        } else if (data.type === 'edge_explore') {
          const event: PlaybackEvent = {
            type: 'edge_explore',
            algorithm: data.algorithm,
            from_node_id: data.from_node_id,
            to_node_id: data.to_node_id,
            from_lat: data.from_lat,
            from_lon: data.from_lon,
            to_lat: data.to_lat,
            to_lon: data.to_lon,
            cost: data.cost,
            nodes_explored: data.nodes_explored,
            geometry: data.geometry,
            metadata: data.metadata,
          };
          playbackStore.getState().addEvent(event);
        } else if (data.type === 'frontier_update') {
          const event: PlaybackEvent = {
            type: 'frontier_update',
            algorithm: data.algorithm,
            frontier_size: data.frontier_size,
            nodes_explored: data.nodes_explored,
          };
          playbackStore.getState().addEvent(event);
        } else if (data.type === 'graph_info') {
          appStore.getState().setGraphInfo(data.metadata);
        } else if (data.type === 'algorithm_start') {
          appStore.getState().setCurrentAlgorithm(data.algorithm);
          // Set as active algorithm for playback and start playing
          playbackStore.getState().setActiveAlgorithm(data.algorithm);
          playbackStore.getState().markRenderStart(data.algorithm);
          playbackStore.getState().play();
        } else if (data.type === 'warning') {
          appStore.getState().setWsWarning(data.message);
        } else if (data.type === 'error') {
          streamCompletedRef.current = true;
          appStore.getState().setWsError(data.message);
          appStore.getState().setRunPhase('completed');
        } else if (data.type === 'complete') {
          const requestedAlgorithm = data.requested_algorithm ?? data.algorithm;
          const executedAlgorithm = data.executed_algorithm ?? data.algorithm;

          // Mark stream complete for the requested algorithm namespace
          playbackStore.getState().markStreamComplete(requestedAlgorithm);
          
          // Store path data
          appStore.getState().setPathNodes(requestedAlgorithm, data.path);
          appStore.getState().setPathGeometry(
            requestedAlgorithm,
            (data.path_geometry ?? []) as [number, number][]
          );
          
          // Add result for metrics display
          appStore.getState().addResult({
            algorithm: requestedAlgorithm,
            requested_algorithm: requestedAlgorithm,
            executed_algorithm: executedAlgorithm,
            path: data.path,
            path_geometry: data.path_geometry,
            cost: data.metrics.cost,
            path_length_km: data.metrics.path_length_km,
            nodes_explored: data.metrics.nodes_explored,
            computation_time_ms: data.metrics.computation_time_ms,
            memory_usage_mb: data.metrics.memory_usage_mb,
            success: data.success,
            error: data.error,
            extra: data.metrics.extra ?? {},
          });
        } else if (data.type === 'all_complete') {
          // Mark stream as completed before closing to prevent onerror from showing error
          streamCompletedRef.current = true;
          appStore.getState().setCurrentAlgorithm(null);
          appStore.getState().setRunPhase('completed');
          appStore.getState().setWsConnected(false);
          // Explicitly close the connection to prevent onerror firing on server close
          if (esRef.current) {
            try {
              esRef.current.close();
            } catch {
              // no-op
            }
            esRef.current = null;
          }
        }
      };

      // Register listeners for named events. Backend sends events with `event: <type>` headers.
      const eventTypes = [
        'loading',
        'node_visit',
        'edge_explore',
        'frontier_update',
        'graph_info',
        'algorithm_start',
        'warning',
        'error',
        'complete',
        'all_complete',
      ];

      for (const t of eventTypes) {
        const handler = (e: MessageEvent) => {
          if (!e.data) return;
          handleMessage(e.data);
        };
        es.addEventListener(t, handler as EventListener);
      }

      // Fallback: some servers may send messages on the default message event
      const defaultHandler = (e: MessageEvent) => {
        if (!e.data) return;
        handleMessage(e.data);
      };
      es.addEventListener('message', defaultHandler as EventListener);

      esRef.current = es;
    },
    [appStore, playbackStore]
  );

  const stopPathfinding = useCallback(() => {
    streamCompletedRef.current = true;
    if (esRef.current) {
      try {
        esRef.current.close();
      } catch {
        // no-op
      }
      esRef.current = null;
    }
    appStore.getState().setWsConnected(false);
    appStore.getState().setCurrentAlgorithm(null);
    appStore.getState().setRunPhase('idle');
  }, [appStore]);

  useEffect(() => {
    return () => {
      streamCompletedRef.current = true;
      if (esRef.current) {
        try {
          esRef.current.close();
        } catch {
          // no-op
        }
        esRef.current = null;
      }
      appStore.getState().setWsConnected(false);
    };
  }, [appStore]);

  const wsConnected = useAppStore((s) => s.wsConnected);
  
  return { startPathfinding, stopPathfinding, isConnected: wsConnected } as const;
}
