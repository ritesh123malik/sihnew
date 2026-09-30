import React from 'react';

export default function Toast({ message, type = 'info', onClose }) {
  if (!message) return null;

  const styleMap = {
    info: {
      bg: '#0f172a',
      color: '#f8fafc',
      borderLeft: '4px solid #38bdf8',
      icon: 'ℹ️',
    },
    success: {
      bg: '#064e3b',
      color: '#f0fdf4',
      borderLeft: '4px solid #22c55e',
      icon: '✅',
    },
    error: {
      bg: '#7f1d1d',
      color: '#fef2f2',
      borderLeft: '4px solid #ef4444',
      icon: '⚠️',
    },
    warning: {
      bg: '#78350f',
      color: '#fffbeb',
      borderLeft: '4px solid #f59e0b',
      icon: '🔔',
    },
  };

  const current = styleMap[type] || styleMap.info;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 99999,
        backgroundColor: current.bg,
        color: current.color,
        border: '1px solid rgba(255, 255, 255, 0.18)',
        borderLeft: current.borderLeft,
        padding: '12px 20px',
        borderRadius: '8px',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.45), 0 4px 12px rgba(0, 0, 0, 0.25)',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        fontSize: '13.5px',
        fontWeight: '500',
        letterSpacing: '0.15px',
        lineHeight: 1.4,
        maxWidth: '560px',
        animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <div style={{ flex: 1, color: current.color }}>{message}</div>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="Dismiss notification"
          style={{
            background: 'rgba(255, 255, 255, 0.12)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '50%',
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            cursor: 'pointer',
            flexShrink: 0,
            transition: 'background 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.25)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)')}
        >
          ✕
        </button>
      )}
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
