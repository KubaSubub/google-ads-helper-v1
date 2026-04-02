import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function TargetVsActualSection({ data }) {
    if (!data?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak kampanii Smart Bidding z celami.</div>
    const statusColor = { ON_TARGET: C.success, OVER_TARGET: C.danger, UNDER_TARGET: C.warning, NO_TARGET: C.w40 }
    const statusLabel = { ON_TARGET: 'W celu', OVER_TARGET: 'Powyżej', UNDER_TARGET: 'Poniżej', NO_TARGET: 'Brak celu' }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: B.subtle }}>
                    {['Kampania', 'Strategia', 'Cel', 'Aktualny', 'Odchylenie', 'Status'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.items.map((item, i) => {
                        const isCpa = item.bidding_strategy?.includes('CPA') || item.bidding_strategy === 'MAXIMIZE_CONVERSIONS'
                        const target = isCpa ? (item.target_cpa_usd ? `$${item.target_cpa_usd}` : '—') : (item.target_roas ? `${item.target_roas}x` : '—')
                        const actual = isCpa ? (item.actual_cpa_usd ? `$${item.actual_cpa_usd}` : '—') : (item.actual_roas ? `${item.actual_roas}x` : '—')
                        return (
                            <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.campaign_name}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.bidding_strategy}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{target}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{actual}</td>
                                <td style={{ ...TD, textAlign: 'right', color: statusColor[item.status], fontWeight: 600 }}>{item.deviation_pct != null ? `${item.deviation_pct > 0 ? '+' : ''}${item.deviation_pct}%` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}><span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, color: statusColor[item.status], background: `${statusColor[item.status]}15` }}>{statusLabel[item.status]}</span></td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}
