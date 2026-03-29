import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function LandingPageSection({ data }) {
    if (!data?.pages?.length) return null
    return (
        <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>URL</th>
                        <th style={TH}>Słów kl.</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>CPA</th>
                        <th style={TH}>ROAS</th>
                    </tr>
                </thead>
                <tbody>
                    {data.pages.map((p, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', maxWidth: 300 }}>
                                <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#4F8EF7' }} title={p.url}>
                                    {p.url.replace(/^https?:\/\/(www\.)?/, '').substring(0, 50)}
                                </span>
                            </td>
                            <td style={TD_DIM}>{p.keyword_count}</td>
                            <td style={TD}>{p.clicks.toLocaleString('pl-PL')}</td>
                            <td style={TD}>{p.cost_usd.toFixed(2)} zł</td>
                            <td style={TD}>{p.conversions.toFixed(1)}</td>
                            <td style={TD_DIM}>{p.cvr}%</td>
                            <td style={TD}>{p.cpa > 0 ? `${p.cpa.toFixed(2)} zł` : '—'}</td>
                            <td style={TD}>{p.roas.toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
