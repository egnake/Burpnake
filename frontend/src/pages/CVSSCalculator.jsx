import React, { useState, useEffect } from 'react';
import { Shield, Copy, Check, Sparkles, BookOpen, Code2 } from 'lucide-react';
import axios from 'axios';

const METRICS_DEF = [
  {
    key: 'av',
    label: 'Attack Vector (AV)',
    options: [
      { val: 'N', name: 'Network', desc: 'Remotely exploitable across boundaries' },
      { val: 'A', name: 'Adjacent', desc: 'Requires same local network or subnet' },
      { val: 'L', name: 'Local', desc: 'Requires local access or shell' },
      { val: 'P', name: 'Physical', desc: 'Requires physical interaction with device' },
    ],
  },
  {
    key: 'ac',
    label: 'Attack Complexity (AC)',
    options: [
      { val: 'L', name: 'Low', desc: 'Repeatable without special conditions' },
      { val: 'H', name: 'High', desc: 'Depends on conditions outside attacker control' },
    ],
  },
  {
    key: 'pr',
    label: 'Privileges Required (PR)',
    options: [
      { val: 'N', name: 'None', desc: 'Unauthenticated attacker' },
      { val: 'L', name: 'Low', desc: 'Basic user privileges required' },
      { val: 'H', name: 'High', desc: 'Administrative privileges required' },
    ],
  },
  {
    key: 'ui',
    label: 'User Interaction (UI)',
    options: [
      { val: 'N', name: 'None', desc: 'Autonomous / No victim interaction needed' },
      { val: 'R', name: 'Required', desc: 'Victim must perform an action (e.g. click link)' },
    ],
  },
  {
    key: 's',
    label: 'Scope (S)',
    options: [
      { val: 'U', name: 'Unchanged', desc: 'Impact confined to vulnerable component' },
      { val: 'C', name: 'Changed', desc: 'Can impact other components or hosting environment' },
    ],
  },
  {
    key: 'c',
    label: 'Confidentiality Impact (C)',
    options: [
      { val: 'N', name: 'None', desc: 'No sensitive data exposed' },
      { val: 'L', name: 'Low', desc: 'Partial or non-sensitive data exposed' },
      { val: 'H', name: 'High', desc: 'Full compromise of confidential information' },
    ],
  },
  {
    key: 'i',
    label: 'Integrity Impact (I)',
    options: [
      { val: 'N', name: 'None', desc: 'Cannot modify data' },
      { val: 'L', name: 'Low', desc: 'Partial or minor modification of data' },
      { val: 'H', name: 'High', desc: 'Total compromise of system or data integrity' },
    ],
  },
  {
    key: 'a',
    label: 'Availability Impact (A)',
    options: [
      { val: 'N', name: 'None', desc: 'No impact on availability' },
      { val: 'L', name: 'Low', desc: 'Reduced performance or intermittent interruptions' },
      { val: 'H', name: 'High', desc: 'Total denial of service or resource shutdown' },
    ],
  },
];

const PRESETS = [
  { name: 'SQL Injection', vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H' },
  { name: 'SSRF (Cloud Metadata)', vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N' },
  { name: 'IDOR (Privilege Escalation)', vector: 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N' },
  { name: 'Stored XSS', vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N' },
  { name: 'CORS Misconfiguration', vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N' },
  { name: 'Open Redirect', vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N' },
];

export default function CVSSCalculator() {
  const [metrics, setMetrics] = useState({
    av: 'N', ac: 'L', pr: 'N', ui: 'N',
    s: 'U', c: 'H', i: 'H', a: 'N'
  });
  const [result, setResult] = useState({
    vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N',
    base_score: 9.1,
    severity: 'Critical',
    exploitability_score: 3.9,
    impact_score: 5.2,
  });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    calculateScore(metrics);
  }, [metrics]);

  const calculateScore = async (currentMetrics) => {
    try {
      const res = await axios.post('/api/cvss/calculate', currentMetrics);
      setResult(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleMetricChange = (key, val) => {
    setMetrics(prev => ({ ...prev, [key]: val }));
  };

  const applyPreset = (vectorStr) => {
    const parts = vectorStr.split('/');
    const nextMetrics = { ...metrics };
    parts.forEach(p => {
      const [k, v] = p.split(':');
      if (k && v && nextMetrics[k.toLowerCase()] !== undefined) {
        nextMetrics[k.toLowerCase()] = v;
      }
    });
    setMetrics(nextMetrics);
  };

  const copyVector = () => {
    navigator.clipboard.writeText(result.vector);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sevColor = {
    Critical: '#ef4444',
    High: '#f97316',
    Medium: '#eab308',
    Low: '#3b82f6',
    None: '#94a3b8',
  }[result.severity] || '#94a3b8';

  return (
    <div className="flex flex-col h-full p-6 gap-6 z-10 relative max-w-7xl mx-auto overflow-y-auto">
      {/* Header */}
      <div className="clay-card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-[var(--color-primary-500)]" />
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">CVSS v3.1 Calculator & Taxonomy</h1>
            <p className="text-xs text-slate-400 mt-0.5">Official FIRST Standard Vulnerability Scoring Engine</p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-slate-400 font-semibold uppercase">Presets:</span>
          {PRESETS.map(p => (
            <button
              key={p.name}
              onClick={() => applyPreset(p.vector)}
              className="px-2.5 py-1 rounded text-xs border border-[var(--color-dark-600)] text-slate-300 hover:text-white hover:border-[var(--color-primary-500)] transition-colors">
              {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Scoring Gauge Card */}
      <div className="clay-card p-6 flex flex-col lg:flex-row items-center justify-between gap-6 border-l-4"
        style={{ borderLeftColor: sevColor }}>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-center justify-center w-24 h-24 rounded-2xl border bg-black/20"
            style={{ borderColor: sevColor }}>
            <span className="text-3xl font-extrabold" style={{ color: sevColor }}>{result.base_score}</span>
            <span className="text-[10px] font-bold uppercase tracking-wider mt-1 text-slate-400">Score</span>
          </div>
          <div>
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold text-white uppercase tracking-tight">{result.severity}</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase"
                style={{ background: sevColor + '20', color: sevColor }}>
                CVSS v3.1
              </span>
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs font-mono text-slate-400">
              <span>Exploitability: <b className="text-slate-200">{result.exploitability_score}</b></span>
              <span>•</span>
              <span>Impact: <b className="text-slate-200">{result.impact_score}</b></span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full lg:w-auto">
          <div className="flex-1 lg:w-96 px-3 py-2 rounded-lg bg-black/40 border border-[var(--color-dark-700)] font-mono text-xs text-slate-300 truncate select-all">
            {result.vector}
          </div>
          <button onClick={copyVector} className="clay-btn-primary px-4 py-2 flex items-center gap-2 text-xs font-semibold shrink-0">
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy Vector'}
          </button>
        </div>
      </div>

      {/* Metrics Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {METRICS_DEF.map(metric => (
          <div key={metric.key} className="clay-card p-4 flex flex-col justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5 block">
              {metric.label}
            </span>
            <div className="grid grid-cols-2 gap-2">
              {metric.options.map(opt => {
                const isSelected = metrics[metric.key] === opt.val;
                return (
                  <button
                    key={opt.val}
                    onClick={() => handleMetricChange(metric.key, opt.val)}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'border-[var(--color-primary-500)] bg-[var(--color-primary-500)]/15 text-white'
                        : 'border-[var(--color-dark-700)] bg-black/10 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                    }`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold">{opt.name} ({opt.val})</span>
                      {isSelected && <span className="w-2 h-2 rounded-full bg-[var(--color-primary-500)]"></span>}
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 line-clamp-1">{opt.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
