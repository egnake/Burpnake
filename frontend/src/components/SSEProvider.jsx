import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';

const SSEContext = createContext(null);

export function SSEProvider({ children }) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState({ total: 0, triage: 0, findings: 0, agent: 0 });
  const esRef = useRef(null);
  const listenersRef = useRef(new Map());

  const connect = useCallback(() => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource('/api/stream/stream');
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => { setConnected(false); setTimeout(connect, 3000); };
    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        const enriched = { ...event, _id: Date.now() + Math.random() };
        setEvents(prev => [...prev.slice(-999), enriched]);
        
        // Update stats
        setStats(prev => ({
          total: prev.total + (event.type === 'new_exchange' ? 1 : 0),
          triage: prev.triage + (event.type === 'new_interesting_request' ? 1 : 0),
          findings: prev.findings + (['new_finding', 'agent_confirmed_finding'].includes(event.type) ? 1 : 0),
          agent: prev.agent + (event.type?.startsWith('agent_') ? 1 : 0),
        }));

        // Notify type-specific listeners
        listenersRef.current.forEach((callback, key) => {
          if (key === '*' || key === event.type) {
            callback(enriched);
          }
        });
        
        // Sound + notification for critical findings
        if (['agent_confirmed_finding', 'new_finding', 'oob_callback_received'].includes(event.type)) {
          try {
            if (Notification.permission === 'granted') {
              new Notification('🎯 BurpNake — Finding!', {
                body: event.data?.msg || event.data?.title || 'New vulnerability detected!',
                icon: '/favicon.ico',
              });
            }
          } catch(e) {}
        }
      } catch {}
    };
  }, []);

  useEffect(() => {
    connect();
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    return () => esRef.current?.close();
  }, [connect]);

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

export function useSSE() {
  const ctx = useContext(SSEContext);
  if (!ctx) throw new Error('useSSE must be used within SSEProvider');
  return ctx;
}

export function useSSEEvent(eventType, callback) {
  const { subscribe } = useSSE();
  useEffect(() => {
    const unsub = subscribe(eventType, callback);
    return unsub;
  }, [eventType, callback, subscribe]);
}
