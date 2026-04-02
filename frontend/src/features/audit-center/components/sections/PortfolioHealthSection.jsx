import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function PortfolioHealthSection({ data }) {
    if (!data?.portfolios?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak portfelowych strategii.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.portfolios.map((p, pi) => (
                <div key={pi} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 8 }}>Portfolio {p.portfolio_id} — {p.bidding_strategy} ({p.campaign_count} kampanii)</div>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                        <MetricPill label="Koszt" value={`$${p.total_cost_usd}`} />
                        <MetricPill label="Konwersje" value={p.total_conversions} />
                        <MetricPill label="Wartość" value={`$${p.total_value_usd}`} />
                    </div>
                    {p.issues?.length > 0 && p.issues.map((iss, ii) => (
                        <div key={ii} style={{ fontSize: 11, color: iss.severity === 'HIGH' ? C.danger : C.warning, marginBottom: 4 }}>⚠ {iss.detail}</div>
                    ))}
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: B.subtle }}>
                            {['Kampania', 'Koszt', 'Konwersje', 'Wartość', '% wydatków'].map(h =>
                                <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                            )}
                        </tr></thead>
                        <tbody>
                            {p.campaigns.map((c, ci) => (
                                <tr key={ci} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary }}>{c.campaign_name}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>${c.cost_usd}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.conversions}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>${c.value_usd}</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.spend_share_pct > 70 ? C.danger : C.w80 }}>{c.spend_share_pct}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}
        </div>
    )
}
