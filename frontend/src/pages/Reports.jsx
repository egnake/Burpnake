import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, X } from 'lucide-react';

function ReportModal({ report, platform, onClose }) {
  const isSarif = platform === 'sarif';
  const copy = () => navigator.clipboard.writeText(report);
  const download = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([report], { type: isSarif ? 'application/json' : 'text/markdown' }));
    a.download = isSarif ? 'burpnake_finding.sarif' : 'burpnake_report.md';
    a.click();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6" style={{ background: 'rgba(0,0,0,0.85)' }}>
      <div className="rounded-xl border w-full max-w-3xl max-h-[85vh] flex flex-col"
        style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }}>
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--color-dark-700)' }}>
          <h3 className="font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5" style={{ color: 'var(--color-primary-500)' }} />
            Oluşturulan Rapor
          </h3>
          <div className="flex items-center gap-2">
            <button onClick={copy}
              className="text-xs px-3 py-1.5 rounded-lg border text-slate-300 hover:text-white"
              style={{ borderColor: 'var(--color-dark-600)' }}>Kopyala</button>
            <button onClick={download}
              className="text-xs px-3 py-1.5 rounded-lg text-white"
              style={{ background: 'var(--color-primary-600)' }}>{isSarif ? 'İndir (.sarif)' : 'İndir (.md)'}</button>
            <button onClick={onClose} className="text-slate-400 hover:text-white ml-1">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <pre className="flex-1 overflow-auto p-5 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
          {report}
        </pre>
      </div>
    </div>
  );
}

const SEV_COLORS = {
  critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#3b82f6', info: '#475569'
};

export default function Reports() {
  const [findings, setFindings] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [platform, setPlatform] = useState('hackerone');
  const [genLoading, setGenLoading] = useState('');

  useEffect(() => { loadFindings(); }, []);

  const loadFindings = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/findings/');
      setFindings(res.data.findings || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const generateReport = async (fid) => {
    setGenLoading(fid);
    try {
      const res = await axios.get(`/api/findings/${fid}/report?platform=${platform}`);
      setReport(res.data.report);
    } catch (e) { alert('Rapor oluşturulamadı: ' + (e.response?.data?.detail || e.message)); }
    finally { setGenLoading(''); }
  };

  const confirmed = findings.filter(f => f.confirmed === 1);
  const unconfirmed = findings.filter(f => f.confirmed !== 1);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {report && <ReportModal report={report} platform={platform} onClose={() => setReport(null)} />}

      <div className="flex items-center gap-3 mb-6">
        <FileText className="w-8 h-8" style={{ color: 'var(--color-primary-500)' }} />
        <h1 className="text-3xl font-bold text-white">Raporlar</h1>
        <div className="ml-auto flex items-center gap-2">
          <label className="text-sm text-slate-400">Platform:</label>
          <select value={platform} onChange={e => setPlatform(e.target.value)}
            className="text-sm rounded-lg px-3 py-1.5 text-white border"
            style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }}>
            <option value="hackerone">HackerOne</option>
            <option value="bugcrowd">Bugcrowd</option>
            <option value="yeswehack">YesWeHack</option>
            <option value="intigriti">Intigriti</option>
            <option value="sarif">SARIF 2.1.0 (JSON)</option>
          </select>
        </div>
      </div>

      {/* Onaylanmış Bulgular */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
          Onaylanmış Bulgular ({confirmed.length})
        </h2>
        {confirmed.length === 0 ? (
          <div className="rounded-xl border p-6 text-center text-slate-500 text-sm"
            style={{ borderColor: 'var(--color-dark-700)' }}>
            Henüz onaylanmış bulgu yok. Findings sayfasından bulguları onayla.
          </div>
        ) : (
          <div className="space-y-3">
            {confirmed.map(f => {
              const col = SEV_COLORS[f.severity] || '#475569';
              return (
                <div key={f.id} className="rounded-xl border p-4 flex items-center gap-4"
                  style={{ background: 'var(--color-dark-800)', borderColor: col + '50',
                    borderLeftWidth: '4px', borderLeftColor: col }}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold uppercase px-2 py-0.5 rounded"
                        style={{ background: col + '20', color: col }}>{f.severity}</span>
                      <span className="text-sm font-semibold text-white truncate">{f.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 truncate">{f.description?.slice(0, 120)}</p>
                  </div>
                  <button onClick={() => generateReport(f.id)} disabled={genLoading === f.id}
                    className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 shrink-0 transition-colors"
                    style={{ background: 'var(--color-primary-600)', color: 'white' }}>
                    <FileText className="w-4 h-4" />
                    {genLoading === f.id ? 'Oluşturuluyor...' : 'Rapor Oluştur'}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Onaylanmamış (Bekleyen) */}
      {unconfirmed.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block"></span>
            Bekleyen Bulgular ({unconfirmed.length})
          </h2>
          <div className="space-y-2">
            {unconfirmed.map(f => {
              const col = SEV_COLORS[f.severity] || '#475569';
              return (
                <div key={f.id} className="rounded-xl border p-3 flex items-center gap-3 opacity-60"
                  style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }}>
                  <span className="text-xs font-bold uppercase px-1.5 py-0.5 rounded"
                    style={{ background: col + '20', color: col }}>{f.severity?.slice(0,3)}</span>
                  <span className="text-xs text-slate-300 truncate flex-1">{f.title}</span>
                  <span className="text-xs text-slate-500">Findings'den onayla →</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
