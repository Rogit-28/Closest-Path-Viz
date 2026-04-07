import { useEffect } from 'react';
import { useAppStore } from './stores/appStore';
import { getFrontendConfig } from './utils/api';
import MapView from './components/MapView';
import ControlPanel from './components/ControlPanel';
import MetricsDashboard from './components/MetricsDashboard';
import AlgorithmComparison from './components/AlgorithmComparison';
import SettingsPanel from './components/SettingsPanel';
import AnimationControls from './components/AnimationControls';
import { PlaybackLoopProvider } from './hooks/usePlaybackLoop';

export default function App() {
  const { results, isRunning, comparisonMode, wsError } = useAppStore();

  // Load frontend config on mount
  useEffect(() => {
    getFrontendConfig()
      .then((cfg) => {
        if (import.meta.env.DEV) console.log('Frontend config loaded:', cfg);
      })
      .catch((err) => {
        if (import.meta.env.DEV) console.warn('Backend not available:', err);
        // Frontend works in standalone mode
      });
  }, []);

  const showComparison = comparisonMode && results.length >= 2 && !isRunning;

  return (
    <div className="app-shell flex h-screen w-screen overflow-hidden text-neutral-100">
      {/* Playback loop - handles animation frame updates */}
      <PlaybackLoopProvider />
      
      {/* Left sidebar */}
      <ControlPanel />

      {/* Map area */}
      <div className="relative flex flex-1 flex-col">
        {wsError && (
          <div className="absolute left-4 top-4 z-40 max-w-md rounded border border-red-900/50 bg-black px-3 py-2 text-xs text-red-400">
            {wsError}
          </div>
        )}
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
