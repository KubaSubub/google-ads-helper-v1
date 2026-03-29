import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function AdGroupHealthSection({ data }) {
    if (!data?.details?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Wszystkie grupy reklam wyglądają dobrze.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {data.issues.map((iss, i) => (
                    <MetricPill key={i} label={iss.type === 'no_ads' ? 'Brak reklam' : iss.type === 'single_ad' ? '1 reklama' : iss.type === 'too_many_keywords' ? 'Za dużo KW' : iss.type === 'too_few_keywords' ? 'Za mało KW' : 'Brak konw.'}
                        value={iss.count} color={iss.severity === 'HIGH' ? '#F87171' : iss.severity === 'MEDIUM' ? '#FBBF24' : '#4F8EF7'} />
                ))}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Grupa reklam', 'Kampania', 'Reklamy', 'Słowa', 'Koszt', 'Konw.', 'Problemy'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa reklam' || h === 'Kampania' || h === 'Problemy' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.details.map((d, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: d.issues.length >= 2 ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.ad_group_name}</td>
                            <td style={{ ...TD_DIM, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.ads_count < 2 ? '#F87171' : '#4ADE80' }}>{d.ads_count}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.keywords_count > 30 || d.keywords_count < 2 ? '#FBBF24' : 'rgba(255,255,255,0.8)' }}>{d.keywords_count}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${d.cost_usd}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.conversions === 0 && d.cost_usd >= 50 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{d.conversions}</td>
                            <td style={{ ...TD_DIM, textAlign: 'left', fontSize: 11 }}>{d.issues.join(', ')}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
