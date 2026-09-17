import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, CheckCircle, X, FileText, ChevronDown } from 'lucide-react';

const SEV_COLORS = {
  critical: { bg: '#7f1d1d', text: '#fca5a5', border: '#ef4444' },
  high:     { bg: '#7c2d12', text: '#fdba74', border: '#f97316' },
  medium:   { bg: '#713f12', text: '#fde047', border: '#eab308' },
  low:      { bg: '#1e3a5f', text: '#93c5fd', border: '#3b82f6' },
  info:     { bg: '#1e293b', text: '#94a3b8', border: '#475569' },
};

function ReportModal({ report, onClose }) {
  const copy = () => navigator.clipboard.writeText(report);
  const download = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([report], { type: 'text/markdown' }));
    a.download = 'burpnake_report.md';
    a.click();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.8)' }}>
      <div className="rounded-xl border w-full max-w-3xl max-h-[80vh] flex flex-col"
        style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }}>
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--color-dark-700)' }}>
          <h3 className="font-bold text-white">Oluşturulan Rapor</h3>
          <div className="flex gap-2">
            <button onClick={copy} className="text-xs px-3 py-1.5 rounded-lg text-slate-300 border hover:text-white"
              style={{ borderColor: 'var(--color-dark-600)' }}>Kopyala</button>
            <button onClick={download} className="text-xs px-3 py-1.5 rounded-lg text-white"
              style={{ background: 'var(--color-primary-600)' }}>İndir (.md)</button>
            <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
          </div>
        </div>
        <pre className="flex-1 overflow-auto p-4 text-xs text-slate-300 font-mono whitespace-pre-wrap">{report}</pre>
      </div>
    </div>
  );
}

export default function Findings() {
  const [findings, setFindings] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState('');

  useEffect(() => { loadFindings(); }, [filter]);

  const loadFindings = async () => {
    setLoading(true);
    try {
      const params = filter !== 'all' ? { severity: filter } : {};
      const res = await axios.get('/api/findings/', { params });
      setFindings(res.data.findings || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const confirm = async (id) => {
    await axios.put(`/api/findings/${id}/confirm`);
    await loadFindings();
  };

  const dismiss = async (id) => {
    await axios.put(`/api/findings/${id}/dismiss`);
    await loadFindings();
  };

  const generateReport = async (id) => {
    setReportLoading(id);
    try {
      const res = await axios.get(`/api/findings/${id}/report?platform=hackerone`);
      setReport(res.data.report);
    } catch (e) { alert('Rapor oluşturulamadı.'); }
    finally { setReportLoading(''); }
  };

  const FILTERS = ['all', 'critical', 'high', 'medium', 'low', 'info'];

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {report && <ReportModal report={report} onClose={() => setReport(null)} />}

      <div className="flex items-center gap-3 mb-6">
        <ShieldAlert className="w-8 h-8" style={{ color: 'var(--color-primary-500)' }} />
        <h1 className="text-3xl font-bold text-white">Bulgular</h1>
        <span className="ml-auto text-sm text-slate-400">{findings.length} bulgu</span>
      </div>

      {/* Filtreler */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {FILTERS.map(f => {
          const col = SEV_COLORS[f] || SEV_COLORS.info;
          const isActive = filter === f;
          return (
            <button key={f} onClick={() => setFilter(f)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all capitalize"
              style={{
                background: isActive ? col.border : 'transparent',
                color: isActive ? '#fff' : col.text,
                borderColor: isActive ? col.border : col.border + '60',
              }}>
              {f === 'all' ? 'Tümü' : f.toUpperCase()}
            </button>
          );
        })}
      </div>

      {loading && <div className="text-center py-12 text-slate-400">Yükleniyor...</div>}

      <div className="space-y-3">
        {!loading && findings.length === 0 && (
          <div className="text-center py-16 text-slate-500">
            <ShieldAlert className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>Henüz bulgu yok. Burp trafiği izlenirken bulgular buraya gelecek.</p>
          </div>
        )}
        {findings.map(f => {
          const sev = (f.severity || 'info').toLowerCase();
          const col = SEV_COLORS[sev] || SEV_COLORS.info;
          return (
            <div key={f.id} className="rounded-xl border p-4 transition-all"
              style={{ background: 'var(--color-dark-800)', borderColor: col.border + '60',
                borderLeftWidth: '4px', borderLeftColor: col.border }}>
              <div className="flex items-start gap-3">
                <span className="text-xs font-bold px-2 py-1 rounded mt-0.5 shrink-0 uppercase"
                  style={{ background: col.bg, color: col.text }}>{sev}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-white truncate">{f.title}</p>
                  <p className="text-sm text-slate-400 mt-1 line-clamp-2">{f.description?.slice(0, 200)}</p>
                  {f.confirmed === 1 && (
                    <span className="text-xs mt-1 inline-block px-2 py-0.5 rounded"
                      style={{ background: 'var(--color-primary-500)', color: '#000' }}>✓ Onaylandı</span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => generateReport(f.id)} disabled={reportLoading === f.id}
                    className="text-xs px-3 py-1.5 rounded-lg border flex items-center gap-1 text-slate-300 hover:text-white transition-colors"
                    style={{ borderColor: 'var(--color-dark-600)' }}>
                    <FileText className="w-3.5 h-3.5" />
                    {reportLoading === f.id ? '...' : 'Rapor'}
                  </button>
                  {f.confirmed !== 1 && (
                    <button onClick={() => confirm(f.id)}
                      className="text-xs px-3 py-1.5 rounded-lg border flex items-center gap-1 transition-colors"
                      style={{ borderColor: 'var(--color-primary-500)', color: 'var(--color-primary-400)' }}>
                      <CheckCircle className="w-3.5 h-3.5" /> Onayla
                    </button>
                  )}
                  <button onClick={() => dismiss(f.id)} className="text-slate-500 hover:text-red-400 transition-colors p-1.5">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
