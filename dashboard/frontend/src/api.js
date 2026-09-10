const BASE_URL = 'http://127.0.0.1:8000'

export async function triggerSimulation({ engine = 'swe_fallback', dem_path = null, breach_hydrograph_csv = null, case_name = 'rishiganga_glof_2021', config = null } = {}) {
  const res = await fetch(`${BASE_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engine, dem_path, breach_hydrograph_csv, case_name, config }),
  })
  if (!res.ok) throw new Error('Failed to trigger simulation')
  return res.json()
}

export async function getStatus(jobId) {
  const res = await fetch(`${BASE_URL}/simulate/${jobId}/status`)
  if (!res.ok) throw new Error('Failed to fetch status')
  return res.json()
}

export async function getResult(jobId) {
  const res = await fetch(`${BASE_URL}/simulate/${jobId}/result`)
  if (!res.ok) throw new Error('Failed to fetch result')
  return res.json()
}
