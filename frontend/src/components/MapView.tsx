import React, { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAppStore } from '../stores/appStore';
import { ALGORITHM_COLORS } from '../types';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

export default function MapView() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const startMarkerRef = useRef<mapboxgl.Marker | null>(null);
  const endMarkerRef = useRef<mapboxgl.Marker | null>(null);

  const {
    startPoint,
    endPoint,
    setStartPoint,
    setEndPoint,
    exploredNodes,
    pathNodes,
    mapCenter,
    mapZoom,
    setMapCenter,
    setMapZoom,
    graphInfo,
  } = useAppStore();

  useEffect(() => {
    if (!mapContainerRef.current) return;

    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [mapCenter.lon, mapCenter.lat],
      zoom: mapZoom,
    });

    const map = mapRef.current;

    map.addControl(new mapboxgl.NavigationControl(), 'top-right');

    map.on('moveend', () => {
      const center = map.getCenter();
      setMapCenter({ lat: center.lat, lon: center.lng });
      setMapZoom(map.getZoom());
    });

    map.on('click', (e) => {
      setStartPoint({ lat: e.lngLat.lat, lon: e.lngLat.lng });
    });

    map.on('contextmenu', (e) => {
      setEndPoint({ lat: e.lngLat.lat, lon: e.lngLat.lng });
    });

    map.on('load', () => {
      map.addSource('explored-nodes', {
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

      Object.entries(ALGORITHM_COLORS).forEach(([algo, color]) => {
        const sourceId = `path-${algo}`;
        map.addSource(sourceId, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
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
            'line-width': 4,
            'line-opacity': 0.8,
          },
        });
      });
    });

    return () => {
      map.remove();
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;
    
    if (startPoint) {
      if (!startMarkerRef.current) {
        startMarkerRef.current = new mapboxgl.Marker({ color: '#22c55e' })
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
        endMarkerRef.current = new mapboxgl.Marker({ color: '#ef4444' })
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource('explored-nodes') as mapboxgl.GeoJSONSource | undefined;
    if (!source) return;

    const features: GeoJSON.Feature[] = [];

    Object.entries(exploredNodes).forEach(([algo, nodes]) => {
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
  }, [exploredNodes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    Object.entries(ALGORITHM_COLORS).forEach(([algo]) => {
      const sourceId = `path-${algo}`;
      const source = map.getSource(sourceId) as mapboxgl.GeoJSONSource | undefined;
      
      if (!source) return;

      const nodes = pathNodes[algo] || [];
      if (nodes.length > 1) {
        source.setData({
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: nodes.map((n) => [n.lon, n.lat]),
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
  }, [pathNodes]);

  return (
    <div className="relative w-full h-full">
      <div className="w-full h-full" ref={mapContainerRef} />
      
      {graphInfo && (
        <div className="absolute bottom-6 left-6 bg-slate-800/80 backdrop-blur text-white p-3 rounded-md text-sm border border-slate-700 pointer-events-none z-10">
          <h3 className="font-semibold text-slate-300 mb-1 border-b border-slate-600 pb-1">Graph Info</h3>
          <div className="flex flex-col gap-1">
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Nodes:</span>
              <span className="font-mono">{graphInfo.node_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Edges:</span>
              <span className="font-mono">{graphInfo.edge_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between gap-4 mt-1 pt-1 border-t border-slate-700">
              <span className="text-slate-400">Source:</span>
              <span className="text-slate-300 truncate max-w-[120px]" title={graphInfo.source}>{graphInfo.source}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
