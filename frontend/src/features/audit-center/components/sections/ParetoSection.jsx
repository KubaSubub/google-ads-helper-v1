import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function ParetoSection({ data }) {
    if (!data?.campaign_pareto?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych do analizy Pareto.</div>
    const { campaign_pareto, summary } = data
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {summary?.campaign_concentration && (
                <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.15)', marginBottom: 16, fontSize: 12, color: '#4F8EF7' }}>
                    {summary.campaign_concentration}
                </div>
            )}
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Wartość', '% total', 'Kumulat.', 'Koszt', 'Konw.', 'Typ'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {campaign_pareto.items.map((item, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: item.tag === 'HERO' ? 'rgba(74,222,128,0.03)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${item.conv_value_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: item.tag === 'HERO' ? '#4ADE80' : 'rgba(255,255,255,0.5)' }}>{item.pct_of_total?.toFixed(1)}%</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.cumulative_pct?.toFixed(1)}%</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${item.cost_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{item.conversions?.toFixed(1)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontFamily: 'inherit' }}>
                                <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                    background: item.tag === 'HERO' ? 'rgba(74,222,128,0.1)' : 'rgba(255,255,255,0.05)',
                                    color: item.tag === 'HERO' ? '#4ADE80' : 'rgba(255,255,255,0.4)',
                                    border: `1px solid ${item.tag === 'HERO' ? 'rgba(74,222,128,0.2)' : 'rgba(255,255,255,0.08)'}`,
                                }}>{item.tag === 'HERO' ? 'Hero' : 'Tail'}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
