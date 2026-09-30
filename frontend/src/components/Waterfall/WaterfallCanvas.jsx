import React, { useRef, useEffect } from 'react';

export default function WaterfallCanvas({
  pings = [],
  width = 800,
  height = 420,
  imageUrl = null,
  fileName = null,
  detections = [],
  onResetStream = null,
}) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // IF an image has been uploaded, render the image across the entire canvas
    if (imageUrl) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = imageUrl;
      img.onload = () => {
        // Draw the uploaded image filling the entire waterfall canvas
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);

        // Center Nadir Track (towfish acoustic track line)
        ctx.save();
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 6]);
        ctx.shadowColor = '#000000';
        ctx.shadowBlur = 4;
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.stroke();
        ctx.restore();

        // Top Hydrographic Swath Bar
        ctx.fillStyle = 'rgba(10, 15, 29, 0.78)';
        ctx.fillRect(0, 0, width, 28);

        ctx.font = 'bold 11px monospace';
        ctx.fillStyle = '#38bdf8';
        ctx.textAlign = 'left';
        ctx.fillText('◀ PORT SWATH (50m)', 14, 18);

        ctx.fillStyle = '#f8fafc';
        ctx.textAlign = 'center';
        ctx.fillText('▼ NADIR TRACK (TOWFISH)', width / 2, 18);

        ctx.fillStyle = '#38bdf8';
        ctx.textAlign = 'right';
        ctx.fillText('STBD SWATH (50m) ▶', width - 14, 18);

        // Draw Bounding Boxes for detected targets
        if (detections && detections.length > 0) {
          detections.forEach((det) => {
            if (!det.bbox) return;

            let bx = det.bbox.x ?? 0;
            let by = det.bbox.y ?? 0;
            let bw = det.bbox.width ?? 0;
            let bh = det.bbox.height ?? 0;

            // Handle normalized coordinates [0, 1] vs pixel coords [0, 640/1024]
            if (bx <= 1.0 && by <= 1.0 && bw <= 1.0 && bh <= 1.0) {
              bx *= width;
              by *= height;
              bw *= width;
              bh *= height;
            } else if (img.naturalWidth && img.naturalHeight) {
              bx = (bx / img.naturalWidth) * width;
              by = (by / img.naturalHeight) * height;
              bw = (bw / img.naturalWidth) * width;
              bh = (bh / img.naturalHeight) * height;
            }

            // Ensure valid minimum box dimensions
            bw = Math.max(12, Math.min(width - bx, bw));
            bh = Math.max(12, Math.min(height - by, bh));

            // Risk color styling
            const isCritical = det.risk_level === 'critical';
            const boxColor = isCritical ? '#ef4444' : '#f59e0b';
            const fillColor = isCritical ? 'rgba(239, 68, 68, 0.20)' : 'rgba(245, 158, 11, 0.20)';

            // Semi-transparent target fill
            ctx.fillStyle = fillColor;
            ctx.fillRect(bx, by, bw, bh);

            // Bounding box border
            ctx.strokeStyle = boxColor;
            ctx.lineWidth = 2;
            ctx.strokeRect(bx, by, bw, bh);

            // Reticle corner marks
            const corner = Math.min(8, bw / 3, bh / 3);
            ctx.lineWidth = 3;
            ctx.beginPath();
            // Top-left
            ctx.moveTo(bx, by + corner);
            ctx.lineTo(bx, by);
            ctx.lineTo(bx + corner, by);
            // Top-right
            ctx.moveTo(bx + bw - corner, by);
            ctx.lineTo(bx + bw, by);
            ctx.lineTo(bx + bw, by + corner);
            // Bottom-left
            ctx.moveTo(bx, by + bh - corner);
            ctx.lineTo(bx, by + bh);
            ctx.lineTo(bx + corner, by + bh);
            // Bottom-right
            ctx.moveTo(bx + bw - corner, by + bh);
            ctx.lineTo(bx + bw, by + bh);
            ctx.lineTo(bx + bw, by + bh - corner);
            ctx.stroke();

            // Label tag badge
            const confPct = Math.round((det.confidence || 0) * 100);
            const labelText = `${(det.class_label || 'target').replace(/_/g, ' ').toUpperCase()} ${confPct}%`;
            
            ctx.font = 'bold 10px monospace';
            const tagW = ctx.measureText(labelText).width + 12;
            const tagH = 18;
            const tagY = Math.max(30, by - tagH - 2);

            ctx.fillStyle = boxColor;
            ctx.fillRect(bx, tagY, tagW, tagH);

            ctx.fillStyle = '#000000';
            ctx.textAlign = 'left';
            ctx.fillText(labelText, bx + 6, tagY + 13);
          });
        }

        // Bottom Telemetry Bar
        ctx.fillStyle = 'rgba(10, 15, 29, 0.82)';
        ctx.fillRect(0, height - 24, width, 24);

        ctx.fillStyle = '#22c55e';
        ctx.textAlign = 'left';
        ctx.font = 'bold 10px monospace';
        ctx.fillText(`● ACOUSTIC SWATH LOADED: ${fileName || 'INGESTED IMAGE'}`, 14, height - 8);

        ctx.fillStyle = '#94a3b8';
        ctx.textAlign = 'right';
        ctx.fillText(
          `AI DETECTIONS: ${detections?.length || 0} TARGETS IDENTIFIED`,
          width - 14,
          height - 8
        );
      };
      return;
    }

    // Default: If pings are present, draw acoustic scanlines
    ctx.fillStyle = '#0a0f1d';
    ctx.fillRect(0, 0, width, height);

    if (pings.length > 0) {
      const pingHeight = Math.max(1, Math.floor(height / Math.min(pings.length, height)));

      pings.slice(-height).forEach((ping, rowIdx) => {
        const y = rowIdx * pingHeight;
        if (Array.isArray(ping)) {
          const colWidth = width / ping.length;
          ping.forEach((val, colIdx) => {
            const intensity = Math.min(255, Math.max(0, val));
            ctx.fillStyle = `rgb(${intensity}, ${Math.floor(intensity * 0.75)}, ${Math.floor(intensity * 0.2)})`;
            ctx.fillRect(colIdx * colWidth, y, colWidth + 0.5, pingHeight);
          });
        }
      });
    } else {
      // Synthetic demo waterfall sweep pattern
      const imgData = ctx.createImageData(width, height);
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const idx = (y * width + x) * 4;
          const distFromCenter = Math.abs(x - width / 2);
          if (distFromCenter < 12) {
            imgData.data[idx] = 10;
            imgData.data[idx + 1] = 15;
            imgData.data[idx + 2] = 25;
            imgData.data[idx + 3] = 255;
          } else {
            const noise = (Math.sin(x * 0.05 + y * 0.08) + Math.cos(x * 0.02 - y * 0.04)) * 30 + 110;
            const r = Math.min(255, Math.floor(noise + Math.random() * 20));
            imgData.data[idx] = r;
            imgData.data[idx + 1] = Math.floor(r * 0.7);
            imgData.data[idx + 2] = Math.floor(r * 0.2);
            imgData.data[idx + 3] = 255;
          }
        }
      }
      ctx.putImageData(imgData, 0, 0);

      // Overlay center nadir line indicator
      ctx.strokeStyle = '#38bdf8';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(width / 2, 0);
      ctx.lineTo(width / 2, height);
      ctx.stroke();

      // Legend overlay
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.fillRect(10, 10, 220, 50);
      ctx.fillStyle = '#38bdf8';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('PORT SWATH | NADIR | STBD SWATH', 15, 28);
      ctx.fillStyle = '#ffffff';
      ctx.fillText('STATUS: STREAMING ACTIVE', 15, 46);
    }
  }, [pings, width, height, imageUrl, fileName, detections]);

  return (
    <div style={{ position: 'relative', width: '100%', overflow: 'hidden', borderRadius: '8px', border: '1px solid rgba(0, 0, 0, 0.12)' }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ width: '100%', height: 'auto', display: 'block' }}
      />
      {imageUrl && onResetStream && (
        <button
          onClick={onResetStream}
          title="Return to real-time live ping stream"
          style={{
            position: 'absolute',
            top: '34px',
            right: '10px',
            padding: '3px 8px',
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            transition: 'background 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(15, 23, 42, 1)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(15, 23, 42, 0.85)')}
        >
          <span>↺</span> Live Ping Stream
        </button>
      )}
    </div>
  );
}

