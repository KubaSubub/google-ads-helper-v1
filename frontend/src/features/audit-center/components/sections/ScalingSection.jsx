import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function ScalingSection({ data }) {
    if (!data?.opportunities?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak okazji do skalowania.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: B.subtle }}>
                    {['Kampania', 'Wartość', '% konta', 'Lost IS (budget)', 'Lost IS (rank)', 'Potencjał'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.opportunities.map((o, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${o.value_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{o.value_pct?.toFixed(1)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: o.lost_budget_is > 20 ? C.danger : C.w80 }}>{o.lost_budget_is?.toFixed(0)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: o.lost_rank_is > 20 ? C.warning : C.w80 }}>{o.lost_rank_is?.toFixed(0)}%</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: C.success }}>~${o.incremental_value_est?.toFixed(0)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
