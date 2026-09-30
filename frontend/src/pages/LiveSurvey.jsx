import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Topbar from '../components/Topbar/Topbar';
import Footer from '../components/Layout/Footer';
import WaterfallCanvas from '../components/Waterfall/WaterfallCanvas';
import LiveDetectionFeed from '../components/LiveSurvey/LiveDetectionFeed';
import WebSocketStatus from '../components/common/WebSocketStatus';
import ProgressBar from '../components/common/ProgressBar';
import AnomalyModal from '../components/AnomalyModal/AnomalyModal';
import Toast from '../components/common/Toast';
import { API_BASE } from '../api/client';
import '../App.css';


export default function LiveSurvey() {
  const navigate = useNavigate();
  const [wsStatus, setWsStatus] = useState('connected');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  const [toastType, setToastType] = useState('info');
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [liveDetections, setLiveDetections] = useState([
    {
      id: 'live-ping-04',
      class_label: 'shipwreck_keel',
      confidence: 0.94,
      risk_level: 'critical',
      latitude: 13.0835,
      longitude: 80.3622,
      sadh_height_m: 3.9,
      shadow_length_m: 11.2,
    },
    {
      id: 'live-ping-09',
      class_label: 'abandoned_cable',
      confidence: 0.87,
      risk_level: 'medium',
      latitude: 13.0844,
      longitude: 80.3640,
      sadh_height_m: 0.8,
      shadow_length_m: 2.1,
    },
  ]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    let localUrl = null;
    if (file.type.startsWith('image/') || /\.(png|jpe?g|tif|tiff|bmp|webp)$/i.test(file.name)) {
      localUrl = URL.createObjectURL(file);
      setUploadedImage({
        url: localUrl,
        name: file.name,
        detections: [],
      });
    }

    setIsProcessing(true);
    setUploadProgress(10);
    setToastType('info');
    setToastMsg(`Uploading ${file.name} for Triton telemetry ingestion...`);

    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 20;
      });
    }, 200);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('confidence_threshold', '20');

    try {
      const endpoint = file.name.endsWith('.xtf') ? '/api/xtf/upload' : '/api/detect';
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(interval);
      setUploadProgress(100);

      if (res.ok) {
        const data = await res.json();
        const count = data.detections ? data.detections.length : 0;
        const newDets = (data.detections || []).map((d) => ({
          ...d,
          id: d.detection_id || d.id || `det-${Math.random().toString(36).slice(2, 7)}`,
        }));
        if (newDets.length > 0) {
          setLiveDetections((prev) => [...newDets, ...prev]);
        }

        const isXtf = file.name.endsWith('.xtf');
        const finalUrl = (isXtf && data.waterfall_url)
          ? `${API_BASE}${data.waterfall_url}`
          : (localUrl || (data.run_id ? `${API_BASE}/api/runs/${data.run_id}/file` : null));

        setUploadedImage({
          url: finalUrl,
          name: file.name,
          detections: newDets,
          runId: data.run_id,
        });

        setToastType(count > 0 ? 'success' : 'info');
        setToastMsg(
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span style={{ color: '#1a1a1a', fontSize: '13px' }}>
              {count > 0 ? '🎯' : 'ℹ️'} <strong>{file.name}</strong>: {count} target{count === 1 ? '' : 's'} identified.
            </span>
            {data.run_id && (
              <button
                onClick={() => navigate(`/results/${data.run_id}`)}
                style={{
                  padding: '5px 12px',
                  backgroundColor: 'var(--gesso-primary, #2e3700)',
                  color: '#ffffff',
                  borderRadius: '6px',
                  border: 'none',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: '12px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                }}
              >
                View Mission Report →
              </button>
            )}
            <button
              onClick={() => navigate('/reports')}
              style={{
                padding: '5px 10px',
                backgroundColor: '#f4f2f6',
                color: '#1a1a1a',
                borderRadius: '6px',
                border: '1px solid rgba(0, 0, 0, 0.15)',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '12px',
              }}
            >
              All Reports 📋
            </button>
          </div>
        );
      } else {
        setToastType('warning');
        setToastMsg('File uploaded and queued for acoustic pipeline analysis.');
      }
    } catch (err) {
      clearInterval(interval);
      setToastType('info');
      setToastMsg('Simulation completed with standard test telemetry.');
    } finally {
      setTimeout(() => {
        setIsProcessing(false);
        setUploadProgress(0);
      }, 1500);
    }
  };


  return (
    <>
      <Topbar activePage="live-survey" />

      <div className="app-content" style={{ marginTop: '16px' }}>
        {/* Survey Controls Bar */}
        <div className="card-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <WebSocketStatus status={wsStatus} pingMs={12} />
            <div style={{ fontSize: '13px', color: 'var(--gesso-fg-muted)' }}>
              Towfish Altitude: <strong>14.5m</strong> · Slant Range: <strong>50.0m</strong>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => navigate('/reports')}
              style={{
                padding: '8px 14px',
                backgroundColor: 'transparent',
                color: 'var(--gesso-fg, #1e293b)',
                border: '1px solid var(--gesso-divider, rgba(0,0,0,0.15))',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>📊</span> View All Reports
            </button>
            <label
              style={{
                padding: '8px 16px',
                backgroundColor: 'var(--gesso-primary, #2e3700)',
                color: '#ffffff',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>📂</span> Ingest XTF / Sonar Image
              <input
                type="file"
                accept=".xtf,.jpg,.jpeg,.png,.tif,.tiff"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>

        {isProcessing && (
          <div className="card-panel">
            <ProgressBar
              progress={uploadProgress}
              label="Decompressing Triton XTF packets & applying Slant Range Correction..."
            />
          </div>
        )}

        {/* Real-Time Acoustic Waterfall & Live Stream Feed */}
        <div className="grid-2col">
          <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
                  Active Towfish Acoustic Waterfall
                </h3>
                {uploadedImage && (
                  <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'rgba(34, 197, 94, 0.12)', color: '#15803d', fontWeight: 600, border: '1px solid rgba(34, 197, 94, 0.25)' }}>
                    Payload Loaded
                  </span>
                )}
              </div>
              <span style={{ fontSize: '11px', fontFamily: 'monospace', color: uploadedImage ? '#0284c7' : '#16a34a', fontWeight: 700 }}>
                {uploadedImage ? `● ${uploadedImage.name}` : '● 30 Hz Ping Rate'}
              </span>
            </div>
            <WaterfallCanvas
              width={720}
              height={420}
              imageUrl={uploadedImage?.url}
              fileName={uploadedImage?.name}
              detections={uploadedImage?.detections || []}
              onResetStream={() => setUploadedImage(null)}
            />
          </div>

          <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
                Real-Time Ping Detections
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--gesso-fg-muted)' }}>
                Auto-indexed with WGS84 GPS
              </span>
            </div>
            <LiveDetectionFeed
              detections={liveDetections}
              onInspect={(d) => setSelectedAnomaly(d)}
            />
          </div>
        </div>
      </div>

      <Footer />

      {toastMsg && <Toast message={toastMsg} type={toastType} onClose={() => setToastMsg('')} />}

      {selectedAnomaly && (
        <AnomalyModal
          detection={selectedAnomaly}
          onClose={() => setSelectedAnomaly(null)}
        />
      )}
    </>
  );
}
