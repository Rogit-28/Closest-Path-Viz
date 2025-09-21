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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        
        <div className="flex justify-between items-center p-6 border-b border-slate-700">
          <h2 className="text-2xl font-bold text-slate-100">Algorithm Comparison</h2>
          <button
            onClick={() => setComparisonMode(false)}
            className="text-slate-400 hover:text-white transition-colors p-2 rounded-lg hover:bg-slate-800"
            aria-label="Close comparison"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          <div className="overflow-x-auto rounded-lg border border-slate-700">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-800/50 text-slate-400 border-b border-slate-700">
                <tr>
                  <th scope="col" className="px-6 py-4">Algorithm</th>
                  <th scope="col" className="px-6 py-4">Time (ms)</th>
                  <th scope="col" className="px-6 py-4">Nodes Explored</th>
                  <th scope="col" className="px-6 py-4">Path Length (km)</th>
                  <th scope="col" className="px-6 py-4">Memory (MB)</th>
                  <th scope="col" className="px-6 py-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, idx) => {
                  const isSuccess = r.success;
                  const algoName = ALGORITHM_NAMES[r.algorithm as AlgorithmType] || r.algorithm;
                  
                  return (
                    <tr 
                      key={`${r.algorithm}-${idx}`} 
                      className="border-b border-slate-700/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="px-6 py-4 font-medium text-slate-100">
                        {algoName}
                      </td>
                      <td className={`px-6 py-4 ${isSuccess && r.computation_time_ms === bestMetrics.time ? 'text-green-400 font-semibold' : ''}`}>
                        {isSuccess ? r.computation_time_ms.toFixed(2) : '-'}
                      </td>
                      <td className={`px-6 py-4 ${isSuccess && r.nodes_explored === bestMetrics.nodes ? 'text-green-400 font-semibold' : ''}`}>
                        {isSuccess ? r.nodes_explored.toLocaleString() : '-'}
                      </td>
                      <td className={`px-6 py-4 ${isSuccess && r.path_length_km === bestMetrics.length ? 'text-green-400 font-semibold' : ''}`}>
                        {isSuccess ? r.path_length_km.toFixed(2) : '-'}
                      </td>
                      <td className={`px-6 py-4 ${isSuccess && r.memory_usage_mb === bestMetrics.memory ? 'text-green-400 font-semibold' : ''}`}>
                        {isSuccess ? r.memory_usage_mb.toFixed(2) : '-'}
                      </td>
                      <td className="px-6 py-4">
                        {isSuccess ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
                            Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20" title={r.error || 'Failed'}>
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
            <div className="bg-slate-800/30 p-6 rounded-xl border border-slate-700">
              <h3 className="text-lg font-medium text-slate-200 mb-6 text-center">
                Relative Performance (Higher is Better)
              </h3>
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 14 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }}
                      itemStyle={{ color: '#f1f5f9' }}
                      formatter={(value: number) => [value.toFixed(2), 'Score']}
                    />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    {activeResults.map((r) => {
                      const algoName = ALGORITHM_NAMES[r.algorithm as AlgorithmType] || r.algorithm;
                      const color = ALGORITHM_COLORS[r.algorithm as keyof typeof ALGORITHM_COLORS] || '#cbd5e1';
                      return (
                        <Radar
                          key={r.algorithm}
                          name={algoName}
                          dataKey={r.algorithm}
                          stroke={color}
                          fill={color}
                          fillOpacity={0.3}
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
  );
}
