import { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import TimelinePlugin from 'wavesurfer.js/dist/plugins/timeline.esm.js';

export interface RegionData {
  id: string;
  start: number;
  end: number;
  color?: string;
}

export interface WaveformPlayerProps {
  audioUrl: string;
  regions: RegionData[];
  activeRegionId?: string;
  isReadOnly?: boolean;
  onRegionUpdate: (id: string, start: number, end: number) => void;
  onRegionCreated?: (start: number, end: number) => void;
  onRegionClicked?: (id: string) => void;
}

export interface WaveformPlayerRef {
  play: () => void;
  pause: () => void;
  playPause: () => void;
  playRegion: (id: string) => void;
  seekTo: (time: number) => void;
  skip: (seconds: number) => void;
  addRegion: (start: number, end: number) => void;
}


const WaveformPlayer = forwardRef<WaveformPlayerRef, WaveformPlayerProps>((
  { audioUrl, regions, activeRegionId, isReadOnly = false, onRegionUpdate, onRegionCreated, onRegionClicked },
  ref
) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const wavesurfer = useRef<WaveSurfer | null>(null);
  const wsRegions = useRef<any>(null);
  const isReady = useRef(false);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [zoom, setZoom] = useState(30);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  // Initialise WaveSurfer once per audioUrl
  useEffect(() => {
    if (!containerRef.current || !timelineRef.current || !audioUrl) return;

    isReady.current = false;
    setLoading(true);
    setError(null);

    let ws: WaveSurfer;
    let reg: any;
    try {
      ws = WaveSurfer.create({
        container: containerRef.current,
        waveColor: 'rgba(140, 200, 255, 0.6)',
        progressColor: 'rgba(56, 189, 248, 1)',
        cursorColor: '#fff',
        url: audioUrl,
        height: 100,
        normalize: true,
        plugins: [
          TimelinePlugin.create({ container: timelineRef.current }),
        ],
      });
      reg = ws.registerPlugin(RegionsPlugin.create());
    } catch (err: any) {
      console.error('Error creating WaveSurfer:', err);
      setError(`Failed to initialize player: ${err.message}`);
      setLoading(false);
      return;
    }

    wsRegions.current = reg;
    wavesurfer.current = ws;

    ws.on('ready', () => {
      isReady.current = true;
      setDuration(ws.getDuration());
      setLoading(false);

      // Draw initial regions
      reg.clearRegions();
      regions.forEach((r, idx) => {
        const isActive = activeRegionId === r.id;
        reg.addRegion({
          id: r.id,
          start: r.start,
          end: r.end,
          content: String(idx + 1),
          color: isActive ? 'rgba(236, 72, 153, 0.4)' : (r.color || 'rgba(99, 179, 237, 0.25)'),
          drag: !isReadOnly,
          resize: !isReadOnly,
        });
      });

      // Safe zoom after ready
      try { ws.zoom(zoom); } catch (_) {}
    });

    ws.on('loading', () => setLoading(true));
    ws.on('play', () => setIsPlaying(true));
    ws.on('pause', () => setIsPlaying(false));
    ws.on('timeupdate', (t) => setCurrentTime(t));
    ws.on('error', (e) => {
      setLoading(false);
      setError(`Failed to load audio: ${String(e)}`);
    });

    reg.on('region-updated', (region: any) => {
      if (!isReadOnly) {
        onRegionUpdate(region.id, region.start, region.end);
      }
    });

    reg.on('region-created', (region: any) => {
      if (!isReadOnly && region.id.startsWith('wavesurfer_') && onRegionCreated) {
        onRegionCreated(region.start, region.end);
        region.remove();
      }
    });

    reg.on('region-clicked', (region: any, e: Event) => {
      e.stopPropagation();
      if (onRegionClicked) onRegionClicked(region.id);
    });

    // Enable drag-to-select new regions only if not read-only
    if (!isReadOnly) {
      reg.enableDragSelection({ color: 'rgba(99, 179, 237, 0.25)' });
    }

    return () => {
      isReady.current = false;
      ws.destroy();
      wavesurfer.current = null;
      wsRegions.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl, isReadOnly]);

  // Sync regions from React state (only when ready)
  useEffect(() => {
    if (!wsRegions.current || !isReady.current) return;
    wsRegions.current.clearRegions();
    regions.forEach((r, idx) => {
      const isActive = activeRegionId === r.id;
      wsRegions.current.addRegion({
        id: r.id,
        start: r.start,
        end: r.end,
        content: String(idx + 1),
        color: isActive ? 'rgba(236, 72, 153, 0.4)' : (r.color || 'rgba(99, 179, 237, 0.25)'),
        drag: !isReadOnly,
        resize: !isReadOnly,
      });
    });
  }, [regions, activeRegionId, isReadOnly]);

  // Zoom (only when ready)
  useEffect(() => {
    if (!wavesurfer.current || !isReady.current) return;
    try { wavesurfer.current.zoom(zoom); } catch (_) {}
  }, [zoom]);

  // Playback rate (only when ready)
  useEffect(() => {
    if (!wavesurfer.current || !isReady.current) return;
    try { wavesurfer.current.setPlaybackRate(playbackRate); } catch (_) {}
  }, [playbackRate]);

  useImperativeHandle(ref, () => ({
    play: () => wavesurfer.current?.play(),
    pause: () => wavesurfer.current?.pause(),
    playPause: () => wavesurfer.current?.playPause(),
    playRegion: (id: string) => {
      if (!wsRegions.current) return;
      const all = wsRegions.current.getRegions?.() ?? [];
      const target = Array.isArray(all) ? all.find((r: any) => r.id === id) : all[id];
      target?.play?.();
    },
    seekTo: (time: number) => {
      if (wavesurfer.current) {
        wavesurfer.current.setTime(time);
      }
    },
    skip: (seconds: number) => {
      if (wavesurfer.current) {
        wavesurfer.current.skip(seconds);
      }
    },
    addRegion: (_start: number, _end: number) => {},
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%' }}>
      {/* Waveform area */}
      <div style={{
        background: 'rgba(10,20,40,0.8)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: '0.75rem',
        position: 'relative',
        minHeight: '140px',
      }}>
        {loading && !error && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-muted)', fontSize: '0.875rem', borderRadius: '8px', background: 'rgba(10,20,40,0.85)',
            zIndex: 2,
          }}>
            Loading audio…
          </div>
        )}
        {error && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#ef4444', fontSize: '0.875rem', borderRadius: '8px', background: 'rgba(10,20,40,0.85)',
            zIndex: 2, padding: '1rem', textAlign: 'center',
          }}>
            {error}
          </div>
        )}
        <div ref={containerRef} style={{ width: '100%' }} />
        <div ref={timelineRef} style={{ width: '100%', marginTop: '4px' }} />
      </div>

      {/* Transport controls — styled like reference image */}
      <div style={{
        background: 'rgba(10,20,40,0.6)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: '0.6rem 1rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
      }}>
        {/* Left: rewind / play / forward + timecode */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={() => wavesurfer.current?.skip(-5)}
            title="Skip back 5s"
            style={{ background: 'none', border: 'none', color: 'var(--text-main)', fontSize: '1.1rem', cursor: 'pointer', padding: '4px' }}
          >⏮</button>
          <button
            onClick={() => wavesurfer.current?.skip(-2)}
            title="Rewind 2s"
            style={{ background: 'none', border: 'none', color: 'var(--text-main)', fontSize: '1rem', cursor: 'pointer', padding: '4px' }}
          >↩</button>
          <button
            onClick={() => wavesurfer.current?.playPause()}
            style={{
              width: '36px', height: '36px', borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none', color: 'white', fontSize: '0.9rem',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >{isPlaying ? '⏸' : '▶'}</button>
          <button
            onClick={() => wavesurfer.current?.skip(2)}
            title="Forward 2s"
            style={{ background: 'none', border: 'none', color: 'var(--text-main)', fontSize: '1rem', cursor: 'pointer', padding: '4px' }}
          >↪</button>
          <button
            onClick={() => wavesurfer.current?.skip(5)}
            title="Skip forward 5s"
            style={{ background: 'none', border: 'none', color: 'var(--text-main)', fontSize: '1.1rem', cursor: 'pointer', padding: '4px' }}
          >⏭</button>
          <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-main)', marginLeft: '0.5rem' }}>
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>

        {/* Right: speed + zoom */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>Playback Speed: {playbackRate.toFixed(1)}x</span>
            <input
              type="range" min="0.25" max="3" step="0.25"
              value={playbackRate}
              onChange={e => setPlaybackRate(parseFloat(e.target.value))}
              style={{ width: '80px', accentColor: '#6366f1' }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>Timeline Scale:</span>
            <input
              type="range" min="1" max="200" step="1"
              value={zoom}
              onChange={e => setZoom(Number(e.target.value))}
              style={{ width: '80px', accentColor: '#6366f1' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
});

WaveformPlayer.displayName = 'WaveformPlayer';
export default WaveformPlayer;
