import React, { useMemo } from 'react';
import { useAppStore } from '../stores/appStore';
import { ALGORITHM_COLORS, ALGORITHM_NAMES, AlgorithmType } from '../types';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { Button } from './ui/button';

export default function AlgorithmComparison() {
  const { results, comparisonMode, setComparisonMode, isRunning } = useAppStore();

  const activeResults = useMemo(() => results.filter((r) => r.success), [results]);

  const bestMetrics = useMemo(() => {
    if (activeResults.length === 0) return { time: 0, nodes: 0, length: 0, memory: 0 };
    return {
      time: Math.min(...activeResults.map((r) => r.computation_time_ms)),
      nodes: Math.min(...activeResults.map((r) => r.nodes_explored)),
      length: Math.min(...activeResults.map((r) => r.path_length_km)),
      memory: Math.min(...activeResults.map((r) => r.memory_usage_mb)),
    };
  }, [activeResults]);

  const radarData = useMemo(() => {
    if (activeResults.length === 0) return [];

    const maxMetrics = {
      time: Math.max(...activeResults.map((r) => r.computation_time_ms)) || 1,
      nodes: Math.max(...activeResults.map((r) => r.nodes_explored)) || 1,
      length: Math.max(...activeResults.map((r) => r.path_length_km)) || 1,
      memory: Math.max(...activeResults.map((r) => r.memory_usage_mb)) || 1,
    };

    const metrics = [
      { subject: 'Time', key: 'time' as const },
      { subject: 'Nodes', key: 'nodes' as const },
      { subject: 'Distance', key: 'length' as const },
      { subject: 'Memory', key: 'memory' as const },
    ];

    return metrics.map((metric) => {
      const dataPoint: Record<string, string | number> = { subject: metric.subject };
      activeResults.forEach((r) => {
        let val = 0;
        switch (metric.key) {
          case 'time':
            val = r.computation_time_ms / maxMetrics.time;
            break;
          case 'nodes':
            val = r.nodes_explored / maxMetrics.nodes;
            break;
          case 'length':
            val = r.path_length_km / maxMetrics.length;
            break;
          case 'memory':
            val = r.memory_usage_mb / maxMetrics.memory;
            break;
        }
        // Invert so higher score is better on the radar
        dataPoint[r.algorithm] = Math.max(0.1, 1 - val); 
      });
      return dataPoint;
    });
  }, [activeResults]);


  if (!comparisonMode || results.length < 2 || isRunning) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
      <div className="glass-panel-strong flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded border border-neutral-800">
        
        <div className="flex items-center justify-between border-b border-neutral-800 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-300">Algorithm Comparison</h2>
          <Button
            onClick={() => setComparisonMode(false)}
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            aria-label="Close comparison"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
        <div className="space-y-6 pb-4">
          
          <div className="overflow-x-auto rounded border border-neutral-800">
            <table className="w-full text-left text-sm text-neutral-300">
              <thead className="border-b border-neutral-800 bg-neutral-950 text-xs uppercase text-neutral-500">
                <tr>
                  <th scope="col" className="px-5 py-3 font-medium">Algorithm</th>
                  <th scope="col" className="px-5 py-3 font-medium">Time (ms)</th>
                  <th scope="col" className="px-5 py-3 font-medium">Nodes Explored</th>
                  <th scope="col" className="px-5 py-3 font-medium">Path Length (km)</th>
                  <th scope="col" className="px-5 py-3 font-medium">Memory (MB)</th>
                  <th scope="col" className="px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, idx) => {
                  const isSuccess = r.success;
                  const algoName = ALGORITHM_NAMES[r.algorithm as AlgorithmType] || r.algorithm;
                  
                  return (
                    <tr 
                      key={`${r.algorithm}-${idx}`} 
                      className="border-b border-neutral-900 transition-colors hover:bg-neutral-950"
                    >
                      <td className="px-5 py-3 font-medium text-white">
                        {algoName}
                      </td>
                      <td className={`px-5 py-3 font-ui-mono ${isSuccess && r.computation_time_ms === bestMetrics.time ? 'text-red-500 font-semibold' : ''}`}>
                        {isSuccess ? r.computation_time_ms.toFixed(2) : '-'}
                      </td>
                      <td className={`px-5 py-3 font-ui-mono ${isSuccess && r.nodes_explored === bestMetrics.nodes ? 'text-red-500 font-semibold' : ''}`}>
                        {isSuccess ? r.nodes_explored.toLocaleString() : '-'}
                      </td>
                      <td className={`px-5 py-3 font-ui-mono ${isSuccess && r.path_length_km === bestMetrics.length ? 'text-red-500 font-semibold' : ''}`}>
                        {isSuccess ? r.path_length_km.toFixed(2) : '-'}
                      </td>
                      <td className={`px-5 py-3 font-ui-mono ${isSuccess && r.memory_usage_mb === bestMetrics.memory ? 'text-red-500 font-semibold' : ''}`}>
                        {isSuccess ? r.memory_usage_mb.toFixed(2) : '-'}
                      </td>
                      <td className="px-5 py-3">
                          {isSuccess ? (
                            <span className="inline-flex items-center rounded border border-green-800/40 bg-green-950/30 px-2 py-0.5 text-xs text-green-400">
                              Success
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded border border-red-800/40 bg-red-950/30 px-2 py-0.5 text-xs text-red-400" title={r.error || 'Failed'}>
                              Failed
                            </span>
                          )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {activeResults.length > 0 && (
            <div className="rounded border border-neutral-800 bg-black p-5">
              <h3 className="mb-4 text-center text-xs font-medium uppercase tracking-wide text-neutral-400">
                Relative Performance (Higher is Better)
              </h3>
              <div className="h-[380px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                    <PolarGrid stroke="#262626" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#737373', fontSize: 12 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0a0a0a', borderColor: '#262626', color: '#fafafa', borderRadius: '0.375rem', fontSize: '12px' }}
                      itemStyle={{ color: '#fafafa' }}
                      formatter={(value: number) => [value.toFixed(2), 'Score']}
                    />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    {activeResults.map((r) => {
                      const algoName = ALGORITHM_NAMES[r.algorithm as AlgorithmType] || r.algorithm;
                      const color = ALGORITHM_COLORS[r.algorithm as keyof typeof ALGORITHM_COLORS] || '#525252';
                      return (
                        <Radar
                          key={r.algorithm}
                          name={algoName}
                          dataKey={r.algorithm}
                          stroke={color}
                          fill={color}
                          fillOpacity={0.25}
                        />
                      );
                    })}
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

        </div>
        </div>
      </div>
    </div>
  );
}
