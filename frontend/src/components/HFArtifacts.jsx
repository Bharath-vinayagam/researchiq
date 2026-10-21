import React, { useState } from 'react'

export function ModelCard({ model }) {
  const [copied, setCopied] = useState(false)

  const copySnippet = () => {
    const code = `from transformers import AutoModelForCausalLM, AutoTokenizer\n\nmodel_id = "${model.id}"\ntokenizer = AutoTokenizer.from_pretrained(model_id)\nmodel = AutoModelForCausalLM.from_pretrained(model_id)`
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      background: '#161b22', border: '1px solid #21262d', borderRadius: 8,
      padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8,
      transition: 'border-color .15s'
    }}
    onMouseEnter={e => e.currentTarget.style.borderColor = '#ff9d00'}
    onMouseLeave={e => e.currentTarget.style.borderColor = '#21262d'}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, color: '#8b949e' }}>🤗 {model.author}/</span>
            <a
              href={model.url}
              target="_blank"
              rel="noreferrer"
              style={{ fontSize: 14, fontWeight: 600, color: '#ff9d00', textDecoration: 'none' }}
            >
              {model.name}
            </a>
            {model.pipeline_tag && (
              <span style={{
                background: 'rgba(88,166,255,0.12)', color: '#58a6ff',
                padding: '2px 7px', borderRadius: 10, fontSize: 10, fontWeight: 600,
                border: '1px solid rgba(88,166,255,0.25)'
              }}>
                {model.pipeline_tag}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <button
            onClick={copySnippet}
            style={{
              background: copied ? 'rgba(63,185,80,0.2)' : 'rgba(255,255,255,0.06)',
              color: copied ? '#3fb950' : '#8b949e',
              border: `1px solid ${copied ? 'rgba(63,185,80,0.4)' : '#30363d'}`,
              borderRadius: 5, padding: '3px 8px', fontSize: 11, cursor: 'pointer'
            }}
          >
            {copied ? '✓ Snippet Copied' : '📋 Python Snippet'}
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 11, color: '#8b949e' }}>
        <span>📥 {(model.downloads || 0).toLocaleString()} downloads</span>
        <span>❤️ {(model.likes || 0).toLocaleString()} likes</span>
        {model.arxiv_id && (
          <a
            href={`https://arxiv.org/abs/${model.arxiv_id}`}
            target="_blank"
            rel="noreferrer"
            style={{ color: '#58a6ff', fontSize: 11 }}
          >
            📄 Paper ({model.arxiv_id})
          </a>
        )}
      </div>

      {/* Tags */}
      {model.tags?.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 2 }}>
          {model.tags.map((t, idx) => (
            <span key={idx} style={{
              background: '#0d1117', border: '1px solid #30363d',
              color: '#6e7681', padding: '1px 6px', borderRadius: 4, fontSize: 10
            }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function DatasetCard({ dataset }) {
  return (
    <div style={{
      background: '#161b22', border: '1px solid #21262d', borderRadius: 8,
      padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8,
      transition: 'border-color .15s'
    }}
    onMouseEnter={e => e.currentTarget.style.borderColor = '#00b4d8'}
    onMouseLeave={e => e.currentTarget.style.borderColor = '#21262d'}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13, color: '#8b949e' }}>📊 {dataset.author}/</span>
          <a
            href={dataset.url}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 14, fontWeight: 600, color: '#00b4d8', textDecoration: 'none' }}
          >
            {dataset.name}
          </a>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: '#8b949e' }}>
          <span>📥 {(dataset.downloads || 0).toLocaleString()} downloads</span>
          <span>❤️ {(dataset.likes || 0).toLocaleString()} likes</span>
        </div>
      </div>

      {dataset.tags?.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {dataset.tags.map((t, idx) => (
            <span key={idx} style={{
              background: '#0d1117', border: '1px solid #30363d',
              color: '#6e7681', padding: '1px 6px', borderRadius: 4, fontSize: 10
            }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
