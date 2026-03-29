export default function MatchBadge({ type }) {
    const colors = {
        EXACT: { color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
        PHRASE: { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', border: 'rgba(79,142,247,0.2)' },
        BROAD: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
    }
    const c = colors[type] || { color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)' }
    return (
        <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: c.bg, color: c.color, border: `1px solid ${c.border}` }}>
            {type}
        </span>
    )
}
