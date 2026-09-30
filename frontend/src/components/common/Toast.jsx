import React from 'react';

export default function Toast({ message, type = 'info', onClose }) {
  if (!message) return null;

  const styleMap = {
    info: {
      bg: '#ffffff',
      color: '#1a1a1a',
      borderLeft: '4px solid var(--gesso-primary, #2e3700)',
      icon: 'ℹ️',
    },
    success: {
      bg: '#ffffff',
      color: '#1a1a1a',
      borderLeft: '4px solid var(--gesso-success, #138b3f)',
      icon: '✅',
    },
    error: {
      bg: '#ffffff',
      color: '#1a1a1a',
      borderLeft: '4px solid var(--gesso-error, #dc2626)',
      icon: '⚠️',
    },
    warning: {
      bg: '#ffffff',
      color: '#1a1a1a',
      borderLeft: '4px solid var(--gesso-warning, #b86505)',
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
        fontFamily: "var(--gesso-font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
        border: '1px solid rgba(0, 0, 0, 0.12)',
        borderLeft: current.borderLeft,
        padding: '12px 18px',
        borderRadius: '8px',
        boxShadow: '0 10px 30px -4px rgba(0, 0, 0, 0.14), 0 4px 10px -2px rgba(0, 0, 0, 0.06)',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        fontSize: '13.5px',
        fontWeight: '500',
        letterSpacing: '0.1px',
        lineHeight: 1.45,
        maxWidth: '580px',
        animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <div style={{ flex: 1, color: current.color }}>{message}</div>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="Dismiss notification"
          style={{
            background: 'rgba(0, 0, 0, 0.05)',
            color: '#5b595f',
            border: 'none',
            borderRadius: '50%',
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '12px',
            cursor: 'pointer',
            flexShrink: 0,
            transition: 'background 0.15s ease, color 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.12)';
            e.currentTarget.style.color = '#1a1a1a';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.05)';
            e.currentTarget.style.color = '#5b595f';
          }}
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

