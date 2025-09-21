import React from 'react';
import { useAppStore } from '../stores/appStore';
import { SPEED_OPTIONS } from '../types';

export default function AnimationControls() {
  const store = useAppStore();

  if (!store.isRunning && !store.isPaused) {
    return null;
  }

  const currentSpeed = store.config.animation_speed;
  const speedIndex = (SPEED_OPTIONS as readonly number[]).indexOf(currentSpeed);

  const cycleSpeed = () => {
    const nextIndex = (speedIndex + 1) % SPEED_OPTIONS.length;
    store.updateConfig({ animation_speed: SPEED_OPTIONS[nextIndex] });
  };

  const formatSpeed = (speed: number) => {
    if (speed === 0) return 'Instant';
    return `${speed}x`;
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/90 backdrop-blur-sm border border-slate-700 rounded-full shadow-2xl flex items-center p-2 space-x-2 z-30 transition-all">
      <button
        onClick={() => store.setPaused(!store.isPaused)}
        className="w-10 h-10 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900"
        title={store.isPaused ? "Play" : "Pause"}
      >
        {store.isPaused ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 ml-1">
            <path fillRule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
            <path fillRule="evenodd" d="M6.75 5.25a.75.75 0 01.75-.75H9a.75.75 0 01.75.75v13.5a.75.75 0 01-.75.75H7.5a.75.75 0 01-.75-.75V5.25zm7.5 0A.75.75 0 0115 4.5h1.5a.75.75 0 01.75.75v13.5a.75.75 0 01-.75.75H15a.75.75 0 01-.75-.75V5.25z" clipRule="evenodd" />
          </svg>
        )}
      </button>

      <div className="w-px h-6 bg-slate-700 mx-1"></div>

      <button
        onClick={cycleSpeed}
        className="min-w-[4rem] px-3 h-8 flex items-center justify-center rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition-colors border border-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-500"
        title="Animation Speed"
      >
        {formatSpeed(currentSpeed)}
      </button>

      {store.isPaused && (
        <button
          onClick={() => {
            // Note: Implementation of step forward would require additional store logic
            // For now, this is a placeholder UI element as requested
          }}
          className="w-8 h-8 flex items-center justify-center rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-500"
          title="Step Forward"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M13.28 11.47a.75.75 0 010 1.06l-6.22 6.22a.75.75 0 01-1.06-1.06L11.69 12 6 6.31a.75.75 0 011.06-1.06l6.22 6.22zm6.22 0a.75.75 0 010 1.06l-6.22 6.22a.75.75 0 01-1.06-1.06L17.91 12l-5.69-5.69a.75.75 0 011.06-1.06l6.22 6.22z" clipRule="evenodd" />
          </svg>
        </button>
      )}

      {store.currentAlgorithm && (
        <>
          <div className="w-px h-6 bg-slate-700 mx-1"></div>
          <div className="px-3 flex flex-col justify-center">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider leading-none mb-1">
              Running
            </span>
            <span className="text-sm text-slate-200 font-medium leading-none">
              {store.currentAlgorithm.replace('_', ' ')}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
