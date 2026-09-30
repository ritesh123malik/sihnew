import { useNavigate } from 'react-router-dom'
import styles from './ActionBar.module.css'

export default function ActionBar({ filename, count = 0, runId, onExport, onDelete }) {
  const navigate = useNavigate()
  return (
    <section className={styles.actionsRow}>
      <div className={styles.actionsRow__info}>
        <strong>Run complete — {filename || 'sonar scan'}</strong>
        <span>{count} detections logged{runId ? ` · ${runId.slice(0, 8)}` : ''}</span>
      </div>
      <div className={styles.actionsRow__btns}>
        <button className={styles.btnGhost} type="button" onClick={() => navigate('/uploads')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m12 19l-7-7l7-7m7 7H5" />
          </svg>
          Back to uploads
        </button>
        {runId ? (
          <button
            className={styles.btnGhost}
            type="button"
            onClick={() => navigate(`/map?run=${encodeURIComponent(runId)}`)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            View on map
          </button>
        ) : null}
        {onDelete ? (
          <button className={styles.btnGhost} type="button" onClick={onDelete}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6h18M8 6V4h8v2m-1 0v14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6h10" />
            </svg>
            Delete upload
          </button>
        ) : null}
        <button className={styles.btnPrimary} type="button" onClick={onExport}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z" />
            <path d="M14 2v5a1 1 0 0 0 1 1h5m-8 10v-6m-3 3l3 3l3-3" />
          </svg>
          Download report
        </button>
      </div>
    </section>
  )
}
