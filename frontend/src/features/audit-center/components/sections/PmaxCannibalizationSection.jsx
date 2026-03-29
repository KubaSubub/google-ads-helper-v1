import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import { AlertTriangle } from 'lucide-react'

export default function PmaxCannibalizationSection({ data }) {
    if (!data?.overlapping_terms?.length && !data?.recommendations?.length) {
        return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak kanibalizacji PMax ↔ Search.</div>
    }
    const s = data.summary || {}
    const PRIO_COLORS = { high: { bg: 'rgba(248,113,113,0.1)', text: '#F87171' }, medium: { bg: 'rgba(251,191,36,0.1)', text: '#FBBF24' } }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
                {[
                    { label: 'Pokrywające się frazy', value: s.total_overlap, color: '#4F8EF7' },
                    { label: 'Koszt kanibalizacji', value: `${(s.overlap_cost_usd || 0).toFixed(0)} zł`, color: '#F87171' },
                    { label: 'Search lepszy', value: s.search_better_count, color: '#4ADE80' },
                    { label: 'PMax lepszy', value: s.pmax_better_count, color: '#7B5CE0' },
                ].map(c => (
                    <div key={c.label} style={{ padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, borderLeft: `3px solid ${c.color}` }}>
                        <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{c.label}</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: c.color, fontFamily: 'Syne' }}>{c.value}</div>
                    </div>
                ))}
            </div>
            {data.recommendations?.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                    {data.recommendations.map((r, i) => {
                        const pc = PRIO_COLORS[r.priority] || PRIO_COLORS.medium
                        return (
                            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: pc.bg, border: `1px solid ${pc.text}20` }}>
                                <AlertTriangle size={13} style={{ color: pc.text, marginTop: 2, flexShrink: 0 }} />
                                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>{r.message}</span>
                            </div>
                        )
                    })}
                </div>
            )}
            {data.overlapping_terms?.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Fraza', 'Search klik.', 'Search koszt', 'Search CPA', 'PMax klik.', 'PMax koszt', 'PMax CPA', 'Zwycięzca'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Fraza' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.overlapping_terms.map((t, i) => {
                            const winColor = t.winner === 'SEARCH' ? '#4ADE80' : t.winner === 'PMAX' ? '#7B5CE0' : 'rgba(255,255,255,0.3)'
                            const winLabel = t.winner === 'SEARCH' ? 'Search' : t.winner === 'PMAX' ? 'PMax' : 'Remis'
                            return (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.search_term}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.search.clicks}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.search.cost_usd.toFixed(0)} zł</td>
                                    <td style={{ ...TD, textAlign: 'right', color: t.winner === 'SEARCH' ? '#4ADE80' : undefined }}>{t.search.cpa != null ? `${t.search.cpa.toFixed(0)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.pmax.clicks}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.pmax.cost_usd.toFixed(0)} zł</td>
                                    <td style={{ ...TD, textAlign: 'right', color: t.winner === 'PMAX' ? '#7B5CE0' : undefined }}>{t.pmax.cpa != null ? `${t.pmax.cpa.toFixed(0)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>
                                        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: `${winColor}15`, color: winColor }}>{winLabel}</span>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </div>
    )
}
