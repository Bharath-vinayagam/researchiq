const BASE = '/api'

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e.detail || `HTTP ${r.status}`)
  }
  return r.json()
}

async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e.detail || `HTTP ${r.status}`)
  }
  return r.json()
}

async function del(path) {
  const r = await fetch(BASE + path, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

async function upload(path, file) {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(BASE + path, {
    method: 'POST',
    body: fd,
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e.detail || `HTTP ${r.status}`)
  }
  return r.json()
}

export const api = {
  search:   (query, sources = ['arxiv', 'semantic_scholar'], max_results = 10) =>
              post('/search', { query, sources, max_results }),
  citations: (title)              => post('/citations', { title }),
  review:    (topic)              => post('/review',    { topic }),
  survey:    (topic)              => post('/survey',    { topic }),
  gaps:      (topic)              => post('/gaps',      { topic }),
  compare:   (paper_a, paper_b)   => post('/compare',   { paper_a, paper_b }),
  chat:      (question, use_rag = false) => post('/chat', { question, use_rag }),
  roadmap:   (topic)              => post('/roadmap',   { topic }),
  reports:   ()                   => get('/reports'),
  searches:  ()                   => get('/searches'),
  ragCount:  ()                   => get('/rag/count'),
  neo4jStatus: ()                 => get('/neo4j/status'),
  neo4jMultihop: (title, hops = 2) => post('/neo4j/citations/multihop', { title, hops }),
  neo4jGraph: (topic)             => get(`/neo4j/graph/${encodeURIComponent(topic)}`),
  mongoStatus: ()                 => get('/mongodb/status'),
  nosqlStatus: ()                 => get('/nosql/status'),
  pdfStatus: ()                   => get('/pdf/status'),
  pdfClear: ()                    => del('/pdf/clear'),
  pdfChat: (question)             => post('/pdf/chat', { question }),
  pdfFetchArxiv: (arxiv_id)       => post('/pdf/fetch_arxiv', { arxiv_id }),
  pdfUpload: (file)               => upload('/pdf/upload', file),
  graphAnalytics: (params = {})   => {
    const q = new URLSearchParams()
    if (params.topic) q.append('topic', params.topic)
    if (params.metric) q.append('metric', params.metric)
    if (params.limit) q.append('limit', params.limit)
    return get(`/graph/analytics?${q.toString()}`)
  },
  graphSyncMetrics: ()            => post('/graph/sync_metrics', {}),
  hfModels: (query, limit = 8)   => get(`/hf/models?query=${encodeURIComponent(query)}&limit=${limit}`),
  hfDatasets: (query, limit = 8) => get(`/hf/datasets?query=${encodeURIComponent(query)}&limit=${limit}`),
}


