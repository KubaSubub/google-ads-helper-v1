import { TH, TD, TD_DIM } from '../../../../constants/designTokens'

export default function ExtPerfSection({ data }) {
    if (!data?.by_type?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o wydajnosci rozszerzen.</div>
    const PERF_COLOR = { BEST: '#4ADE80', GOOD: '#4F8EF7', LOW: '#F87171', LEARNING: '#FBBF24' }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Typ rozszerzenia', 'Ilosc', 'Klikniecia', 'Wyswietlenia', 'CTR', 'BEST', 'GOOD', 'LOW'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Typ rozszerzenia' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.by_type.map((t, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{t.asset_type}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.count}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.total_clicks?.toLocaleString('pl-PL')}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.total_impressions?.toLocaleString('pl-PL')}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.avg_ctr?.toFixed(2)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: PERF_COLOR.BEST }}>{t.performance_labels?.BEST || 0}</td>
                            <td style={{ ...TD, textAlign: 'right', color: PERF_COLOR.GOOD }}>{t.performance_labels?.GOOD || 0}</td>
                            <td style={{ ...TD, textAlign: 'right', color: PERF_COLOR.LOW }}>{t.performance_labels?.LOW || 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
