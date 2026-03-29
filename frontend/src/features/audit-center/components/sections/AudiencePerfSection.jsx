import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function AudiencePerfSection({ data }) {
    if (!data?.audiences?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o grupach odbiorcow.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Grupa odbiorcow', 'Typ', 'Koszt', 'Konwersje', 'CPA', 'ROAS', 'Anomalia'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa odbiorcow' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.audiences.map((a, i) => {
                        const cost = a.cost_micros / 1e6
                        const cpa = a.cpa_micros ? a.cpa_micros / 1e6 : null
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{a.audience_name || a.audience_resource_name}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.audience_type || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{cost.toFixed(0)} zl</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.conversions?.toFixed(1)}</td>
                                <td style={{ ...TD, textAlign: 'right', color: a.is_anomaly ? '#F87171' : undefined }}>{cpa != null ? `${cpa.toFixed(0)} zl` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.roas != null ? `${a.roas.toFixed(2)}x` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.is_anomaly ? <span style={{ color: '#F87171', fontWeight: 600 }}>TAK</span> : '—'}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}
