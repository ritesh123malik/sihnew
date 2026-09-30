import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Launch from './pages/Launch/Launch';
import Reports from './pages/Reports/Reports';
import LiveSurvey from './pages/LiveSurvey';
import Map from './pages/Map/Map';
import Uploads from './pages/Uploads/Uploads';
import DetectionResults from './pages/DetectionResults/DetectionResults';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Core Scan Launch Workflow */}
        <Route path="/" element={<Launch />} />
        <Route path="/launch" element={<Navigate to="/" replace />} />

        {/* Operational Intelligence Pages */}
        <Route path="/live-survey" element={<LiveSurvey />} />
        <Route path="/map" element={<Map />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/uploads" element={<Uploads />} />
        <Route path="/results" element={<Navigate to="/uploads" replace />} />
        <Route path="/results/:runId" element={<DetectionResults />} />

        {/* Removed Pages Redirects */}
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="/anomalies" element={<Navigate to="/" replace />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
