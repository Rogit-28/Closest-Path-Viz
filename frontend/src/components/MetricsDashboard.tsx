import React from 'react';
import { useAppStore } from '../stores/appStore';
import { usePlaybackStore } from '../stores/playbackStore';
import { ALGORITHM_COLORS, ALGORITHM_NAMES, AlgorithmType } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';
import { Button } from './ui/button';

export default function MetricsDashboard() {
  const { results, showMetrics, toggleMetrics } = useAppStore();
  const { 
    getProgress, 
    getRenderTime, 
    isAlgoComplete,
    getTotalEvents,
  } = usePlaybackStore();

  if (results.length === 0 || !showMetrics) {
    return null;
  }

  const chartData = results.filter((r) => r.success).map(r => ({
    name: ALGORITHM_NAMES[r.algorithm as AlgorithmType] || r.algorithm,
    algorithm: r.algorithm as AlgorithmType,
    computation_time_ms: r.computation_time_ms,
    nodes_explored: r.nodes_explored,
  }));

  // Helper to format render time
  const formatRenderTime = (algo: string) => {
    const renderTime = getRenderTime(algo);
    if (renderTime === null) return null;
    
    if (renderTime >= 1000) {
      return `${(renderTime / 1000).toFixed(1)}s`;
    }
    return `${renderTime.toFixed(0)}ms`;
  };

  return (
    <div className="glass-panel absolute right-4 top-4 z-20 flex max-h-[calc(100vh-6rem)] w-96 flex-col rounded border border-neutral-800 p-4 text-neutral-200">
      <div className="mb-3 flex items-center justify-between border-b border-neutral-800 pb-2">
        <h2 className="text-xs font-medium uppercase tracking-wide text-neutral-400">Algorithm Metrics</h2>
        <Button
          onClick={toggleMetrics}
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Close metrics dashboard"
        >
          <svg className="w-4 h-4" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
            <path d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto pr-2">
        <div className="space-y-3 pb-4">
          {results.map((result, index) => {
            const algo = result.algorithm;
            const progress = getProgress(algo);
            const isComplete = isAlgoComplete(algo);
            const renderTimeStr = formatRenderTime(algo);
            const totalEvents = getTotalEvents(algo);
            const isRendering = totalEvents > 0 && !isComplete;
            
            return (
              <div key={`${result.algorithm}-${index}`} className="rounded border border-neutral-800 bg-neutral-950 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <div
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: ALGORITHM_COLORS[result.algorithm as AlgorithmType] || '#525252' }}
                  />
                  <span className="text-sm font-medium text-white">{ALGORITHM_NAMES[result.algorithm as AlgorithmType] || result.algorithm}</span>
                  {result.success ? (
                    isComplete ? (
                      <span className="ml-auto rounded border border-green-800/40 bg-green-950/30 px-2 py-0.5 text-xs text-green-400">Success</span>
                    ) : isRendering ? (
                      <span className="ml-auto rounded border border-cyan-800/40 bg-cyan-950/30 px-2 py-0.5 text-xs text-cyan-400">
                        Rendering {progress}%
                      </span>
                    ) : (
                      <span className="ml-auto rounded border border-yellow-800/40 bg-yellow-950/30 px-2 py-0.5 text-xs text-yellow-400">Computed</span>
                    )
                  ) : (
                    <span className="ml-auto rounded border border-red-800/40 bg-red-950/30 px-2 py-0.5 text-xs text-red-400">Failed</span>
                  )}
                </div>

                {result.success ? (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {/* Compute Time - always shown */}
                    <div className="flex flex-col rounded border border-neutral-800 bg-black p-2">
                      <span className="text-neutral-500">Compute</span>
                      <span className="font-ui-mono text-neutral-200">{result.computation_time_ms.toFixed(2)} ms</span>
                    </div>
                    
                    {/* Render Time or Progress */}
                    <div className="flex flex-col rounded border border-neutral-800 bg-black p-2">
                      <span className="text-neutral-500">{isComplete ? 'Render' : 'Progress'}</span>
                      {isComplete && renderTimeStr ? (
                        <span className="font-ui-mono text-neutral-200">{renderTimeStr}</span>
                      ) : isRendering ? (
                        <span className="font-ui-mono text-cyan-400">{progress}%</span>
                      ) : (
                        <span className="font-ui-mono text-neutral-500">—</span>
                      )}
                    </div>
                    
                    <div className="flex flex-col rounded border border-neutral-800 bg-black p-2">
                      <span className="text-neutral-500">Nodes</span>
                      <span className="font-ui-mono text-neutral-200">{result.nodes_explored.toLocaleString()}</span>
                    </div>
                    <div className="flex flex-col rounded border border-neutral-800 bg-black p-2">
                      <span className="text-neutral-500">Distance</span>
                      <span className="font-ui-mono text-neutral-200">{result.path_length_km.toFixed(2)} km</span>
                    </div>
                    <div className="flex flex-col rounded border border-neutral-800 bg-black p-2">
                      <span className="text-neutral-500">Cost</span>
                      <span className="font-ui-mono text-neutral-200">
                        {result.cost == null ? 'N/A' : result.cost.toLocaleString()}
                      </span>
                    </div>
                    {result.memory_usage_mb && (
                      <div className="flex flex-col rounded border border-neutral-800 bg-black p-2">
                        <span className="text-neutral-500">Memory</span>
                        <span className="font-ui-mono text-neutral-200">{result.memory_usage_mb.toFixed(2)} MB</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="break-words rounded border border-red-900/30 bg-red-950/20 p-2 text-xs text-red-400/80">
                    {result.error || 'Unknown error occurred'}
                  </div>
                )}
              </div>
            );
          })}

          {results.length > 0 && results.some((r) => r.success) && (
            <>
              <div className="mt-2">
                <h3 className="mb-2 text-xs font-medium text-neutral-400">Computation Time (ms)</h3>
                <div className="h-40 w-full rounded border border-neutral-800 bg-black p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: '#737373', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#404040' }} />
                      <YAxis tick={{ fill: '#737373', fontSize: 10 }} tickLine={false} axisLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0a0a0a', borderColor: '#262626', color: '#fafafa', borderRadius: '0.375rem', fontSize: '12px' }}
                        itemStyle={{ color: '#fafafa' }}
                        cursor={{ fill: '#262626', opacity: 0.4 }}
                      />
                      <Bar dataKey="computation_time_ms" radius={[2, 2, 0, 0]}>
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={ALGORITHM_COLORS[entry.algorithm] || '#525252'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="mb-2 mt-2">
                <h3 className="mb-2 text-xs font-medium text-neutral-400">Nodes Explored</h3>
                <div className="h-40 w-full rounded border border-neutral-800 bg-black p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: '#737373', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#404040' }} />
                      <YAxis tick={{ fill: '#737373', fontSize: 10 }} tickLine={false} axisLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0a0a0a', borderColor: '#262626', color: '#fafafa', borderRadius: '0.375rem', fontSize: '12px' }}
                        itemStyle={{ color: '#fafafa' }}
                        cursor={{ fill: '#262626', opacity: 0.4 }}
                      />
                      <Bar dataKey="nodes_explored" radius={[2, 2, 0, 0]}>
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={ALGORITHM_COLORS[entry.algorithm] || '#525252'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
