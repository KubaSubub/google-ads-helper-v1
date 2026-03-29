export default function MetricPill({ label, value, color }) {
    return (
        <div style={{
            display: 'inline-flex', flexDirection: 'column', alignItems: 'center',
            padding: '8px 14px', borderRadius: 10,
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
        }}>
            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 2 }}>{label}</span>
            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: color || '#F0F0F0' }}>{value}</span>
        </div>
    )
}
