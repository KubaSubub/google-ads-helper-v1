import { useEffect, useState } from 'react'
import {
    Monitor, RefreshCw, Target, Link2,
    CheckCircle2, Clock, XCircle,
} from 'lucide-react'
import { getClientHealth } from '../../api'
import { C, R, FONT } from '../../constants/designTokens'

// ─── Freshness badge ──────────────────────────────────────────────────────────

const FRESHNESS = {
    green:  { color: C.success,  bg: C.successBg,  border: C.successBorder,  icon: CheckCircle2, label: 'Aktualny' },
    yellow: { color: C.warning,  bg: C.warningBg,  border: C.warningBorder,  icon: Clock,        label: 'Starszy niż 6h' },
    red:    { color: C.danger,   bg: C.dangerBg,   border: C.dangerBorder,   icon: XCircle,      label: 'Nieaktualny' },
}

function FreshnessBadge({ value }) {
    const cfg = FRESHNESS[value] ?? FRESHNESS.red
    const Icon = cfg.icon
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '2px 8px', borderRadius: R.full,
            background: cfg.bg, border: `1px solid ${cfg.border}`,
            color: cfg.color, fontSize: 11, fontWeight: 600,
        }}>
            <Icon size={11} />
            {cfg.label}
        </span>
    )
}

// ─── Linked account row ───────────────────────────────────────────────────────

const LINKED_LABELS = {
    GA4: 'Google Analytics 4',
    MERCHANT_CENTER: 'Merchant Center',
    YOUTUBE: 'YouTube',
    SEARCH_CONSOLE: 'Search Console',
}

function LinkedRow({ type, status }) {
    const linked = status === 'linked'
    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: C.textSecondary }}>{LINKED_LABELS[type] ?? type}</span>
            <span style={{
                fontSize: 11, fontWeight: 600,
                color: linked ? C.success : C.textMuted,
            }}>
                {linked ? '✓ Połączony' : '—'}
            </span>
        </div>
    )
}

// ─── Card ─────────────────────────────────────────────────────────────────────

function HealthCard({ icon: Icon, iconColor, title, children }) {
    return (
        <div className="v2-card" style={{ padding: '14px 16px', minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
                <Icon size={13} color={iconColor} />
                <span style={{ fontSize: 11, fontWeight: 600, color: C.textMuted,
                    fontFamily: FONT.display, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {title}
                </span>
            </div>
            {children}
        </div>
    )
}

function Row({ label, value, dim }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
            marginBottom: 3, gap: 8 }}>
            <span style={{ fontSize: 11, color: C.textMuted, whiteSpace: 'nowrap' }}>{label}</span>
            <span style={{ fontSize: 12, color: dim ? C.textMuted : C.textPrimary,
                fontWeight: dim ? 400 : 500, textAlign: 'right', minWidth: 0, wordBreak: 'break-all' }}>
                {value ?? '—'}
            </span>
        </div>
    )
}

// ─── Relative time ────────────────────────────────────────────────────────────

function relativeTime(iso) {
    if (!iso) return null
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 60) return 'przed chwilą'
    if (diff < 3600) return `${Math.round(diff / 60)} min temu`
    if (diff < 86400) return `${Math.round(diff / 3600)} godz. temu`
    return `${Math.round(diff / 86400)} dni temu`
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ClientHealthSection({ clientId }) {
    const [health, setHealth] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!clientId) return
        let cancelled = false
        setLoading(true)
        setError(null)
        // Note: api.js interceptor unwraps `response.data` — so getClientHealth
        // resolves directly to the payload object, not an axios response wrapper.
        getClientHealth(clientId)
            .then(data => {
                if (!cancelled) setHealth(data)
            })
            .catch(() => {
                if (!cancelled) setError('Nie udało się załadować danych konta')
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => { cancelled = true }
    }, [clientId])

    if (loading) {
        return (
            <div data-testid="client-health-loading" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 24 }}>
                {[0, 1, 2, 3].map(i => (
                    <div key={i} style={{
                        background: C.w03, border: `1px solid ${C.w07}`,
                        borderRadius: R.md, padding: '14px 16px', height: 120,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <RefreshCw size={14} color={C.textMuted} className="animate-spin" />
                    </div>
                ))}
            </div>
        )
    }

    if (error || !health) {
        return null  // silent — Settings page still works without health section
    }

    // Destructure only after !health guard above — optional chaining not needed here.
    const meta = health.account_metadata
    const sync = health.sync_health
    const conv = health.conversion_tracking
    const linked = health.linked_accounts ?? []

    // Guard against malformed response (e.g. catch-all API mock returning {items:[]})
    if (!meta || !sync || !conv) {
        return null
    }

    const statusLabel = { success: 'Sukces', partial: 'Częściowy', failed: 'Błąd', running: 'W toku' }

    return (
        <div data-testid="client-health-section" style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textMuted, fontFamily: FONT.display,
                textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10 }}>
                Stan konta i integracje
            </div>
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 10,
            }}>
                {/* Card 1 — Konto */}
                <HealthCard icon={Monitor} iconColor={C.accentBlue} title="Konto">
                    <Row label="ID" value={meta.customer_id} />
                    <Row label="Typ" value={meta.account_type} />
                    <Row label="Waluta" value={meta.currency} />
                    <Row label="Strefa" value={meta.timezone} dim={!meta.timezone} />
                    {meta.auto_tagging_enabled != null && (
                        <Row label="Auto-tag" value={meta.auto_tagging_enabled ? 'Włączony' : 'Wyłączony'} />
                    )}
                </HealthCard>

                {/* Card 2 — Synchronizacja */}
                <HealthCard icon={RefreshCw} iconColor={C.accentPurple} title="Synchronizacja">
                    <div style={{ marginBottom: 8 }}>
                        <FreshnessBadge value={sync.freshness} />
                    </div>
                    <Row label="Ostatni sync" value={relativeTime(sync.last_synced_at)} />
                    <Row label="Status" value={statusLabel[sync.last_status] ?? sync.last_status} />
                    {sync.last_duration_seconds != null && (
                        <Row label="Czas" value={`${Math.round(sync.last_duration_seconds)}s`} />
                    )}
                    {!sync.last_synced_at && (
                        <div style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>
                            Brak danych — uruchom synchronizację
                        </div>
                    )}
                </HealthCard>

                {/* Card 3 — Konwersje */}
                <HealthCard icon={Target} iconColor={C.success} title="Konwersje">
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 6 }}>
                        <span style={{ fontSize: 20, fontWeight: 700, fontFamily: FONT.display,
                            color: conv.active_count > 0 ? C.textPrimary : C.textMuted }}>
                            {conv.active_count}
                        </span>
                        <span style={{ fontSize: 11, color: C.textMuted }}>aktywnych</span>
                    </div>
                    {conv.attribution_model && (
                        <Row label="Atrybucja" value={conv.attribution_model.replace(/_/g, ' ')} />
                    )}
                    {conv.active_count === 0 && (
                        <div style={{ fontSize: 11, color: C.danger, marginTop: 4 }}>
                            Brak aktywnych konwersji
                        </div>
                    )}
                    {conv.actions.slice(0, 2).map(a => (
                        <div key={a.name} style={{ fontSize: 11, color: C.textSecondary,
                            marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            · {a.name}
                        </div>
                    ))}
                    {conv.actions.length > 2 && (
                        <div style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>
                            + {conv.actions.length - 2} więcej
                        </div>
                    )}
                </HealthCard>

                {/* Card 4 — Połączenia */}
                <HealthCard icon={Link2} iconColor={C.warning} title="Połączenia">
                    {linked.map(l => (
                        <LinkedRow key={l.type} type={l.type} status={l.status} />
                    ))}
                    {linked.length === 0 && (
                        <div style={{ fontSize: 11, color: C.textMuted }}>
                            Dane niedostępne
                        </div>
                    )}
                </HealthCard>
            </div>
        </div>
    )
}
