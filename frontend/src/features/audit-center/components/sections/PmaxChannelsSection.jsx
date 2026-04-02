import { useState } from 'react'
import { LineChart, Line, ResponsiveContainer, XAxis, Tooltip, CartesianGrid } from 'recharts'
import { TH, TD, TD_DIM, CHANNEL_COLORS } from '../../../../constants/designTokens'

export default function PmaxChannelsSection({ data, trends }) {
    const [view, setView] = useState('table')
    if (!data?.channels?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: C.w40 }}>Brak danych o kanalach PMax.</div>
    const hasTrends = trends?.trends?.length > 0
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {hasTrends && (
                <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
                    {[{ key: 'table', label: 'Tabela' }, { key: 'trend', label: 'Trend' }].map(t => (
                        <button key={t.key} onClick={() => setView(t.key)} style={{
                            padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500, cursor: 'pointer',
                            background: view === t.key ? 'rgba(79,142,247,0.12)' : 'transparent',
                            color: view === t.key ? C.accentBlue : C.w40,
                            border: view === t.key ? '1px solid rgba(79,142,247,0.3)' : `1px solid ${C.w08}`,
                        }}>{t.label}</button>
                    ))}
                </div>
            )}
            {view === 'table' ? (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: B.subtle }}>
                        {['Kanal', 'Klikniecia', 'Koszt', 'Konwersje', '% kosztow', '% konwersji'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Kanal' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.channels.map((ch, i) => (
                            <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: C.textPrimary }}>{ch.network_type}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{ch.clicks?.toLocaleString('pl-PL')}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{(ch.cost_micros / 1e6).toFixed(0)} zl</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{ch.conversions?.toFixed(1)}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{ch.cost_share_pct?.toFixed(1)}%</td>
                                <td style={{ ...TD_DIM, textAlign: 'right', color: ch.cost_share_pct > 60 && ch.conv_share_pct < 30 ? C.danger : undefined }}>{ch.conv_share_pct?.toFixed(1)}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <div>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
                        {trends.channels.map(ch => (
                            <div key={ch} className="flex items-center gap-1" style={{ fontSize: 10, color: C.w50 }}>
                                <div style={{ width: 8, height: 8, borderRadius: 2, background: CHANNEL_COLORS[ch] || '#64748B' }} />
                                {ch}
                            </div>
                        ))}
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={trends.trends} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                            <XAxis
                                dataKey="date"
                                tickFormatter={v => { const d = new Date(v); return `${d.getDate()}.${(d.getMonth()+1).toString().padStart(2,'0')}` }}
                                tick={{ fontSize: 9, fill: C.w20 }}
                                axisLine={false} tickLine={false}
                                interval="preserveStartEnd"
                            />
                            <Tooltip
                                contentStyle={{ background: C.surfaceElevated, border: B.hover, borderRadius: 8, fontSize: 11 }}
                                labelFormatter={v => { const d = new Date(v); return `${d.getDate()}.${(d.getMonth()+1).toString().padStart(2,'0')}` }}
                            />
                            {trends.channels.map(ch => (
                                <Line key={ch} type="monotone" dataKey={`${ch}_cost`} stroke={CHANNEL_COLORS[ch] || '#64748B'} strokeWidth={1.5} dot={false} name={`${ch} koszt`} />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    )
}
