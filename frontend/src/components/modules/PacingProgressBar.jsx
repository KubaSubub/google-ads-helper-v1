export default function PacingProgressBar({ pct, color, height = 4 }) {
    return (
        <div style={{ height, borderRadius: height / 2, background: 'rgba(255,255,255,0.06)' }}>
            <div style={{
                height: '100%',
                borderRadius: height / 2,
                background: color,
                width: `${Math.min(pct ?? 0, 100)}%`,
                transition: 'width 0.3s',
            }} />
        </div>
    )
}
