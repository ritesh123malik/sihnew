import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Topbar from '../../components/Topbar/Topbar'
import UploadPanel from '../../components/UploadPanel/UploadPanel'
import DetectionSettings from '../../components/DetectionSettings/DetectionSettings'
import LaunchBar from '../../components/LaunchBar/LaunchBar'
import { createReportInstance, detectScan, getHealth, getRun } from '../../api/client'
import styles from './Launch.module.css'

const DEFAULT_METADATA = {
  latitude: '13.0628',
  longitude: '80.3582',
  sonarType: 'Side-Scan',
  resolution: '0.5 m/px',
  depthMin: '4',
  depthMax: '38',
}

const LAST_SCAN_KEY = 'sonarLastScan'

function fileKey(file) {
  if (!file) return ''
  return `${file.name}:${file.size}:${file.lastModified || 0}`
}

function classKey(selected) {
  return [...selected].sort().join(',')
}

function readLastScan() {
  try {
    return JSON.parse(localStorage.getItem(LAST_SCAN_KEY) || 'null')
  } catch {
    return null
  }
}

export default function Launch() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [settings, setSettings] = useState({
    confidence: 20,
    selected: ['Shipwreck', 'Aircraft', 'Submarine Pipeline', 'Ghost Net', 'Mine / Munitions', 'Geology / Rocks', 'Debris', 'Other'],

  })
  const [confidenceTouched, setConfidenceTouched] = useState(false)
  const [pipeline, setPipeline] = useState('idle')
  const [error, setError] = useState('')
  const [health, setHealth] = useState(null)
  const [lastScan, setLastScan] = useState(readLastScan)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'error' }))
  }, [])

  useEffect(() => {
    if (!file) {
      setPreviewUrl('')
      return undefined
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const instanceOnly = useMemo(() => {
    if (!file || !lastScan?.runId) return false
    return (
      lastScan.fileKey === fileKey(file)
      && lastScan.classes === classKey(settings.selected)
    )
  }, [file, lastScan, settings.selected])

  function rememberScan(runId) {
    const record = {
      runId,
      fileKey: fileKey(file),
      classes: classKey(settings.selected),
      confidence: settings.confidence,
    }
    localStorage.setItem(LAST_SCAN_KEY, JSON.stringify(record))
    localStorage.setItem('lastRunId', runId)
    setLastScan(record)
  }

  async function handleLaunch() {
    setError('')
    if (!file) {
      setError('Upload a sonar image before launching the pipeline.')
      return
    }
    const lat = Number(DEFAULT_METADATA.latitude)
    const lng = Number(DEFAULT_METADATA.longitude)
    const depthMin = Number(DEFAULT_METADATA.depthMin)
    const depthMax = Number(DEFAULT_METADATA.depthMax)
    if (Number.isNaN(lat) || Number.isNaN(lng) || Number.isNaN(depthMin) || Number.isNaN(depthMax)) {
      setError('Latitude, longitude, and depth must be numbers.')
      return
    }
    if (depthMin >= depthMax) {
      setError('Minimum depth must be less than maximum depth.')
      return
    }

    setPipeline('running')
    try {
      if (instanceOnly) {
        await getRun(lastScan.runId)
        await createReportInstance(lastScan.runId, settings.confidence)
        rememberScan(lastScan.runId)
        setPipeline('done')
        navigate(`/results/${lastScan.runId}?threshold=${settings.confidence}`)
        return
      }

      const formData = new FormData()
      formData.append('file', file)
      formData.append('latitude', String(lat))
      formData.append('longitude', String(lng))
      formData.append('sonar_type', DEFAULT_METADATA.sonarType)
      formData.append('resolution', DEFAULT_METADATA.resolution)
      formData.append('depth_min', String(depthMin))
      formData.append('depth_max', String(depthMax))
      formData.append('confidence_threshold', String(settings.confidence))
      formData.append('selected_classes', settings.selected.join(','))
      formData.append('min_object_size', '10')

      const result = await detectScan(formData)
      rememberScan(result.run_id)
      setPipeline('done')
      navigate(`/results/${result.run_id}?threshold=${settings.confidence}`)
    } catch (err) {
      if (instanceOnly) {
        localStorage.removeItem(LAST_SCAN_KEY)
        setLastScan(null)
      }
      setPipeline('error')
      setError(err.message || 'Detection failed.')
    }
  }

  return (
    <>
      <Topbar activePage="launch" />
      <main className={styles.workSurface}>
        {error ? <div className={styles.errorBanner}>{error}</div> : null}
        <UploadPanel file={file} previewUrl={previewUrl} onFile={setFile} />
        <DetectionSettings
          value={settings}
          onChange={setSettings}
          onConfidenceChange={() => setConfidenceTouched(true)}
        />
        <LaunchBar
          ready={Boolean(file) && health?.status === 'ok'}
          running={pipeline === 'running'}
          instanceOnly={instanceOnly}
          threshold={settings.confidence}
          onLaunch={handleLaunch}
        />
      </main>
    </>
  )
}
