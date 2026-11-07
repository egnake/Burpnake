import { createContext, useContext, useEffect } from 'react';

export const SSEContext = createContext(null);

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

