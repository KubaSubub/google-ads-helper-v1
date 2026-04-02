import { TH, TD, TD_DIM } from '../../../../constants/designTokens'
import MetricPill from '../../../../components/shared/MetricPill'

export default function ConversionQualitySection({ data }) {
    if (!data) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak danych konwersji.</div>
    const scoreColor = data.quality_score >= 80 ? C.success : data.quality_score >= 50 ? C.warning : C.danger
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
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: iss.severity === 'HIGH' ? C.dangerBg : iss.severity === 'MEDIUM' ? 'rgba(251,191,36,0.08)' : C.w03, border: `1px solid ${iss.severity === 'HIGH' ? C.dangerBorder : iss.severity === 'MEDIUM' ? C.warningBorder : C.w07}` }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: iss.severity === 'HIGH' ? C.danger : iss.severity === 'MEDIUM' ? C.warning : C.textPrimary }}>{iss.type}</div>
                            <div style={{ fontSize: 11, color: C.w60, marginTop: 2 }}>{iss.detail}</div>
                            {iss.affected?.length > 0 && <div style={{ fontSize: 10, color: C.textMuted, marginTop: 4 }}>{iss.affected.join(', ')}</div>}
                        </div>
                    ))}
                </div>
            )}
            {data.actions?.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: B.subtle }}>
                        {['Nazwa', 'Kategoria', 'Primary', 'Counting', 'Wartość dom.', 'Atrybucja', 'Lookback'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Nazwa' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.actions.map((a, i) => (
                            <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name}</td>
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
