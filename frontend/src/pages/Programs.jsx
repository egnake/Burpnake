import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Target, Plus, Trash2, CheckCircle, Globe, ChevronRight } from 'lucide-react';

const PLATFORM_LABELS = { hackerone: 'HackerOne', bugcrowd: 'Bugcrowd', yeswehack: 'YesWeHack', manual: 'Manuel' };
const PLATFORM_COLORS = { hackerone: '#f26722', bugcrowd: '#028900', yeswehack: '#1c2b4b', manual: '#6366f1' };

export default function Programs() {
  const [programs, setPrograms] = useState([]);
  const [handle, setHandle] = useState('');
  const [platform, setPlatform] = useState('hackerone');
  const [loading, setLoading] = useState(false);
  const [fetchedScope, setFetchedScope] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => { loadPrograms(); }, []);

  const loadPrograms = async () => {
    try {
      const res = await axios.get('/api/programs/');
      setPrograms(res.data.programs || []);
    } catch (e) { console.error(e); }
  };

  const fetchScope = async () => {
    if (!handle.trim()) return;
    setLoading(true); setError(''); setFetchedScope(null);
    try {
      const ep = platform === 'hackerone' ? 'fetch-hackerone' : 'fetch-bugcrowd';
      const res = await axios.post(`/api/programs/${ep}?handle=${handle.trim()}`);
      setFetchedScope(res.data);
      await loadPrograms();
    } catch (e) {
      setError(e.response?.data?.detail || 'Scope çekme başarısız. Program herkese açık olmayabilir.');
    } finally { setLoading(false); }
  };

  const createManual = async () => {
    setLoading(true);
    try {
      await axios.post('/api/programs/', { name: handle || 'Manuel Program', platform: 'manual', include_domains: [], exclude_domains: [] });
      await loadPrograms();
      setHandle('');
    } catch (e) { setError('Oluşturma başarısız.'); }
    finally { setLoading(false); }
  };

  const activate = async (pid) => {
    await axios.put(`/api/programs/${pid}/activate`);
    await loadPrograms();
  };

  const deleteProgram = async (pid) => {
    await axios.delete(`/api/programs/${pid}`);
    await loadPrograms();
  };

  const scopeData = fetchedScope?.scope || {};
  const includes = scopeData.include || [];
  const excludes = scopeData.exclude || [];

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Target className="w-8 h-8" style={{ color: 'var(--color-primary-500)' }} />
        <h1 className="text-3xl font-bold text-white">Program Yönetimi</h1>
      </div>

      {/* Scope Çekme */}
      <div className="rounded-xl border p-6 mb-8" style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }}>
        <h2 className="text-lg font-bold text-white mb-4">Otomatik Scope Çek</h2>
        <div className="flex gap-3 mb-4">
          <select value={platform} onChange={e => setPlatform(e.target.value)}
            className="rounded-lg px-3 py-2.5 text-white text-sm border"
            style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }}>
            <option value="hackerone">HackerOne</option>
            <option value="bugcrowd">Bugcrowd</option>
            <option value="manual">Manuel</option>
          </select>
          <input value={handle} onChange={e => setHandle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchScope()}
            placeholder={platform === 'manual' ? 'Program adı' : 'Program slug (örn: tesla)'}
            className="flex-1 rounded-lg px-4 py-2.5 text-white text-sm border focus:outline-none"
            style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }} />
          {platform === 'manual'
            ? <button onClick={createManual} disabled={loading}
                className="px-5 py-2.5 rounded-lg text-white text-sm font-medium flex items-center gap-2"
                style={{ background: 'var(--color-primary-600)' }}>
                <Plus className="w-4 h-4" /> Oluştur
              </button>
            : <button onClick={fetchScope} disabled={loading}
                className="px-5 py-2.5 rounded-lg text-white text-sm font-medium flex items-center gap-2"
                style={{ background: 'var(--color-primary-600)' }}>
                <Globe className="w-4 h-4" /> {loading ? 'Çekiliyor...' : 'Scope Çek'}
              </button>
          }
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {fetchedScope && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="rounded-lg p-4" style={{ background: 'var(--color-dark-900)' }}>
              <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-primary-400)' }}>
                ✅ In-Scope ({includes.length})
              </h3>
              <ul className="space-y-1 max-h-40 overflow-y-auto">
                {includes.map((d, i) => <li key={i} className="font-mono text-xs text-slate-300">{d}</li>)}
              </ul>
            </div>
            <div className="rounded-lg p-4" style={{ background: 'var(--color-dark-900)' }}>
              <h3 className="text-sm font-semibold text-red-400 mb-2">❌ Out-of-Scope ({excludes.length})</h3>
              <ul className="space-y-1 max-h-40 overflow-y-auto">
                {excludes.map((d, i) => <li key={i} className="font-mono text-xs text-slate-400">{d}</li>)}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Program Listesi */}
      <h2 className="text-lg font-bold text-white mb-4">Programlarım ({programs.length})</h2>
      <div className="space-y-3">
        {programs.length === 0 && (
          <div className="text-center py-12 text-slate-500">Henüz program yok. Yukarıdan ekle.</div>
        )}
        {programs.map(p => {
          const scope = (() => { try { return JSON.parse(p.scope_json || '{}'); } catch { return {}; } })();
          const color = PLATFORM_COLORS[p.platform] || '#6366f1';
          return (
            <div key={p.id} className="rounded-xl border p-4 flex items-center gap-4 transition-all"
              style={{ background: 'var(--color-dark-800)', borderColor: p.is_active ? 'var(--color-primary-500)' : 'var(--color-dark-700)' }}>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 text-white text-xs font-bold"
                style={{ background: color }}>
                {p.platform?.slice(0, 2).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white truncate">{p.name}</span>
                  {p.is_active === 1 && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                      style={{ background: 'var(--color-primary-500)', color: '#000' }}>AKTİF</span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {PLATFORM_LABELS[p.platform]} • {(scope.include || []).length} domain in-scope
                </p>
              </div>
              <div className="flex items-center gap-2">
                {p.is_active !== 1 && (
                  <button onClick={() => activate(p.id)}
                    className="text-xs px-3 py-1.5 rounded-lg border flex items-center gap-1 text-slate-300 hover:text-white transition-colors"
                    style={{ borderColor: 'var(--color-dark-600)' }}>
                    <CheckCircle className="w-3.5 h-3.5" /> Aktif Yap
                  </button>
                )}
                <button onClick={() => deleteProgram(p.id)}
                  className="text-slate-500 hover:text-red-400 transition-colors p-1.5">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
