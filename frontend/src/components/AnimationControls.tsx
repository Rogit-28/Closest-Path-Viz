import React, { useCallback, useRef, useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import { usePlaybackStore } from '../stores/playbackStore';
import { SPEED_OPTIONS } from '../types';
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

export default function AnimationControls() {
  const isRunning = useAppStore((s) => s.isRunning);
  const progressRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Use selectors to only subscribe to what we need
  const isPlaying = usePlaybackStore((s) => s.isPlaying);
  const speed = usePlaybackStore((s) => s.speed);
  const activeAlgorithm = usePlaybackStore((s) => s.activeAlgorithm);
  const events = usePlaybackStore((s) => s.events);
  const playbackIndex = usePlaybackStore((s) => s.playbackIndex);
  const streamComplete = usePlaybackStore((s) => s.streamComplete);

  // Get all algorithms that have events
  const algorithms = Object.keys(events);
  const hasEvents = algorithms.length > 0;
  
  // Check if we should show controls
  const shouldShow = isRunning || hasEvents;
  
  const currentAlgo = activeAlgorithm || algorithms[0] || null;
  
  // Calculate derived values
  const totalEvents = currentAlgo ? (events[currentAlgo]?.length || 0) : 0;
  const currentIndex = currentAlgo ? (playbackIndex[currentAlgo] || 0) : 0;
  const progress = totalEvents > 0 ? Math.round((currentIndex / totalEvents) * 100) : 0;
  const isStreamComplete = currentAlgo ? (streamComplete[currentAlgo] || false) : false;
  const isComplete = totalEvents > 0 && currentIndex >= totalEvents && isStreamComplete;

  const formatSpeed = (spd: number) => {
    if (spd === 0) return 'Instant';
    return `${spd}x`;
  };

  // Handle scrubber click/drag
  const handleProgressInteraction = useCallback((clientX: number) => {
    if (!progressRef.current || !currentAlgo) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const newIndex = Math.round(percentage * totalEvents);
    usePlaybackStore.getState().seekTo(currentAlgo, newIndex);
  }, [currentAlgo, totalEvents]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    handleProgressInteraction(e.clientX);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isDragging) {
      handleProgressInteraction(e.clientX);
    }
  }, [isDragging, handleProgressInteraction]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add/remove event listeners for drag
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Step forward by a small number of events
  const handleStepForward = () => {
    if (currentAlgo) {
      usePlaybackStore.getState().advancePlayback(currentAlgo, 10);
    }
  };

  const handleTogglePlayPause = () => {
    usePlaybackStore.getState().togglePlayPause();
  };

  const handleRestart = () => {
    if (!currentAlgo) return;
    usePlaybackStore.getState().restartAlgorithmPlayback(currentAlgo);
  };

  const handleSetSpeed = (newSpeed: number) => {
    usePlaybackStore.getState().setSpeed(newSpeed);
  };

  const handleSetActiveAlgorithm = (algo: string) => {
    usePlaybackStore.getState().setActiveAlgorithm(algo);
  };

  if (!shouldShow) {
    return null;
  }

  return (
    <div className="glass-panel absolute bottom-6 left-1/2 z-30 flex -translate-x-1/2 flex-col gap-2 rounded border border-neutral-800 px-3 py-2">
      {/* Progress bar / Scrubber */}
      {hasEvents && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-neutral-500 w-8 text-right tabular-nums">
            {progress}%
          </span>
          <div
            ref={progressRef}
            className="relative h-2 w-48 cursor-pointer rounded-full bg-neutral-800"
            onMouseDown={handleMouseDown}
          >
            {/* Progress fill */}
            <div
              className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-cyan-500 to-cyan-400 transition-all duration-75"
              style={{ width: `${progress}%` }}
            />
            {/* Scrubber thumb */}
            <div
              className="absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 rounded-full border-2 border-cyan-400 bg-neutral-900 shadow-lg transition-all duration-75"
              style={{ left: `calc(${progress}% - 7px)` }}
            />
          </div>
          <span className="text-[10px] text-neutral-500 w-16 tabular-nums">
            {currentIndex.toLocaleString()}/{totalEvents.toLocaleString()}
          </span>
        </div>
      )}

      {/* Controls row */}
      <div className="flex items-center gap-2">
        {/* Play/Pause button */}
        <Button
          onClick={handleTogglePlayPause}
          variant="secondary"
          size="icon"
          className="h-8 w-8"
          title={isPlaying ? "Pause" : "Play"}
          aria-label={isPlaying ? "Pause animation" : "Play animation"}
        >
          {isPlaying ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M6.75 5.25a.75.75 0 01.75-.75H9a.75.75 0 01.75.75v13.5a.75.75 0 01-.75.75H7.5a.75.75 0 01-.75-.75V5.25zm7.5 0A.75.75 0 0115 4.5h1.5a.75.75 0 01.75.75v13.5a.75.75 0 01-.75.75H15a.75.75 0 01-.75-.75V5.25z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 ml-0.5">
              <path fillRule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clipRule="evenodd" />
            </svg>
          )}
        </Button>

        {hasEvents && currentAlgo && (
          <Button
            onClick={handleRestart}
            variant="secondary"
            size="icon"
            className="h-8 w-8"
            title="Restart from beginning"
            aria-label="Restart animation from beginning"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
              <path fillRule="evenodd" d="M4.5 12a7.5 7.5 0 1112.866 5.303.75.75 0 111.06 1.06A9 9 0 103 12h1.5a.75.75 0 010 1.5H1.75A.75.75 0 011 12.75V10a.75.75 0 011.5 0v2z" clipRule="evenodd" />
            </svg>
          </Button>
        )}

        {/* Step forward button (when paused) */}
        {!isPlaying && !isComplete && hasEvents && (
          <Button
            onClick={handleStepForward}
            variant="secondary"
            size="icon"
            className="h-8 w-8"
            title="Step Forward (+10 events)"
            aria-label="Step forward 10 events"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
              <path fillRule="evenodd" d="M13.28 11.47a.75.75 0 010 1.06l-6.22 6.22a.75.75 0 01-1.06-1.06L11.69 12 6 6.31a.75.75 0 011.06-1.06l6.22 6.22zm6.22 0a.75.75 0 010 1.06l-6.22 6.22a.75.75 0 01-1.06-1.06L17.91 12l-5.69-5.69a.75.75 0 011.06-1.06l6.22 6.22z" clipRule="evenodd" />
            </svg>
          </Button>
        )}

        <Separator orientation="vertical" className="mx-1 h-5" />

        {/* Speed selector */}
        <div className="w-[90px]">
          <Select
            value={String(speed)}
            onValueChange={(value) => handleSetSpeed(Number(value))}
          >
            <SelectTrigger className="h-8 px-2">
              <SelectValue placeholder="Speed">{formatSpeed(speed)}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(SPEED_OPTIONS as readonly number[]).map((spd) => (
                <SelectItem key={spd} value={String(spd)}>
                  {formatSpeed(spd)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Algorithm selector (when multiple algorithms) */}
        {algorithms.length > 1 && (
          <>
            <Separator orientation="vertical" className="mx-1 h-5" />
            <div className="w-[100px]">
              <Select
                value={currentAlgo || ''}
                onValueChange={handleSetActiveAlgorithm}
              >
                <SelectTrigger className="h-8 px-2">
                  <SelectValue placeholder="Algorithm">
                    {currentAlgo?.toUpperCase().replace('_', ' ')}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {algorithms.map((algo) => (
                    <SelectItem key={algo} value={algo}>
                      {algo.toUpperCase().replace('_', ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        )}

        {/* Status indicator */}
        {currentAlgo && (
          <>
            <Separator orientation="vertical" className="mx-1 h-5" />
            <div className="flex flex-col justify-center px-1.5">
              <span className="text-[9px] uppercase leading-none tracking-wide text-neutral-500">
                {isComplete ? 'Complete' : isPlaying ? 'Playing' : 'Paused'}
              </span>
              <span className="mt-0.5 text-xs font-medium capitalize leading-none text-white">
                {currentAlgo.replace('_', ' ')}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
