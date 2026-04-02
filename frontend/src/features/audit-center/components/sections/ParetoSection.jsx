import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function ParetoSection({ data }) {
    if (!data?.campaign_pareto?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak danych do analizy Pareto.</div>
    const { campaign_pareto, summary } = data
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {summary?.campaign_concentration && (
                <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.15)', marginBottom: 16, fontSize: 12, color: C.accentBlue }}>
                    {summary.campaign_concentration}
                </div>
            )}
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: B.subtle }}>
                    {['Kampania', 'Wartość', '% total', 'Kumulat.', 'Koszt', 'Konw.', 'Typ'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {campaign_pareto.items.map((item, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${C.w04}`, background: item.tag === 'HERO' ? 'rgba(74,222,128,0.03)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${item.conv_value_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: item.tag === 'HERO' ? C.success : C.w50 }}>{item.pct_of_total?.toFixed(1)}%</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.cumulative_pct?.toFixed(1)}%</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${item.cost_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{item.conversions?.toFixed(1)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontFamily: 'inherit' }}>
                                <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                    background: item.tag === 'HERO' ? C.successBg : C.w05,
                                    color: item.tag === 'HERO' ? C.success : C.w40,
                                    border: `1px solid ${item.tag === 'HERO' ? C.successBorder : C.w08}`,
                                }}>{item.tag === 'HERO' ? 'Hero' : 'Tail'}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
