import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ShieldAlert, Zap, Globe, Target, TerminalSquare, AlertTriangle } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({ total_exchanges: 0, total_findings: 0, pending_critical: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/agent/status')
      .then(r => r.json())
      .then(d => {
        if (d.stats) setStats(d.stats);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col h-full p-6 gap-6 z-10 relative overflow-y-auto">
      
      {/* Welcome Banner */}
      <div className="clay-card p-8 flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--color-primary-500)] opacity-10 blur-[80px] rounded-full pointer-events-none"></div>
        <div className="relative z-10">
          <h1 className="text-3xl font-bold text-white tracking-tight drop-shadow-md mb-2">
            Welcome to BurpNake <span className="text-[var(--color-primary-500)]">Pro</span>
          </h1>
          <p className="text-sm text-slate-400 max-w-xl leading-relaxed">
            Autonomous AI Bug Bounty Hunting Platform. Traffic flows from your Burp Suite proxy into our Passive Analyzer, and critical findings trigger the Autonomous Agent loop for zero-hallucination verification.
          </p>
        </div>
        <div className="flex gap-3 relative z-10">
          <Link to="/live" className="clay-btn-primary flex items-center gap-2">
            <Activity className="w-4 h-4" /> Live Feed
          </Link>
          <Link to="/hunt" className="clay-btn-secondary flex items-center gap-2">
            <TerminalSquare className="w-4 h-4" /> AI Hunter
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="clay-card p-6 flex items-center gap-5">
          <div className="w-14 h-14 rounded-full flex items-center justify-center clay-badge" style={{ background: 'var(--color-dark-900)' }}>
            <Globe className="w-6 h-6 text-slate-400" />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-widest font-bold text-slate-500">Captured Traffic</p>
            <h2 className="text-3xl font-bold font-mono text-white drop-shadow-sm mt-1">{loading ? '...' : stats.total_exchanges}</h2>
          </div>
        </div>
        
        <div className="clay-card p-6 flex items-center gap-5 border-t-2 border-[var(--color-primary-500)]">
          <div className="w-14 h-14 rounded-full flex items-center justify-center clay-badge" style={{ background: 'var(--color-dark-900)' }}>
            <Zap className="w-6 h-6 text-[var(--color-primary-500)]" style={{ filter: 'drop-shadow(0 0 6px rgba(255,102,51,0.5))' }} />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-widest font-bold text-[var(--color-primary-400)]">Pending Triage</p>
            <h2 className="text-3xl font-bold font-mono text-white drop-shadow-sm mt-1">{loading ? '...' : stats.pending_critical}</h2>
          </div>
        </div>

        <div className="clay-card p-6 flex items-center gap-5 border-t-2 border-red-500">
          <div className="w-14 h-14 rounded-full flex items-center justify-center clay-badge" style={{ background: 'var(--color-dark-900)' }}>
            <ShieldAlert className="w-6 h-6 text-red-500" style={{ filter: 'drop-shadow(0 0 6px rgba(239,68,68,0.5))' }} />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-widest font-bold text-red-400">Confirmed Findings</p>
            <h2 className="text-3xl font-bold font-mono text-white drop-shadow-sm mt-1">{loading ? '...' : stats.total_findings}</h2>
          </div>
        </div>
      </div>

      {/* Quick Info & Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
        
        <div className="clay-card flex flex-col">
          <div className="p-4 border-b border-[var(--color-dark-700)] bg-black/10">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Target className="w-4 h-4 text-[var(--color-primary-500)]" /> System Status
            </h3>
          </div>
          <div className="p-5 flex-1 flex flex-col gap-4">
            <div className="clay-inset p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-300">FastAPI Backend</p>
                <p className="text-[10px] text-slate-500 mt-1">Port 8899 — SQLite Database</p>
              </div>
              <span className="text-xs font-bold text-green-400 px-2 py-1 rounded bg-green-400/10 border border-green-400/20">ONLINE</span>
            </div>
            <div className="clay-inset p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-300">LLM Engine</p>
                <p className="text-[10px] text-slate-500 mt-1">Anti-Hallucination Protocol Active</p>
              </div>
              <span className="text-xs font-bold text-green-400 px-2 py-1 rounded bg-green-400/10 border border-green-400/20">READY</span>
            </div>
            <div className="clay-inset p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-300">Burp Connector</p>
                <p className="text-[10px] text-slate-500 mt-1">Awaiting HTTP/S Traffic via JAR</p>
              </div>
              <span className="text-xs font-bold text-[var(--color-primary-400)] px-2 py-1 rounded bg-[var(--color-primary-500)]/10 border border-[var(--color-primary-500)]/20">LISTENING</span>
            </div>
          </div>
        </div>

        <div className="clay-card flex flex-col">
          <div className="p-4 border-b border-[var(--color-dark-700)] bg-black/10">
            <h3 className="font-semibold text-sm flex items-center gap-2 text-slate-300">
              <AlertTriangle className="w-4 h-4 text-yellow-500" /> Active Rulesets
            </h3>
          </div>
          <div className="p-5 flex-1 clay-inset m-4 overflow-y-auto">
            <ul className="text-xs font-mono text-slate-400 space-y-2">
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> SQLi (Error/Blind/Time)</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> XSS (Reflected/Stored/DOM)</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> SSRF (Cloud Metadata/WebRTC)</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> Prototype Pollution & AST</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> HTTP Request Smuggling</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> RCE & Command Injection</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> Deserialization (Java/PHP/Python)</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> LLM Prompt Injection</li>
              <li className="text-slate-500 italic mt-4 pl-4">...and 80 more vulnerability patterns.</li>
            </ul>
          </div>
        </div>

      </div>

    </div>
  );
}