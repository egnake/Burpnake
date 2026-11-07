import React, { useState, useEffect, useRef, useCallback } from 'react';
import { SSEContext } from './sseContext';

export function SSEProvider({ children }) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState({ total: 0, triage: 0, findings: 0, agent: 0 });
  const esRef = useRef(null);
  const listenersRef = useRef(new Map());

  useEffect(() => {
    let cancelled = false;
    let timerId = null;

    function openStream() {
      if (cancelled) return;
      if (esRef.current) esRef.current.close();
      const es = new EventSource('/api/stream/stream');
      esRef.current = es;
      es.onopen = () => {
        if (!cancelled) setConnected(true);
      };
      es.onerror = () => {
        if (cancelled) return;
        setConnected(false);
        es.close();
        timerId = setTimeout(openStream, 3000);
      };
      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          const enriched = { ...event, _id: Date.now() + Math.random() };
          setEvents(prev => [...prev.slice(-999), enriched]);

          setStats(prev => ({
            total: prev.total + (event.type === 'new_exchange' ? 1 : 0),
            triage: prev.triage + (event.type === 'new_interesting_request' ? 1 : 0),
            findings: prev.findings + (['new_finding', 'agent_confirmed_finding'].includes(event.type) ? 1 : 0),
            agent: prev.agent + (event.type?.startsWith('agent_') ? 1 : 0),
          }));

          listenersRef.current.forEach((callback) => {
            callback(enriched);
          });

          if (['agent_confirmed_finding', 'new_finding', 'oob_callback_received'].includes(event.type)) {
            try {
              if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('🎯 BurpNake — Finding!', {
                  body: event.data?.msg || event.data?.title || 'New vulnerability detected!',
                  icon: '/logo.jpg',
                });
              }
            } catch {
              // Ignore browser notification errors
            }
          }
        } catch {
          // Ignore non-JSON keepalive lines
        }
      };
    }

    openStream();
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    return () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
      esRef.current?.close();
    };
  }, []);

  const subscribe = useCallback((eventType, callback) => {
    const id = Symbol();
    listenersRef.current.set(id, (event) => {
      if (eventType === '*' || event.type === eventType) callback(event);
    });
    return () => listenersRef.current.delete(id);
  }, []);

  const clearEvents = useCallback(() => setEvents([]), []);

  return (
    <SSEContext.Provider value={{ events, connected, stats, subscribe, clearEvents }}>
      {children}
    </SSEContext.Provider>
  );
}
