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
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Separator } from './ui/separator';
import { ScrollArea } from './ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

export default function SettingsPanel() {
  const showSettings = useAppStore((state) => state.showSettings);
  const setShowSettings = useAppStore((state) => state.setShowSettings);
  const updateConfig = useAppStore((state) => state.updateConfig);
  const config = useAppStore((state) => state.config);
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const [settings, setSettings] = useState<UserSettings>({
    pathfinding: {
      default_algorithm: 'astar',
      astar_heuristic: config.astar_heuristic,
      weight_function: config.weight_function,
      k_paths: config.k_paths,
      show_all_explored: config.show_all_explored,
      floyd_warshall_node_limit: config.floyd_warshall_node_limit || 1000,
    },
    visualization: {
      animation_speed: config.animation_speed,
      animation_granularity: config.animation_granularity,
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
    if (showSettings) {
      setLoading(true);
      getUserSettings()
        .then((data) => {
          setSettings(data);
          updateConfig({
            astar_heuristic: data.pathfinding.astar_heuristic,
            weight_function: data.pathfinding.weight_function,
            k_paths: data.pathfinding.k_paths,
            show_all_explored: data.pathfinding.show_all_explored,
            animation_speed: data.visualization.animation_speed,
            animation_granularity: data.visualization.animation_granularity,
            floyd_warshall_node_limit: data.pathfinding.floyd_warshall_node_limit || 1000,
          });
        })
        .catch((err) => console.error('Failed to load settings:', err))
        .finally(() => setLoading(false));
    }
  }, [showSettings, updateConfig]);


  const handleSave = async () => {
    setLoading(true);
    setSaveStatus(null);
    try {
      const updated = await updateUserSettings(settings);
      setSettings(updated);

      updateConfig({
        astar_heuristic: updated.pathfinding.astar_heuristic,
        weight_function: updated.pathfinding.weight_function,
        k_paths: updated.pathfinding.k_paths,
        show_all_explored: updated.pathfinding.show_all_explored,
        animation_speed: updated.visualization.animation_speed,
        animation_granularity: updated.visualization.animation_granularity,
        floyd_warshall_node_limit: updated.pathfinding.floyd_warshall_node_limit || 1000,
      });

      setSaveStatus('Settings saved successfully.');
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

      updateConfig({
        astar_heuristic: data.pathfinding.astar_heuristic,
        weight_function: data.pathfinding.weight_function,
        k_paths: data.pathfinding.k_paths,
        show_all_explored: data.pathfinding.show_all_explored,
        animation_speed: data.visualization.animation_speed,
        animation_granularity: data.visualization.animation_granularity,
        floyd_warshall_node_limit: data.pathfinding.floyd_warshall_node_limit || 1000,
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

  const updatePathfinding = <K extends keyof UserSettings['pathfinding']>(
    key: K,
    value: UserSettings['pathfinding'][K]
  ) => {
    setSettings((prev) => ({
      ...prev,
      pathfinding: { ...prev.pathfinding, [key]: value },
    }));
  };

  const updateViz = <K extends keyof UserSettings['visualization']>(
    key: K,
    value: UserSettings['visualization'][K]
  ) => {
    setSettings((prev) => ({
      ...prev,
      visualization: { ...prev.visualization, [key]: value },
    }));
  };

  const updateCache = <K extends keyof UserSettings['cache']>(
    key: K,
    value: UserSettings['cache'][K]
  ) => {
    setSettings((prev) => ({
      ...prev,
      cache: { ...prev.cache, [key]: value },
    }));
  };

  return (
    <Dialog open={showSettings} onOpenChange={(open) => setShowSettings(open)}>
      <DialogContent className="border-neutral-800 bg-black p-0 text-neutral-100 sm:max-w-2xl">
        <DialogHeader className="border-b border-neutral-800 px-6 py-4">
          <DialogTitle className="text-base font-semibold text-white">Settings</DialogTitle>
          <DialogDescription className="text-neutral-500">
            Configure pathfinding, visualization, and cache preferences.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[70vh] px-6 py-5">
          <div className="space-y-6">
            <section className="space-y-4">
              <h3 className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Pathfinding
              </h3>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">Default algorithm</label>
                  <Select
                    value={settings.pathfinding.default_algorithm}
                    onValueChange={(value) =>
                      updatePathfinding('default_algorithm', value as AlgorithmType)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select algorithm" />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(ALGORITHM_NAMES) as AlgorithmType[]).map((key) => (
                        <SelectItem key={key} value={key}>
                          {ALGORITHM_NAMES[key]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">A* heuristic</label>
                  <Select
                    value={settings.pathfinding.astar_heuristic}
                    onValueChange={(value) =>
                      updatePathfinding('astar_heuristic', value as HeuristicType)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select heuristic" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="haversine">Haversine</SelectItem>
                      <SelectItem value="manhattan">Manhattan</SelectItem>
                      <SelectItem value="euclidean">Euclidean</SelectItem>
                      <SelectItem value="zero">Zero (Dijkstra)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">Weight function</label>
                  <Select
                    value={settings.pathfinding.weight_function}
                    onValueChange={(value) =>
                      updatePathfinding('weight_function', value as WeightFunction)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select weight function" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="distance">Shortest distance</SelectItem>
                      <SelectItem value="time">Fastest time</SelectItem>
                      <SelectItem value="hybrid">Hybrid</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">K-Paths</label>
                  <Input
                    type="number"
                    min="1"
                    max="5"
                    value={settings.pathfinding.k_paths}
                    onChange={(e) =>
                      updatePathfinding('k_paths', parseInt(e.target.value, 10) || 1)
                    }
                    className="font-ui-mono"
                  />
                </div>
              </div>

              {/* Floyd-Warshall Node Limit Slider */}
              <div className="space-y-3 rounded border border-neutral-800 bg-black p-3">
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-neutral-500">
                    <span>Floyd-Warshall Node Limit</span>
                    <span className="font-ui-mono text-neutral-300">
                      {(settings.pathfinding.floyd_warshall_node_limit || 1000).toLocaleString()}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1000"
                    max="5000"
                    step="100"
                    value={settings.pathfinding.floyd_warshall_node_limit || 1000}
                    onChange={(e) => {
                      updatePathfinding('floyd_warshall_node_limit', parseInt(e.target.value, 10));
                    }}
                    className="h-2 w-full cursor-pointer rounded bg-neutral-800"
                    style={{
                      accentColor: `rgb(${Math.round(220 + ((settings.pathfinding.floyd_warshall_node_limit || 1000) - 1000) / 4000 * 35)}, ${Math.round(38 - ((settings.pathfinding.floyd_warshall_node_limit || 1000) - 1000) / 4000 * 38)}, ${Math.round(38 - ((settings.pathfinding.floyd_warshall_node_limit || 1000) - 1000) / 4000 * 38)})`,
                    }}
                  />
                </div>
                <p className="text-xs leading-relaxed text-neutral-500">
                  Floyd-Warshall has O(V³) complexity. Higher limits increase computation time exponentially.
                  {(settings.pathfinding.floyd_warshall_node_limit || 1000) >= 4000 && (
                    <span className="block mt-1 text-amber-400">
                      ⚠️ Values above 4000 may cause significant delays or timeouts.
                    </span>
                  )}
                </p>
              </div>

              <label className="flex items-center gap-2 text-sm text-neutral-400">
                <Checkbox
                  checked={settings.pathfinding.show_all_explored}
                  onCheckedChange={(checked) =>
                    updatePathfinding('show_all_explored', Boolean(checked))
                  }
                />
                Show explored junctions + streets
              </label>
            </section>

            <Separator />

            <section className="space-y-4">
              <h3 className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Visualization
              </h3>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">Animation speed</label>
                  <Select
                    value={String(settings.visualization.animation_speed)}
                    onValueChange={(value) =>
                      updateViz('animation_speed', parseFloat(value))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select speed" />
                    </SelectTrigger>
                    <SelectContent>
                      {SPEED_OPTIONS.map((speed) => (
                        <SelectItem key={speed} value={String(speed)}>
                          {speed === 0 ? 'Instant (No animation)' : `${speed}x`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">Animation granularity</label>
                  <Select
                    value={settings.visualization.animation_granularity}
                    onValueChange={(value) =>
                      updateViz('animation_granularity', value as AnimationGranularity)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select granularity" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="every_node">Every node</SelectItem>
                      <SelectItem value="every_n">Batch (every N nodes)</SelectItem>
                      <SelectItem value="frontier_only">Frontier only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-sm text-neutral-500">Color scheme</label>
                  <Input
                    type="text"
                    value={settings.visualization.color_scheme}
                    onChange={(e) => updateViz('color_scheme', e.target.value)}
                  />
                </div>
              </div>
            </section>

            <Separator />

            <section className="space-y-4">
              <h3 className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Cache
              </h3>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-sm text-neutral-500">Refresh schedule</label>
                  <Input
                    type="text"
                    placeholder="daily"
                    value={settings.cache.refresh_schedule}
                    onChange={(e) => updateCache('refresh_schedule', e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">Auto-approve after (days)</label>
                  <Input
                    type="number"
                    min="1"
                    value={settings.cache.auto_approve_after_days}
                    onChange={(e) =>
                      updateCache('auto_approve_after_days', parseInt(e.target.value, 10) || 0)
                    }
                    className="font-ui-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-neutral-500">Defer max (days)</label>
                  <Input
                    type="number"
                    min="1"
                    value={settings.cache.defer_max_days}
                    onChange={(e) =>
                      updateCache('defer_max_days', parseInt(e.target.value, 10) || 0)
                    }
                    className="font-ui-mono"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-neutral-400">
                <Checkbox
                  checked={settings.cache.prompt_on_refresh}
                  onCheckedChange={(checked) =>
                    updateCache('prompt_on_refresh', Boolean(checked))
                  }
                />
                Prompt before cache refresh
              </label>
            </section>
          </div>
        </ScrollArea>

        <DialogFooter className="items-center border-t border-neutral-800 px-6 py-4">
          <span className="mr-auto text-sm text-neutral-500">{saveStatus}</span>
          <Button onClick={handleReset} disabled={loading} variant="secondary">
            Reset to Defaults
          </Button>
          <Button onClick={handleSave} disabled={loading} variant="primary">
            {loading ? 'Saving...' : 'Save Settings'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
