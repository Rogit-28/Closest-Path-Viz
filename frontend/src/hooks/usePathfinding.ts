/**
 * React hook for real-time pathfinding visualization via WebSocket.
 * Handles connection, streaming, and error management.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface NodeVisitEvent {
  type: 'node_visit';
  algorithm: string;
  node_id: string;
  lat: number;
  lon: number;
  cost: number;
  nodes_explored: number;
  metadata?: Record<string, any>;
}

export interface FrontierUpdateEvent {
  type: 'frontier_update';
  algorithm: string;
  frontier_size: number;
  nodes_explored: number;
}

export interface CompleteEvent {
  type: 'complete';
  algorithm: string;
  path: Array<{ node_id: string; lat: number; lon: number }>;
  metrics: {
    nodes_explored: number;
    computation_time_ms: number;
    memory_usage_mb: number;
    path_length_km: number;
    cost: number;
    success: boolean;
  };
  extra?: Record<string, any>;
}

export interface ErrorEvent {
  type: 'error';
  message: string;
  client_id?: string;
}

export type PathfindingEvent = 
  | NodeVisitEvent 
  | FrontierUpdateEvent 
  | CompleteEvent 
  | ErrorEvent;

export interface PathfindingOptions {
  algorithm: string;
  startLat: number;
  startLon: number;
  endLat: number;
  endLon: number;
  weight?: 'distance' | 'time' | 'hybrid';
  heuristic?: 'haversine' | 'manhattan' | 'euclidean' | 'zero';
  kPaths?: number;
  serverUrl?: string;
}

interface VisitedNode {
  id: string;
  cost: number;
  lat: number;
  lon: number;
  timestamp: number;
}

export const usePathfinding = () => {
  const [visitedNodes, setVisitedNodes] = useState<VisitedNode[]>([]);
  const [frontierSize, setFrontierSize] = useState<number>(0);
  const [nodesExplored, setNodesExplored] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompleteEvent | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const messageHandlerRef = useRef<(event: PathfindingEvent) => void>(() => {});

  /**
   * Connect to pathfinding WebSocket endpoint
   */
  const connect = useCallback((options: PathfindingOptions) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    setIsLoading(true);
    setError(null);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const clientId = `client-${Date.now()}`;
    const wsUrl = `${protocol}//${host}/ws/pathfinding/${clientId}`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');

        // Send request
        ws.send(
          JSON.stringify({
            action: 'find_path',
            algorithm: options.algorithm,
            start_lat: options.startLat,
            start_lon: options.startLon,
            end_lat: options.endLat,
            end_lon: options.endLon,
            weight: options.weight || 'distance',
            heuristic: options.heuristic || 'haversine',
            k_paths: options.kPaths || 1,
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          messageHandlerRef.current(data);

          if (data.type === 'node_visit') {
            setVisitedNodes((prev) => [
              ...prev,
              {
                id: data.node_id,
                cost: data.cost,
                lat: data.lat,
                lon: data.lon,
                timestamp: Date.now(),
              },
            ]);
            setNodesExplored(data.nodes_explored);
          } else if (data.type === 'frontier_update') {
            setFrontierSize(data.frontier_size);
          } else if (data.type === 'complete') {
            setResult(data);
            setIsLoading(false);
          } else if (data.type === 'error') {
            setError(data.message);
            setIsLoading(false);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket error');
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
      };

      wsRef.current = ws;
    } catch (e) {
      const err = e instanceof Error ? e.message : 'Unknown error';
      setError(err);
      setIsLoading(false);
    }
  }, []);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    visitedNodes,
    frontierSize,
    nodesExplored,
    isLoading,
    error,
    result,
    isConnected,
    connect,
    disconnect,
  };
};
