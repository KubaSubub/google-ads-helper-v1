import clsx from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function KPICard({ title, value, change, prefix = '', suffix = '', icon: Icon }) {
    const isUp = change > 0
    const isDown = change < 0
    const changeColor = isUp ? 'text-green-400' : isDown ? 'text-red-400' : 'text-slate-400'
    const ChangeTrend = isUp ? TrendingUp : isDown ? TrendingDown : Minus

    return (
        <div className="glass rounded-xl p-5 glass-hover transition-all duration-300 group animate-fade-in">
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-surface-200/50 uppercase tracking-wider">{title}</span>
                {Icon && (
                    <div className="w-8 h-8 rounded-lg bg-brand-600/15 flex items-center justify-center">
                        <Icon size={16} className="text-brand-400" />
                    </div>
                )}
            </div>

            <div className="flex items-end gap-2">
                <span className="text-2xl font-bold text-white tracking-tight">
                    {prefix}{typeof value === 'number' ? value.toLocaleString('pl-PL') : value}{suffix}
                </span>
            </div>

            {change !== undefined && (
                <div className={clsx('flex items-center gap-1 mt-2 text-xs font-medium', changeColor)}>
                    <ChangeTrend size={14} />
                    <span>{Math.abs(change).toFixed(1)}%</span>
                    <span className="text-surface-200/30 ml-1">vs prev</span>
                </div>
            )}
        </div>
    )
}
