import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function SmartBiddingHealthSection({ data }) {
    if (!data?.campaigns?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak kampanii Smart Bidding lub wszystkie zdrowe.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <MetricPill label="Zdrowe" value={data.summary?.healthy || 0} color="#4ADE80" />
                <MetricPill label="Niski wolumen" value={data.summary?.low_volume || 0} color="#FBBF24" />
                <MetricPill label="Krytyczne" value={data.summary?.critical || 0} color="#F87171" />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: B.subtle }}>
                    {['Kampania', 'Strategia', 'Konw. / 30d', 'Min.', 'Status'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.campaigns.map((c, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${C.w04}`, background: c.status === 'CRITICAL' ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.bidding_strategy}</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: c.status === 'HEALTHY' ? C.success : c.status === 'CRITICAL' ? C.danger : C.warning }}>{c.conversions_30d?.toFixed(1)}</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.min_recommended}</td>
                            <td style={{ ...TD, textAlign: 'right', fontFamily: 'inherit' }}>
                                <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                    background: c.status === 'HEALTHY' ? C.successBg : c.status === 'CRITICAL' ? C.dangerBg : C.warningBg,
                                    color: c.status === 'HEALTHY' ? C.success : c.status === 'CRITICAL' ? C.danger : C.warning,
                                    border: `1px solid ${c.status === 'HEALTHY' ? C.successBorder : c.status === 'CRITICAL' ? C.dangerBorder : C.warningBorder}`,
                                }}>{c.status === 'HEALTHY' ? 'Zdrowa' : c.status === 'CRITICAL' ? 'Krytyczna' : 'Niski wolumen'}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
