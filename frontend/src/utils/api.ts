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
  results: AlgorithmResult[];
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
  mapbox_token: string;
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

// ─── Health ───────────────────────────────────────────────────

export async function healthCheck(): Promise<{
  status: string;
  version: string;
}> {
  const res = await fetch('/health');
  return res.json();
}
