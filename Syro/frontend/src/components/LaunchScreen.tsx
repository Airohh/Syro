import { useState, useEffect, useRef } from 'react';

interface LogEntry {
  type: 'info' | 'log' | 'error';
  message: string;
  ts: number;
}

interface Props {
  onBackendReady: () => void;
}

export default function LaunchScreen({ onBackendReady }: Props) {
  const [status, setStatus] = useState<'idle' | 'launching' | 'ready' | 'error'>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [dots, setDots] = useState('');
  const logRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const interval = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 500);
    return () => clearInterval(interval);
  }, []);

  // Auto-start polling on mount
  useEffect(() => {
    handleStart();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (type: LogEntry['type'], message: string) => {
    setLogs(prev => [...prev.slice(-60), { type, message, ts: Date.now() }]);
  };

  const pollHealth = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/health');
        if (res.ok) {
          clearInterval(pollRef.current!);
          setStatus('ready');
          addLog('info', '✓ Backend prêt !');
          setTimeout(onBackendReady, 800);
        }
      } catch {
        // still waiting
      }
    }, 1500);
  };

  const handleStart = () => {
    if (status === 'launching') return;
    setStatus('launching');
    setLogs([]);
    addLog('info', 'En attente du backend sur http://127.0.0.1:8000...');
    pollHealth();
  };

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const isLaunching = status === 'launching';

  return (
    <div className="launch-root">
      <div className="launch-bg" />
      <div className="launch-grid" />

      <div className="launch-card">
        <div className="launch-logo">
          <span className="launch-logo-icon">◆</span>
          <span className="launch-logo-text">SYRO</span>
        </div>

        <p className="launch-subtitle">Assistant RAG Multi-Domaines</p>

        <div className="launch-status-row">
          <span className={`launch-dot ${isLaunching ? 'pulsing' : 'offline'}`} />
          <span className="launch-status-text">
            {isLaunching ? `Démarrage en cours${dots}` : 'Backend hors ligne'}
          </span>
        </div>

        {!isLaunching && (
          <button className="launch-btn" onClick={handleStart}>
            <span className="launch-btn-icon">▶</span>
            Démarrer Syro
          </button>
        )}

        {logs.length > 0 && (
          <div className="launch-terminal" ref={logRef}>
            {logs.map((l, i) => (
              <div key={i} className={`launch-log launch-log-${l.type}`}>
                <span className="launch-log-prefix">
                  {l.type === 'error' ? '✗' : l.type === 'info' ? '›' : '·'}
                </span>
                {l.message}
              </div>
            ))}
            {isLaunching && (
              <div className="launch-cursor">█</div>
            )}
          </div>
        )}

        <p className="launch-hint">
          Commande manuelle :{' '}
          <code>uvicorn app.main:app --port 8000</code>
        </p>
      </div>

      <style>{`
        .launch-root {
          position: fixed; inset: 0;
          display: flex; align-items: center; justify-content: center;
          z-index: 9999;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .launch-bg {
          position: absolute; inset: 0;
          background: radial-gradient(ellipse at 20% 50%, #1a1040 0%, #0d0d1a 50%, #0a0a14 100%);
        }

        .launch-grid {
          position: absolute; inset: 0;
          background-image:
            linear-gradient(rgba(99,102,241,.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99,102,241,.06) 1px, transparent 1px);
          background-size: 40px 40px;
        }

        .launch-card {
          position: relative;
          width: 480px;
          background: rgba(255,255,255,.04);
          backdrop-filter: blur(24px);
          border: 1px solid rgba(255,255,255,.08);
          border-radius: 24px;
          padding: 48px 40px 40px;
          box-shadow:
            0 0 0 1px rgba(99,102,241,.15),
            0 32px 64px rgba(0,0,0,.6),
            inset 0 1px 0 rgba(255,255,255,.06);
          display: flex; flex-direction: column; align-items: center;
          gap: 20px;
          animation: fadeUp .4s ease both;
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .launch-logo {
          display: flex; align-items: center; gap: 10px;
        }

        .launch-logo-icon {
          font-size: 28px;
          color: #818cf8;
          filter: drop-shadow(0 0 12px rgba(129,140,248,.8));
        }

        .launch-logo-text {
          font-size: 32px;
          font-weight: 800;
          letter-spacing: .12em;
          background: linear-gradient(135deg, #c7d2fe 0%, #818cf8 50%, #6366f1 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .launch-subtitle {
          margin: 0;
          font-size: 13px;
          color: rgba(255,255,255,.35);
          letter-spacing: .04em;
        }

        .launch-status-row {
          display: flex; align-items: center; gap: 8px;
          background: rgba(255,255,255,.04);
          border: 1px solid rgba(255,255,255,.06);
          border-radius: 100px;
          padding: 6px 14px;
        }

        .launch-dot {
          width: 8px; height: 8px; border-radius: 50%;
        }

        .launch-dot.offline { background: #ef4444; box-shadow: 0 0 6px #ef4444; }

        .launch-dot.pulsing {
          background: #818cf8;
          box-shadow: 0 0 8px #818cf8;
          animation: pulse 1s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: .5; transform: scale(.8); }
        }

        .launch-status-text {
          font-size: 12px;
          color: rgba(255,255,255,.5);
          min-width: 160px;
        }

        .launch-btn {
          display: flex; align-items: center; gap: 10px;
          background: linear-gradient(135deg, #6366f1, #818cf8);
          color: white;
          border: none;
          border-radius: 12px;
          padding: 14px 32px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          width: 100%;
          justify-content: center;
          transition: all .2s;
          box-shadow: 0 4px 20px rgba(99,102,241,.4);
        }

        .launch-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 28px rgba(99,102,241,.6);
          background: linear-gradient(135deg, #4f52e0, #6366f1);
        }

        .launch-btn:active { transform: translateY(0); }

        .launch-btn-icon { font-size: 12px; }

        .launch-terminal {
          width: 100%;
          max-height: 200px;
          overflow-y: auto;
          background: rgba(0,0,0,.5);
          border: 1px solid rgba(255,255,255,.06);
          border-radius: 10px;
          padding: 12px 14px;
          font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
          font-size: 11px;
          line-height: 1.6;
          scrollbar-width: thin;
          scrollbar-color: rgba(255,255,255,.1) transparent;
        }

        .launch-log {
          display: flex; gap: 8px;
          color: rgba(255,255,255,.5);
          word-break: break-all;
        }

        .launch-log-info { color: rgba(129,140,248,.9); }
        .launch-log-error { color: rgba(248,113,113,.9); }

        .launch-log-prefix {
          flex-shrink: 0;
          color: rgba(255,255,255,.2);
        }

        .launch-cursor {
          color: rgba(129,140,248,.7);
          animation: blink .8s step-end infinite;
        }

        @keyframes blink { 50% { opacity: 0; } }

        .launch-hint {
          margin: 0;
          font-size: 11px;
          color: rgba(255,255,255,.2);
          text-align: center;
        }

        .launch-hint code {
          background: rgba(255,255,255,.06);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: monospace;
        }
      `}</style>
    </div>
  );
}
