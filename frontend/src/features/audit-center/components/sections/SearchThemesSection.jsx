export default function SearchThemesSection({ data }) {
    if (!data?.asset_groups?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak sygnalow PMax.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.asset_groups.map((ag, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0', marginBottom: 6 }}>{ag.name}</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {ag.search_themes?.map((t, j) => (
                            <span key={j} style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11, background: 'rgba(79,142,247,0.1)', border: '1px solid rgba(79,142,247,0.2)', color: '#4F8EF7' }}>{t}</span>
                        ))}
                        {ag.audience_signals?.map((a, j) => (
                            <span key={`a-${j}`} style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11, background: 'rgba(123,92,224,0.1)', border: '1px solid rgba(123,92,224,0.2)', color: '#7B5CE0' }}>{a.name} ({a.type})</span>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    )
}
