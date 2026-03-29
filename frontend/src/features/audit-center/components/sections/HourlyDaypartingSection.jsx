import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function HourlyDaypartingSection({ data }) {
    if (!data?.hours?.length) return null
    const maxConv = Math.max(...data.hours.map(h => h.conversions))
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 3, marginBottom: 12 }}>
                {data.hours.map(h => {
                    const intensity = maxConv > 0 ? h.conversions / maxConv : 0
                    const isBusinessHour = h.hour >= 9 && h.hour <= 18
                    return (
                        <div key={h.hour} title={`${h.hour_label}: ${h.clicks} klik, ${h.conversions} konw, CPA ${h.cpa > 0 ? h.cpa.toFixed(0) + ' zł' : '—'}`}
                            style={{
                                height: 56, borderRadius: 6, cursor: 'default',
                                background: `rgba(79,142,247,${0.08 + intensity * 0.72})`,
                                border: `1px solid ${isBusinessHour ? 'rgba(79,142,247,0.2)' : 'rgba(255,255,255,0.05)'}`,
                                display: 'flex', flexDirection: 'column',
                                alignItems: 'center', justifyContent: 'flex-end',
                                paddingBottom: 4, position: 'relative',
                            }}>
                            {h.conversions > 0 && (
                                <span style={{ fontSize: 8, color: '#4ADE80', fontWeight: 600, marginBottom: 1 }}>
                                    {h.conversions.toFixed(0)}
                                </span>
                            )}
                            <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.5)' }}>
                                {h.hour}
                            </span>
                        </div>
                    )
                })}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>Godzina</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CTR</th>
                        <th style={TH}>CPA</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>ROAS</th>
                    </tr>
                </thead>
                <tbody>
                    {data.hours.filter(h => h.clicks > 0).map(h => {
                        const isBizHour = h.hour >= 9 && h.hour <= 18
                        return (
                            <tr key={h.hour} style={{
                                borderBottom: '1px solid rgba(255,255,255,0.04)',
                                background: isBizHour ? 'rgba(79,142,247,0.03)' : 'transparent',
                            }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500 }}>{h.hour_label}</td>
                                <td style={TD}>{h.clicks.toLocaleString('pl-PL')}</td>
                                <td style={TD}>{h.cost_usd.toFixed(2)} zł</td>
                                <td style={TD}>{h.conversions.toFixed(1)}</td>
                                <td style={TD_DIM}>{h.ctr}%</td>
                                <td style={TD}>{h.cpa > 0 ? `${h.cpa.toFixed(0)} zł` : '—'}</td>
                                <td style={TD_DIM}>{h.cvr}%</td>
                                <td style={TD}>{h.roas.toFixed(2)}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}
