import React from 'react';
import { Settings } from 'lucide-react';
import { useAppStore } from '../stores/appStore';
import { usePlaybackStore } from '../stores/playbackStore';
import { useSSEPathfinding } from '../hooks/useSSEPathfinding';
import {
  AlgorithmType,
  HeuristicType,
  WeightFunction,
  ALGORITHM_NAMES
} from '../types';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Separator } from './ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { ScrollArea } from './ui/scroll-area';

export default function ControlPanel() {
  const store = useAppStore();
  const resetPlayback = usePlaybackStore((s) => s.reset);
  const { startPathfinding, stopPathfinding } = useSSEPathfinding();

  const resetRunState = () => {
    store.setStartPoint(null);
    store.setEndPoint(null);
    store.clearResults();
    resetPlayback();
    store.setRunPhase('idle');
  };

  const handleRun = () => {
    if (store.runPhase !== 'idle') return;
    if (store.startPoint && store.endPoint && store.selectedAlgorithms.length > 0) {
      console.log('[ControlPanel] Starting pathfinding with algorithms:', store.selectedAlgorithms);
      startPathfinding(store.startPoint, store.endPoint, store.selectedAlgorithms, store.config);
    }
  };

  const handleClear = () => {
    if (store.isRunning) stopPathfinding();
    resetRunState();
  };

  const handleNewRun = () => {
    if (store.isRunning) stopPathfinding();
    resetRunState();
  };

  const isAstarSelected = store.selectedAlgorithms.includes('astar');
  const isHybridSelected = store.config.weight_function === 'hybrid';
  const isKPathsApplicable = store.selectedAlgorithms.length > 0;
  const selectedCount = store.selectedAlgorithms.length;

  return (
    <aside className="glass-panel-strong z-20 flex h-full w-80 flex-col text-neutral-100">
      <div className="border-b border-neutral-800 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-lg font-semibold text-white">
              Pathfinder
            </h1>
            <p className="mt-0.5 text-xs text-neutral-500">Routing workspace</p>
          </div>
          <div className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-400">
            {selectedCount} selected
          </div>
        </div>
      </div>

      <div className="px-5 pt-3">
        <Button
          onClick={store.toggleSettings}
          variant="secondary"
          className="w-full justify-center gap-2"
          title="Settings"
        >
          <Settings className="h-4 w-4" />
          Settings
        </Button>
      </div>

      <ScrollArea className="mt-3 flex-1 px-5 pb-5">
        <section className="rounded border border-neutral-800 bg-neutral-950 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Algorithms
            </h2>
            <label className="flex items-center gap-2 text-xs text-neutral-500">
              <Checkbox
                checked={store.comparisonMode}
                onCheckedChange={(checked) => store.setComparisonMode(Boolean(checked))}
              />
              Compare
            </label>
          </div>

          <div className="space-y-1.5">
            {(Object.keys(ALGORITHM_NAMES) as AlgorithmType[]).map((alg) => (
              <label
                key={alg}
                className={`flex cursor-pointer items-center gap-3 rounded border px-3 py-2 transition-colors ${
                  store.selectedAlgorithms.includes(alg)
                    ? 'border-red-600/50 bg-red-950/20 text-white'
                    : 'border-neutral-800 bg-black text-neutral-400 hover:border-neutral-700 hover:text-neutral-200'
                }`}
              >
                <input
                  type={store.comparisonMode ? 'checkbox' : 'radio'}
                  name="algorithm"
                  checked={store.selectedAlgorithms.includes(alg)}
                  onChange={() => {
                    if (store.comparisonMode) {
                      // Comparison mode: toggle individual algorithm (checkbox behavior)
                      store.toggleAlgorithm(alg);
                    } else {
                      // Single mode: replace entire selection array (radio behavior)
                      if (store.selectedAlgorithms.includes(alg)) {
                        // Clicking already-selected algorithm: do nothing (radio can't be unchecked)
                        return;
                      } else {
                        // Replace entire array with just this algorithm
                        store.setSelectedAlgorithms([alg]);
                      }
                    }
                  }}
                  className="h-3.5 w-3.5 accent-red-600"
                />
                <span className="text-sm">{ALGORITHM_NAMES[alg]}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="mt-4 rounded border border-neutral-800 bg-neutral-950 p-4">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
            Configuration
          </h2>

          <div className="space-y-4">
            {isAstarSelected && (
              <div className="space-y-1.5">
                <label className="block text-xs text-neutral-500">Heuristic</label>
                <Select
                  value={store.config.astar_heuristic}
                  onValueChange={(value) =>
                    store.updateConfig({ astar_heuristic: value as HeuristicType })
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
            )}

            <div className="space-y-1.5">
              <label className="block text-xs text-neutral-500">Weight function</label>
              <Select
                value={store.config.weight_function}
                onValueChange={(value) =>
                  store.updateConfig({ weight_function: value as WeightFunction })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select weight function" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="distance">Distance</SelectItem>
                  <SelectItem value="time">Time</SelectItem>
                  <SelectItem value="hybrid">Hybrid</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {isHybridSelected && (
              <div className="space-y-3 rounded border border-neutral-800 bg-black p-3">
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-neutral-500">
                    <span>Distance (α)</span>
                    <span className="font-ui-mono text-neutral-300">
                      {store.config.hybrid_weights?.alpha.toFixed(2) || '0.50'}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={store.config.hybrid_weights?.alpha || 0.5}
                    onChange={(e) => {
                      const current = store.config.hybrid_weights || { alpha: 0.5, beta: 0.5 };
                      store.updateConfig({
                        hybrid_weights: { ...current, alpha: parseFloat(e.target.value) },
                      });
                    }}
                    className="h-1 w-full cursor-pointer rounded bg-neutral-800 accent-red-600"
                  />
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-neutral-500">
                    <span>Time (β)</span>
                    <span className="font-ui-mono text-neutral-300">
                      {store.config.hybrid_weights?.beta.toFixed(2) || '0.50'}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={store.config.hybrid_weights?.beta || 0.5}
                    onChange={(e) => {
                      const current = store.config.hybrid_weights || { alpha: 0.5, beta: 0.5 };
                      store.updateConfig({
                        hybrid_weights: { ...current, beta: parseFloat(e.target.value) },
                      });
                    }}
                    className="h-1 w-full cursor-pointer rounded bg-neutral-800 accent-red-600"
                  />
                </div>
              </div>
            )}

            {isKPathsApplicable && (
              <div className="space-y-1.5">
                <label className="block text-xs text-neutral-500">K-Paths</label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  value={store.config.k_paths}
                  onChange={(e) =>
                    store.updateConfig({ k_paths: parseInt(e.target.value, 10) || 1 })
                  }
                  className="font-ui-mono"
                />
              </div>
            )}

              <label className="flex items-center gap-2 pt-1 text-sm text-neutral-400">
                <Checkbox
                  checked={store.config.show_all_explored}
                  onCheckedChange={(checked) =>
                    store.updateConfig({ show_all_explored: Boolean(checked) })
                  }
                />
                Show explored junctions + streets
              </label>
            </div>
          </section>

        {store.graphInfo && (
          <section className="mt-4 rounded border border-neutral-800 bg-neutral-950 p-4">
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
              Graph info
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded border border-neutral-800 bg-black px-2 py-1.5">
                <span className="block text-neutral-600">Nodes</span>
                <span className="font-ui-mono text-neutral-200">
                  {store.graphInfo.node_count.toLocaleString()}
                </span>
              </div>
              <div className="rounded border border-neutral-800 bg-black px-2 py-1.5">
                <span className="block text-neutral-600">Edges</span>
                <span className="font-ui-mono text-neutral-200">
                  {store.graphInfo.edge_count.toLocaleString()}
                </span>
              </div>
            </div>
            <div className="mt-2 rounded border border-neutral-800 bg-black px-2 py-1.5 text-xs">
              <span className="block text-neutral-600">Source</span>
              <span
                className={`font-ui-mono ${
                  store.graphInfo.source === 'synthetic' ? 'text-amber-400' : 'text-neutral-200'
                }`}
              >
                {store.graphInfo.source}
              </span>
            </div>
            {store.graphInfo.source === 'synthetic' && (
              <div className="mt-2 rounded border border-amber-900/40 bg-amber-950/20 px-2 py-1.5 text-xs text-amber-300">
                Synthetic fallback mode: routes may not follow real streets.
              </div>
            )}
          </section>
        )}
      </ScrollArea>

      <div className="border-t border-neutral-800 bg-black px-5 py-4">
        <div className="space-y-2 rounded border border-neutral-800 bg-neutral-950 px-3 py-3">
          <div className="flex items-center space-x-2 text-xs">
            <div className={`h-2 w-2 rounded-full ${store.startPoint ? 'bg-green-500' : 'bg-neutral-700'}`} />
            <span className="text-neutral-500">Start</span>
            <span className="font-ui-mono truncate text-neutral-300">
              {store.startPoint
                ? `${store.startPoint.lat.toFixed(4)}, ${store.startPoint.lon.toFixed(4)}`
                : 'Not set'}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <div className={`h-2 w-2 rounded-full ${store.endPoint ? 'bg-red-500' : 'bg-neutral-700'}`} />
            <span className="text-neutral-500">End</span>
            <span className="font-ui-mono truncate text-neutral-300">
              {store.endPoint
                ? `${store.endPoint.lat.toFixed(4)}, ${store.endPoint.lon.toFixed(4)}`
                : 'Not set'}
            </span>
          </div>
        </div>

        <Separator className="my-3" />

        {store.runPhase === 'completed' && (
          <div className="mb-3 rounded border border-amber-900/40 bg-amber-950/20 px-3 py-2 text-xs text-amber-300">
            Run complete. Click <span className="font-semibold">New Run</span> to unlock map coordinate picking.
          </div>
        )}

        <div className="flex gap-2">
          <Button
            onClick={handleClear}
            variant="secondary"
            className="flex-1"
          >
            Clear
          </Button>
          {store.runPhase === 'completed' && (
            <Button
              onClick={handleNewRun}
              variant="secondary"
              className="flex-1"
            >
              New Run
            </Button>
          )}
          <Button
            onClick={handleRun}
            disabled={
              store.isRunning ||
              store.runPhase !== 'idle' ||
              !store.startPoint ||
              !store.endPoint ||
              store.selectedAlgorithms.length === 0
            }
            variant="primary"
            className="flex-[2]"
          >
            {store.isRunning ? 'Running...' : 'Find Path'}
          </Button>
        </div>
      </div>
    </aside>
  );
}
