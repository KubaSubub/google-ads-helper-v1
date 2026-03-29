import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function ScalingSection({ data }) {
    if (!data?.opportunities?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak okazji do skalowania.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Wartość', '% konta', 'Lost IS (budget)', 'Lost IS (rank)', 'Potencjał'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.opportunities.map((o, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${o.value_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{o.value_pct?.toFixed(1)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: o.lost_budget_is > 20 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{o.lost_budget_is?.toFixed(0)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: o.lost_rank_is > 20 ? '#FBBF24' : 'rgba(255,255,255,0.8)' }}>{o.lost_rank_is?.toFixed(0)}%</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: '#4ADE80' }}>~${o.incremental_value_est?.toFixed(0)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
