import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Radio, ShieldAlert, Eye, Activity, Filter, Trash2, ChevronRight, CheckCircle2 } from 'lucide-react';

const TYPE_CONFIG = {
  connected:               { color: '#4ade80', icon: '📡', label: 'Connection' },
  new_interesting_request: { color: '#ff855c', icon: '🔍', label: 'Triage Match' },
  ai_analyzing:            { color: '#60a5fa', icon: '🤖', label: 'AI Hunter Active' },
  new_finding:             { color: '#ef4444', icon: '🚨', label: 'Vulnerability!' },
  new_exchange:            { color: '#a9b7c6', icon: '→',  label: 'HTTP Exchange' },
};

const LEVEL_COLOR = {
  critical:    '#ef4444',
  interesting: '#ff6633',
  low:         '#eab308',
  normal:      '#5c5f61',
};

export default function LiveFeed() {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState({ total: 0, interesting: 0, findings: 0 });
  const [filter, setFilter] = useState('all');
  const bottomRef = useRef(null);
  const navigate = useNavigate();
  const esRef = useRef(null);

  useEffect(() => {
    connect();
    return () => esRef.current?.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const connect = () => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource('/api/stream/stream');
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => { setConnected(false); setTimeout(connect, 3000); };

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        setEvents(prev => [...prev.slice(-499), { ...event, id: Date.now() + Math.random() }]);
        setStats(prev => ({
          total: prev.total + (event.type === 'new_exchange' ? 1 : 0),
          interesting: prev.interesting + (event.type === 'new_interesting_request' ? 1 : 0),
          findings: prev.findings + (event.type === 'new_finding' ? 1 : 0),
        }));
      } catch {}
    };
  };

  const filtered = filter === 'all' ? events : events.filter(e => e.type === filter);

  return (
    <div className="flex flex-col h-full p-6 gap-6 z-10 relative">
      {/* Header Panel */}
      <div className="clay-card p-5 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Radio className="w-8 h-8" style={{ color: connected ? '#4ade80' : '#ef4444' }} />
            {connected && <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-green-400 rounded-full animate-ping"></span>}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight drop-shadow-sm">Proxy Live Feed</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider px-2 py-0.5 clay-badge"
                style={{ background: connected ? 'rgba(74, 222, 128, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: connected ? '#4ade80' : '#fca5a5' }}>
                {connected ? <><CheckCircle2 className="w-3 h-3"/> CONNECTED</> : 'DISCONNECTED'}
              </span>
              <span className="text-xs text-slate-500">Listening to Burp Suite</span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="flex gap-4">
          <div className="clay-inset px-4 py-2 flex flex-col items-center min-w-[90px]">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Total</span>
            <span className="text-lg font-bold text-slate-200 font-mono">{stats.total}</span>
          </div>
          <div className="clay-inset px-4 py-2 flex flex-col items-center min-w-[90px]" style={{ borderColor: 'rgba(255,102,51,0.2)' }}>
            <span className="text-[10px] text-[var(--color-primary-500)] uppercase tracking-widest font-semibold">Triage</span>
            <span className="text-lg font-bold text-[var(--color-primary-400)] font-mono">{stats.interesting}</span>
          </div>
          <div className="clay-inset px-4 py-2 flex flex-col items-center min-w-[90px]" style={{ borderColor: 'rgba(239,68,68,0.2)' }}>
            <span className="text-[10px] text-red-500 uppercase tracking-widest font-semibold">Findings</span>
            <span className="text-lg font-bold text-red-400 font-mono">{stats.findings}</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col clay-card overflow-hidden">
        
        {/* Toolbar */}
        <div className="p-3 border-b border-[var(--color-dark-700)] flex items-center justify-between bg-black/10">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400 ml-1" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">Filters:</span>
            {['all', 'new_interesting_request', 'ai_analyzing', 'new_finding'].map(f => {
              const cfg = TYPE_CONFIG[f] || { color: '#a9b7c6', label: 'All Events' };
              const isActive = filter === f;
              return (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${isActive ? 'clay-badge' : 'hover:bg-white/5'}`}
                  style={{
                    color: isActive ? '#fff' : cfg.color,
                    background: isActive ? cfg.color : 'transparent',
                    textShadow: isActive ? '0 1px 2px rgba(0,0,0,0.5)' : 'none'
                  }}>
                  {f === 'all' ? 'All Events' : cfg.label}
                </button>
              );
            })}
          </div>
          <button onClick={() => setEvents([])} className="clay-btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3">
            <Trash2 className="w-3.5 h-3.5" /> Clear
          </button>
        </div>

        {/* Event List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[var(--color-dark-950)]">
          {filtered.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
              <div className="relative">
                <div className="absolute inset-0 bg-[var(--color-primary-500)] blur-xl opacity-20 rounded-full"></div>
                <Activity className="w-16 h-16 opacity-50 relative z-10" />
              </div>
              <div className="text-center">
                <p className="text-lg font-medium text-slate-300 drop-shadow-md">Awaiting Target Traffic</p>
                <p className="text-sm mt-1">Configure your browser to use Burp Proxy.</p>
              </div>
            </div>
          )}

          {filtered.map(ev => {
            const cfg = TYPE_CONFIG[ev.type] || { color: '#a9b7c6', icon: '•', label: ev.type };
            const d = ev.data || {};
            const isClickable = ev.type === 'new_interesting_request' || ev.type === 'new_finding';
            const levelColor = LEVEL_COLOR[d.level] || '#5c5f61';

            return (
              <div key={ev.id}
                onClick={() => isClickable && d.id && navigate(`/request/${d.exchange_id || d.id}`)}
                className={`clay-inset p-3.5 flex items-start gap-4 transition-all border-l-4 ${isClickable ? 'cursor-pointer hover:brightness-110' : ''}`}
                style={{ borderLeftColor: cfg.color }}>
                
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 clay-badge"
                  style={{ background: 'var(--color-dark-900)' }}>
                  <span className="text-lg leading-none" style={{ textShadow: `0 0 8px ${cfg.color}80` }}>{cfg.icon}</span>
                </div>

                <div className="flex-1 min-w-0 flex flex-col justify-center">
                  <div className="flex items-center gap-3 mb-1.5">
                    <span className="font-bold text-sm" style={{ color: cfg.color, textShadow: `0 0 10px ${cfg.color}40` }}>{cfg.label}</span>
                    
                    {d.level && (
                      <span className="text-[10px] px-2 py-0.5 rounded uppercase font-bold tracking-wider clay-badge"
                        style={{ color: '#fff', background: levelColor }}>
                        {d.level}
                      </span>
                    )}
                    
                    {d.method && (
                      <span className="text-xs font-mono font-bold text-slate-300 px-1.5 py-0.5 rounded bg-white/5 border border-white/10">
                        {d.method}
                      </span>
                    )}
                    
                    {d.score > 0 && (
                      <span className="text-xs font-mono text-[var(--color-primary-400)]">{d.score} pts</span>
                    )}

                    <span className="ml-auto text-[10px] font-mono text-slate-500">
                      {ev.ts ? new Date(ev.ts).toISOString().split('T')[1].slice(0,-1) : ''}
                    </span>
                  </div>

                  <div className="text-sm font-mono text-slate-300 truncate opacity-90">
                    {d.msg || d.path || JSON.stringify(d).slice(0, 120)}
                  </div>

                  {d.summary && (
                    <div className="text-xs text-slate-400 mt-2 bg-black/20 p-2 rounded border border-white/5 line-clamp-2 leading-relaxed">
                      {d.summary}
                    </div>
                  )}
                </div>

                {isClickable && (
                  <div className="shrink-0 h-full flex flex-col justify-center pl-2">
                    <ChevronRight className="w-5 h-5 text-slate-500 opacity-50 transition-opacity group-hover:opacity-100" />
                  </div>
                )}
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}