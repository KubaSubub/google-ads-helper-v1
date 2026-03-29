export default function DaypartingSection({ data }) {
    if (!data?.days?.length) return null
    const maxClicks = Math.max(...data.days.map(d => d.clicks))
    const maxConv = Math.max(...data.days.map(d => d.conversions))
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
                {data.days.map(d => {
                    const barH = maxClicks > 0 ? (d.clicks / maxClicks * 48) : 0
                    const convBarH = maxConv > 0 ? (d.conversions / maxConv * 48) : 0
                    const isWeekend = d.day_of_week >= 5
                    return (
                        <div key={d.day_of_week} style={{
                            padding: 10, borderRadius: 8, textAlign: 'center',
                            background: isWeekend ? 'rgba(248,113,113,0.05)' : 'rgba(255,255,255,0.03)',
                            border: `1px solid ${isWeekend ? 'rgba(248,113,113,0.15)' : 'rgba(255,255,255,0.07)'}`,
                        }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: isWeekend ? '#F87171' : '#F0F0F0', marginBottom: 8 }}>
                                {d.day_name}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: 3, height: 52, alignItems: 'flex-end', marginBottom: 8 }}>
                                <div style={{ width: 14, height: barH, background: '#4F8EF7', borderRadius: 3, minHeight: 2 }} title={`Kliknięcia: ${d.clicks}`} />
                                <div style={{ width: 14, height: convBarH, background: '#4ADE80', borderRadius: 3, minHeight: 2 }} title={`Konwersje: ${d.conversions}`} />
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>{d.avg_clicks} klik/dz</div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>{d.avg_conversions.toFixed(1)} conv/dz</div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>CPA {d.cpa.toFixed(0)} zł</div>
                        </div>
                    )
                })}
            </div>
            <div className="flex items-center gap-4" style={{ marginTop: 10, fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: '#4F8EF7' }} /> Kliknięcia
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: '#4ADE80' }} /> Konwersje
                </span>
            </div>
        </div>
    )
}
