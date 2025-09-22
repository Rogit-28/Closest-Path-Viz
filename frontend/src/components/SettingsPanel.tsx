import { useState, useEffect } from 'react';
import {
  HeuristicType,
  WeightFunction,
  AnimationGranularity,
  SPEED_OPTIONS,
  AlgorithmType,
  ALGORITHM_NAMES,
  UserSettings,
} from '../types';
import { useAppStore } from '../stores/appStore';
import { getUserSettings, updateUserSettings, resetUserSettings } from '../utils/api';

export default function SettingsPanel() {
  const store = useAppStore();
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const [settings, setSettings] = useState<UserSettings>({
    pathfinding: {
      default_algorithm: 'astar',
      astar_heuristic: store.config.astar_heuristic,
      weight_function: store.config.weight_function,
      k_paths: store.config.k_paths,
      show_all_explored: store.config.show_all_explored,
    },
    visualization: {
      animation_speed: store.config.animation_speed,
      animation_granularity: store.config.animation_granularity,
      color_scheme: 'dark',
    },
    cache: {
      refresh_schedule: 'daily',
      prompt_on_refresh: true,
      auto_approve_after_days: 7,
      defer_max_days: 14,
    },
  });

  useEffect(() => {
    if (store.showSettings) {
      setLoading(true);
      getUserSettings()
        .then((data) => {
          setSettings(data);
          store.updateConfig({
            astar_heuristic: data.pathfinding.astar_heuristic,
            weight_function: data.pathfinding.weight_function,
            k_paths: data.pathfinding.k_paths,
            show_all_explored: data.pathfinding.show_all_explored,
            animation_speed: data.visualization.animation_speed,
            animation_granularity: data.visualization.animation_granularity,
          });
        })
        .catch((err) => console.error('Failed to load settings:', err))
        .finally(() => setLoading(false));
    }
  }, [store.showSettings]); // Intentional omit of store to avoid loops

  if (!store.showSettings) return null;

  const handleSave = async () => {
    setLoading(true);
    setSaveStatus(null);
    try {
      const updated = await updateUserSettings(settings);
      setSettings(updated);
      
      store.updateConfig({
        astar_heuristic: updated.pathfinding.astar_heuristic,
        weight_function: updated.pathfinding.weight_function,
        k_paths: updated.pathfinding.k_paths,
        show_all_explored: updated.pathfinding.show_all_explored,
        animation_speed: updated.visualization.animation_speed,
        animation_granularity: updated.visualization.animation_granularity,
      });

      setSaveStatus('Settings saved successfully!');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('Failed to save settings.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setSaveStatus(null);
    try {
      await resetUserSettings();
      
      const data = await getUserSettings();
      setSettings(data);
      
      store.updateConfig({
        astar_heuristic: data.pathfinding.astar_heuristic,
        weight_function: data.pathfinding.weight_function,
        k_paths: data.pathfinding.k_paths,
        show_all_explored: data.pathfinding.show_all_explored,
        animation_speed: data.visualization.animation_speed,
        animation_granularity: data.visualization.animation_granularity,
      });

      setSaveStatus('Reset to defaults.');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (error) {
      console.error('Failed to reset settings:', error);
      setSaveStatus('Failed to reset settings.');
    } finally {
      setLoading(false);
    }
  };

  const updatePathfinding = <K extends keyof UserSettings['pathfinding']>(key: K, value: UserSettings['pathfinding'][K]) => {
    setSettings(prev => ({
      ...prev,
      pathfinding: { ...prev.pathfinding, [key]: value }
    }));
  };

  const updateViz = <K extends keyof UserSettings['visualization']>(key: K, value: UserSettings['visualization'][K]) => {
    setSettings(prev => ({
      ...prev,
      visualization: { ...prev.visualization, [key]: value }
    }));
  };

  const updateCache = <K extends keyof UserSettings['cache']>(key: K, value: UserSettings['cache'][K]) => {
    setSettings(prev => ({
      ...prev,
      cache: { ...prev.cache, [key]: value }
    }));
  };

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={store.toggleSettings}
    >
      <div 
        className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-w-lg w-full mx-4 max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center p-4 border-b border-slate-700 sticky top-0 bg-slate-900 z-10">
          <h2 className="text-xl font-semibold text-slate-100">Settings</h2>
          <button 
            onClick={store.toggleSettings}
            className="text-slate-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-8">
          {loading && !settings ? (
            <div className="text-center text-slate-400">Loading settings...</div>
          ) : (
            <>
              {/* Pathfinding Section */}
              <section className="space-y-4">
                <h3 className="text-lg font-medium text-slate-200 border-b border-slate-800 pb-2">Pathfinding</h3>
                
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Default Algorithm</label>
                    <select 
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.pathfinding.default_algorithm}
                      onChange={e => updatePathfinding('default_algorithm', e.target.value as AlgorithmType)}
                    >
                      {(Object.keys(ALGORITHM_NAMES) as AlgorithmType[]).map(key => (
                        <option key={key} value={key}>{ALGORITHM_NAMES[key]}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">A* Heuristic</label>
                    <select 
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.pathfinding.astar_heuristic}
                      onChange={e => updatePathfinding('astar_heuristic', e.target.value as HeuristicType)}
                    >
                      <option value="haversine">Haversine (Great Circle)</option>
                      <option value="manhattan">Manhattan</option>
                      <option value="euclidean">Euclidean</option>
                      <option value="zero">Zero (Dijkstra)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Weight Function</label>
                    <select 
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.pathfinding.weight_function}
                      onChange={e => updatePathfinding('weight_function', e.target.value as WeightFunction)}
                    >
                      <option value="distance">Shortest Distance</option>
                      <option value="time">Fastest Time</option>
                      <option value="hybrid">Hybrid</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">K-Paths (Alternative Routes)</label>
                    <input 
                      type="number" 
                      min="1" max="5"
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.pathfinding.k_paths}
                      onChange={e => updatePathfinding('k_paths', parseInt(e.target.value) || 1)}
                    />
                  </div>

                  <div className="flex items-center mt-2">
                    <input 
                      type="checkbox" 
                      id="showExplored"
                      className="w-4 h-4 bg-slate-800 border-slate-700 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900"
                      checked={settings.pathfinding.show_all_explored}
                      onChange={e => updatePathfinding('show_all_explored', e.target.checked)}
                    />
                    <label htmlFor="showExplored" className="ml-2 text-sm text-slate-300">
                      Show all explored nodes
                    </label>
                  </div>
                </div>
              </section>

              {/* Visualization Section */}
              <section className="space-y-4">
                <h3 className="text-lg font-medium text-slate-200 border-b border-slate-800 pb-2">Visualization</h3>
                
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Animation Speed</label>
                    <select 
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.visualization.animation_speed}
                      onChange={e => updateViz('animation_speed', parseFloat(e.target.value))}
                    >
                      {SPEED_OPTIONS.map(speed => (
                        <option key={speed} value={speed}>
                          {speed === 0 ? 'Instant (No Animation)' : `${speed}x`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Animation Granularity</label>
                    <select 
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.visualization.animation_granularity}
                      onChange={e => updateViz('animation_granularity', e.target.value as AnimationGranularity)}
                    >
                      <option value="every_node">Every Node</option>
                      <option value="every_n">Batch (Every N nodes)</option>
                      <option value="frontier_only">Frontier Only</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Color Scheme</label>
                    <input 
                      type="text" 
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.visualization.color_scheme}
                      onChange={e => updateViz('color_scheme', e.target.value)}
                    />
                  </div>
                </div>
              </section>

              {/* Cache Section */}
              <section className="space-y-4">
                <h3 className="text-lg font-medium text-slate-200 border-b border-slate-800 pb-2">Cache</h3>
                
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1">Refresh Schedule</label>
                    <input 
                      type="text" 
                      placeholder="daily"
                      className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                      value={settings.cache.refresh_schedule}
                      onChange={e => updateCache('refresh_schedule', e.target.value)}
                    />
                  </div>

                  <div className="flex items-center mt-2">
                    <input 
                      type="checkbox" 
                      id="promptRefresh"
                      className="w-4 h-4 bg-slate-800 border-slate-700 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900"
                      checked={settings.cache.prompt_on_refresh}
                      onChange={e => updateCache('prompt_on_refresh', e.target.checked)}
                    />
                    <label htmlFor="promptRefresh" className="ml-2 text-sm text-slate-300">
                      Prompt before cache refresh
                    </label>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Auto-approve after (days)</label>
                      <input 
                        type="number" 
                        min="1"
                        className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                        value={settings.cache.auto_approve_after_days}
                        onChange={e => updateCache('auto_approve_after_days', parseInt(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Defer max (days)</label>
                      <input 
                        type="number" 
                        min="1"
                        className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 w-full"
                        value={settings.cache.defer_max_days}
                        onChange={e => updateCache('defer_max_days', parseInt(e.target.value) || 0)}
                      />
                    </div>
                  </div>
                </div>
              </section>

              <div className="flex items-center justify-between pt-4 mt-6 border-t border-slate-700">
                <span className="text-sm text-green-400">{saveStatus}</span>
                <div className="space-x-4">
                  <button 
                    onClick={handleReset}
                    disabled={loading}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded text-sm font-medium text-slate-300 transition-colors disabled:opacity-50"
                  >
                    Reset to Defaults
                  </button>
                  <button 
                    onClick={handleSave}
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : 'Save Settings'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
