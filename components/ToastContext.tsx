'use client';

import React, { createContext, useCallback, useContext, useState } from 'react';

type ToastType = 'success' | 'error';

type ToastState = {
  message: string;
  type: ToastType;
} | null;

interface ToastContextValue {
  toast: ToastState;
  showToast: (message: string, type: ToastType) => void;
  clearToast: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_DURATION_MS = 5000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastState>(null);

  const showToast = useCallback((message: string, type: ToastType) => {
    setToast({ message, type });
    const t = setTimeout(() => setToast(null), TOAST_DURATION_MS);
    return () => clearTimeout(t);
  }, []);

  const clearToast = useCallback(() => setToast(null), []);

  return (
    <ToastContext.Provider value={{ toast, showToast, clearToast }}>
      {children}
      {toast && (
        <div
          role="alert"
          aria-live="assertive"
          className="fixed left-1/2 top-4 z-50 w-full max-w-md -translate-x-1/2 rounded-lg border px-4 py-3 shadow-lg"
          style={{
            backgroundColor:
              toast.type === 'error' ? 'var(--card)' : 'var(--card)',
            borderColor:
              toast.type === 'error' ? 'var(--error)' : 'var(--success)',
            color: toast.type === 'error' ? 'var(--error)' : 'var(--success)',
          }}
        >
          <p className="text-sm font-medium">
            <span className="font-semibold">{toast.type === 'error' ? 'Error: ' : 'Success: '}</span>
            {toast.message}
          </p>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return {
      toast: null,
      showToast: () => {},
      clearToast: () => {},
    };
  }
  return ctx;
}
