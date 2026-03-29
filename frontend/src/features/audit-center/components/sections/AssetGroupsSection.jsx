import { TH, TD, TD_DIM, AD_STRENGTH_COLOR } from '../../../../constants/designTokens'

export default function AssetGroupsSection({ data }) {
    if (!data?.asset_groups?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak grup zasobow PMax.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Grupa zasobow', 'Sila reklamy', 'Koszt', 'Konwersje', 'CPA', 'ROAS', 'Zasoby'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa zasobow' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.asset_groups.map((ag, i) => {
                        const cost = ag.total_cost_micros / 1e6
                        const cpa = ag.total_conversions > 0 ? cost / ag.total_conversions : null
                        const roas = cost > 0 ? (ag.total_conversion_value_micros || 0) / 1e6 / cost : null
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{ag.name}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>
                                    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, background: `${AD_STRENGTH_COLOR[ag.ad_strength] || 'rgba(255,255,255,0.1)'}22`, color: AD_STRENGTH_COLOR[ag.ad_strength] || 'rgba(255,255,255,0.5)' }}>{ag.ad_strength || '—'}</span>
                                </td>
                                <td style={{ ...TD, textAlign: 'right' }}>{cost.toFixed(0)} zl</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{ag.total_conversions?.toFixed(1)}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{cpa != null ? `${cpa.toFixed(0)} zl` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{roas != null ? `${roas.toFixed(2)}x` : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{ag.asset_count || 0}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}
