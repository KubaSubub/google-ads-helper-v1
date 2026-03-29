import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function NgramSection({ data, ngramSize, setNgramSize }) {
    if (!data?.ngrams) return null
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                {[1, 2, 3].map(n => (
                    <button
                        key={n}
                        onClick={() => setNgramSize(n)}
                        style={{
                            padding: '4px 11px', borderRadius: 999, fontSize: 11, cursor: 'pointer',
                            border: `1px solid ${ngramSize === n ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
                            background: ngramSize === n ? 'rgba(79,142,247,0.18)' : 'transparent',
                            color: ngramSize === n ? '#4F8EF7' : 'rgba(255,255,255,0.4)',
                        }}
                    >
                        {n === 1 ? 'Słowa' : n === 2 ? 'Bigramy' : 'Trigramy'}
                    </button>
                ))}
                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginLeft: 8 }}>{data.total} wyników</span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>N-gram</th>
                        <th style={TH}>Wystąpień</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>CPA</th>
                    </tr>
                </thead>
                <tbody>
                    {data.ngrams.slice(0, 30).map((ng, i) => {
                        const isWaste = ng.conversions === 0 && ng.cost_usd > 10
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: isWaste ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: isWaste ? '#F87171' : '#F0F0F0' }}>{ng.ngram}</td>
                                <td style={TD_DIM}>{ng.occurrences}</td>
                                <td style={TD}>{ng.clicks.toLocaleString('pl-PL')}</td>
                                <td style={TD}>{ng.cost_usd.toFixed(2)} zł</td>
                                <td style={TD}>{ng.conversions.toFixed(1)}</td>
                                <td style={TD_DIM}>{ng.cvr}%</td>
                                <td style={TD}>{ng.cpa > 0 ? `${ng.cpa.toFixed(2)} zł` : '—'}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}
