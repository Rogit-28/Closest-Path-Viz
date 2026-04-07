/**
 * Playback loop hook using requestAnimationFrame.
 * 
 * Advances the playback index based on the current speed setting.
 * Handles batching at high speeds for smooth performance.
 */
import { useEffect, useRef } from 'react';
import { usePlaybackStore } from '../stores/playbackStore';

/**
 * Calculate how many events to advance per frame based on speed.
 */
function getEventsPerFrame(speed: number, totalRemaining: number): number {
  if (speed === 0) {
    return totalRemaining; // Instant - jump to end
  }
  
  if (speed >= 1) {
    return Math.ceil(speed);
  }
  
  return 1;
}

/**
 * For slow speeds (< 1x), determine how many frames to wait between advances.
 */
function getFrameSkip(speed: number): number {
  if (speed >= 1 || speed === 0) {
    return 1;
  }
  return Math.round(1 / speed);
}

export function usePlaybackLoop() {
  const frameCountRef = useRef(0);
  const rafIdRef = useRef<number | null>(null);
  
  // Subscribe to specific state changes
  const isPlaying = usePlaybackStore((s) => s.isPlaying);
  const activeAlgorithm = usePlaybackStore((s) => s.activeAlgorithm);
  const speed = usePlaybackStore((s) => s.speed);

  useEffect(() => {
    if (!isPlaying || !activeAlgorithm) {
      // Cancel any existing animation frame
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
      return;
    }

    frameCountRef.current = 0;

    const tick = () => {
      // Get fresh state inside the tick function
      const state = usePlaybackStore.getState();
      const algo = state.activeAlgorithm;
      
      if (!algo || !state.isPlaying) {
        rafIdRef.current = null;
        return;
      }

      const currentIndex = state.playbackIndex[algo] || 0;
      const totalEvents = state.events[algo]?.length || 0;
      const isStreamComplete = state.streamComplete[algo];
      const currentSpeed = state.speed;

      // Check if we've reached the end
      if (currentIndex >= totalEvents && isStreamComplete) {
        state.markRenderEnd(algo);
        state.pause();
        rafIdRef.current = null;
        return;
      }

      // If stream is still coming and we've caught up, wait for more events
      if (currentIndex >= totalEvents && !isStreamComplete) {
        rafIdRef.current = requestAnimationFrame(tick);
        return;
      }

      // Handle instant speed
      if (currentSpeed === 0) {
        const remaining = totalEvents - currentIndex;
        if (remaining > 0) {
          state.advancePlayback(algo, remaining);
        }
        if (isStreamComplete) {
          state.markRenderEnd(algo);
          state.pause();
        }
        rafIdRef.current = null;
        return;
      }

      const frameSkip = getFrameSkip(currentSpeed);
      frameCountRef.current++;

      // For slow speeds, only advance on certain frames
      if (frameCountRef.current % frameSkip === 0) {
        const remaining = totalEvents - currentIndex;
        const eventsThisFrame = getEventsPerFrame(currentSpeed, remaining);
        state.advancePlayback(algo, eventsThisFrame);
      }

      rafIdRef.current = requestAnimationFrame(tick);
    };

    rafIdRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
    };
  }, [isPlaying, activeAlgorithm, speed]);
}

/**
 * Component to activate the playback loop.
 * Should be rendered once at the app level.
 */
export function PlaybackLoopProvider() {
  usePlaybackLoop();
  return null;
}
