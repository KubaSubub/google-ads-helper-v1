import { ChevronDown, ChevronRight } from 'lucide-react'

export default function SectionHeader({ icon: Icon, title, subtitle, open, onToggle }) {
    return (
        <button
            onClick={onToggle}
            style={{
                display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                padding: '12px 16px', cursor: 'pointer',
                background: 'transparent', border: 'none', textAlign: 'left',
            }}
        >
            <Icon size={16} style={{ color: '#4F8EF7', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0' }}>{title}</span>
                {subtitle && <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginLeft: 8 }}>{subtitle}</span>}
            </div>
            {open ? <ChevronDown size={14} style={{ color: 'rgba(255,255,255,0.3)' }} /> : <ChevronRight size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />}
        </button>
    )
}
