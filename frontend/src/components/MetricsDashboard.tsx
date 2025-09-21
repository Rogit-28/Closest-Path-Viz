import React from 'react';
import { useAppStore } from '../stores/appStore';
import { AlgorithmResult, ALGORITHM_COLORS, ALGORITHM_NAMES, AlgorithmType } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

export default function MetricsDashboard() {
  const { results, showMetrics, toggleMetrics } = useAppStore();

  if (results.length === 0 || !showMetrics) {
    return null;
  }

  const chartData = results.map(r => ({
    name: ALGORITHM_NAMES[r.algorithm as AlgorithmType] || r.algorithm,
    algorithm: r.algorithm as AlgorithmType,
    computation_time_ms: r.computation_time_ms,
    nodes_explored: r.nodes_explored,
  }));

  return (
    <div className="absolute top-4 right-4 z-20 w-80 max-h-[calc(100vh-6rem)] overflow-y-auto bg-slate-900/95 backdrop-blur rounded-xl border border-slate-700 shadow-2xl p-4 text-slate-200 flex flex-col gap-4">
      <div className="flex justify-between items-center sticky top-0 bg-slate-900/95 py-2 z-10 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Algorithm Metrics</h2>
        <button
          onClick={toggleMetrics}
          className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800"
          aria-label="Close metrics dashboard"
        >
          <svg className="w-5 h-5" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
            <path d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <div className="space-y-4">
        {results.map((result, index) => (
          <div key={`${result.algorithm}-${index}`} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: ALGORITHM_COLORS[result.algorithm as AlgorithmType] || '#CBD5E1' }}
              />
              <span className="font-medium text-slate-100">{ALGORITHM_NAMES[result.algorithm as AlgorithmType] || result.algorithm}</span>
              {result.success ? (
                <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">Success</span>
              ) : (
                <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400">Failed</span>
              )}
            </div>

            {result.success ? (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-800 p-2 rounded flex flex-col">
                  <span className="text-slate-400">Time</span>
                  <span className="font-mono text-slate-200">{result.computation_time_ms.toFixed(2)} ms</span>
                </div>
                <div className="bg-slate-800 p-2 rounded flex flex-col">
                  <span className="text-slate-400">Nodes</span>
                  <span className="font-mono text-slate-200">{result.nodes_explored.toLocaleString()}</span>
                </div>
                <div className="bg-slate-800 p-2 rounded flex flex-col">
                  <span className="text-slate-400">Distance</span>
                  <span className="font-mono text-slate-200">{result.path_length_km.toFixed(2)} km</span>
                </div>
                <div className="bg-slate-800 p-2 rounded flex flex-col">
                  <span className="text-slate-400">Cost</span>
                  <span className="font-mono text-slate-200">{result.cost.toLocaleString()}</span>
                </div>
                {result.memory_usage_mb && (
                   <div className="bg-slate-800 p-2 rounded flex flex-col col-span-2">
                     <span className="text-slate-400">Memory</span>
                     <span className="font-mono text-slate-200">{result.memory_usage_mb.toFixed(2)} MB</span>
                   </div>
                )}
              </div>
            ) : (
               <div className="text-xs text-rose-400/80 bg-rose-950/30 p-2 rounded break-words">
                 {result.error || 'Unknown error occurred'}
               </div>
            )}
          </div>
        ))}
      </div>

      {results.length > 0 && results.some(r => r.success) && (
        <>
          <div className="mt-2">
            <h3 className="text-sm font-medium text-slate-300 mb-2">Computation Time (ms)</h3>
            <div className="h-40 w-full bg-slate-800/30 rounded-lg p-2 border border-slate-700/30">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#475569' }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9', borderRadius: '0.5rem', fontSize: '12px' }}
                    itemStyle={{ color: '#f1f5f9' }}
                    cursor={{ fill: '#334155', opacity: 0.4 }}
                  />
                  <Bar dataKey="computation_time_ms" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={ALGORITHM_COLORS[entry.algorithm] || '#94a3b8'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mt-2 mb-2">
            <h3 className="text-sm font-medium text-slate-300 mb-2">Nodes Explored</h3>
            <div className="h-40 w-full bg-slate-800/30 rounded-lg p-2 border border-slate-700/30">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#475569' }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9', borderRadius: '0.5rem', fontSize: '12px' }}
                    itemStyle={{ color: '#f1f5f9' }}
                    cursor={{ fill: '#334155', opacity: 0.4 }}
                  />
                  <Bar dataKey="nodes_explored" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={ALGORITHM_COLORS[entry.algorithm] || '#94a3b8'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
