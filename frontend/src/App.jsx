import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  Activity, Target, FileJson, MessageSquare,
  FileText, ShieldAlert, Layers, Radio, Search, Download, Send, Shield
} from 'lucide-react';

import Dashboard      from './pages/Dashboard';
import ScopeManager   from './pages/ScopeManager';
import DataImport     from './pages/DataImport';
import AIHunter       from './pages/AIHunter';
import Reports        from './pages/Reports';
import Programs       from './pages/Programs';
import Findings       from './pages/Findings';
import RequestDetail  from './pages/RequestDetail';
import LiveFeed       from './pages/LiveFeed';
import ParamDiscovery from './pages/ParamDiscovery';
import AgentLive      from './pages/AgentLive';
import Repeater       from './pages/Repeater';
import CVSSCalculator from './pages/CVSSCalculator';

const NAV = [
  { name: 'Dashboard',      path: '/',        icon: Activity },
  { name: 'Live Feed',      path: '/live',    icon: Radio },
  { name: 'Programs',       path: '/programs',icon: Layers },
  { name: 'AI Hunter',      path: '/hunt',    icon: MessageSquare },
  { name: 'Agent Live',     path: '/agent',   icon: Activity },
  { name: 'Findings',       path: '/findings',icon: ShieldAlert },
  { name: 'Param Discovery',path: '/params',  icon: Search },
  { name: 'Repeater',       path: '/repeater', icon: Send },
  { name: 'Scope Manager',  path: '/scope',   icon: Target },
  { name: 'Data Import',    path: '/import',  icon: FileJson },
  { name: 'Reports',        path: '/reports', icon: FileText },
  { name: 'CVSS 3.1 & CWE', path: '/cvss',    icon: Shield },
];

function Sidebar() {
  const { pathname } = useLocation();
  return (
    <div className="w-64 h-screen flex flex-col shrink-0 clay-sidebar relative z-10">
      
      <div className="p-5 border-b border-[var(--color-dark-700)] flex items-center gap-3">
        <img src="/logo.jpg" alt="BurpNake Logo" className="w-8 h-8 rounded-md shadow-[0_0_8px_rgba(255,102,51,0.4)]" />
        <div>
          <span className="text-lg font-bold text-white tracking-tight drop-shadow-md">BurpNake</span>
          
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-2 overflow-y-auto">
        <p className="text-[11px] font-semibold text-slate-500 mb-3 px-3 uppercase tracking-wider drop-shadow-sm">Modules</p>
        {NAV.map(({ name, path, icon: Icon }) => {
          const active = pathname === path || (path !== '/' && pathname.startsWith(path));
          return (
            <Link key={path} to={path}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm font-medium clay-nav-item ${active ? 'active' : ''}`}>
              <Icon className="w-4 h-4 shrink-0" />
              {name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--color-dark-700)] bg-black/10">
        <div className="space-y-2">
          <a href="/api/export/findings/json" target="_blank" rel="noreferrer"
            className="flex items-center justify-center gap-2 w-full clay-btn-secondary text-xs">
            <Download className="w-3.5 h-3.5" /> Export Data
          </a>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <div className="flex h-screen w-screen overflow-hidden bg-[var(--color-dark-950)] text-slate-200 selection:bg-[var(--color-primary-500)] selection:text-white">
        <Sidebar />
        <main className="flex-1 overflow-auto relative">
          {/* Subtle background glow effect for Burp feel */}
          <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[var(--color-primary-500)] opacity-5 blur-[120px] pointer-events-none"></div>
          <Routes>
            <Route path="/"              element={<Dashboard />} />
            <Route path="/live"          element={<LiveFeed />} />
            <Route path="/programs"      element={<Programs />} />
            <Route path="/scope"         element={<ScopeManager />} />
            <Route path="/import"        element={<DataImport />} />
            <Route path="/hunt"          element={<AIHunter />} />
            <Route path="/findings"      element={<Findings />} />
            <Route path="/params"        element={<ParamDiscovery />} />
            <Route path="/reports"       element={<Reports />} />
            <Route path="/request/:id"   element={<RequestDetail />} />
            <Route path="/agent"         element={<AgentLive />} />
            <Route path="/repeater"      element={<Repeater />} />
            <Route path="/cvss"          element={<CVSSCalculator />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}