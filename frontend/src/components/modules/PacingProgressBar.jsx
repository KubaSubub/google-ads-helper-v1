export default function PacingProgressBar({ pct, color, height = 4, style: extraStyle }) {
    const radius = Math.floor(height / 2)
    return (
        <div style={{ height, borderRadius: radius, background: 'rgba(255,255,255,0.06)', ...extraStyle }}>
            <div style={{
                height: '100%',
                borderRadius: radius,
                background: color,
                width: `${Math.min(pct ?? 0, 100)}%`,
                transition: 'width 0.3s',
            }} />
        </div>
    )
}
