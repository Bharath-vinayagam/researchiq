import React, { useState, useEffect, createContext, useContext } from 'react'
import { api } from './services/api'
import Discover from './pages/Discover'
import Review from './pages/Review'
import Survey from './pages/Survey'
import Gaps from './pages/Gaps'
import Compare from './pages/Compare'
import Chat from './pages/Chat'
import Roadmap from './pages/Roadmap'
import History from './pages/History'

// Shared context so any tab can read/write the global topic
export const TopicContext = createContext({ topic: '', setTopic: () => {} })
export const useTopicContext = () => useContext(TopicContext)

const TABS = [
  { id: 'discover', label: '🔍 Discover' },
  { id: 'review',   label: '📖 Review' },
  { id: 'survey',   label: '📚 Survey' },
  { id: 'gaps',     label: '💡 Gaps' },
  { id: 'compare',  label: '⚖️ Compare' },
  { id: 'chat',     label: '💬 Chat' },
  { id: 'roadmap',  label: '🗺️ Roadmap' },
  { id: 'history',  label: '🗂️ History' },
]

export default function App() {
  const [tab, setTab] = useState('discover')
  const [topic, setTopic] = useState('')
  const [neo4jInfo, setNeo4jInfo] = useState(null)

  useEffect(() => {
    api.neo4jStatus().then(data => setNeo4jInfo(data)).catch(() => {})
  }, [])

  return (
    <TopicContext.Provider value={{ topic, setTopic }}>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        {/* Header */}
        <header style={{
          background: '#0d1117', borderBottom: '1px solid #21262d',
          padding: '0 16px', height: 50, display: 'flex', alignItems: 'center',
          gap: 12, flexShrink: 0, zIndex: 100,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <span style={{ fontWeight: 700, fontSize: 15, color: '#58a6ff' }}>
              ⚗️ ResearchIQ
            </span>
            {neo4jInfo && (
              <span
                title={
                  neo4jInfo.connected
                    ? `Connected to Neo4j (${neo4jInfo.uri})\nPapers: ${neo4jInfo.stats?.papers || 0}, Relationships: ${neo4jInfo.stats?.relationships || 0}`
                    : `Neo4j Offline (${neo4jInfo.uri || 'bolt://localhost:7687'}) - Using in-memory NetworkX`
                }
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 12,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  background: neo4jInfo.connected ? 'rgba(63,185,80,0.12)' : 'rgba(139,148,158,0.12)',
                  color: neo4jInfo.connected ? '#3fb950' : '#8b949e',
                  border: `1px solid ${neo4jInfo.connected ? 'rgba(63,185,80,0.3)' : 'rgba(139,148,158,0.25)'}`,
                  cursor: 'help'
                }}
              >
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: neo4jInfo.connected ? '#3fb950' : '#8b949e',
                  display: 'inline-block'
                }}></span>
                Neo4j {neo4jInfo.connected ? 'Active' : 'Offline'}
              </span>
            )}
          </div>

          {/* Global topic bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, maxWidth: 420 }}>
            <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="Enter a research topic here…"
              style={{
                flex: 1, background: '#161b22', border: '1px solid #30363d',
                borderRadius: 6, color: '#e6edf3', padding: '5px 10px',
                fontSize: 13, outline: 'none',
              }}
              onFocus={e => e.target.style.borderColor = '#58a6ff'}
              onBlur={e => e.target.style.borderColor = '#30363d'}
            />
            {topic && (
              <button
                onClick={() => setTopic('')}
                style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 14, padding: '2px 4px' }}
                title="Clear topic"
              >✕</button>
            )}
          </div>

          <nav style={{ display: 'flex', gap: 1, overflowX: 'auto' }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                background: tab === t.id ? '#161b22' : 'none',
                border: 'none',
                borderBottom: tab === t.id ? '2px solid #58a6ff' : '2px solid transparent',
                color: tab === t.id ? '#58a6ff' : '#8b949e',
                padding: '6px 11px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                whiteSpace: 'nowrap', cursor: 'pointer', transition: 'all .15s',
              }}>
                {t.label}
              </button>
            ))}
          </nav>
        </header>

        {/* Pages — all mounted, just show/hide to preserve state */}
        <main style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {[
            ['discover', <Discover />],
            ['review',   <Review />],
            ['survey',   <Survey />],
            ['gaps',     <Gaps />],
            ['compare',  <Compare />],
            ['chat',     <Chat />],
            ['roadmap',  <Roadmap />],
            ['history',  <History />],
          ].map(([id, page]) => (
            <div key={id} style={{
              position: 'absolute', inset: 0,
              display: tab === id ? 'block' : 'none',
              overflow: 'hidden',
            }}>
              {page}
            </div>
          ))}
        </main>
      </div>
    </TopicContext.Provider>
  )
}
