import React, { useState, useEffect, useRef } from 'react';
import { Cpu, Zap, CheckCircle2, XCircle, Clock, ChevronRight, Play } from 'lucide-react';

const DECISION_ICONS = {
  try_payload: { icon: '🔄', color: '#60a5fa', label: 'Testing' },
  confirmed: { icon: '🎯', color: '#22c55e', label: 'CONFIRMED!' },
  give_up: { icon: '🔍', color: '#94a3b8', label: 'Gave Up' },
};

export default function AgentLive() {
  const [sessions, setSessions] = useState([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef(null);
  const esRef = useRef(null);

  useEffect(() => {
    const es = new EventSource('/api/stream/stream');
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => { setConnected(false); setTimeout(() => {
      es.close();
      const newEs = new EventSource('/api/stream/stream');
      esRef.current = newEs;
    }, 3000); };
    
    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        const d = event.data || {};
        if (!event.type?.startsWith('agent_') && event.type !== 'oob_callback_received') return;
        
        setSessions(prev => {
          const eid = d.exchange_id || 'unknown';
          const existing = prev.find(s => s.eid === eid);
          const entry = { type: event.type, data: d, ts: event.ts, _id: Date.now() + Math.random() };
          
          if (existing) {
            return prev.map(s => s.eid === eid ? {
              ...s,
              events: [...s.events, entry],
              status: event.type === 'agent_confirmed_finding' ? 'confirmed' :
                      event.type === 'agent_gave_up' ? 'gave_up' :
                      event.type === 'agent_complete' ? (d.success ? 'confirmed' : 'done') : 'hunting',
            } : s);
          } else {
            return [{
              eid,
              host: d.host || '',
              path: d.path || '',
              vulns: d.vulns || [],
              status: 'hunting',
              events: [entry],
            }, ...prev];
          }
        });
      } catch {}
    };
    
    return () => es.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sessions]);

  const startAutoHunt = () => {
    fetch('/api/agent/auto-hunt-all', { method: 'POST' });
  };

  const statusColors = {
    hunting: '#60a5fa',
    confirmed: '#22c55e',
    gave_up: '#94a3b8',
    done: '#94a3b8',
  };

  return (
    <div className="flex flex-col h-full p-6 gap-6 z-10 relative">
      {/* Header */}
      <div className="clay-card p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Cpu className="w-7 h-7 text-[var(--color-primary-500)]" />
            {connected && <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-400 rounded-full animate-ping"></span>}
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight drop-shadow-sm">Agent Live Monitor</h1>
            <p className="text-xs text-slate-400 mt-0.5">Real-time autonomous hunting visualization</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold px-2 py-1 rounded ${connected ? 'bg-green-400/10 text-green-400' : 'bg-red-400/10 text-red-400'}`}>
            {connected ? '● LIVE' : '○ OFFLINE'}
          </span>
          <button onClick={startAutoHunt} className="clay-btn-primary px-4 py-2 flex items-center gap-2 text-sm">
            <Play className="w-4 h-4" /> Auto-Hunt All
          </button>
        </div>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {sessions.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-3">
            <Cpu className="w-16 h-16 opacity-20" />
            <p className="text-lg font-medium text-slate-400">Waiting for Agent Activity</p>
            <p className="text-sm">Start a hunt from AI Hunter or click Auto-Hunt All above.</p>
          </div>
        )}
        
        {sessions.map(session => (
          <div key={session.eid} className="clay-card overflow-hidden"
            style={{ borderLeft: `3px solid ${statusColors[session.status] || '#94a3b8'}` }}>
            {/* Session header */}
            <div className="p-4 border-b border-[var(--color-dark-700)] bg-black/10 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold" style={{ color: statusColors[session.status] }}>
                  {session.status === 'confirmed' ? '🎯 CONFIRMED' :
                   session.status === 'hunting' ? '🤖 HUNTING...' :
                   session.status === 'gave_up' ? '🔍 Done' : '✅ Complete'}
                </span>
                <span className="text-xs font-mono text-slate-300">{session.path}</span>
                <span className="text-xs text-slate-500">{session.host}</span>
              </div>
              <span className="text-xs font-mono text-slate-500">{session.events.length} events</span>
            </div>
            
            {/* Event timeline */}
            <div className="p-4 space-y-2 max-h-64 overflow-y-auto bg-[var(--color-dark-950)]">
              {session.events.map(ev => {
                const d = ev.data;
                const cfg = DECISION_ICONS[d.decision] || { icon: '•', color: '#94a3b8', label: ev.type };
                return (
                  <div key={ev._id} className="clay-inset p-3 flex items-start gap-3 border-l-2"
                    style={{ borderLeftColor: cfg.color }}>
                    <span className="text-lg leading-none mt-0.5">{cfg.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold" style={{ color: cfg.color }}>
                          {d.iteration ? `Iter ${d.iteration}` : cfg.label}
                        </span>
                        {d.payload_description && (
                          <span className="text-xs text-slate-400 truncate">{d.payload_description}</span>
                        )}
                        <span className="ml-auto text-[10px] font-mono text-slate-600">
                          {ev.ts ? new Date(ev.ts).toISOString().split('T')[1]?.slice(0, 8) : ''}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {d.msg || d.reasoning?.slice(0, 200) || JSON.stringify(d).slice(0, 150)}
                      </p>
                      {d.response_preview && (
                        <pre className="text-[10px] text-slate-500 mt-1.5 bg-black/30 p-2 rounded max-h-20 overflow-hidden">
                          {d.response_preview}
                        </pre>
                      )}
                      {d.poc_curl && (
                        <pre className="text-[10px] text-green-400 mt-1.5 bg-green-900/20 p-2 rounded">
                          {d.poc_curl}
                        </pre>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
