const BASE_URL = 'http://127.0.0.1:8000'

export async function triggerSimulation({ engine = 'swe_fallback' } = {}) {
  const res = await fetch(`${BASE_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engine }),
  })
  if (!res.ok) throw new Error('Failed to trigger simulation')
  return res.json() // { job_id, status }
}

export async function getStatus(jobId) {
  const res = await fetch(`${BASE_URL}/simulate/${jobId}/status`)
  if (!res.ok) throw new Error('Failed to fetch status')
  return res.json() // { job_id, status, error }
}

export async function getResult(jobId) {
  const res = await fetch(`${BASE_URL}/simulate/${jobId}/result`)
  if (!res.ok) throw new Error('Failed to fetch result')
  return res.json()
}