import { useMemo, useState } from 'react'
import styles from './AnnotatedScan.module.css'

const MODEL_W = 800
const MODEL_H = 600

const RISK_COLOR = {
  critical: '#c45c26',
  high: '#d97706',
  medium: '#ca8a04',
  low: '#4f6f8f',
}

function scaledBox(bbox, imgW, imgH) {
  if (!bbox || !imgW || !imgH) return null
  let x = Number(bbox.x) || 0
  let y = Number(bbox.y) || 0
  let width = Number(bbox.width) || 0
  let height = Number(bbox.height) || 0

  // If bounding box was returned in normalized [0, 1] space:
  if (x <= 1.0 && y <= 1.0 && width <= 1.0 && height <= 1.0 && imgW > 10) {
    x *= imgW
    y *= imgH
    width *= imgW
    height *= imgH
  }

  // Ensure within image bounds
  x = Math.max(0, Math.min(imgW, x))
  y = Math.max(0, Math.min(imgH, y))
  width = Math.max(0, Math.min(imgW - x, width))
  height = Math.max(0, Math.min(imgH - y, height))

  return { x, y, width, height }
}

export default function AnnotatedScan({
  imageUrl,
  filename,
  detections = [],
  selectedId,
  onSelect,
}) {
  const [size, setSize] = useState({ w: 0, h: 0 })

  const boxes = useMemo(
    () => detections
      .filter((d) => d.bbox)
      .map((d) => ({
        ...d,
        box: scaledBox(d.bbox, size.w || MODEL_W, size.h || MODEL_H),
      }))
      .filter((d) => d.box),
    [detections, size],
  )

  const viewW = size.w || MODEL_W
  const viewH = size.h || MODEL_H

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <span className={styles.label}>Annotated sonar scan</span>
        <span className={styles.meta}>{boxes.length} boxes · click a box or list row</span>
      </div>
      <div className={styles.stage}>
        {imageUrl ? (
          <>
            <img
              src={imageUrl}
              alt={filename || 'Sonar scan with detections'}
              onLoad={(e) => setSize({
                w: e.currentTarget.naturalWidth,
                h: e.currentTarget.naturalHeight,
              })}
            />
            {viewW > 0 ? (
              <svg
                className={styles.overlay}
                viewBox={`0 0 ${viewW} ${viewH}`}
                preserveAspectRatio="xMidYMid meet"
                role="img"
                aria-label="Detection bounding boxes"
              >
                {boxes.map((d) => {
                  const active = d.detection_id === selectedId
                  const color = RISK_COLOR[d.risk_level] || RISK_COLOR.low
                  return (
                    <g
                      key={d.detection_id}
                      className={styles.boxGroup}
                      onClick={() => onSelect?.(d.detection_id)}
                    >
                      <rect
                        x={d.box.x}
                        y={d.box.y}
                        width={d.box.width}
                        height={d.box.height}
                        fill={active ? `${color}33` : 'transparent'}
                        stroke={color}
                        strokeWidth={active ? Math.max(viewW / 180, 4) : Math.max(viewW / 280, 3)}
                      />
                      <rect
                        x={d.box.x}
                        y={Math.max(0, d.box.y - Math.max(viewH / 28, 22))}
                        width={Math.min(d.box.width + 80, viewW - d.box.x)}
                        height={Math.max(viewH / 30, 20)}
                        fill={color}
                      />
                      <text
                        x={d.box.x + 6}
                        y={Math.max(14, d.box.y - 6)}
                        fill="#fff"
                        fontSize={Math.max(viewH / 42, 14)}
                        fontFamily="system-ui, sans-serif"
                      >
                        {d.class_label} {Math.round((d.confidence || 0) * 100)}%
                      </text>
                    </g>
                  )
                })}
              </svg>
            ) : null}
          </>
        ) : (
          <div className={styles.empty}>No scan preview available</div>
        )}
      </div>
    </div>
  )
}
