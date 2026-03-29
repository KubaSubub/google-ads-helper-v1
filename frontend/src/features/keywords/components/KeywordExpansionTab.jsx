import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

import EmptyState from '../../../components/EmptyState'
import { ErrorMessage, TH_STYLE } from '../../../components/UI'
import { getKeywordExpansion } from '../../../api'
import { MATCH_COLORS } from './shared'

export default function KeywordExpansionTab({ selectedClientId }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!selectedClientId) return
        setLoading(true)
        getKeywordExpansion(selectedClientId, { days: 30, min_clicks: 3 })
            .then(res => setData(res))
            .catch(err => setError(err.message))
            .finally(() => setLoading(false))
    }, [selectedClientId])

    if (loading) return <div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={20} className="animate-spin" style={{ color: '#4F8EF7' }} /></div>
    if (error) return <ErrorMessage message={error} />
    if (!data?.suggestions?.length) return <EmptyState message="Brak sugestii — wszystkie dobrze performujące frazy są już dodane jako słowa kluczowe" />

    return (
        <div>
            {/* Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10, marginBottom: 16 }}>
                {[
                    { label: 'Niezmapowane frazy', value: data.summary.total_unmapped_terms },
                    { label: 'Sugestie', value: data.summary.total_suggestions },
                    { label: 'Wysoki priorytet', value: data.summary.high_priority },
                    { label: 'Obecne słowa', value: data.summary.existing_keywords },
                ].map(({ label, value }) => (
                    <div key={label} className="v2-card" style={{ padding: '12px 14px' }}>
                        <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
                        <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0' }}>{value}</div>
                    </div>
                ))}
            </div>

            {/* Suggestions table */}
            <div className="v2-card" style={{ padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                        <tr>
                            {['Fraza', 'Kliknięcia', 'Wyświetlenia', 'CTR', 'Koszt', 'Konw.', 'CPA', 'Priorytet', 'Sugerowany typ'].map(h => (
                                <th key={h} style={{ ...TH_STYLE, textAlign: h === 'Fraza' ? 'left' : 'right' }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.suggestions.map((s, i) => {
                            const priorityColor = s.priority_score >= 50 ? '#4ADE80' : s.priority_score >= 30 ? '#FBBF24' : 'rgba(255,255,255,0.4)'
                            const matchColor = MATCH_COLORS[s.suggested_match_type] || MATCH_COLORS.BROAD
                            return (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ padding: '8px 12px', color: '#F0F0F0', fontWeight: 500, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.search_term}</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#F0F0F0' }}>{s.clicks}</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{s.impressions?.toLocaleString('pl-PL')}</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{s.ctr_pct}%</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{s.cost_usd} zł</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{s.conversions}</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{s.cpa_usd != null ? `${s.cpa_usd} zł` : '—'}</td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                                        <span style={{ fontSize: 11, fontWeight: 600, color: priorityColor }}>{s.priority_score}</span>
                                    </td>
                                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                                        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: matchColor.bg, color: matchColor.color, border: `1px solid ${matchColor.border}` }}>
                                            {s.suggested_match_type}
                                        </span>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
