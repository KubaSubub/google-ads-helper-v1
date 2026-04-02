import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function LearningStatusSection({ data }) {
    if (!data?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak kampanii Smart Bidding.</div>
    const statusColor = { STABLE: C.success, LEARNING: C.warning, EXTENDED_LEARNING: C.danger, STUCK_LEARNING: C.danger }
    const statusLabel = { STABLE: 'Stabilna', LEARNING: 'Nauka', EXTENDED_LEARNING: 'Przedłużona', STUCK_LEARNING: 'Zablokowana' }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <MetricPill label="Smart Bidding" value={data.total_smart_bidding} />
                <MetricPill label="W nauce" value={data.learning_count} color={data.learning_count > 0 ? C.warning : C.success} />
                <MetricPill label="Zablokowane" value={data.stuck_count} color={data.stuck_count > 0 ? C.danger : C.success} />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: B.subtle }}>
                    {['Kampania', 'Strategia', 'Status', 'Dni w nauce'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.items.map((item, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.campaign_name}</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.bidding_strategy}</td>
                            <td style={{ ...TD, textAlign: 'right' }}><span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, color: statusColor[item.status], background: `${statusColor[item.status]}15` }}>{statusLabel[item.status]}</span></td>
                            <td style={{ ...TD, textAlign: 'right' }}>{item.days_in_learning ?? '—'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
