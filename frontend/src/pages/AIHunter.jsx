import React, { useState, useEffect } from 'react';
import { TerminalSquare, Play, RefreshCw, Server, AlertCircle } from 'lucide-react';

export default function AIHunter() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hunting, setHunting] = useState(false);

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = () => {
    setLoading(true);
    fetch('/api/agent/auto-hunt-queue')
      .then(r => r.json())
      .then(d => {
        setQueue(d.queue || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  const startAutoHunt = () => {
    setHunting(true);
    fetch('/api/agent/auto-hunt-all', { method: 'POST' })
      .then(r => r.json())
      .then(() => {
        setHunting(false);
        fetchQueue();
      })
      .catch(() => setHunting(false));
  };

  const startSingleHunt = (id) => {
    fetch('/api/agent/hunt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exchange_id: id })
    }).then(() => fetchQueue());
  };

  return (
    <div className="flex flex-col h-full p-6 gap-6 z-10 relative">
      <div className="clay-card p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TerminalSquare className="w-6 h-6 text-[var(--color-primary-500)]" />
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight drop-shadow-sm">AI Hunter Control</h1>
            <p className="text-xs text-slate-400 mt-0.5">Autonomous Exploitation Engine</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button onClick={fetchQueue} className="clay-btn-secondary px-3 py-1.5 flex items-center gap-2 text-xs">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
          <button 
            onClick={startAutoHunt} 
            disabled={hunting || queue.length === 0}
            className="clay-btn-primary px-4 py-2 flex items-center gap-2 text-sm disabled:opacity-50">
            <Play className={`w-4 h-4 ${hunting ? 'animate-pulse' : ''}`} /> 
            {hunting ? 'Hunting in progress...' : 'Auto-Hunt All'}
          </button>
        </div>
      </div>

      <div className="flex-1 clay-card flex flex-col overflow-hidden">
        <div className="p-3 border-b border-[var(--color-dark-700)] bg-black/10 flex items-center gap-2">
          <Server className="w-4 h-4 text-slate-400 ml-1" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Triage Queue</span>
          <span className="ml-auto text-xs font-mono bg-[var(--color-dark-900)] px-2 py-0.5 rounded border border-[var(--color-dark-700)] text-slate-300">
            {queue.length} items
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 bg-[var(--color-dark-950)]">
          {loading ? (
            <div className="flex items-center justify-center h-full text-slate-500 text-sm font-mono">Loading queue...</div>
          ) : queue.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3">
              <AlertCircle className="w-10 h-10 opacity-30" />
              <p>Queue is empty. Waiting for passive analyzer to find vulnerabilities.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {queue.map(item => (
                <div key={item.id} className="clay-inset p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-l-2 border-[var(--color-primary-500)]">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[var(--color-primary-500)]/20 text-[var(--color-primary-400)]">
                        Score: {item.score}
                      </span>
                      <span className="text-xs font-mono text-slate-400">{item.method}</span>
                    </div>
                    <div className="text-sm font-mono text-white truncate max-w-2xl" title={item.url}>
                      {item.path}
                    </div>
                    <div className="text-xs text-slate-500 mt-1.5 truncate max-w-2xl">
                      Matched: {item.matched_vulns ? JSON.parse(item.matched_vulns).join(', ') : 'Unknown'}
                    </div>
                  </div>
                  
                  <button onClick={() => startSingleHunt(item.id)} className="clay-btn-secondary shrink-0 text-xs py-1.5 px-4 flex items-center gap-2">
                    <Play className="w-3 h-3 text-[var(--color-primary-400)]" /> Hunt
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}