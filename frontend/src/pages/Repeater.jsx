import React, { useState } from 'react';
import { Send, Clock, Hash, ArrowRight, Copy, RotateCcw } from 'lucide-react';

export default function Repeater() {
  const [url, setUrl] = useState('https://');
  const [method, setMethod] = useState('GET');
  const [headers, setHeaders] = useState('Content-Type: application/json\nAccept: */*');
  const [body, setBody] = useState('');
  const [followRedirects, setFollowRedirects] = useState(false);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const sendRequest = async () => {
    setLoading(true);
    setError('');
    setResponse(null);
    
    const headerObj = {};
    headers.split('\n').forEach(line => {
      const idx = line.indexOf(':');
      if (idx > 0) {
        headerObj[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
    });

    try {
      const res = await fetch('/api/replay/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url, method, headers: headerObj, body,
          follow_redirects: followRedirects,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResponse(data);
      } else {
        setError(data.detail || 'Request failed');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const copyResponse = () => {
    if (response) {
      const text = `HTTP/${response.http_version} ${response.status_code} ${response.reason}\n` +
        Object.entries(response.headers || {}).map(([k, v]) => `${k}: ${v}`).join('\n') +
        '\n\n' + (response.body || '');
      navigator.clipboard.writeText(text);
    }
  };

  const statusColor = (code) => {
    if (code >= 500) return '#ef4444';
    if (code >= 400) return '#f97316';
    if (code >= 300) return '#eab308';
    if (code >= 200) return '#22c55e';
    return '#94a3b8';
  };

  return (
    <div className="flex flex-col h-full p-6 gap-4 z-10 relative">
      {/* Header */}
      <div className="clay-card p-4 flex items-center gap-3">
        <Send className="w-6 h-6 text-[var(--color-primary-500)]" />
        <h1 className="text-xl font-bold text-white">Request Repeater</h1>
        <p className="text-xs text-slate-400 ml-2">Burp Repeater alternative — modify and resend requests</p>
      </div>

      {/* Request Builder */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Left: Request */}
        <div className="flex-1 clay-card flex flex-col overflow-hidden">
          <div className="p-3 border-b border-[var(--color-dark-700)] bg-black/10 flex items-center gap-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Request</span>
          </div>
          <div className="p-4 space-y-3 flex-1 overflow-y-auto">
            {/* URL + Method */}
            <div className="flex gap-2">
              <select value={method} onChange={e => setMethod(e.target.value)}
                className="px-3 py-2 rounded-lg text-sm font-bold text-white border"
                style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)', minWidth: '100px' }}>
                {['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'].map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <input value={url} onChange={e => setUrl(e.target.value)}
                placeholder="https://target.com/api/endpoint"
                className="flex-1 px-3 py-2 rounded-lg text-sm text-white border font-mono"
                style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }} />
            </div>
            
            {/* Headers */}
            <div>
              <label className="text-xs text-slate-400 font-semibold block mb-1">Headers</label>
              <textarea value={headers} onChange={e => setHeaders(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 border font-mono resize-y"
                style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }} />
            </div>
            
            {/* Body */}
            <div>
              <label className="text-xs text-slate-400 font-semibold block mb-1">Body</label>
              <textarea value={body} onChange={e => setBody(e.target.value)}
                rows={6}
                placeholder='{"username": "test", "password": "test"}'
                className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 border font-mono resize-y"
                style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }} />
            </div>

            {/* Options */}
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                <input type="checkbox" checked={followRedirects} onChange={e => setFollowRedirects(e.target.checked)} />
                Follow Redirects
              </label>
            </div>
          </div>
          
          <div className="p-3 border-t border-[var(--color-dark-700)] bg-black/10">
            <button onClick={sendRequest} disabled={loading || !url}
              className="clay-btn-primary w-full py-2.5 flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50">
              {loading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {loading ? 'Sending...' : 'Send Request'}
            </button>
          </div>
        </div>

        {/* Right: Response */}
        <div className="flex-1 clay-card flex flex-col overflow-hidden">
          <div className="p-3 border-b border-[var(--color-dark-700)] bg-black/10 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Response</span>
            {response && (
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold font-mono px-2 py-0.5 rounded"
                  style={{ color: statusColor(response.status_code), background: statusColor(response.status_code) + '20' }}>
                  {response.status_code} {response.reason}
                </span>
                <span className="text-xs font-mono text-slate-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {response.elapsed_ms}ms
                </span>
                <span className="text-xs font-mono text-slate-500 flex items-center gap-1">
                  <Hash className="w-3 h-3" /> {response.content_length}B
                </span>
                <button onClick={copyResponse} className="text-slate-400 hover:text-white">
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
          
          <div className="flex-1 overflow-auto p-4 bg-[var(--color-dark-950)]">
            {error && (
              <div className="text-sm text-red-400 p-3 rounded bg-red-400/10 border border-red-400/20">
                {error}
              </div>
            )}
            {!response && !error && (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                <ArrowRight className="w-5 h-5 mr-2 opacity-30" />
                Send a request to see the response
              </div>
            )}
            {response && (
              <div className="space-y-3">
                {/* Response Headers */}
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-semibold">Headers</p>
                  <pre className="text-xs font-mono text-slate-400 bg-black/30 p-3 rounded overflow-x-auto">
                    {Object.entries(response.headers || {}).map(([k, v]) => `${k}: ${v}`).join('\n')}
                  </pre>
                </div>
                {/* Response Body */}
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-semibold">Body</p>
                  <pre className="text-xs font-mono text-slate-300 bg-black/30 p-3 rounded overflow-x-auto whitespace-pre-wrap max-h-[50vh]">
                    {response.body}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
