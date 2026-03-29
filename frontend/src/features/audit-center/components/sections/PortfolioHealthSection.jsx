import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function PortfolioHealthSection({ data }) {
    if (!data?.portfolios?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak portfelowych strategii.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.portfolios.map((p, pi) => (
                <div key={pi} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', marginBottom: 8 }}>Portfolio {p.portfolio_id} — {p.bidding_strategy} ({p.campaign_count} kampanii)</div>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                        <MetricPill label="Koszt" value={`$${p.total_cost_usd}`} />
                        <MetricPill label="Konwersje" value={p.total_conversions} />
                        <MetricPill label="Wartość" value={`$${p.total_value_usd}`} />
                    </div>
                    {p.issues?.length > 0 && p.issues.map((iss, ii) => (
                        <div key={ii} style={{ fontSize: 11, color: iss.severity === 'HIGH' ? '#F87171' : '#FBBF24', marginBottom: 4 }}>⚠ {iss.detail}</div>
                    ))}
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                            {['Kampania', 'Koszt', 'Konwersje', 'Wartość', '% wydatków'].map(h =>
                                <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                            )}
                        </tr></thead>
                        <tbody>
                            {p.campaigns.map((c, ci) => (
                                <tr key={ci} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{c.campaign_name}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>${c.cost_usd}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.conversions}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>${c.value_usd}</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.spend_share_pct > 70 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{c.spend_share_pct}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}
        </div>
    )
}
