import React from 'react';
import { useAppStore } from '../stores/appStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { 
  AlgorithmType, 
  HeuristicType, 
  WeightFunction, 
  ALGORITHM_NAMES 
} from '../types';

export default function ControlPanel() {
  const store = useAppStore();
  const { startPathfinding } = useWebSocket();

  const handleRun = () => {
    if (store.startPoint && store.endPoint && store.selectedAlgorithms.length > 0) {
      startPathfinding(store.startPoint, store.endPoint, store.selectedAlgorithms, store.config);
    }
  };

  const isAstarSelected = store.selectedAlgorithms.includes('astar');
  const isHybridSelected = store.config.weight_function === 'hybrid';
  const isKPathsApplicable = store.selectedAlgorithms.some(a => ['dijkstra', 'astar'].includes(a));

  return (
    <div className="w-72 bg-slate-900 border-r border-slate-700 flex flex-col h-full overflow-y-auto text-slate-200 z-20">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800">
        <h1 className="text-xl font-bold text-slate-100">Pathfinder</h1>
        <button 
          onClick={store.toggleSettings}
          className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          title="Settings"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287-.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      <div className="p-4 flex-1 space-y-5">
        <section>
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Algorithms</h2>
            <label className="flex items-center space-x-2 text-xs cursor-pointer">
              <input 
                type="checkbox" 
                checked={store.comparisonMode}
                onChange={() => store.setComparisonMode(!store.comparisonMode)}
                className="rounded border-slate-600 bg-slate-800 text-blue-500"
              />
              <span className="text-slate-400">Compare</span>
            </label>
          </div>
          <div className="space-y-2">
            {(Object.keys(ALGORITHM_NAMES) as AlgorithmType[]).map((alg) => (
              <label key={alg} className={`flex items-center space-x-3 p-2 rounded cursor-pointer ${store.selectedAlgorithms.includes(alg) ? 'bg-slate-800 border border-slate-600' : 'hover:bg-slate-800/50 border border-transparent'}`}>
                <input
                  type={store.comparisonMode ? "checkbox" : "radio"}
                  name="algorithm"
                  checked={store.selectedAlgorithms.includes(alg)}
                  onChange={() => {
                    if (!store.comparisonMode && !store.selectedAlgorithms.includes(alg)) {
                      store.selectedAlgorithms.forEach(a => store.toggleAlgorithm(a));
                      store.toggleAlgorithm(alg);
                    } else if (store.comparisonMode || store.selectedAlgorithms.includes(alg)) {
                      store.toggleAlgorithm(alg);
                    }
                  }}
                  className={`${store.comparisonMode ? 'rounded' : 'rounded-full'} border-slate-600 bg-slate-800 text-blue-500`}
                />
                <span className="text-sm font-medium">{ALGORITHM_NAMES[alg]}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="space-y-4 pt-4 border-t border-slate-800">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Configuration</h2>
          
          {isAstarSelected && (
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 block">Heuristic</label>
              <select
                value={store.config.astar_heuristic}
                onChange={(e) => store.updateConfig({ astar_heuristic: e.target.value as HeuristicType })}
                className="w-full bg-slate-800 border border-slate-700 rounded py-1 px-2 text-sm text-slate-200"
              >
                <option value="haversine">Haversine</option>
                <option value="manhattan">Manhattan</option>
                <option value="euclidean">Euclidean</option>
                <option value="zero">Zero (Dijkstra)</option>
              </select>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs text-slate-400 block">Weight Function</label>
            <select
              value={store.config.weight_function}
              onChange={(e) => store.updateConfig({ weight_function: e.target.value as WeightFunction })}
              className="w-full bg-slate-800 border border-slate-700 rounded py-1 px-2 text-sm text-slate-200"
            >
              <option value="distance">Distance</option>
              <option value="time">Time</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </div>

          {isHybridSelected && (
            <div className="p-2 bg-slate-800 rounded border border-slate-700 space-y-3">
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Distance (α)</span>
                  <span>{store.config.hybrid_weights?.alpha.toFixed(2) || '0.50'}</span>
                </div>
                <input
                  type="range"
                  min="0" max="1" step="0.05"
                  value={store.config.hybrid_weights?.alpha || 0.5}
                  onChange={(e) => {
                    const current = store.config.hybrid_weights || { alpha: 0.5, beta: 0.5 };
                    store.updateConfig({ hybrid_weights: { ...current, alpha: parseFloat(e.target.value) } });
                  }}
                  className="w-full h-1 bg-slate-600 rounded cursor-pointer"
                />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Time (β)</span>
                  <span>{store.config.hybrid_weights?.beta.toFixed(2) || '0.50'}</span>
                </div>
                <input
                  type="range"
                  min="0" max="1" step="0.05"
                  value={store.config.hybrid_weights?.beta || 0.5}
                  onChange={(e) => {
                    const current = store.config.hybrid_weights || { alpha: 0.5, beta: 0.5 };
                    store.updateConfig({ hybrid_weights: { ...current, beta: parseFloat(e.target.value) } });
                  }}
                  className="w-full h-1 bg-slate-600 rounded cursor-pointer"
                />
              </div>
            </div>
          )}

          {isKPathsApplicable && (
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 block">K-Paths</label>
              <input
                type="number"
                min="1" max="10"
                value={store.config.k_paths}
                onChange={(e) => store.updateConfig({ k_paths: parseInt(e.target.value, 10) })}
                className="w-full bg-slate-800 border border-slate-700 rounded py-1 px-2 text-sm text-slate-200"
              />
            </div>
          )}

          <label className="flex items-center space-x-2 cursor-pointer pt-2">
            <input
              type="checkbox"
              checked={store.config.show_all_explored}
              onChange={(e) => store.updateConfig({ show_all_explored: e.target.checked })}
              className="rounded border-slate-600 bg-slate-800 text-blue-500"
            />
            <span className="text-sm font-medium">Show All Explored</span>
          </label>
        </section>

        {store.graphInfo && (
          <section className="pt-4 border-t border-slate-800">
            <div className="bg-slate-800 rounded p-3">
              <h3 className="text-xs font-semibold text-slate-400 mb-2">Graph Info</h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-slate-500 block">Nodes</span>
                  <span className="font-mono text-slate-300">{store.graphInfo.node_count.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Edges</span>
                  <span className="font-mono text-slate-300">{store.graphInfo.edge_count.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </section>
        )}
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-900 space-y-4 mt-auto">
        <div className="space-y-2">
          <div className="flex items-center space-x-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${store.startPoint ? 'bg-green-500' : 'bg-slate-600'}`}></div>
            <span className="text-slate-400 w-10">Start:</span>
            <span className="font-mono text-slate-300 truncate">
              {store.startPoint ? `${store.startPoint.lat.toFixed(4)}, ${store.startPoint.lon.toFixed(4)}` : 'Not set'}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${store.endPoint ? 'bg-red-500' : 'bg-slate-600'}`}></div>
            <span className="text-slate-400 w-10">End:</span>
            <span className="font-mono text-slate-300 truncate">
              {store.endPoint ? `${store.endPoint.lat.toFixed(4)}, ${store.endPoint.lon.toFixed(4)}` : 'Not set'}
            </span>
          </div>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={() => { store.clearResults(); store.reset(); }}
            disabled={store.isRunning}
            className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Clear
          </button>
          <button
            onClick={handleRun}
            disabled={store.isRunning || !store.startPoint || !store.endPoint || store.selectedAlgorithms.length === 0}
            className="flex-[2] py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {store.isRunning ? 'Running...' : 'Find Path'}
          </button>
        </div>
      </div>
    </div>
  );
}
