import React, { useState, useEffect } from 'react';
import { CachedCity } from '../types';
import { getCachedCities, refreshCityCache, setCacheSchedule } from '../utils/api';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ScrollArea } from './ui/scroll-area';

export default function CacheManager() {
  const [cities, setCities] = useState<CachedCity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [refreshingAll, setRefreshingAll] = useState<boolean>(false);

  useEffect(() => {
    fetchCities();
  }, []);

  const fetchCities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCachedCities();
      setCities(data);
    } catch (err) {
      setError('Failed to fetch cached cities. Please try again later.');
      if (import.meta.env.DEV) console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async (cityId: number) => {
    try {
      setRefreshingId(cityId);
      setError(null);
      await refreshCityCache(cityId);
      await fetchCities();
    } catch (err) {
      setError(`Failed to refresh city ${cityId}.`);
      if (import.meta.env.DEV) console.error(err);
    } finally {
      setRefreshingId(null);
    }
  };

  const handleRefreshAll = async () => {
    try {
      setRefreshingAll(true);
      setError(null);
      const refreshPromises = cities.map((city) => refreshCityCache(city.id));
      const results = await Promise.allSettled(refreshPromises);
      const failures = results.filter((r) => r.status === 'rejected');
      if (failures.length > 0) {
        setError(`Failed to refresh ${failures.length} of ${cities.length} cities.`);
      }
      await fetchCities();
    } catch (err) {
      setError('Failed to refresh all cities.');
      if (import.meta.env.DEV) console.error(err);
    } finally {
      setRefreshingAll(false);
    }
  };

  const handleScheduleChange = async (cityId: number, schedule: string) => {
    try {
      setError(null);
      await setCacheSchedule(cityId, schedule);
      await fetchCities();
    } catch (err) {
      setError(`Failed to set schedule for city ${cityId}.`);
      if (import.meta.env.DEV) console.error(err);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const m = date.getMonth();
    const d = date.getDate();
    const y = date.getFullYear();
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[m]} ${d}, ${y}`;
  };

  return (
    <div className="min-h-screen bg-black p-6 text-neutral-200">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-base font-semibold text-white">Cache manager</h1>
        <Button
          onClick={handleRefreshAll}
          disabled={loading || refreshingAll || cities.length === 0}
          variant="primary"
        >
          {refreshingAll ? 'Refreshing all...' : 'Refresh all'}
        </Button>
      </div>

      {error && (
        <div className="mb-6 rounded border border-red-900/50 bg-red-950/30 px-4 py-3 text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-10 text-center">
          <p className="text-xl text-neutral-500">Loading cities...</p>
        </div>
      ) : cities.length === 0 ? (
        <div className="rounded border border-neutral-800 bg-neutral-950 py-10 text-center">
          <p className="text-xl text-neutral-500">No cached cities</p>
        </div>
      ) : (
        <div className="glass-panel rounded border border-neutral-800">
          <ScrollArea className="w-full">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-950 text-neutral-400">
                  <th className="p-4 font-medium">City</th>
                  <th className="p-4 font-medium">Nodes / Edges</th>
                  <th className="p-4 font-medium">Last Refresh</th>
                  <th className="p-4 font-medium">Next Refresh</th>
                  <th className="p-4 font-medium">Schedule</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cities.map((city) => (
                  <tr
                    key={city.id}
                    className="border-b border-neutral-900 transition-colors hover:bg-neutral-950"
                  >
                    <td className="p-4">
                      <div className="font-medium text-white">{city.name}</div>
                      <div className="text-xs text-neutral-500">{city.country}</div>
                    </td>
                    <td className="p-4 text-xs text-neutral-400">
                      <div>{city.node_count.toLocaleString()} N</div>
                      <div className="text-neutral-600">{city.edge_count.toLocaleString()} E</div>
                    </td>
                    <td className="p-4 text-xs text-neutral-400">{formatDate(city.last_refresh)}</td>
                    <td className="p-4 text-xs text-neutral-400">{formatDate(city.next_refresh)}</td>
                    <td className="min-w-[140px] p-4">
                      <Select
                        value={city.schedule}
                        onValueChange={(value) => handleScheduleChange(city.id, value)}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue placeholder="Schedule" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="manual">Manual</SelectItem>
                          <SelectItem value="daily">Daily</SelectItem>
                          <SelectItem value="weekly">Weekly</SelectItem>
                          <SelectItem value="monthly">Monthly</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="p-4">
                      {city.pending_approval ? (
                        <span className="rounded border border-amber-700/40 bg-amber-950/30 px-2 py-0.5 text-xs text-amber-400">
                          Pending
                        </span>
                      ) : (
                        <span className="rounded border border-green-700/40 bg-green-950/30 px-2 py-0.5 text-xs text-green-400">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <Button
                        onClick={() => handleRefresh(city.id)}
                        disabled={refreshingId === city.id || refreshingAll}
                        variant="secondary"
                        size="sm"
                      >
                        {refreshingId === city.id ? 'Refreshing...' : 'Refresh'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
