import styles from './DetectionSettings.module.css'

export const SONAR_CLASSES = [
  'Shipwreck',
  'Aircraft',
  'Submarine Pipeline',
  'Ghost Net',
  'Mine / Munitions',
  'Geology / Rocks',
  'Debris',
  'Other'
]
const CLASSES = SONAR_CLASSES


export default function DetectionSettings({ value, onChange, onConfidenceChange }) {
  const { confidence, selected } = value

  function toggleClass(name) {
    const next = selected.includes(name)
      ? selected.filter((n) => n !== name)
      : [...selected, name]
    onChange({ ...value, selected: next })
  }

  function handleConfidenceChange(e) {
    const val = Number(e.target.value)
    if (onConfidenceChange) {
      onConfidenceChange(val)
    }
    onChange({ ...value, confidence: val })
  }

  const pct = ((confidence - 15) / 80) * 100

  return (
    <section className={styles.panel}>
      <div className={styles.panelTitle}>Detection settings</div>

      <div className={styles.confViz}>
        <div className={styles.confTop}>
          <span className={styles.confLabel}>Confidence threshold</span>
          <span className={`${styles.confValue} tabular`}>{confidence}%</span>
        </div>
        <p className={styles.confHint}>Findings below {confidence}% will not be displayed.</p>
        <div className={styles.confTrackWrap}>
          <input
            type="range"
            min={15}
            max={95}
            value={confidence}
            onChange={handleConfidenceChange}
            className={styles.slider}
            aria-label="Confidence threshold"
          />
          <div className={styles.trackBg}>
            <div className={styles.trackFill} style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className={styles.confRange}>
          <span>15%</span>
          <span>95%</span>
        </div>
      </div>

      <div className={styles.field}>
        <label>Detection classes</label>
        <div className={styles.checkrow}>
          {CLASSES.map((cls) => (
            <button
              key={cls}
              type="button"
              className={`${styles.checkChip} ${selected.includes(cls) ? styles.checkChipActive : ''}`}
              onClick={() => toggleClass(cls)}
              aria-selected={selected.includes(cls)}
            >
              {selected.includes(cls) && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
              {cls}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
