import { useEffect } from 'react';
import { useAppStore } from './stores/appStore';
import { getFrontendConfig } from './utils/api';
import MapView from './components/MapView';
import ControlPanel from './components/ControlPanel';
import MetricsDashboard from './components/MetricsDashboard';
import AlgorithmComparison from './components/AlgorithmComparison';
import SettingsPanel from './components/SettingsPanel';
import AnimationControls from './components/AnimationControls';

export default function App() {
  const { showSettings, showMetrics, results, isRunning, comparisonMode } = useAppStore();

  // Load frontend config on mount
  useEffect(() => {
    getFrontendConfig()
      .then((cfg) => {
        console.log('Frontend config loaded:', cfg);
      })
      .catch((err) => {
        console.warn('Backend not available:', err);
        // Frontend works in standalone mode
      });
  }, []);

  const showComparison = comparisonMode && results.length >= 2 && !isRunning;

  return (
    <div className="flex w-screen h-screen overflow-hidden bg-slate-950 text-white">
      {/* Left sidebar */}
      <ControlPanel />

      {/* Map area */}
      <div className="relative flex-1 flex flex-col">
        <MapView />

        {/* Animation controls - floating at bottom center */}
        <AnimationControls />

        {/* Metrics dashboard - uses fixed positioning internally */}
        <MetricsDashboard />

        {/* Comparison overlay - shown after multi-algo run */}
        {showComparison && <AlgorithmComparison />}
      </div>

      {/* Settings modal */}
      <SettingsPanel />
    </div>
  );
}
