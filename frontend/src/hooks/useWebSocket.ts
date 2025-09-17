/**
 * WebSocket hook for real-time pathfinding
 */
import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../stores/appStore';
import type { PathfindingConfig, AlgorithmType, Coordinate } from '../types';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { addResult, addExploredNode, setFrontierSize, setRunning, setCurrentAlgorithm } = useAppStore();

  const startPathfinding = useCallback(
    (
      startPoint: Coordinate,
      endPoint: Coordinate,
      algorithms: AlgorithmType[],
      config: PathfindingConfig
    ) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/pathfinding`;

      if (wsRef.current) wsRef.current.close();

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setRunning(true);
        ws.send(
          JSON.stringify({
            start: startPoint,
            end: endPoint,
            algorithms,
            config,
          })
        );
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'node_visit') {
          addExploredNode(data.algorithm, {
            node_id: data.node_id,
            lat: data.lat,
            lon: data.lon,
            cost: data.cost,
            algorithm: data.algorithm,
          });
        } else if (data.type === 'frontier_update') {
          setFrontierSize(data.algorithm, data.frontier_size);
        } else if (data.type === 'complete') {
          addResult({
            algorithm: data.algorithm,
            path: data.path,
            cost: data.metrics.cost,
            path_length_km: data.metrics.path_length_km,
            nodes_explored: data.metrics.nodes_explored,
            computation_time_ms: data.metrics.computation_time_ms,
            memory_usage_mb: data.metrics.memory_usage_mb,
            success: data.metrics.success,
            error: null,
            extra: {},
          });
        }
      };

      ws.onclose = () => {
        setRunning(false);
      };

      wsRef.current = ws;
    },
    [addResult, addExploredNode, setFrontierSize, setRunning, setCurrentAlgorithm]
  );

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { startPathfinding, disconnect };
}
