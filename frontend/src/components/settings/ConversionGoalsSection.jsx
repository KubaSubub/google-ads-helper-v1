import { useEffect, useMemo, useState } from 'react'
import { Target, Check, RefreshCw } from 'lucide-react'
import { getClientHealth } from '../../api'
import { C, R, FONT } from '../../constants/designTokens'

/**
 * ConversionGoalsSection — goal-setting interface for priority conversions.
 *
 * Fetches the list of active ConversionActions from GET /clients/{id}/health
 * and renders a full-width section with a checkbox per conversion. Checked
 * state reflects presence in business_rules.priority_conversions (passed as
 * prop). Toggling a checkbox calls onTogglePriority(name) which the parent
 * Settings.jsx uses to update formData.business_rules.priority_conversions.
 *
 * This REPLACES the previous ClientHealthSection (4 operational cards —
 * Konto/Synchronizacja/Konwersje/Połączenia) which duplicated data from
 * Dashboard, Daily Audit, Campaigns, and the existing Settings sections.
 */
export default function ConversionGoalsSection({ clientId, priorityConversions = [], onTogglePriority }) {
    const [actions, setActions] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!clientId) return
        let cancelled = false
        setLoading(true)
        setError(null)
        getClientHealth(clientId)
            .then(data => {
                if (cancelled) return
                // Use only conversion_tracking.actions — ignore account_metadata,
                // sync_health, linked_accounts (all duplicates of other tabs).
                const list = data?.conversion_tracking?.actions ?? []
                setActions(list)
            })
            .catch(() => {
                if (!cancelled) setError('Nie udało się załadować listy konwersji')
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => { cancelled = true }
    }, [clientId])

    const sortedActions = useMemo(() => {
        if (!actions) return []
        const isPriority = name => priorityConversions.includes(name)
        // Stable sort: priorities first, others after, preserving original order within each group
        const withIdx = actions.map((a, i) => ({ a, i }))
        withIdx.sort((x, y) => {
            const px = isPriority(x.a.name) ? 0 : 1
            const py = isPriority(y.a.name) ? 0 : 1
            if (px !== py) return px - py
            return x.i - y.i
        })
        return withIdx.map(w => w.a)
    }, [actions, priorityConversions])

    const containerStyle = {
        marginBottom: 24,
    }
    const cardStyle = {
        padding: '18px 20px',
    }

    if (loading) {
        return (
            <section data-testid="conversion-goals-loading" style={containerStyle}>
                <SectionHeader />
                <div className="v2-card" style={{ ...cardStyle, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 120 }}>
                    <RefreshCw size={14} color={C.textMuted} className="animate-spin" />
                </div>
            </section>
        )
    }

    if (error) {
        return (
            <section data-testid="conversion-goals-error" style={containerStyle}>
                <SectionHeader />
                <div className="v2-card" style={{ ...cardStyle, color: C.danger, fontSize: 12 }}>
                    {error}
                </div>
            </section>
        )
    }

    if (!sortedActions || sortedActions.length === 0) {
        return (
            <section data-testid="conversion-goals-empty" style={containerStyle}>
                <SectionHeader />
                <div className="v2-card" style={{ ...cardStyle, color: C.textMuted, fontSize: 12 }}>
                    Brak aktywnych konwersji — sprawdź konfigurację konta w Google Ads.
                </div>
            </section>
        )
    }

    return (
        <section data-testid="conversion-goals-section" style={containerStyle}>
            <SectionHeader />
            <div className="v2-card" style={cardStyle}>
                <p style={{ fontSize: 12, color: C.textMuted, marginBottom: 12, lineHeight: 1.5 }}>
                    Zaznacz konwersje które są celem biznesowym dla tego klienta. AI
                    i rekomendacje będą optymalizować pod wybrane konwersje.{' '}
                    <strong style={{ color: C.textSecondary }}>Priorytet lokalny</strong>{' '}
                    ustawia optymalizację w tej aplikacji — nie zmienia ustawień{' '}
                    <em>Primary for goal</em> na koncie Google Ads.
                </p>
                <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                        <thead>
                            <tr>
                                <th style={thStyle} title="Priorytet lokalny — używany przez AI i rekomendacje w tej aplikacji"></th>
                                <th style={thStyle}>Nazwa</th>
                                <th style={thStyle}>Kategoria</th>
                                <th style={thStyle}>Status</th>
                                <th style={thStyle} title="W kolumnie 'Conversions' Google Ads (atrybut primary_for_goal z konta)">Cel Google Ads</th>
                                <th style={thStyle}>W konwersjach</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedActions.map((a, i) => {
                                const isPriority = priorityConversions.includes(a.name)
                                return (
                                    <tr key={`${a.name}-${i}`} style={{
                                        background: i % 2 === 0 ? C.w03 : 'transparent',
                                        transition: 'background 0.15s',
                                    }}>
                                        <td style={{ ...tdStyle, width: 36 }}>
                                            <button
                                                type="button"
                                                aria-label={isPriority ? `Usuń ${a.name} z celów` : `Dodaj ${a.name} do celów`}
                                                aria-pressed={isPriority}
                                                onClick={() => onTogglePriority?.(a.name)}
                                                style={{
                                                    width: 18, height: 18, borderRadius: 4,
                                                    border: `1.5px solid ${isPriority ? C.success : C.w25}`,
                                                    background: isPriority ? C.successBg : 'transparent',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    cursor: 'pointer', padding: 0,
                                                }}
                                            >
                                                {isPriority && <Check size={12} color={C.success} strokeWidth={3} />}
                                            </button>
                                        </td>
                                        <td style={{ ...tdStyle, color: isPriority ? C.textPrimary : C.textSecondary, fontWeight: isPriority ? 600 : 400 }}>
                                            {a.name}
                                        </td>
                                        <td style={{ ...tdStyle, color: C.textMuted, fontSize: 11 }}>
                                            {a.category ?? '—'}
                                        </td>
                                        <td style={tdStyle}>
                                            <StatusBadge status={a.status} />
                                        </td>
                                        <td style={{ ...tdStyle, color: a.primary_for_goal ? C.success : C.textMuted, fontSize: 11, textAlign: 'center' }}>
                                            {a.primary_for_goal ? '✓' : '—'}
                                        </td>
                                        <td style={{ ...tdStyle, color: C.textMuted, fontSize: 11, textAlign: 'center' }}>
                                            {a.include_in_conversions ? '✓' : '—'}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
                <div style={{ marginTop: 12, fontSize: 11, color: C.textMuted }}>
                    Wybrano <strong style={{ color: C.textPrimary }}>{priorityConversions.length}</strong> z {sortedActions.length} konwersji
                </div>
            </div>
        </section>
    )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionHeader() {
    return (
        <h3 className="flex items-center gap-2" style={{
            fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 12, fontFamily: FONT.display,
        }}>
            <Target size={16} style={{ color: C.success }} />
            Cele konwersji
        </h3>
    )
}

function StatusBadge({ status }) {
    const map = {
        ENABLED: { label: 'Aktywna', color: C.success, bg: C.successBg },
        PAUSED:  { label: 'Wstrzymana', color: C.warning, bg: C.warningBg },
        REMOVED: { label: 'Usunięta', color: C.textMuted, bg: C.w05 },
    }
    const cfg = map[status] ?? { label: status ?? '—', color: C.textMuted, bg: C.w05 }
    return (
        <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: R.full,
            background: cfg.bg, color: cfg.color, fontSize: 10, fontWeight: 600,
        }}>
            {cfg.label}
        </span>
    )
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const thStyle = {
    textAlign: 'left',
    padding: '8px 10px',
    fontSize: 10,
    fontWeight: 500,
    color: C.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    borderBottom: `1px solid ${C.w07}`,
}

const tdStyle = {
    padding: '9px 10px',
    verticalAlign: 'middle',
    color: C.textSecondary,
}
