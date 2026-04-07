/**
 * Hook for detecting user location with fallback chain:
 * 1. Browser Geolocation API (GPS)
 * 2. IP-based geolocation (ip-api.com)
 * 3. Manual mode (user clicks on map)
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export type LocationSource = 'gps' | 'ip' | 'manual' | 'loading' | 'error';

export interface UserLocation {
  lat: number;
  lon: number;
}

export interface UseUserLocationResult {
  location: UserLocation | null;
  source: LocationSource;
  error: string | null;
  isLoading: boolean;
  /** Manually set location (for manual mode or override) */
  setManualLocation: (location: UserLocation) => void;
  /** Retry location detection */
  retry: () => void;
}

const GEOLOCATION_TIMEOUT = 10000; // 10 seconds
const IP_FETCH_TIMEOUT = 5000; // 5 seconds
const IP_API_URL = 'http://ip-api.com/json/?fields=status,lat,lon,city,country';
const STORAGE_KEY = 'pathfinder_last_location';

interface StoredLocation {
  lat: number;
  lon: number;
  source: LocationSource;
  timestamp: number;
}

function getStoredLocation(): StoredLocation | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as StoredLocation;
    // Use stored location if less than 24 hours old
    const ageMs = Date.now() - parsed.timestamp;
    if (ageMs < 24 * 60 * 60 * 1000) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

function storeLocation(lat: number, lon: number, source: LocationSource): void {
  try {
    const data: StoredLocation = { lat, lon, source, timestamp: Date.now() };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Ignore storage errors
  }
}

export function useUserLocation(): UseUserLocationResult {
  const [location, setLocation] = useState<UserLocation | null>(null);
  const [source, setSource] = useState<LocationSource>('loading');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const hasAttemptedRef = useRef(false);

  const tryGpsLocation = useCallback((): Promise<UserLocation> => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation not supported'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          });
        },
        (err) => {
          reject(new Error(err.message || 'Geolocation failed'));
        },
        {
          enableHighAccuracy: false,
          timeout: GEOLOCATION_TIMEOUT,
          maximumAge: 5 * 60 * 1000, // Accept cached position up to 5 minutes old
        }
      );
    });
  }, []);

  const tryIpLocation = useCallback(async (): Promise<UserLocation> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), IP_FETCH_TIMEOUT);
    
    try {
      const response = await fetch(IP_API_URL, { signal: controller.signal });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error('IP geolocation request failed');
      }
      const data = await response.json();
      if (data.status !== 'success') {
        throw new Error('IP geolocation returned error status');
      }
      return {
        lat: data.lat,
        lon: data.lon,
      };
    } catch (err) {
      clearTimeout(timeoutId);
      if (err instanceof Error && err.name === 'AbortError') {
        throw new Error('IP geolocation request timed out');
      }
      throw err;
    }
  }, []);

  const detectLocation = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSource('loading');

    // First, check if we have a recent stored location
    const stored = getStoredLocation();
    if (stored) {
      setLocation({ lat: stored.lat, lon: stored.lon });
      setSource(stored.source);
      setIsLoading(false);
      // Still try to get fresh location in background
    }

    // Try GPS first
    try {
      const gpsLocation = await tryGpsLocation();
      setLocation(gpsLocation);
      setSource('gps');
      setError(null);
      storeLocation(gpsLocation.lat, gpsLocation.lon, 'gps');
      setIsLoading(false);
      return;
    } catch (gpsError) {
      if (import.meta.env.DEV) console.log('GPS location failed, trying IP fallback:', gpsError);
    }

    // Fallback to IP geolocation
    try {
      const ipLocation = await tryIpLocation();
      setLocation(ipLocation);
      setSource('ip');
      setError(null);
      storeLocation(ipLocation.lat, ipLocation.lon, 'ip');
      setIsLoading(false);
      return;
    } catch (ipError) {
      if (import.meta.env.DEV) console.log('IP location failed:', ipError);
    }

    // Both failed - go to manual mode
    // If we had a stored location, keep using it
    if (stored) {
      setIsLoading(false);
      return;
    }

    setSource('manual');
    setError('Could not detect location. Please click on the map to set your starting area.');
    setIsLoading(false);
  }, [tryGpsLocation, tryIpLocation]);

  const setManualLocation = useCallback((loc: UserLocation) => {
    setLocation(loc);
    setSource('manual');
    setError(null);
    storeLocation(loc.lat, loc.lon, 'manual');
  }, []);

  const retry = useCallback(() => {
    hasAttemptedRef.current = false;
    detectLocation();
  }, [detectLocation]);

  useEffect(() => {
    if (hasAttemptedRef.current) return;
    hasAttemptedRef.current = true;
    detectLocation();
  }, [detectLocation]);

  return {
    location,
    source,
    error,
    isLoading,
    setManualLocation,
    retry,
  };
}
