import { useState, useRef } from 'react'
import { triggerSimulation, getStatus, getResult } from './api'

const POLL_INTERVAL_MS = 2000
const REAL_DEM = 'data/processed/rishiganga_dem_utm44n.tif'
const REAL_HYDROGRAPH = 'data/processed/rishiganga_breach_hydrograph.csv'

export default function App() {
  const [engine, setEngine] = useState('swe_fallback')
  const [useRealData, setUseRealData] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const pollRef = useRef(null)

  async function handleTrigger() {
    setError(null); setResult(null); setStatus(null); setRunning(true)
    try {
      const payload = { engine }
      if (useRealData) {
        payload.dem_path = REAL_DEM
        payload.breach_hydrograph_csv = REAL_HYDROGRAPH
      }
      const { job_id, status: initialStatus } = await triggerSimulation(payload)
      setJobId(job_id); setStatus(initialStatus)
      poll(job_id)
    } catch (err) {
      setError(err.message); setRunning(false)
    }
  }

  function poll(id) {
    pollRef.current = setInterval(async () => {
      try {
        const s = await getStatus(id)
        setStatus(s.status)
        if (s.status === 'success' || s.status === 'failed') {
          clearInterval(pollRef.current); setRunning(false)
          if (s.status === 'success') setResult(await getResult(id))
          else setError(s.error || 'Simulation failed')
        }
      } catch (err) {
        clearInterval(pollRef.current); setRunning(false); setError(err.message)
      }
    }, POLL_INTERVAL_MS)
  }

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', maxWidth: 600 }}>
      <h1>Fuzzy-Train — Flood Simulation</h1>

      <div style={{ marginBottom: 12 }}>
        <label>Engine: </label>
        <select value={engine} onChange={e => setEngine(e.target.value)} disabled={running}>
          <option value="swe_fallback">SWE fallback</option>
          <option value="dualsphysics">DualSPHysics (SPH)</option>
        </select>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label>
          <input type="checkbox" checked={useRealData} onChange={e => setUseRealData(e.target.checked)} disabled={running} />
          {' '}Use real Rishiganga DEM + hydrograph (falls back to synthetic sample data if unchecked)
        </label>
      </div>

      <button onClick={handleTrigger} disabled={running}>
        {running ? 'Running…' : 'Run simulation'}
      </button>
      {jobId && <p>Job ID: {jobId}</p>}
      {status && <p>Status: {status}</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {result && (
        <div>
          <h2>Result</h2>
          <p>Engine: {result.engine}</p>
          <p>Runtime: {result.runtime_seconds ?? 'n/a'}s</p>
          <p>Max depth raster: {result.max_depth_raster ?? 'n/a'}</p>
          <p>
            Flood extent (.shp/.kml): {result.flood_extent_vector
              ? <a href={result.flood_extent_vector}>Download</a>
              : 'Not available yet'}
          </p>
        </div>
      )}
    </div>
  )
}
