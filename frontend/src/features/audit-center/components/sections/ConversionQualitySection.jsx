import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function ConversionQualitySection({ data }) {
    if (!data) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych konwersji.</div>
    const scoreColor = data.quality_score >= 80 ? '#4ADE80' : data.quality_score >= 50 ? '#FBBF24' : '#F87171'
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <MetricPill label="Quality Score" value={data.quality_score} color={scoreColor} />
                <MetricPill label="Akcji konwersji" value={data.total_actions} />
                <MetricPill label="Primary" value={data.primary_count} />
            </div>
            {data.issues?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    {data.issues.map((iss, i) => (
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: iss.severity === 'HIGH' ? 'rgba(248,113,113,0.08)' : iss.severity === 'MEDIUM' ? 'rgba(251,191,36,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${iss.severity === 'HIGH' ? 'rgba(248,113,113,0.2)' : iss.severity === 'MEDIUM' ? 'rgba(251,191,36,0.2)' : 'rgba(255,255,255,0.07)'}` }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: iss.severity === 'HIGH' ? '#F87171' : iss.severity === 'MEDIUM' ? '#FBBF24' : '#F0F0F0' }}>{iss.type}</div>
                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 }}>{iss.detail}</div>
                            {iss.affected?.length > 0 && <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>{iss.affected.join(', ')}</div>}
                        </div>
                    ))}
                </div>
            )}
            {data.actions?.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Nazwa', 'Kategoria', 'Primary', 'Counting', 'Wartość dom.', 'Atrybucja', 'Lookback'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Nazwa' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.actions.map((a, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.category}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.primary_for_goal ? '✓' : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.counting_type || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.value_default != null ? `$${a.value_default}` : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right', fontSize: 10 }}>{a.attribution_model || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.lookback_days ?? '—'}d</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    )
}
