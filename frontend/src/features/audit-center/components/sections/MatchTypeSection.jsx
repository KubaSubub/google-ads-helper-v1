import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MatchBadge from '../../../../components/shared/MatchBadge'

export default function MatchTypeSection({ data }) {
    if (!data?.match_types?.length) return null
    return (
        <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>Dopasowanie</th>
                        <th style={TH}>Słów kl.</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CTR</th>
                        <th style={TH}>CPC</th>
                        <th style={TH}>CPA</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>ROAS</th>
                        <th style={TH}>Udział %</th>
                    </tr>
                </thead>
                <tbody>
                    {data.match_types.map(mt => (
                        <tr key={mt.match_type} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit' }}><MatchBadge type={mt.match_type} /></td>
                            <td style={TD_DIM}>{mt.keyword_count}</td>
                            <td style={TD}>{mt.clicks.toLocaleString('pl-PL')}</td>
                            <td style={TD}>{mt.cost_usd.toFixed(2)} zł</td>
                            <td style={TD}>{mt.conversions.toFixed(1)}</td>
                            <td style={TD_DIM}>{mt.ctr}%</td>
                            <td style={TD_DIM}>{mt.cpc.toFixed(2)} zł</td>
                            <td style={TD}>{mt.cpa > 0 ? `${mt.cpa.toFixed(2)} zł` : '—'}</td>
                            <td style={TD_DIM}>{mt.cvr}%</td>
                            <td style={TD}>{mt.roas.toFixed(2)}</td>
                            <td style={TD_DIM}>{mt.cost_share_pct}%</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
