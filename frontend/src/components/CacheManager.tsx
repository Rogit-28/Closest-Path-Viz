import React, { useState, useEffect } from 'react';
import { CachedCity } from '../types';
import { getCachedCities, refreshCityCache, setCacheSchedule } from '../utils/api';

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
      console.error(err);
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
      console.error(err);
    } finally {
      setRefreshingId(null);
    }
  };

  const handleRefreshAll = async () => {
    try {
      setRefreshingAll(true);
      setError(null);
      const refreshPromises = cities.map(city => refreshCityCache(city.id));
      await Promise.all(refreshPromises);
      await fetchCities();
    } catch (err) {
      setError('Failed to refresh all cities.');
      console.error(err);
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
      console.error(err);
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
    <div className="p-6 bg-slate-900 min-h-screen text-slate-200">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Cache Manager</h1>
        <button
          onClick={handleRefreshAll}
          disabled={loading || refreshingAll || cities.length === 0}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md disabled:opacity-50 transition-colors"
        >
          {refreshingAll ? 'Refreshing All...' : 'Refresh All'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-10">
          <p className="text-xl text-slate-400">Loading cities...</p>
        </div>
      ) : cities.length === 0 ? (
        <div className="text-center py-10 bg-slate-800 rounded-lg border border-slate-700">
          <p className="text-xl text-slate-400">No cached cities</p>
        </div>
      ) : (
        <div className="overflow-x-auto bg-slate-800 rounded-lg border border-slate-700 shadow-xl">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-700 border-b border-slate-600">
                <th className="p-4 font-semibold">City</th>
                <th className="p-4 font-semibold">Nodes / Edges</th>
                <th className="p-4 font-semibold">Last Refresh</th>
                <th className="p-4 font-semibold">Next Refresh</th>
                <th className="p-4 font-semibold">Schedule</th>
                <th className="p-4 font-semibold">Status</th>
                <th className="p-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {cities.map((city) => (
                <tr key={city.id} className="border-b border-slate-700 hover:bg-slate-700/50 transition-colors">
                  <td className="p-4">
                    <div className="font-medium">{city.name}</div>
                    <div className="text-sm text-slate-400">{city.country}</div>
                  </td>
                  <td className="p-4 text-sm">
                    <div>{city.node_count.toLocaleString()} N</div>
                    <div className="text-slate-400">{city.edge_count.toLocaleString()} E</div>
                  </td>
                  <td className="p-4 text-sm">{formatDate(city.last_refresh)}</td>
                  <td className="p-4 text-sm">{formatDate(city.next_refresh)}</td>
                  <td className="p-4">
                    <select
                      value={city.schedule}
                      onChange={(e) => handleScheduleChange(city.id, e.target.value)}
                      className="bg-slate-900 border border-slate-600 text-slate-200 text-sm rounded focus:ring-blue-500 focus:border-blue-500 block p-2"
                    >
                      <option value="manual">Manual</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </td>
                  <td className="p-4">
                    {city.pending_approval ? (
                      <span className="bg-yellow-900 text-yellow-200 text-xs font-medium px-2.5 py-0.5 rounded border border-yellow-700">
                        Pending Approval
                      </span>
                    ) : (
                      <span className="bg-green-900 text-green-200 text-xs font-medium px-2.5 py-0.5 rounded border border-green-700">
                        Active
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-right">
                    <button
                      onClick={() => handleRefresh(city.id)}
                      disabled={refreshingId === city.id || refreshingAll}
                      className="bg-slate-600 hover:bg-slate-500 text-white text-sm px-3 py-1.5 rounded disabled:opacity-50 transition-colors"
                    >
                      {refreshingId === city.id ? 'Refreshing...' : 'Refresh'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
