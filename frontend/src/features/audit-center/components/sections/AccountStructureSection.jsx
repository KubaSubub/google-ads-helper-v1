import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'
import MatchBadge from '../../../../components/shared/MatchBadge'

export default function AccountStructureSection({ data }) {
    if (!data) return null
    const { issues, oversized_ad_groups, mixed_match_ad_groups, cannibalized_keywords } = data
    if (!issues?.length) {
        return (
            <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>
                Brak wykrytych problemów strukturalnych
            </div>
        )
    }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
                {issues.map(issue => (
                    <MetricPill key={issue.type} label={
                        issue.type === 'cannibalization' ? 'Kanibalizacja' :
                        issue.type === 'oversized_ad_groups' ? 'Zbyt duże grupy' : 'Mieszane dopas.'
                    } value={issue.count} color={issue.severity === 'HIGH' ? C.danger : C.warning} />
                ))}
            </div>

            {cannibalized_keywords?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: C.w50, marginBottom: 8 }}>
                        Kanibalizacja słów kluczowych ({cannibalized_keywords.length})
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: B.subtle }}>
                                <th style={TH}>Słowo kluczowe</th>
                                <th style={TH}>Dopasowanie</th>
                                <th style={TH}>Wystąpień</th>
                                <th style={TH}>Łączny koszt</th>
                                <th style={TH}>Lokalizacje</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cannibalized_keywords.slice(0, 15).map((item, i) => (
                                <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.danger }}>{item.keyword_text}</td>
                                    <td style={{ ...TD, fontFamily: 'inherit' }}><MatchBadge type={item.match_type} /></td>
                                    <td style={TD}>{item.occurrences}</td>
                                    <td style={TD}>{item.total_cost_usd.toFixed(2)} zł</td>
                                    <td style={{ ...TD_DIM, fontSize: 10 }}>
                                        {item.locations.map((l, j) => (
                                            <div key={j}>{l.campaign_name} → {l.ad_group_name}</div>
                                        ))}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {oversized_ad_groups?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: C.w50, marginBottom: 8 }}>
                        Zbyt duże grupy reklam — &gt;20 słów kluczowych ({oversized_ad_groups.length})
                    </div>
                    {oversized_ad_groups.map((ag, i) => (
                        <div key={i} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '6px 8px', borderRadius: 6,
                            background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                        }}>
                            <span style={{ fontSize: 12, color: C.w70 }}>
                                {ag.campaign_name} → {ag.ad_group_name}
                            </span>
                            <span style={{ fontSize: 12, fontFamily: 'monospace', color: C.warning }}>
                                {ag.keyword_count} słów
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {mixed_match_ad_groups?.length > 0 && (
                <div>
                    <div style={{ fontSize: 11, fontWeight: 500, color: C.w50, marginBottom: 8 }}>
                        Mieszane dopasowania BROAD + EXACT w grupie ({mixed_match_ad_groups.length})
                    </div>
                    {mixed_match_ad_groups.map((ag, i) => (
                        <div key={i} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '6px 8px', borderRadius: 6,
                            background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                        }}>
                            <span style={{ fontSize: 12, color: C.w70 }}>
                                {ag.campaign_name} → {ag.ad_group_name}
                            </span>
                            <div className="flex items-center gap-1">
                                {ag.match_types.map(mt => <MatchBadge key={mt} type={mt} />)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
