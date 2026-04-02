import { ChevronDown, ChevronRight } from 'lucide-react'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../../constants/designTokens'

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
            <Icon size={16} style={{ color: C.accentBlue, flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>{title}</span>
                {subtitle && <span style={{ fontSize: 11, color: C.textMuted, marginLeft: 8 }}>{subtitle}</span>}
            </div>
            {open ? <ChevronDown size={14} style={{ color: C.w30 }} /> : <ChevronRight size={14} style={{ color: C.w30 }} />}
        </button>
    )
}
