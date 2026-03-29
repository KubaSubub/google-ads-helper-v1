// Design tokens extracted from SearchOptimization.jsx
// Used across audit-center sections and shared components

export const SECTION_STYLE = { marginBottom: 24 }

export const CARD = 'v2-card'

export const TH = {
    padding: '8px 12px', fontSize: 10, fontWeight: 500,
    color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
    letterSpacing: '0.08em', whiteSpace: 'nowrap', textAlign: 'left',
}

export const TD = { padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }

export const TD_DIM = { ...TD, color: 'rgba(255,255,255,0.45)' }

export const STATUS_COLORS = {
    danger:  { border: 'rgba(248,113,113,0.3)', dot: '#F87171', valueFill: '#F87171' },
    warning: { border: 'rgba(251,191,36,0.3)', dot: '#FBBF24', valueFill: '#FBBF24' },
    ok:      { border: 'rgba(74,222,128,0.3)', dot: '#4ADE80', valueFill: '#4ADE80' },
    info:    { border: 'rgba(79,142,247,0.2)', dot: '#4F8EF7', valueFill: '#4F8EF7' },
    neutral: { border: 'rgba(255,255,255,0.07)', dot: 'rgba(255,255,255,0.3)', valueFill: '#F0F0F0' },
}

export const CHANNEL_COLORS = {
    SEARCH: '#4F8EF7', DISPLAY: '#7B5CE0', VIDEO: '#FBBF24',
    SHOPPING: '#4ADE80', DISCOVER: '#F472B6', CROSS_NETWORK: '#94A3B8',
}

export const AD_STRENGTH_COLOR = { EXCELLENT: '#4ADE80', GOOD: '#4F8EF7', AVERAGE: '#FBBF24', POOR: '#F87171' }
