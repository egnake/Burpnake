import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Search, Tag, ArrowRight, AlertTriangle } from 'lucide-react';

const RISKY_PARAMS = ['id','user_id','uid','admin','role','redirect','url','file','path','cmd','exec','system','token','key','secret','callback','next','return'];

function riskLevel(param) {
  const p = param.toLowerCase();
  if (['cmd','exec','system','file','path'].includes(p)) return 'critical';
  if (['id','user_id','uid','admin','role'].includes(p))  return 'high';
  if (['redirect','url','callback','next','return'].includes(p)) return 'medium';
  if (['token','key','secret'].includes(p)) return 'medium';
  return 'normal';
}

const RISK_COLORS = {
  critical: { bg: '#7f1d1d', text: '#fca5a5' },
  high:     { bg: '#7c2d12', text: '#fdba74' },
  medium:   { bg: '#713f12', text: '#fde047' },
  normal:   { bg: '#1e293b', text: '#94a3b8' },
};

export default function ParamDiscovery() {
  const [paramMap, setParamMap]   = useState({});  // param -> [{exchange_id, path, method}]
  const [selected, setSelected]   = useState(null);
  const [search, setSearch]       = useState('');
  const [loading, setLoading]     = useState(true);
  const navigate = useNavigate();

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/import/live-pull');
      const exchanges = res.data.exchanges || [];
      const map = {};
      for (const ex of exchanges) {
        let params = [];
        try { params = JSON.parse(ex.interesting_params || '[]'); } catch { params = []; }
        params = params.filter(p => !p.startsWith('TECH:'));
        for (const p of params) {
          if (!map[p]) map[p] = [];
          map[p].push({ exchange_id: ex.id, path: ex.path, method: ex.method, host: ex.host });
        }
      }
      setParamMap(map);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  // Parametre listesi: frekansa gore sirala
  const sorted = Object.entries(paramMap)
    .sort((a, b) => b[1].length - a[1].length)
    .filter(([p]) => p.toLowerCase().includes(search.toLowerCase()));

  const risky = sorted.filter(([p]) => riskLevel(p) !== 'normal');

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Search className="w-8 h-8" style={{ color: 'var(--color-primary-500)' }} />
        <h1 className="text-3xl font-bold text-white">Parameter Discovery</h1>
        <span className="ml-auto text-sm text-slate-400">{sorted.length} unique param</span>
        <button onClick={load} className="text-xs px-3 py-1.5 rounded-lg border text-slate-400"
          style={{ borderColor: 'var(--color-dark-700)' }}>Yenile</button>
      </div>

      {/* Riskli parametreler banner */}
      {risky.length > 0 && (
        <div className="rounded-xl border p-4 mb-6 flex items-start gap-3"
          style={{ background: '#7f1d1d30', borderColor: '#ef444460' }}>
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-300 mb-1">Riskli Parametreler Tespit Edildi</p>
            <div className="flex flex-wrap gap-2">
              {risky.map(([p]) => {
                const risk = riskLevel(p);
                const col = RISK_COLORS[risk];
                return (
                  <span key={p} onClick={() => setSelected(p)}
                    className="text-xs px-2 py-0.5 rounded cursor-pointer font-mono font-bold"
                    style={{ background: col.bg, color: col.text }}>
                    {p} ({paramMap[p]?.length})
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Parametre listesi */}
        <div>
          <div className="mb-3">
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Parametre ara..." className="w-full rounded-lg px-3 py-2 text-sm text-white border focus:outline-none"
              style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }} />
          </div>
          <div className="space-y-1.5 max-h-[60vh] overflow-y-auto">
            {loading && <p className="text-slate-500 text-sm text-center py-8">Yükleniyor...</p>}
            {!loading && sorted.length === 0 && (
              <p className="text-slate-500 text-sm text-center py-8">
                Henüz parametre yok. Burp trafiği izleniyor...
              </p>
            )}
            {sorted.map(([param, usages]) => {
              const risk = riskLevel(param);
              const col  = RISK_COLORS[risk];
              const maxFreq = sorted[0]?.[1].length || 1;
              const widthPct = Math.max(10, Math.round((usages.length / maxFreq) * 100));
              const isSelected = selected === param;
              return (
                <div key={param} onClick={() => setSelected(isSelected ? null : param)}
                  className="p-3 rounded-lg border cursor-pointer transition-all"
                  style={{
                    background: isSelected ? 'var(--color-dark-700)' : 'var(--color-dark-800)',
                    borderColor: isSelected ? 'var(--color-primary-500)' : 'var(--color-dark-700)',
                  }}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="font-mono text-sm text-white">{param}</span>
                    {risk !== 'normal' && (
                      <span className="text-xs px-1.5 py-0.5 rounded font-bold uppercase"
                        style={{ background: col.bg, color: col.text }}>{risk}</span>
                    )}
                    <span className="ml-auto text-xs text-slate-400">{usages.length}x</span>
                  </div>
                  <div className="h-1 rounded-full" style={{ background: 'var(--color-dark-600)' }}>
                    <div className="h-1 rounded-full transition-all"
                      style={{ width: `${widthPct}%`, background: col.text }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Secilen parametrenin kullanıldığı istekler */}
        <div>
          {selected ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Tag className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
                <h2 className="text-base font-bold text-white">
                  <span className="font-mono">{selected}</span> parametresi
                </h2>
                <span className="text-xs text-slate-400">({paramMap[selected]?.length} istek)</span>
              </div>
              <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                {(paramMap[selected] || []).map((u, i) => (
                  <div key={i} onClick={() => navigate(`/request/${u.exchange_id}`)}
                    className="p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-all hover:border-slate-500"
                    style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }}>
                    <span className="text-xs font-bold" style={{ color: 'var(--color-primary-400)' }}>{u.method}</span>
                    <span className="font-mono text-xs text-slate-300 truncate flex-1">{u.path}</span>
                    <span className="text-xs text-slate-500 truncate max-w-[100px]">{u.host}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-600 text-sm text-center rounded-xl border"
              style={{ borderColor: 'var(--color-dark-700)', minHeight: '200px' }}>
              <div>
                <Tag className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p>Soldan bir parametreye tıkla</p>
                <p className="text-xs mt-1 text-slate-700">Hangi isteklerde kullanıldığını görmek için</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
