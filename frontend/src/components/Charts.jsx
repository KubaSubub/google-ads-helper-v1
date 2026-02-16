import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    BarChart,
    Bar,
    Legend,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload) return null
    return (
        <div className="glass rounded-lg px-3 py-2 text-xs border border-brand-500/20">
            <p className="text-surface-200/60 mb-1">{label}</p>
            {payload.map((entry, i) => (
                <p key={i} className="font-medium" style={{ color: entry.color }}>
                    {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString('pl-PL') : entry.value}
                </p>
            ))}
        </div>
    )
}

export function MetricsAreaChart({ data, dataKey = 'cost', title = '', color = '#6366f1' }) {
    return (
        <div className="glass rounded-xl p-5 animate-fade-in">
            {title && <h3 className="text-sm font-semibold text-surface-200/70 mb-4">{title}</h3>}
            <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                            <stop offset="100%" stopColor={color} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} width={50} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                        type="monotone"
                        dataKey={dataKey}
                        stroke={color}
                        strokeWidth={2}
                        fill={`url(#grad-${dataKey})`}
                        animationDuration={800}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    )
}

export function CampaignBarChart({ data, title = '' }) {
    return (
        <div className="glass rounded-xl p-5 animate-fade-in">
            {title && <h3 className="text-sm font-semibold text-surface-200/70 mb-4">{title}</h3>}
            <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} angle={-20} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                    <Bar dataKey="cost" name="Koszt (PLN)" fill="#6366f1" radius={[4, 4, 0, 0]} animationDuration={600} />
                    <Bar dataKey="clicks" name="Kliknięcia" fill="#22d3ee" radius={[4, 4, 0, 0]} animationDuration={600} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    )
}
