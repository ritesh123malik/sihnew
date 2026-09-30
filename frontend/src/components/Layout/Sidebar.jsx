import React from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const NAV_ITEMS = [
  { path: '/', label: 'Launch', icon: '🚀' },
  { path: '/live-survey', label: 'Live Survey', icon: '📡' },
  { path: '/map', label: 'Swath Map', icon: '🗺️' },
  { path: '/reports', label: 'Reports & Export', icon: '📑' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__header">
        <div className="sidebar__logo-badge">S</div>
        <div className="sidebar__brand-text">
          <h2>SONARIS</h2>
          <p>SIH 2026 · NIOT / MoES</p>
        </div>
      </div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `sidebar__item ${isActive ? 'active' : ''}`
            }
          >
            <span className="sidebar__icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div><strong>Mission:</strong> MSN-3D02</div>
        <div><strong>Vessel:</strong> Sagar Nidhi</div>
        <div><strong>Status:</strong> Ready</div>
      </div>
    </aside>
  );
}
