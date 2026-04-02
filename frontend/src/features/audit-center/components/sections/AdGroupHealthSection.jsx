import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function AdGroupHealthSection({ data }) {
    if (!data?.details?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Wszystkie grupy reklam wyglądają dobrze.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {data.issues.map((iss, i) => (
                    <MetricPill key={i} label={iss.type === 'no_ads' ? 'Brak reklam' : iss.type === 'single_ad' ? '1 reklama' : iss.type === 'too_many_keywords' ? 'Za dużo KW' : iss.type === 'too_few_keywords' ? 'Za mało KW' : 'Brak konw.'}
                        value={iss.count} color={iss.severity === 'HIGH' ? C.danger : iss.severity === 'MEDIUM' ? C.warning : C.accentBlue} />
                ))}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: B.subtle }}>
                    {['Grupa reklam', 'Kampania', 'Reklamy', 'Słowa', 'Koszt', 'Konw.', 'Problemy'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa reklam' || h === 'Kampania' || h === 'Problemy' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.details.map((d, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${C.w04}`, background: d.issues.length >= 2 ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.ad_group_name}</td>
                            <td style={{ ...TD_DIM, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.ads_count < 2 ? C.danger : C.success }}>{d.ads_count}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.keywords_count > 30 || d.keywords_count < 2 ? C.warning : C.w80 }}>{d.keywords_count}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${d.cost_usd}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.conversions === 0 && d.cost_usd >= 50 ? C.danger : C.w80 }}>{d.conversions}</td>
                            <td style={{ ...TD_DIM, textAlign: 'left', fontSize: 11 }}>{d.issues.join(', ')}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
