import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

function StatusBadge({ status }) {
    const config = {
        OK:                    { label: 'OK',        color: C.success },
        UPGRADE_RECOMMENDED:   { label: 'Upgrade',   color: C.warning },
        CHANGE_RECOMMENDED:    { label: 'Zmień!',    color: C.danger },
    }
    const c = config[status] || { label: status, color: C.w30 }
    return (
        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
            background: `${c.color}15`, color: c.color, border: `1px solid ${c.color}30` }}>
            {c.label}
        </span>
    )
}

export default function BiddingAdvisorSection({ data }) {
    if (!data?.campaigns?.length) return null
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
                <MetricPill label="OK" value={data.summary.ok} color="#4ADE80" />
                <MetricPill label="Upgrade" value={data.summary.upgrade} color="#FBBF24" />
                <MetricPill label="Do zmiany" value={data.summary.change} color="#F87171" />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: B.subtle }}>
                        <th style={TH}>Kampania</th>
                        <th style={TH}>Obecna strategia</th>
                        <th style={TH}>Rekomendacja</th>
                        <th style={TH}>Konw. / 30d</th>
                        <th style={TH}>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {data.campaigns.map(c => (
                        <tr key={c.campaign_id} style={{
                            borderBottom: `1px solid ${C.w04}`,
                            background: c.status === 'CHANGE_RECOMMENDED' ? 'rgba(248,113,113,0.04)' :
                                        c.status === 'UPGRADE_RECOMMENDED' ? 'rgba(251,191,36,0.04)' : 'transparent',
                        }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {c.campaign_name}
                            </td>
                            <td style={TD_DIM}>{c.current_strategy}</td>
                            <td style={{ ...TD, color: c.status !== 'OK' ? C.accentBlue : C.w50 }}>
                                {c.recommended_strategy}
                            </td>
                            <td style={TD}>{c.conversions_30d}</td>
                            <td style={{ ...TD, fontFamily: 'inherit' }}><StatusBadge status={c.status} /></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
