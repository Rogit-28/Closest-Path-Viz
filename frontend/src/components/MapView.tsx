import React, { useEffect, useRef, useState, useMemo } from 'react';
import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useAppStore } from '../stores/appStore';
import { usePlaybackStore } from '../stores/playbackStore';
import { ALGORITHM_COLORS } from '../types';
import { useUserLocation } from '../hooks/useUserLocation';

const MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    'carto-darkmatter': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: 'carto-darkmatter',
      type: 'raster',
      source: 'carto-darkmatter',
      minzoom: 0,
      maxzoom: 22,
    },
  ],
};

export default function MapView() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const startMarkerRef = useRef<maplibregl.Marker | null>(null);
  const endMarkerRef = useRef<maplibregl.Marker | null>(null);
  const currentMarkerRef = useRef<maplibregl.Marker | null>(null);
  const userLocationMarkerRef = useRef<maplibregl.Marker | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [selectionLockHint, setSelectionLockHint] = useState<string | null>(null);
  const selectionHintTimeoutRef = useRef<number | null>(null);
  const [hasLoadedMap, setHasLoadedMap] = useState(false);
  const hasFlownToUserLocation = useRef(false);

  // User location hook
  const { location: userLocation, source: locationSource, error: locationError } = useUserLocation();

  const {
    startPoint,
    endPoint,
    config,
    setStartPoint,
    setEndPoint,
    pathNodes,
    pathGeometry,
    mapCenter,
    mapZoom,
    setMapCenter,
    setMapZoom,
    graphInfo,
    wsWarning,
    runPhase,
    canEditCoordinates,
    setUserLocation,
  } = useAppStore();

  // Get playback state for rendering visible events - use selectors to minimize re-renders
  const events = usePlaybackStore((s) => s.events);
  const playbackIndex = usePlaybackStore((s) => s.playbackIndex);
  const activeAlgorithm = usePlaybackStore((s) => s.activeAlgorithm);

  const initialCenterRef = useRef(mapCenter);
  const initialZoomRef = useRef(mapZoom);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    try {
      mapRef.current = new maplibregl.Map({
        container: mapContainerRef.current,
        style: MAP_STYLE,
        center: [initialCenterRef.current.lon, initialCenterRef.current.lat],
        zoom: initialZoomRef.current,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unknown MapLibre initialization error';
      setMapError(`Failed to initialize map: ${message}`);
      return;
    }

    const map = mapRef.current;

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.on('error', (event) => {
      const eventError = event.error as { message?: string } | undefined;
      setMapError(
        `Map rendering error: ${eventError?.message ?? 'Unknown MapLibre runtime error'}`
      );
    });

    map.on('moveend', () => {
      const center = map.getCenter();
      setMapCenter({ lat: center.lat, lon: center.lng });
      setMapZoom(map.getZoom());
    });

    map.on('click', (e) => {
      if (!useAppStore.getState().canEditCoordinates) {
        setSelectionLockHint(
          useAppStore.getState().runPhase === 'running'
            ? 'Coordinate selection is locked while a run is active.'
            : 'Coordinate selection is locked. Click New Run to select new points.'
        );
        if (selectionHintTimeoutRef.current !== null) {
          window.clearTimeout(selectionHintTimeoutRef.current);
        }
        selectionHintTimeoutRef.current = window.setTimeout(() => {
          setSelectionLockHint(null);
          selectionHintTimeoutRef.current = null;
        }, 2000);
        return;
      }
      setStartPoint({ lat: e.lngLat.lat, lon: e.lngLat.lng });
    });

    map.on('contextmenu', (e) => {
      if (!useAppStore.getState().canEditCoordinates) {
        setSelectionLockHint(
          useAppStore.getState().runPhase === 'running'
            ? 'Coordinate selection is locked while a run is active.'
            : 'Coordinate selection is locked. Click New Run to select new points.'
        );
        if (selectionHintTimeoutRef.current !== null) {
          window.clearTimeout(selectionHintTimeoutRef.current);
        }
        selectionHintTimeoutRef.current = window.setTimeout(() => {
          setSelectionLockHint(null);
          selectionHintTimeoutRef.current = null;
        }, 2000);
        return;
      }
      setEndPoint({ lat: e.lngLat.lat, lon: e.lngLat.lng });
    });

    map.on('style.load', () => {
      setMapError(null);
    });

    map.on('load', () => {
      setHasLoadedMap(true);
      setMapError(null);
      map.addSource('explored-nodes', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addSource('explored-edges', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id: 'explored-nodes-layer',
        type: 'circle',
        source: 'explored-nodes',
        paint: {
          'circle-radius': 4,
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.6,
        },
      });

      map.addLayer({
        id: 'explored-edges-layer',
        type: 'line',
        source: 'explored-edges',
        layout: {
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': ['get', 'color'],
          'line-width': ['coalesce', ['get', 'lineWidth'], 1.8],
          'line-opacity': ['coalesce', ['get', 'lineOpacity'], 0.45],
        },
      });

      Object.entries(ALGORITHM_COLORS).forEach(([algo, color]) => {
        const sourceId = `path-${algo}`;
        map.addSource(sourceId, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
        });

        map.addLayer({
          id: `${sourceId}-casing`,
          type: 'line',
          source: sourceId,
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': '#f8fafc',
            'line-width': 8,
            'line-opacity': 0.95,
          },
        });

        map.addLayer({
          id: `${sourceId}-layer`,
          type: 'line',
          source: sourceId,
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': color,
            'line-width': 4.5,
            'line-opacity': 1,
          },
        });
      });
    });

    return () => {
      setHasLoadedMap(false);
      if (selectionHintTimeoutRef.current !== null) {
        window.clearTimeout(selectionHintTimeoutRef.current);
        selectionHintTimeoutRef.current = null;
      }
      startMarkerRef.current = null;
      endMarkerRef.current = null;
      currentMarkerRef.current = null;
      map.remove();
      mapRef.current = null;
    };
  }, [setEndPoint, setMapCenter, setMapZoom, setStartPoint]);

  // Fly to user location when detected
  useEffect(() => {
    if (!mapRef.current || !userLocation || hasFlownToUserLocation.current) return;
    
    // Update store with user location (this also triggers cache warming)
    setUserLocation(userLocation, locationSource, locationError);
    
    // Fly to user location
    mapRef.current.flyTo({
      center: [userLocation.lon, userLocation.lat],
      zoom: 13,
      duration: 1500,
    });
    
    hasFlownToUserLocation.current = true;
  }, [userLocation, locationSource, locationError, setUserLocation]);

  // Show user location marker
  useEffect(() => {
    if (!mapRef.current || !userLocation) return;
    
    // Create a pulsing dot for user location
    const el = document.createElement('div');
    el.className = 'user-location-marker';
    el.innerHTML = `
      <div class="user-location-dot"></div>
      <div class="user-location-pulse"></div>
    `;
    
    if (!userLocationMarkerRef.current) {
      userLocationMarkerRef.current = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([userLocation.lon, userLocation.lat])
        .addTo(mapRef.current);
    } else {
      userLocationMarkerRef.current.setLngLat([userLocation.lon, userLocation.lat]);
    }
    
    return () => {
      if (userLocationMarkerRef.current) {
        userLocationMarkerRef.current.remove();
        userLocationMarkerRef.current = null;
      }
    };
  }, [userLocation]);

  useEffect(() => {
    if (!mapRef.current) return;
    
    if (startPoint) {
      if (!startMarkerRef.current) {
        startMarkerRef.current = new maplibregl.Marker({ color: '#22c55e' })
          .setLngLat([startPoint.lon, startPoint.lat])
          .addTo(mapRef.current);
      } else {
        startMarkerRef.current.setLngLat([startPoint.lon, startPoint.lat]);
      }
    } else if (startMarkerRef.current) {
      startMarkerRef.current.remove();
      startMarkerRef.current = null;
    }
  }, [startPoint]);

  useEffect(() => {
    if (!mapRef.current) return;

    if (endPoint) {
      if (!endMarkerRef.current) {
        endMarkerRef.current = new maplibregl.Marker({ color: '#ef4444' })
          .setLngLat([endPoint.lon, endPoint.lat])
          .addTo(mapRef.current);
      } else {
        endMarkerRef.current.setLngLat([endPoint.lon, endPoint.lat]);
      }
    } else if (endMarkerRef.current) {
      endMarkerRef.current.remove();
      endMarkerRef.current = null;
    }
  }, [endPoint]);

  // Compute visible nodes from playback store for all algorithms
  const visibleNodes = useMemo(() => {
    const result: Record<string, { lat: number; lon: number }[]> = {};
    // Get all algorithms that have events
    const algorithms = Object.keys(events);
    for (const algo of algorithms) {
      const algoEvents = events[algo] || [];
      const index = playbackIndex[algo] || 0;
      const nodeEvents = algoEvents
        .slice(0, index)
        .filter((e): e is { type: 'node_visit'; lat: number; lon: number; algorithm: string; node_id: string; cost: number; nodes_explored: number } => e.type === 'node_visit');
      result[algo] = nodeEvents.map(e => ({ lat: e.lat, lon: e.lon }));
    }
    return result;
  }, [events, playbackIndex]);

  // Compute visible edges from playback store for all algorithms
  const visibleEdges = useMemo(() => {
    const result: Record<string, Array<{
      from_lat: number;
      from_lon: number;
      to_lat: number;
      to_lon: number;
      geometry?: number[][];
      metadata?: Record<string, unknown>;
    }>>= {};
    const algorithms = Object.keys(events);
    for (const algo of algorithms) {
      const algoEvents = events[algo] || [];
      const index = playbackIndex[algo] || 0;
      const edgeEvents = algoEvents
        .slice(0, index)
        .filter((e): e is { type: 'edge_explore'; algorithm: string; from_node_id: string; to_node_id: string; from_lat: number; from_lon: number; to_lat: number; to_lon: number; cost: number; nodes_explored: number; geometry?: number[][]; metadata?: Record<string, unknown> } => e.type === 'edge_explore');
      result[algo] = edgeEvents.map(e => ({
        from_lat: e.from_lat,
        from_lon: e.from_lon,
        to_lat: e.to_lat,
        to_lon: e.to_lon,
        geometry: e.geometry,
        metadata: e.metadata,
      }));
    }
    return result;
  }, [events, playbackIndex]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource('explored-nodes') as GeoJSONSource | undefined;
    if (!source) return;

    // If the user doesn't want to show all explored, clear the source and return
    if (!config?.show_all_explored) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const features: GeoJSON.Feature[] = [];

    Object.entries(visibleNodes).forEach(([algo, nodes]) => {
      const color = ALGORITHM_COLORS[algo] || '#ffffff';
      nodes.forEach((node) => {
        features.push({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [node.lon, node.lat],
          },
          properties: {
            color,
          },
        });
      });
    });

    source.setData({
      type: 'FeatureCollection',
      features,
    });
  }, [visibleNodes, config?.show_all_explored]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource('explored-edges') as GeoJSONSource | undefined;
    if (!source) return;

    // Respect the UI toggle: if not showing explored, clear the source
    if (!config?.show_all_explored) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const features: GeoJSON.Feature[] = [];

    Object.entries(visibleEdges).forEach(([algo, edges]) => {
      const color = ALGORITHM_COLORS[algo] || '#ffffff';
      edges.forEach((edge) => {
        const improved = Boolean((edge.metadata as { improved?: boolean } | undefined)?.improved);
        const geometry = Array.isArray(edge.geometry) && edge.geometry.length > 1
          ? edge.geometry.map((coord) => [coord[0], coord[1]] as [number, number])
          : [
              [edge.from_lon, edge.from_lat] as [number, number],
              [edge.to_lon, edge.to_lat] as [number, number],
            ];
        features.push({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: geometry,
          },
          properties: {
            color,
            lineWidth: improved ? 2.3 : 1.4,
            lineOpacity: improved ? 0.62 : 0.28,
          },
        });
      });
    });

    source.setData({
      type: 'FeatureCollection',
      features,
    });
  }, [visibleEdges, config?.show_all_explored]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    Object.entries(ALGORITHM_COLORS).forEach(([algo]) => {
      const sourceId = `path-${algo}`;
      const source = map.getSource(sourceId) as GeoJSONSource | undefined;
      
      if (!source) return;

      const nodes = pathNodes[algo] || [];
      const geometry = pathGeometry[algo] || [];
      const hasGeometryPath = geometry.length > 1;
      const hasNodePath = nodes.length > 1;

      if (hasGeometryPath || hasNodePath) {
        const lineCoordinates = hasGeometryPath
          ? geometry
          : nodes.map((n) => [n.lon, n.lat] as [number, number]);
        source.setData({
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: lineCoordinates,
              },
              properties: {},
            },
          ],
        });
      } else {
        source.setData({
          type: 'FeatureCollection',
          features: [],
        });
      }
    });
  }, [pathGeometry, pathNodes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !activeAlgorithm) {
      if (currentMarkerRef.current) {
        currentMarkerRef.current.remove();
        currentMarkerRef.current = null;
      }
      return;
    }

    // Get the last visible node for the active algorithm
    const currentNodes = visibleNodes[activeAlgorithm] || [];
    const lastNode = currentNodes[currentNodes.length - 1];
    if (!lastNode) {
      if (currentMarkerRef.current) {
        currentMarkerRef.current.remove();
        currentMarkerRef.current = null;
      }
      return;
    }

    const currentEl = document.createElement('div');
    currentEl.className = 'map-current-node';

    if (!currentMarkerRef.current) {
      currentMarkerRef.current = new maplibregl.Marker({ element: currentEl, anchor: 'center' })
        .setLngLat([lastNode.lon, lastNode.lat])
        .addTo(map);
    } else {
      const existingElement = currentMarkerRef.current.getElement();
      existingElement.className = 'map-current-node';
      currentMarkerRef.current.setLngLat([lastNode.lon, lastNode.lat]);
    }
  }, [activeAlgorithm, visibleNodes]);

  useEffect(() => {
    if (canEditCoordinates && selectionLockHint) {
      setSelectionLockHint(null);
    }
  }, [canEditCoordinates, selectionLockHint]);

  return (
    <div className="relative w-full h-full">
      <div className="w-full h-full" ref={mapContainerRef} />

      {mapError && (
        <div className="absolute left-4 top-4 z-30 max-w-md rounded border border-red-900/50 bg-red-950/90 px-3 py-2 text-xs text-red-300">
          {mapError}
        </div>
      )}

      {wsWarning && (
        <div className="absolute right-4 top-4 z-30 max-w-sm rounded border border-amber-900/50 bg-amber-950/90 px-3 py-2 text-xs text-amber-300">
          {wsWarning}
        </div>
      )}

      {!canEditCoordinates && (
        <div className="pointer-events-none absolute left-1/2 top-4 z-30 -translate-x-1/2 rounded border border-neutral-700/80 bg-black/80 px-3 py-1.5 text-xs text-neutral-300">
          {runPhase === 'running'
            ? 'Run in progress: coordinate editing is locked.'
            : 'Run complete: click New Run to pick new coordinates.'}
        </div>
      )}

      {selectionLockHint && (
        <div className="pointer-events-none absolute left-1/2 top-16 z-30 -translate-x-1/2 rounded border border-amber-900/50 bg-amber-950/90 px-3 py-1.5 text-xs text-amber-300">
          {selectionLockHint}
        </div>
      )}

      {!mapError && !hasLoadedMap && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/70">
          <div className="rounded border border-neutral-800 bg-neutral-950 px-4 py-2 text-xs text-neutral-400">
            Loading map...
          </div>
        </div>
      )}
      
      {graphInfo && (
        <div className="pointer-events-none absolute bottom-4 left-4 z-10 rounded border border-neutral-800 bg-black/90 p-2.5 text-xs text-white">
          <h3 className="mb-1.5 border-b border-neutral-800 pb-1 text-[10px] font-medium uppercase tracking-wide text-neutral-500">Graph Info</h3>
          <div className="flex flex-col gap-1">
            <div className="flex justify-between gap-3">
              <span className="text-neutral-500">Nodes:</span>
              <span className="font-ui-mono text-neutral-200">{graphInfo.node_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-neutral-500">Edges:</span>
              <span className="font-ui-mono text-neutral-200">{graphInfo.edge_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between gap-3 mt-1 pt-1 border-t border-neutral-800">
              <span className="text-neutral-500">Source:</span>
              <span className="text-neutral-400 truncate max-w-[100px]" title={graphInfo.source}>{graphInfo.source}</span>
            </div>
          </div>
        </div>
      )}
      
      {/* Location status indicator */}
      {userLocation && (
        <div className="absolute bottom-4 right-4 z-10 rounded border border-neutral-800 bg-black/90 px-2.5 py-1.5 text-xs text-white flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-neutral-400">
            {locationSource === 'gps' ? 'GPS' : locationSource === 'ip' ? 'IP Location' : 'Manual'}
          </span>
        </div>
      )}
      
      {/* Manual location prompt */}
      {locationSource === 'manual' && !userLocation && locationError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 rounded border border-amber-900/50 bg-amber-950/90 px-4 py-2 text-sm text-amber-300">
          {locationError}
        </div>
      )}
    </div>
  );
}
