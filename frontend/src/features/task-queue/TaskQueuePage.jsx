import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    AlertTriangle,
    ArrowRight,
    Ban,
    CheckCircle2,
    ClipboardCheck,
    ExternalLink,
    Lightbulb,
    Loader2,
    RefreshCw,
    Shield,
    Sparkles,
    TrendingDown,
    Zap,
} from 'lucide-react'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import { getRecommendations, getAnomalies, getWastedSpend } from '../../api'
import EmptyState from '../../components/EmptyState'

// ─── Design tokens ───
const CARD = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 12,
}

const PRIORITY_CONFIG = {
    HIGH: { color: '#F87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.25)', label: 'HIGH', order: 0 },
    MEDIUM: { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.25)', label: 'MEDIUM', order: 1 },
    LOW: { color: 'rgba(255,255,255,0.45)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.12)', label: 'LOW', order: 2 },
}

const SOURCE_CONFIG = {
    recommendation: { icon: Lightbulb, color: '#4F8EF7', label: 'Rekomendacja', route: '/recommendations' },
    alert: { icon: AlertTriangle, color: '#FBBF24', label: 'Alert', route: '/alerts' },
    wasted_spend: { icon: Ban, color: '#F87171', label: 'Zmarnowany budżet', route: '/audit-center' },
}

// ─── localStorage helpers ───
function getTodayKey() {
    return `task-queue-done-${new Date().toISOString().slice(0, 10)}`
}

function loadDoneIds() {
    try {
        const raw = localStorage.getItem(getTodayKey())
        return raw ? JSON.parse(raw) : []
    } catch {
        return []
    }
}

function saveDoneIds(ids) {
    localStorage.setItem(getTodayKey(), JSON.stringify(ids))
}

// ─── Sub-components ───
function PriorityBadge({ priority }) {
    const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.LOW
    return (
        <span
            style={{
                fontSize: 10,
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 999,
                background: cfg.bg,
                color: cfg.color,
                border: `1px solid ${cfg.border}`,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                whiteSpace: 'nowrap',
            }}
        >
            {cfg.label}
        </span>
    )
}

function SourceBadge({ source }) {
    const cfg = SOURCE_CONFIG[source] || SOURCE_CONFIG.recommendation
    const Icon = cfg.icon
    return (
        <span
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 500,
                padding: '2px 8px 2px 6px',
                borderRadius: 999,
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: cfg.color,
            }}
        >
            <Icon size={11} />
            {cfg.label}
        </span>
    )
}

function ProgressBar({ done, total }) {
    const pct = total > 0 ? Math.round((done / total) * 100) : 0
    return (
        <div style={{ ...CARD, padding: '16px 20px', marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0' }}>
                    {done}/{total} {total === 1 ? 'zadanie wykonane' : total < 5 ? 'zadania wykonane' : 'zadań wykonanych'} dzisiaj
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, color: pct === 100 ? '#4ADE80' : '#4F8EF7' }}>
                    {pct}%
                </span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                <div
                    style={{
                        height: '100%',
                        width: `${pct}%`,
                        borderRadius: 3,
                        background: pct === 100
                            ? 'linear-gradient(90deg, #4ADE80, #22c55e)'
                            : 'linear-gradient(90deg, #4F8EF7, #7B5CE0)',
                        transition: 'width 0.4s ease',
                    }}
                />
            </div>
        </div>
    )
}

function TaskCard({ task, isDone, onToggle, onNavigate }) {
    const srcCfg = SOURCE_CONFIG[task.source] || SOURCE_CONFIG.recommendation
    const Icon = srcCfg.icon

    return (
        <div
            style={{
                ...CARD,
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 14,
                opacity: isDone ? 0.45 : 1,
                transition: 'opacity 0.25s ease',
            }}
        >
            {/* Checkbox */}
            <button
                onClick={onToggle}
                style={{
                    flex: '0 0 auto',
                    marginTop: 2,
                    width: 22,
                    height: 22,
                    borderRadius: 6,
                    border: isDone
                        ? '2px solid #4ADE80'
                        : '2px solid rgba(255,255,255,0.15)',
                    background: isDone ? 'rgba(74,222,128,0.15)' : 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.15s',
                    padding: 0,
                }}
                title={isDone ? 'Oznacz jako niewykonane' : 'Oznacz jako wykonane'}
            >
                {isDone && <CheckCircle2 size={14} style={{ color: '#4ADE80' }} />}
            </button>

            {/* Icon */}
            <div
                style={{
                    flex: '0 0 auto',
                    width: 34,
                    height: 34,
                    borderRadius: 8,
                    background: `${srcCfg.color}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}
            >
                <Icon size={16} style={{ color: srcCfg.color }} />
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                    <PriorityBadge priority={task.priority} />
                    <SourceBadge source={task.source} />
                    {task.impact && (
                        <span style={{
                            fontSize: 10,
                            color: 'rgba(255,255,255,0.4)',
                            fontFamily: 'monospace',
                        }}>
                            {task.impact}
                        </span>
                    )}
                </div>
                <div
                    style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: isDone ? 'rgba(255,255,255,0.35)' : '#F0F0F0',
                        textDecoration: isDone ? 'line-through' : 'none',
                        lineHeight: 1.4,
                        marginBottom: task.detail ? 4 : 0,
                    }}
                >
                    {task.description}
                </div>
                {task.detail && (
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', lineHeight: 1.3 }}>
                        {task.detail}
                    </div>
                )}
            </div>

            {/* Action button */}
            <button
                onClick={() => onNavigate(task)}
                style={{
                    flex: '0 0 auto',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    padding: '6px 12px',
                    borderRadius: 999,
                    fontSize: 11,
                    fontWeight: 500,
                    border: `1px solid ${srcCfg.color}30`,
                    background: `${srcCfg.color}10`,
                    color: srcCfg.color,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                    whiteSpace: 'nowrap',
                }}
                title={task.actionLabel || 'Przejdź'}
            >
                {task.actionLabel || 'Przejdź'}
                <ArrowRight size={12} />
            </button>
        </div>
    )
}

function FilterPill({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '4px 14px',
                borderRadius: 999,
                fontSize: 12,
                fontWeight: active ? 500 : 400,
                border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
                background: active ? 'rgba(79,142,247,0.18)' : 'transparent',
                color: active ? 'white' : 'rgba(255,255,255,0.45)',
                cursor: 'pointer',
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
            }}
        >
            {children}
        </button>
    )
}

// ─── Task builders ───
function buildRecommendationTasks(recs) {
    if (!Array.isArray(recs)) return []
    return recs.map(rec => {
        const impact = rec.estimated_impact
            || (rec.impact_micros ? `~ ${(rec.impact_micros / 1_000_000).toFixed(2)} PLN` : null)
        return {
            id: `rec-${rec.id}`,
            source: 'recommendation',
            priority: rec.priority || 'MEDIUM',
            description: `Zastosuj rekomendację: ${rec.action_type_display || rec.action_type || 'Przejrzyj'}`,
            detail: rec.reason || rec.description || null,
            impact,
            actionLabel: 'Zastosuj',
            route: '/recommendations',
            impactValue: rec.impact_micros || 0,
        }
    })
}

function buildAlertTasks(alerts) {
    if (!Array.isArray(alerts)) return []
    return alerts.map(alert => ({
        id: `alert-${alert.id}`,
        source: 'alert',
        priority: (alert.severity || 'MEDIUM').toUpperCase(),
        description: `Sprawdź alert: ${alert.description || alert.metric || 'Anomalia'}`,
        detail: alert.campaign_name ? `Kampania: ${alert.campaign_name}` : null,
        impact: alert.deviation ? `Odchylenie: ${Number(alert.deviation).toFixed(1)}%` : null,
        actionLabel: 'Sprawdź',
        route: '/alerts',
        impactValue: Math.abs(alert.deviation || 0),
    }))
}

function buildWastedSpendTasks(data) {
    const items = data?.items || data?.wasted_terms || []
    if (!Array.isArray(items) || items.length === 0) return []

    // Group wasted spend into a single task or a few grouped tasks
    const totalWaste = items.reduce((sum, item) => {
        const cost = item.cost_micros ? item.cost_micros / 1_000_000 : (item.cost || 0)
        return sum + cost
    }, 0)

    const topTerms = items
        .slice(0, 5)
        .map(item => item.search_term || item.term || item.query)
        .filter(Boolean)

    const tasks = []

    if (totalWaste > 0) {
        tasks.push({
            id: 'wasted-spend-summary',
            source: 'wasted_spend',
            priority: totalWaste > 50 ? 'HIGH' : totalWaste > 10 ? 'MEDIUM' : 'LOW',
            description: `Wyklucz frazy marnujące budżet (${items.length} fraz, ~${totalWaste.toFixed(2)} PLN)`,
            detail: topTerms.length > 0 ? `Top: ${topTerms.join(', ')}` : null,
            impact: `~${totalWaste.toFixed(2)} PLN oszczędności`,
            actionLabel: 'Wyklucz',
            route: '/audit-center',
            impactValue: totalWaste * 1_000_000,
        })
    }

    // Also add individual high-cost terms
    items
        .filter(item => {
            const cost = item.cost_micros ? item.cost_micros / 1_000_000 : (item.cost || 0)
            return cost > 5
        })
        .slice(0, 5)
        .forEach((item, idx) => {
            const cost = item.cost_micros ? item.cost_micros / 1_000_000 : (item.cost || 0)
            const term = item.search_term || item.term || item.query || 'Nieznana fraza'
            tasks.push({
                id: `wasted-${idx}-${term}`,
                source: 'wasted_spend',
                priority: cost > 20 ? 'HIGH' : 'MEDIUM',
                description: `Wyklucz frazę: "${term}"`,
                detail: item.campaign_name ? `Kampania: ${item.campaign_name}` : null,
                impact: `~${cost.toFixed(2)} PLN`,
                actionLabel: 'Wyklucz',
                route: '/search-terms',
                impactValue: cost * 1_000_000,
            })
        })

    return tasks
}

// ─── Main Component ───
export default function TaskQueuePage() {
    const { selectedClientId, showToast } = useApp()
    const { days } = useFilter()
    const navigate = useNavigate()

    const [tasks, setTasks] = useState([])
    const [loading, setLoading] = useState(true)
    const [doneIds, setDoneIds] = useState(() => loadDoneIds())
    const [filter, setFilter] = useState('all') // 'all' | 'pending' | 'done'
    const [sourceFilter, setSourceFilter] = useState('all') // 'all' | 'recommendation' | 'alert' | 'wasted_spend'

    // Fetch data from all sources
    const fetchTasks = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)

        try {
            const [recsData, alertsData, wastedData] = await Promise.allSettled([
                getRecommendations(selectedClientId, { status: 'pending', days }),
                getAnomalies(selectedClientId, 'unresolved'),
                getWastedSpend(selectedClientId, { days: days || 30 }),
            ])

            const allTasks = []

            if (recsData.status === 'fulfilled') {
                const recs = recsData.value?.recommendations || recsData.value || []
                allTasks.push(...buildRecommendationTasks(recs))
            }

            if (alertsData.status === 'fulfilled') {
                const alerts = alertsData.value?.alerts || alertsData.value || []
                allTasks.push(...buildAlertTasks(alerts))
            }

            if (wastedData.status === 'fulfilled') {
                allTasks.push(...buildWastedSpendTasks(wastedData.value))
            }

            setTasks(allTasks)
        } catch (err) {
            console.error('TaskQueue fetch error:', err)
            showToast?.('Błąd ładowania planu dnia', 'error')
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, days, showToast])

    useEffect(() => {
        fetchTasks()
    }, [fetchTasks])

    // Sort: priority order first, then impact descending
    const sortedTasks = useMemo(() => {
        const sorted = [...tasks].sort((a, b) => {
            const pa = PRIORITY_CONFIG[a.priority]?.order ?? 2
            const pb = PRIORITY_CONFIG[b.priority]?.order ?? 2
            if (pa !== pb) return pa - pb
            return (b.impactValue || 0) - (a.impactValue || 0)
        })
        return sorted
    }, [tasks])

    // Apply filters
    const filteredTasks = useMemo(() => {
        let result = sortedTasks

        if (filter === 'pending') result = result.filter(t => !doneIds.includes(t.id))
        if (filter === 'done') result = result.filter(t => doneIds.includes(t.id))

        if (sourceFilter !== 'all') result = result.filter(t => t.source === sourceFilter)

        return result
    }, [sortedTasks, filter, sourceFilter, doneIds])

    const doneCount = useMemo(() => tasks.filter(t => doneIds.includes(t.id)).length, [tasks, doneIds])

    // Toggle task done/undone
    const toggleDone = useCallback((taskId) => {
        setDoneIds(prev => {
            const next = prev.includes(taskId)
                ? prev.filter(id => id !== taskId)
                : [...prev, taskId]
            saveDoneIds(next)
            return next
        })
    }, [])

    // Navigate to source page
    const handleNavigate = useCallback((task) => {
        if (task.route) navigate(task.route)
    }, [navigate])

    // Counts per source
    const sourceCounts = useMemo(() => {
        const counts = { recommendation: 0, alert: 0, wasted_spend: 0 }
        tasks.forEach(t => { if (counts[t.source] !== undefined) counts[t.source]++ })
        return counts
    }, [tasks])

    // ─── Render ───
    if (!selectedClientId) {
        return (
            <div style={{ padding: 24 }}>
                <EmptyState message="Wybierz klienta, aby zobaczyć plan dnia" icon={ClipboardCheck} />
            </div>
        )
    }

    return (
        <div style={{ padding: 24, maxWidth: 900 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0', margin: 0 }}>
                        Plan dnia
                    </h1>
                    <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', margin: '4px 0 0 0' }}>
                        Priorytetyzowana lista działań do wykonania dzisiaj
                    </p>
                </div>
                <button
                    onClick={fetchTasks}
                    disabled={loading}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '8px 16px',
                        borderRadius: 999,
                        fontSize: 12,
                        fontWeight: 500,
                        border: '1px solid rgba(255,255,255,0.1)',
                        background: 'rgba(255,255,255,0.04)',
                        color: 'rgba(255,255,255,0.6)',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        transition: 'all 0.15s',
                    }}
                >
                    {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                    Odśwież
                </button>
            </div>

            {/* Progress bar */}
            <ProgressBar done={doneCount} total={tasks.length} />

            {/* Filters */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
                <FilterPill active={filter === 'all'} onClick={() => setFilter('all')}>
                    Wszystkie ({tasks.length})
                </FilterPill>
                <FilterPill active={filter === 'pending'} onClick={() => setFilter('pending')}>
                    Do zrobienia ({tasks.length - doneCount})
                </FilterPill>
                <FilterPill active={filter === 'done'} onClick={() => setFilter('done')}>
                    Wykonane ({doneCount})
                </FilterPill>

                <div style={{ width: 1, background: 'rgba(255,255,255,0.08)', margin: '0 4px' }} />

                <FilterPill active={sourceFilter === 'all'} onClick={() => setSourceFilter('all')}>
                    Wszystkie źródła
                </FilterPill>
                <FilterPill active={sourceFilter === 'recommendation'} onClick={() => setSourceFilter('recommendation')}>
                    Rekomendacje ({sourceCounts.recommendation})
                </FilterPill>
                <FilterPill active={sourceFilter === 'alert'} onClick={() => setSourceFilter('alert')}>
                    Alerty ({sourceCounts.alert})
                </FilterPill>
                <FilterPill active={sourceFilter === 'wasted_spend'} onClick={() => setSourceFilter('wasted_spend')}>
                    Zmarnowany budżet ({sourceCounts.wasted_spend})
                </FilterPill>
            </div>

            {/* Loading state */}
            {loading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
                    <Loader2 size={24} className="animate-spin" style={{ color: 'rgba(255,255,255,0.3)' }} />
                    <span style={{ marginLeft: 10, fontSize: 13, color: 'rgba(255,255,255,0.35)' }}>
                        Ładowanie planu dnia...
                    </span>
                </div>
            )}

            {/* Empty state */}
            {!loading && filteredTasks.length === 0 && (
                <EmptyState
                    message={
                        filter === 'done'
                            ? 'Nie ukończono jeszcze żadnych zadań'
                            : tasks.length === 0
                                ? 'Brak zadań do wykonania — wszystko wygląda dobrze!'
                                : 'Brak zadań pasujących do filtrów'
                    }
                    icon={filter === 'done' ? CheckCircle2 : tasks.length === 0 ? Sparkles : ClipboardCheck}
                />
            )}

            {/* Task list */}
            {!loading && filteredTasks.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {filteredTasks.map(task => (
                        <TaskCard
                            key={task.id}
                            task={task}
                            isDone={doneIds.includes(task.id)}
                            onToggle={() => toggleDone(task.id)}
                            onNavigate={handleNavigate}
                        />
                    ))}
                </div>
            )}

            {/* Summary footer */}
            {!loading && tasks.length > 0 && (
                <div style={{
                    marginTop: 24,
                    padding: '12px 16px',
                    borderRadius: 10,
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.04)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    flexWrap: 'wrap',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#F87171' }} />
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                            HIGH: {tasks.filter(t => t.priority === 'HIGH').length}
                        </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#FBBF24' }} />
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                            MEDIUM: {tasks.filter(t => t.priority === 'MEDIUM').length}
                        </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'rgba(255,255,255,0.3)' }} />
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                            LOW: {tasks.filter(t => t.priority === 'LOW').length}
                        </span>
                    </div>
                </div>
            )}
        </div>
    )
}
