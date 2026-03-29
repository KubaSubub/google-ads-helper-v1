import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function DemographicsSection({ data }) {
    if (!data) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych demograficznych.</div>
    const BreakdownTable = ({ items, title }) => {
        if (!items?.length) return null
        return (
            <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.5)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</div>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Segment', 'Kliknięcia', 'Koszt', 'Konwersje', 'CPA', 'ROAS', '% kosztów'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Segment' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {items.map((item, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{item.segment}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{item.clicks?.toLocaleString('pl-PL')}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>${item.cost_usd}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{item.conversions}</td>
                                <td style={{ ...TD, textAlign: 'right', color: item.cpa_usd && data.avg_cpa_usd && item.cpa_usd > data.avg_cpa_usd * 2 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{item.cpa_usd != null ? `$${item.cpa_usd}` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{item.roas != null ? `${item.roas}x` : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.cost_share_pct}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        )
    }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.anomalies?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    {data.anomalies.map((a, i) => (
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)' }}>
                            <span style={{ fontSize: 12, fontWeight: 600, color: '#F87171' }}>Anomalia: </span>
                            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>{a.segment} — CPA ${a.cpa_usd} ({a.multiplier}x średniej ${a.avg_cpa_usd})</span>
                        </div>
                    ))}
                </div>
            )}
            <BreakdownTable items={data.age_breakdown} title="Przedziały wiekowe" />
            <BreakdownTable items={data.gender_breakdown} title="Płeć" />
        </div>
    )
}
