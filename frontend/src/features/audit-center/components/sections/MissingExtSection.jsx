import { TH, TD } from '../../../../constants/designTokens'

export default function MissingExtSection({ data }) {
    if (!data?.campaigns?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o rozszerzeniach.</div>
    const Check = ({ ok }) => <span style={{ color: ok ? '#4ADE80' : '#F87171', fontWeight: 700, fontSize: 14 }}>{ok ? '\u2713' : '\u2717'}</span>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Sitelinks', 'Callouts', 'Snippets', 'Call', 'Score'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'center' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.campaigns.map((c, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{c.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.sitelink_count >= 4} /> {c.sitelink_count}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.callout_count >= 4} /> {c.callout_count}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.snippet_count >= 1} /> {c.snippet_count}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.has_call} /></td>
                            <td style={{ ...TD, textAlign: 'center' }}>
                                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, background: c.extension_score >= 80 ? 'rgba(74,222,128,0.1)' : c.extension_score >= 50 ? 'rgba(251,191,36,0.1)' : 'rgba(248,113,113,0.1)', color: c.extension_score >= 80 ? '#4ADE80' : c.extension_score >= 50 ? '#FBBF24' : '#F87171' }}>{c.extension_score}%</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
