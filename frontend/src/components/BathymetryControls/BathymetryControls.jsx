import React, { useState } from 'react';

export default function BathymetryControls({
  settings = {},
  onSettingsChange = () => {},
  onExport = () => {},
  isGenerating = false,
  onGenerate = () => {}
}) {
  const [exportFormat, setExportFormat] = useState('geotiff');
  const [showExportModal, setShowExportModal] = useState(false);

  const handleChange = (key, value) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const handleExportSubmit = () => {
    onExport(exportFormat);
    setShowExportModal(false);
  };

  return (
    <div
      style={{
        padding: '14px',
        background: '#0a192f',
        borderRadius: '8px',
        border: '1px solid #1e293b',
        color: '#e2e8f0',
        fontFamily: 'system-ui, sans-serif',
        fontSize: '13px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: '13px' }}>
          ⚙️ Bathymetry Controls
        </span>
      </div>

      {/* Color Scheme */}
      <div>
        <label style={{ display: 'block', marginBottom: '4px', color: '#94a3b8', fontSize: '11px' }}>
          Color Scheme
        </label>
        <select
          value={settings.colorScheme || 'elevation'}
          onChange={(e) => handleChange('colorScheme', e.target.value)}
          style={{
            width: '100%',
            padding: '6px 8px',
            background: '#1e293b',
            color: '#e2e8f0',
            border: '1px solid #334155',
            borderRadius: '4px',
            outline: 'none',
            fontSize: '12px'
          }}
        >
          <option value="elevation">Elevation (Acoustic Height)</option>
          <option value="intensity">Backscatter Intensity</option>
          <option value="cyan">Tactical Cyan</option>
        </select>
      </div>

      {/* Vertical Exaggeration Slider */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ color: '#94a3b8', fontSize: '11px' }}>Vertical Exaggeration</span>
          <span style={{ color: '#38bdf8', fontSize: '11px', fontWeight: 600 }}>
            {(settings.elevationScale || 4).toFixed(1)}x
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="15"
          step="0.5"
          value={settings.elevationScale || 4}
          onChange={(e) => handleChange('elevationScale', parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: '#00f0ff' }}
        />
      </div>

      {/* Point Size Slider */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ color: '#94a3b8', fontSize: '11px' }}>Point Density Size</span>
          <span style={{ color: '#38bdf8', fontSize: '11px', fontWeight: 600 }}>
            {settings.pointSize || 3}px
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="8"
          step="1"
          value={settings.pointSize || 3}
          onChange={(e) => handleChange('pointSize', parseInt(e.target.value, 10))}
          style={{ width: '100%', accentColor: '#00f0ff' }}
        />
      </div>

      {/* Toggle Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={settings.showShadows !== false}
            onChange={(e) => handleChange('showShadows', e.target.checked)}
            style={{ accentColor: '#00f0ff' }}
          />
          <span style={{ fontSize: '12px' }}>Render Acoustic Shadows</span>
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={settings.showTargets !== false}
            onChange={(e) => handleChange('showTargets', e.target.checked)}
            style={{ accentColor: '#00f0ff' }}
          />
          <span style={{ fontSize: '12px' }}>Highlight Target Hazards</span>
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={settings.showGrid !== false}
            onChange={(e) => handleChange('showGrid', e.target.checked)}
            style={{ accentColor: '#00f0ff' }}
          />
          <span style={{ fontSize: '12px' }}>Display Seafloor Grid</span>
        </label>
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
        <button
          type="button"
          onClick={onGenerate}
          disabled={isGenerating}
          style={{
            padding: '8px 12px',
            background: 'linear-gradient(135deg, #0284c7 0%, #00f0ff 100%)',
            color: '#060f1e',
            fontWeight: 700,
            border: 'none',
            borderRadius: '4px',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            transition: 'opacity 0.2s'
          }}
        >
          {isGenerating ? '⏳ Computing Inversion...' : '🌊 Re-calculate Inversion'}
        </button>

        <button
          type="button"
          onClick={() => setShowExportModal(true)}
          style={{
            padding: '7px 12px',
            background: '#1e293b',
            color: '#e2e8f0',
            border: '1px solid #334155',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          💾 Export 3D Bathymetry
        </button>
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999
          }}
        >
          <div
            style={{
              background: '#0a192f',
              padding: '20px',
              borderRadius: '8px',
              border: '1px solid #38bdf8',
              width: '320px',
              color: '#e2e8f0'
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#38bdf8' }}>
              Export Bathymetry
            </h3>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '12px', color: '#94a3b8' }}>
              Format
            </label>
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                background: '#1e293b',
                color: '#e2e8f0',
                border: '1px solid #334155',
                borderRadius: '4px',
                marginBottom: '16px'
              }}
            >
              <option value="geotiff">GeoTIFF (GIS Elevation Raster)</option>
              <option value="obj">OBJ (3D Polygon Mesh)</option>
              <option value="ply">PLY (3D Sounding Point Cloud)</option>
              <option value="json">JSON (Raw Soundings)</option>
            </select>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setShowExportModal(false)}
                style={{
                  padding: '6px 12px',
                  background: '#334155',
                  color: '#e2e8f0',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExportSubmit}
                style={{
                  padding: '6px 14px',
                  background: '#10b981',
                  color: '#ffffff',
                  fontWeight: 600,
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Download
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
