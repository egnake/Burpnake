import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Send, Bot, User, Tag } from 'lucide-react';

const TEMPLATES = [
  'IDOR var mı? Farklı user ID\'leri dene ve yanıtları karşılaştır.',
  'SQL injection açığı var mı? Parametreleri test et.',
  'Auth bypass mümkün mü? Token olmadan veya farklı role ile dene.',
  'Tüm parametreleri listele ve her biri için test öner.',
  'Business logic açığı var mı? Mantıksal akışı analiz et.',
  'XSS mümkün mü? Input alanlarını test et.',
  'Bu endpoint\'e benzer admin endpoint bul.',
];

function RawView({ b64, label }) {
  const text = React.useMemo(() => {
    try { return atob(b64 || ''); } catch { return b64 || ''; }
  }, [b64]);
  return (
    <div className="flex-1 flex flex-col min-h-0 rounded-xl border overflow-hidden"
      style={{ borderColor: 'var(--color-dark-700)' }}>
      <div className="px-4 py-2 text-xs font-semibold text-slate-400 border-b"
        style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }}>
        {label}
      </div>
      <pre className="flex-1 overflow-auto p-4 text-xs text-slate-300 font-mono whitespace-pre-wrap"
        style={{ background: 'var(--color-dark-800)' }}>{text || '(boş)'}</pre>
    </div>
  );
}

export default function RequestDetail() {
  const { id } = useParams();
  const [exchange, setExchange] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2));
  const chatEndRef = useRef(null);

  useEffect(() => {
    axios.get('/api/import/live-pull').then(res => {
      const all = res.data.exchanges || [];
      const found = all.find(e => e.id === id);
      setExchange(found || null);
    });
  }, [id]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async (msg) => {
    const text = msg || input;
    if (!text.trim() || chatLoading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setChatLoading(true);
    try {
      const res = await axios.post('/api/chat/send', {
        session_id: sessionId,
        message: text,
        exchange_ids: [id],
      });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'AI yanıt veremedi. Backend çalışıyor mu?' }]);
    } finally { setChatLoading(false); }
  };

  const params = (() => {
    try { return JSON.parse(exchange?.interesting_params || '[]'); } catch { return []; }
  })();

  if (!exchange) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <p>İstek bulunamadı. Önce Data Import ile veri yükle.</p>
      </div>
    );
  }

  const SEV_COLOR = { critical: '#ef4444', interesting: '#f97316', low: '#eab308', normal: '#475569' };
  const borderColor = SEV_COLOR[exchange.interest_level] || '#475569';

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] p-4 gap-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="font-mono text-xs font-bold px-2 py-1 rounded"
          style={{ background: exchange.method === 'POST' ? '#1e3a5f' : '#1a3a2a', color: '#93c5fd' }}>
          {exchange.method}
        </span>
        <span className="font-mono text-sm text-slate-300 truncate">{exchange.url}{exchange.path}</span>
        <span className={`ml-auto text-xs font-mono px-2 py-1 rounded`}
          style={{ color: exchange.status_code < 300 ? '#4ade80' : exchange.status_code < 400 ? '#93c5fd' : '#f87171' }}>
          {exchange.status_code}
        </span>
        <span className="text-xs px-2 py-1 rounded border capitalize"
          style={{ borderColor, color: borderColor }}>
          {exchange.interest_level} {exchange.score > 0 && `(${exchange.score}pt)`}
        </span>
      </div>

      {/* Parametreler */}
      {params.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <Tag className="w-4 h-4 text-yellow-400 shrink-0" />
          {params.map((p, i) => (
            <span key={i} className="text-xs px-2 py-0.5 rounded font-mono"
              style={{ background: '#422006', color: '#fde047' }}>{p}</span>
          ))}
        </div>
      )}

      {/* Ana İçerik */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Request/Response */}
        <div className="flex-1 flex flex-col gap-3 min-h-0">
          <RawView b64={exchange.request_b64} label="REQUEST" />
          <RawView b64={exchange.response_b64} label="RESPONSE" />
        </div>

        {/* AI Chat */}
        <div className="w-96 flex flex-col rounded-xl border overflow-hidden"
          style={{ borderColor: 'var(--color-dark-700)' }}>
          <div className="px-4 py-3 border-b flex items-center gap-2"
            style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }}>
            <Bot className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
            <span className="text-sm font-semibold text-white">AI Analiz</span>
          </div>

          {/* Şablon butonlar */}
          <div className="p-2 border-b flex flex-col gap-1 overflow-y-auto max-h-40"
            style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }}>
            {TEMPLATES.map((t, i) => (
              <button key={i} onClick={() => send(t)} disabled={chatLoading}
                className="text-xs text-left px-2 py-1.5 rounded hover:text-white transition-colors truncate"
                style={{ color: 'var(--color-primary-400)', background: 'var(--color-dark-800)' }}>
                ▶ {t.slice(0, 55)}...
              </button>
            ))}
          </div>

          {/* Mesajlar */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3" style={{ background: 'var(--color-dark-800)' }}>
            {messages.length === 0 && (
              <p className="text-xs text-slate-500 text-center mt-4">Şablon seç veya soru sor.</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: m.role === 'user' ? 'var(--color-dark-600)' : 'var(--color-primary-500)' }}>
                  {m.role === 'user' ? <User className="w-3.5 h-3.5 text-white" /> : <Bot className="w-3.5 h-3.5 text-white" />}
                </div>
                <div className="text-xs rounded-lg p-2.5 max-w-[85%] whitespace-pre-wrap leading-relaxed"
                  style={{ background: m.role === 'user' ? 'var(--color-dark-700)' : 'var(--color-dark-900)',
                    color: '#cbd5e1', border: '1px solid var(--color-dark-600)' }}>
                  {m.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: 'var(--color-primary-500)' }}>
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="flex items-center gap-1 px-3 py-2 rounded-lg" style={{ background: 'var(--color-dark-900)' }}>
                  {[0, 0.2, 0.4].map((d, i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
                      style={{ background: 'var(--color-primary-500)', animationDelay: `${d}s` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={e => { e.preventDefault(); send(); }} className="p-2 border-t"
            style={{ background: 'var(--color-dark-900)', borderColor: 'var(--color-dark-700)' }}>
            <div className="flex gap-2">
              <input value={input} onChange={e => setInput(e.target.value)} disabled={chatLoading}
                placeholder="Soru sor..." className="flex-1 text-xs rounded-lg px-3 py-2 text-white border focus:outline-none"
                style={{ background: 'var(--color-dark-800)', borderColor: 'var(--color-dark-700)' }} />
              <button type="submit" disabled={!input.trim() || chatLoading}
                className="p-2 rounded-lg disabled:opacity-50" style={{ background: 'var(--color-primary-600)' }}>
                <Send className="w-3.5 h-3.5 text-white" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
