/**
 * API client for the Pathfinding Visualization Platform.
 * Wraps fetch calls to backend REST endpoints.
 */

import type {
  PathfindingRequest,
  AlgorithmResult,
  UserSettings,
  CachedCity,
} from '../types';

const API_BASE = '/api';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── Pathfinding ──────────────────────────────────────────────

export async function findPath(req: PathfindingRequest): Promise<{
  start: { lat: number; lon: number };
  end: { lat: number; lon: number };
  graph_info?: Record<string, unknown>;
  warnings?: string[];
  results: Array<AlgorithmResult & { path_geometry?: number[][] }>;
}> {
  return request('/pathfinding/find-path', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function getAlgorithms(): Promise<Record<string, {
  name: string;
  description: string;
  time_complexity: string;
  space_complexity: string;
  supports_negative_weights: boolean;
  supports_all_pairs: boolean;
  parameters: string[];
}>> {
  return request('/pathfinding/algorithms');
}

export async function compareAlgorithms(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
  algorithms: string[],
): Promise<Record<string, unknown>> {
  const params = new URLSearchParams({
    lat1: lat1.toString(),
    lon1: lon1.toString(),
    lat2: lat2.toString(),
    lon2: lon2.toString(),
    algorithms: algorithms.join(','),
  });
  return request(`/pathfinding/compare?${params}`);
}

// ─── Config ───────────────────────────────────────────────────

export async function getFrontendConfig(): Promise<{
  ws_url: string;
  floyd_warshall_node_limit: number;
  fallback_warning_threshold: number;
}> {
  return request('/config');
}

// ─── User Settings ────────────────────────────────────────────

export async function getUserSettings(): Promise<UserSettings> {
  return request('/user/settings');
}

export async function updateUserSettings(
  settings: Partial<UserSettings>,
): Promise<UserSettings> {
  return request('/user/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

export async function resetUserSettings(): Promise<void> {
  return request('/user/settings', { method: 'DELETE' });
}

// ─── Cache Management ─────────────────────────────────────────

export async function getCachedCities(): Promise<CachedCity[]> {
  return request('/cache/cities');
}

export async function refreshCityCache(
  cityId: number,
  approve: boolean = true,
): Promise<Record<string, unknown>> {
  return request('/cache/refresh', {
    method: 'POST',
    body: JSON.stringify({ city_id: cityId, approve }),
  });
}

export async function setCacheSchedule(
  cityId: number,
  schedule: string,
  promptBehavior: string = 'always_ask',
): Promise<Record<string, unknown>> {
  return request('/cache/schedule', {
    method: 'POST',
    body: JSON.stringify({
      city_id: cityId,
      schedule,
      prompt_behavior: promptBehavior,
    }),
  });
}

/**
 * Warm the cache for a region. This triggers background fetching of the road
 * network graph if not already cached. Fire-and-forget - does not wait for completion.
 */
export function warmCache(lat: number, lon: number, radiusKm: number = 15): void {
  // Fire and forget - don't await
  fetch(`${API_BASE}/cache/warm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat, lon, radius_km: radiusKm }),
  }).catch((err) => {
    console.warn('Cache warming request failed (non-blocking):', err);
  });
}

/**
 * Check if a region is already cached.
 */
export async function getCacheStatus(
  lat: number,
  lon: number,
  radiusKm: number = 15,
): Promise<{
  cached: boolean;
  cache_key: string;
  node_count?: number;
  edge_count?: number;
  source?: string;
}> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    radius_km: radiusKm.toString(),
  });
  return request(`/cache/status?${params}`);
}

/**
 * Calculate the center point and required radius to cover two coordinates.
 * Returns the center lat/lon and a radius that covers both points with a buffer.
 */
export function calculateCacheRegion(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
  bufferKm: number = 5,
): { centerLat: number; centerLon: number; radiusKm: number } {
  const centerLat = (lat1 + lat2) / 2;
  const centerLon = (lon1 + lon2) / 2;
  
  // Haversine distance calculation
  const R = 6371; // Earth's radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distance = R * c;
  
  // Radius is half the distance plus buffer
  const radiusKm = Math.min(distance / 2 + bufferKm, 100); // Cap at 100km
  
  return { centerLat, centerLon, radiusKm };
}

// ─── Health ───────────────────────────────────────────────────

export async function healthCheck(): Promise<{
  status: string;
  version: string;
}> {
  const res = await fetch('/health');
  return res.json();
}
