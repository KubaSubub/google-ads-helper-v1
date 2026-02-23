import { Loader2 } from 'lucide-react'

export function LoadingSpinner() {
    return (
        <div className="flex items-center justify-center py-20">
            <Loader2 size={32} className="text-brand-400 animate-spin" />
        </div>
    )
}

export function ErrorMessage({ message, onRetry }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center mb-3">
                <span className="text-red-400 text-xl">!</span>
            </div>
            <p className="text-sm text-red-300 mb-3">{message}</p>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className="px-4 py-2 rounded-lg bg-brand-600/20 text-brand-300 text-sm hover:bg-brand-600/30 transition-colors"
                >
                    Spróbuj ponownie
                </button>
            )}
        </div>
    )
}

export function PageHeader({ title, subtitle, children }) {
    return (
        <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
            <div>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>{title}</h1>
                {subtitle && <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>{subtitle}</p>}
            </div>
            {children}
        </div>
    )
}

export function Badge({ children, variant = 'default' }) {
    const colors = {
        default: 'bg-surface-700/50 text-surface-200/70',
        success: 'bg-green-500/15 text-green-400',
        warning: 'bg-yellow-500/15 text-yellow-400',
        danger: 'bg-red-500/15 text-red-400',
        brand: 'bg-brand-500/15 text-brand-300',
    }
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium ${colors[variant]}`}>
            {children}
        </span>
    )
}

export function StatusBadge({ status }) {
    const map = {
        ENABLED: { label: 'Aktywna', variant: 'success' },
        PAUSED: { label: 'Wstrzymana', variant: 'warning' },
        REMOVED: { label: 'Usunięta', variant: 'danger' },
    }
    const { label, variant } = map[status] || { label: status, variant: 'default' }
    return <Badge variant={variant}>{label}</Badge>
}
