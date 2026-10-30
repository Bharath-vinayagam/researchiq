import React from 'react'

const badge = {
  arxiv: { bg: 'rgba(88,166,255,.12)', c: '#58a6ff' },
  semantic_scholar: { bg: 'rgba(124,58,237,.15)', c: '#bc8cff' },
  openalex: { bg: 'rgba(16,185,129,.15)', c: '#10b981' }
}

export default function PaperCard({ paper, onSelect, selected, onViewCitations, onAuthorClick }) {
  const src = paper.source || (paper.url?.includes('arxiv') ? 'arxiv' : 'semantic_scholar')
  const b = badge[src] || badge.arxiv

  const handleCardClick = () => {
    if (onViewCitations) {
      onViewCitations(paper)
    } else if (onSelect) {
      onSelect(paper)
    }
  }

  return (
    <div
      onClick={handleCardClick}
      style={{
        background: 'var(--panel2, #161b22)',
        border: `1px solid ${selected ? '#58a6ff' : '#21262d'}`,
        borderRadius: 'var(--radius, 8px)',
        padding: '14px',
        cursor: 'pointer',
        transition: 'border-color .15s, transform .1s',
        display: 'flex',
        flexDirection: 'column',
        gap: 8
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#388bfd'}
      onMouseLeave={e => e.currentTarget.style.borderColor = selected ? '#58a6ff' : '#21262d'}
    >
      {/* Title & Source Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
        <a
          href={paper.url || paper.id}
          target="_blank"
          rel="noreferrer"
          style={{ fontWeight: 600, fontSize: 14, color: 'var(--accent, #58a6ff)', lineHeight: 1.4, flex: 1, textDecoration: 'none' }}
          onClick={e => e.stopPropagation()}
        >
          {paper.title}
        </a>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
          <span style={{
            background: b.bg,
            color: b.c,
            padding: '2px 7px',
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
            whiteSpace: 'nowrap'
          }}>
            {src === 'semantic_scholar' ? 'Scholar' : src === 'openalex' ? 'OpenAlex' : 'ArXiv'}
          </span>
        </div>
      </div>

      {/* Metadata & Clickable Authors */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', fontSize: 12, color: 'var(--muted, #8b949e)' }}>
        {paper.year && <span>📅 {paper.year}</span>}
        {paper.year && <span>·</span>}
        <span style={{ color: '#6e7681' }}>Authors:</span>
        {(paper.authors || []).slice(0, 4).map((auth, idx) => (
          <button
            key={idx}
            type="button"
            title={`Search all papers by ${auth}`}
            onClick={e => {
              e.stopPropagation()
              if (onAuthorClick) {
                onAuthorClick(auth)
              }
            }}
            style={{
              background: 'rgba(227, 179, 65, 0.1)',
              border: '1px solid rgba(227, 179, 65, 0.25)',
              color: '#e3b341',
              borderRadius: 10,
              padding: '1px 7px',
              fontSize: 11,
              cursor: onAuthorClick ? 'pointer' : 'default',
              transition: 'background .15s'
            }}
            onMouseEnter={e => { if (onAuthorClick) e.target.style.background = 'rgba(227, 179, 65, 0.25)' }}
            onMouseLeave={e => { if (onAuthorClick) e.target.style.background = 'rgba(227, 179, 65, 0.1)' }}
          >
            👤 {auth}
          </button>
        ))}
        {(paper.authors || []).length > 4 && (
          <span style={{ color: '#6e7681', fontSize: 11 }}>+{paper.authors.length - 4} more</span>
        )}
      </div>

      {/* Abstract/Summary */}
      {paper.summary && (
        <div style={{
          fontSize: 12,
          color: 'var(--muted2, #c9d1d9)',
          lineHeight: 1.55,
          overflow: 'hidden',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical'
        }}>
          {paper.summary}
        </div>
      )}

      {/* Action footer: View Citations button & link */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: 4,
        borderTop: '1px solid #21262d',
        marginTop: 2
      }}>
        <button
          type="button"
          onClick={e => {
            e.stopPropagation()
            if (onViewCitations) onViewCitations(paper)
            else if (onSelect) onSelect(paper)
          }}
          style={{
            background: 'rgba(63, 185, 80, 0.12)',
            border: '1px solid rgba(63, 185, 80, 0.3)',
            borderRadius: 6,
            color: '#3fb950',
            padding: '3px 10px',
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            transition: 'all 0.15s'
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(63, 185, 80, 0.22)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(63, 185, 80, 0.12)'}
        >
          📊 Citations &amp; Network
          {paper.citations ? ` (${paper.citations.toLocaleString()})` : ''}
        </button>

        <span style={{ fontSize: 11, color: '#6e7681' }}>
          Click card to inspect
        </span>
      </div>
    </div>
  )
}
