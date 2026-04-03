import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    RefreshCw, TrendingUp, TrendingDown, ArrowRight,
    AlertTriangle, CheckCircle, Minus, Bell, ExternalLink,
    ChevronDown, ChevronRight, Shield, List,
    UserPlus, CreditCard, Columns, EyeOff,
} from 'lucide-react'
import {
    getMccOverview, getMccSharedLists,
    dismissMccGoogleRecommendations, syncClient,
} from '../../api'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import PacingProgressBar from '../../components/modules/PacingProgressBar'
import { C, B, T, R, S, CARD, STATUS_COLORS } from '../../constants/designTokens'

const TH = T.th
const TD = T.td
const TD_DIM = T.tdDim

function fmtNum(n, decimals = 0) {
    if (n == null) return '—'
    return n.toLocaleString('pl-PL', { maximumFractionDigits: decimals })
}

function fmtMoney(n) {
    if (n == null) return '—'
    return n.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function SpendChange({ pct }) {
    if (pct == null) return <span style={{ color: C.w30 }}>—</span>
    const isUp = pct > 0
    const Icon = isUp ? TrendingUp : TrendingDown
    const color = isUp ? C.warning : C.success
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color }}>
            <Icon size={12} />
            {Math.abs(pct).toFixed(1)}%
        </span>
    )
}

function SyncIndicator({ lastSyncedAt, syncing }) {
    if (syncing) return <RefreshCw size={13} style={{ color: C.accentBlue, animation: 'spin 1s linear infinite' }} />
    if (!lastSyncedAt) return <span style={{ color: C.w30, fontSize: 11 }}>—</span>
    const d = new Date(lastSyncedAt)
    const label = `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`
    return <span style={{ fontSize: 11, color: C.w50 }}>{label}</span>
}

function SortHeader({ label, field, sortBy, sortDir, onSort, align }) {
    const active = sortBy === field
    return (
        <th style={{ ...TH, textAlign: align || 'left', cursor: 'pointer', userSelect: 'none' }} onClick={() => onSort(field)}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                {label}
                {active && (sortDir === 'asc'
                    ? <TrendingUp size={10} style={{ opacity: 0.6 }} />
                    : <TrendingDown size={10} style={{ opacity: 0.6 }} />
                )}
            </span>
        </th>
    )
}

function AlertTooltip({ alerts }) {
    if (!alerts?.length) return null
    return (
        <div style={{
            position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
            marginBottom: 6, padding: '8px 10px', borderRadius: R.md, minWidth: 200, maxWidth: 300,
            background: C.surfaceElevated, border: B.hover,
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)', zIndex: 10,
            fontSize: 11, color: C.w70,
        }}>
            {alerts.map((a, i) => (
                <div key={i} style={{ padding: '3px 0', display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                    <span style={{ color: a.severity === 'HIGH' ? C.danger : C.warning, fontWeight: 600, fontSize: 9, marginTop: 1 }}>
                        {a.severity === 'HIGH' ? '!!!' : '!!'}
                    </span>
                    <span>{a.title}</span>
                </div>
            ))}
        </div>
    )
}

function BillingTooltip({ status }) {
    if (!status) return null
    const messages = {
        ok: 'Płatności skonfigurowane poprawnie',
        no_billing: 'Brak aktywnego billing setup — konto może mieć problemy z płatnościami',
        no_access: 'Brak dostępu do API billing — nie można sprawdzić statusu płatności',
        unknown: status?.reason || 'Status płatności nieznany',
        error: 'Błąd sprawdzania statusu płatności',
    }
    const colors = { ok: C.success, no_billing: C.danger, no_access: C.w40, unknown: C.w40, error: C.danger }
    return (
        <div style={{
            position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
            marginBottom: 6, padding: '8px 10px', borderRadius: R.md, minWidth: 180, maxWidth: 260,
            background: C.surfaceElevated, border: B.hover,
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)', zIndex: 10,
            fontSize: 11, color: colors[status.status] || C.w50,
        }}>
            {messages[status.status] || messages.unknown}
        </div>
    )
}

function googleAdsUrl(googleCustomerId) {
    const clean = googleCustomerId?.replace(/-/g, '') || ''
    return `https://ads.google.com/aw/overview?ocid=${clean}`
}

// ─────────────────────────────────────────────────────────────────────────────

export default function MCCOverviewPage() {
    const navigate = useNavigate()
    const { setSelectedClientId, showToast } = useApp()
    const { filters } = useFilter()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [syncingIds, setSyncingIds] = useState(new Set())
    const [sharedLists, setSharedLists] = useState(null)
    const [sharedOpen, setSharedOpen] = useState(false)
    const [sortBy, setSortBy] = useState('spend')
    const [sortDir, setSortDir] = useState('desc')
    const [compactMode, setCompactMode] = useState(true)
    const [billingStatuses, setBillingStatuses] = useState({})
    const [hoveredAlert, setHoveredAlert] = useState(null)
    const [hoveredBilling, setHoveredBilling] = useState(null)
    const [dismissingAll, setDismissingAll] = useState(null)

    const load = useCallback(async () => {
        try {
            setLoading(true)
            const params = {}
            if (filters.dateFrom) params.date_from = filters.dateFrom
            if (filters.dateTo) params.date_to = filters.dateTo
            const result = await getMccOverview(params)
            setData(result)
        } catch {
            showToast?.('Błąd ładowania MCC overview', 'error')
        } finally {
            setLoading(false)
        }
    }, [showToast, filters.dateFrom, filters.dateTo])

    useEffect(() => { load() }, [load])

    // Lazy load billing
    useEffect(() => {
        if (!data?.accounts?.length) return
        data.accounts.forEach(acc => {
            const cid = acc.google_customer_id
            if (billingStatuses[cid]) return
            import('../../api').then(({ getMccBillingStatus }) =>
                getMccBillingStatus(cid)
                    .then(r => setBillingStatuses(prev => ({ ...prev, [cid]: r })))
                    .catch(() => setBillingStatuses(prev => ({ ...prev, [cid]: { status: 'error' } })))
            )
        })
    }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

    // Lazy load shared lists
    useEffect(() => {
        if (sharedOpen && !sharedLists) {
            getMccSharedLists().then(setSharedLists).catch(() => {})
        }
    }, [sharedOpen, sharedLists])

    const handleSort = (field) => {
        if (sortBy === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        else { setSortBy(field); setSortDir('desc') }
    }

    const handleRowClick = (acc) => {
        setSelectedClientId(acc.client_id)
        navigate('/dashboard', { state: { fromMCC: true } })
    }

    const handleDeepLink = (acc, path, e) => {
        e.stopPropagation()
        setSelectedClientId(acc.client_id)
        navigate(path)
    }

    const handleSync = async (clientId, e) => {
        e.stopPropagation()
        setSyncingIds(prev => new Set(prev).add(clientId))
        try {
            await syncClient(clientId, 30)
            showToast?.('Synchronizacja uruchomiona', 'success')
        } catch {
            showToast?.('Błąd synchronizacji', 'error')
        } finally {
            setSyncingIds(prev => { const n = new Set(prev); n.delete(clientId); return n })
        }
    }

    const handleSyncAll = async () => {
        if (!data?.accounts?.length) return
        const staleThreshold = 6 * 60 * 60 * 1000
        const stale = data.accounts.filter(acc =>
            !acc.last_synced_at || Date.now() - new Date(acc.last_synced_at).getTime() > staleThreshold
        )
        if (!stale.length) { showToast?.('Wszystkie konta aktualne', 'info'); return }
        for (const acc of stale.slice(0, 3)) handleSync(acc.client_id, { stopPropagation: () => {} })
    }

    const handleDismissRecs = async (clientId, e) => {
        e.stopPropagation()
        setDismissingAll(clientId)
        try {
            const result = await dismissMccGoogleRecommendations({ client_id: clientId, dismiss_all: true })
            showToast?.(`Ukryto ${result.dismissed} rekomendacji w aplikacji`, 'success')
            load()
        } catch {
            showToast?.('Błąd ukrywania rekomendacji', 'error')
        } finally {
            setDismissingAll(null)
        }
    }

    const rawAccounts = data?.accounts || []

    const accounts = useMemo(() => {
        const sorted = [...rawAccounts]
        sorted.sort((a, b) => {
            const va = a[sortBy] ?? -Infinity
            const vb = b[sortBy] ?? -Infinity
            return sortDir === 'asc' ? va - vb : vb - va
        })
        return sorted
    }, [rawAccounts, sortBy, sortDir])

    const totalSpend = accounts.reduce((s, a) => s + (a.spend || 0), 0)
    const totalClicks = accounts.reduce((s, a) => s + (a.clicks || 0), 0)
    const totalConv = accounts.reduce((s, a) => s + (a.conversions || 0), 0)
    const totalImpr = accounts.reduce((s, a) => s + (a.impressions || 0), 0)
    const activeCount = accounts.filter(a => (a.spend || 0) > 0).length

    return (
        <div style={{ padding: '24px 32px', maxWidth: 1600 }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: S['5xl'] }}>
                <div>
                    <h1 style={T.pageTitle}>Wszystkie konta</h1>
                    <p style={T.pageSubtitle}>
                        Przegląd MCC — {accounts.length} {accounts.length === 1 ? 'konto' : 'kont'}
                        {data?.date_from && data?.date_to && (
                            <span style={{ marginLeft: 8, color: C.w40 }}>
                                ({data.date_from} — {data.date_to})
                            </span>
                        )}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button onClick={() => setCompactMode(p => !p)} title={compactMode ? 'Pokaż wszystkie kolumny' : 'Tryb kompaktowy'} style={{
                        display: 'flex', alignItems: 'center', gap: S.sm, padding: '7px 10px',
                        borderRadius: R.md, background: compactMode ? C.infoBg : C.w04, border: compactMode ? B.info : B.subtle,
                        color: compactMode ? C.accentBlue : C.w50, fontSize: 12, cursor: 'pointer',
                    }}>
                        <Columns size={13} />
                    </button>
                    <button onClick={handleSyncAll} style={{
                        display: 'flex', alignItems: 'center', gap: S.sm, padding: '7px 14px',
                        borderRadius: R.md, background: C.infoBg, border: B.info,
                        color: C.accentBlue, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                    }}>
                        <RefreshCw size={13} /> Synchronizuj nieaktualne
                    </button>
                </div>
            </div>

            {/* KPI strip */}
            {(() => {
                const kpis = [
                    { label: 'Wydatki', value: fmtMoney(totalSpend) },
                    totalClicks > 0 && { label: 'Kliknięcia', value: fmtNum(totalClicks) },
                    totalImpr > 0 && { label: 'Wyświetlenia', value: fmtNum(totalImpr) },
                    { label: 'Konwersje', value: fmtNum(totalConv, 1) },
                    { label: 'Aktywne konta', value: `${activeCount} / ${accounts.length}` },
                ].filter(Boolean)
                return (
                    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${kpis.length}, 1fr)`, gap: S.xl, marginBottom: S['4xl'] }}>
                        {kpis.map(kpi => (
                            <div key={kpi.label} className={CARD} style={{ padding: '14px 16px' }}>
                                <div style={T.kpiLabel}>{kpi.label}</div>
                                <div style={{ ...T.kpiValue, fontSize: 18, marginTop: 2 }}>{kpi.value}</div>
                            </div>
                        ))}
                    </div>
                )
            })()}

            {/* Accounts table */}
            <div className={CARD} style={{ overflow: 'visible' }}>
                {loading ? (
                    <div style={{ padding: 40, textAlign: 'center', color: C.w30 }}>
                        <RefreshCw size={20} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
                        <div style={{ fontSize: 12 }}>Ładowanie kont...</div>
                    </div>
                ) : accounts.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: C.w30, fontSize: 13 }}>
                        Brak kont. Dodaj klienta w ustawieniach.
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: B.card }}>
                                <SortHeader label="Konto" field="client_name" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                                <SortHeader label="Wydatki" field="spend" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                {!compactMode && <SortHeader label="Kliknięcia" field="clicks" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                {!compactMode && <SortHeader label="Wyśw." field="impressions" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                {!compactMode && <SortHeader label="CTR" field="ctr_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                {!compactMode && <SortHeader label="CPC" field="avg_cpc" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                <SortHeader label="Konwersje" field="conversions" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                {!compactMode && <SortHeader label="CVR" field="conversion_rate_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                {!compactMode && <SortHeader label="Wart. konw." field="conversion_value" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                <SortHeader label="CPA" field="cpa" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="ROAS" field="roas_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <th style={{ ...TH, minWidth: 120 }}>Pacing</th>
                                <th style={{ ...TH, textAlign: 'center' }}>Płatności</th>
                                <SortHeader label="Zmiany" field="total_changes" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <th style={{ ...TH, minWidth: 100 }}>Rekomendacje Google</th>
                                <th style={{ ...TH, textAlign: 'center' }}>Sync</th>
                                <th style={{ ...TH, width: 50 }}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {accounts.map(acc => {
                                const syncing = syncingIds.has(acc.client_id)
                                const hasNewAccess = acc.new_access_emails?.length > 0
                                const billing = billingStatuses[acc.google_customer_id]
                                const billingColor = billing?.status === 'ok' ? C.success
                                    : billing?.status === 'no_billing' ? C.danger
                                    : C.w30
                                const pacingPct = acc.pacing?.pacing_pct || 0
                                const pacingColor = acc.pacing?.status === 'on_track' ? C.success
                                    : acc.pacing?.status === 'overspend' ? C.danger
                                    : acc.pacing?.status === 'underspend' ? C.warning : C.w30

                                return (
                                    <tr
                                        key={acc.client_id}
                                        onClick={() => handleRowClick(acc)}
                                        style={{ borderBottom: `1px solid ${C.w05}`, cursor: 'pointer', transition: 'background 0.15s' }}
                                        onMouseEnter={e => e.currentTarget.style.background = C.w03}
                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                    >
                                        {/* Konto + badges */}
                                        <td style={TD}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <div>
                                                    <div style={{ fontWeight: 500, color: '#fff', fontSize: 13 }}>{acc.client_name}</div>
                                                    <div style={{ fontSize: 10, color: C.w30, marginTop: 1 }}>{acc.google_customer_id}</div>
                                                </div>
                                                {acc.unresolved_alerts > 0 && (
                                                    <span
                                                        style={{ cursor: 'default', position: 'relative' }}
                                                        onMouseEnter={() => setHoveredAlert(acc.client_id)}
                                                        onMouseLeave={() => setHoveredAlert(null)}
                                                        onClick={e => e.stopPropagation()}
                                                    >
                                                        <Bell size={13} style={{ color: C.danger }} />
                                                        {hoveredAlert === acc.client_id && <AlertTooltip alerts={acc.alert_details} />}
                                                    </span>
                                                )}
                                                {hasNewAccess && (
                                                    <span title={`Nowe dostępy: ${acc.new_access_emails.join(', ')}`} style={{ cursor: 'default' }} onClick={e => e.stopPropagation()}>
                                                        <UserPlus size={13} style={{ color: C.warning }} />
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        {/* Wydatki */}
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            <div>{fmtMoney(acc.spend)}</div>
                                            <SpendChange pct={acc.spend_change_pct} />
                                        </td>
                                        {/* Opcjonalne kolumny */}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.clicks)}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.impressions)}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.ctr_pct != null ? `${acc.ctr_pct}%` : '—'}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.avg_cpc != null ? fmtMoney(acc.avg_cpc) : '—'}</td>}
                                        {/* Konwersje */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.conversions, 1)}</td>
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.conversion_rate_pct != null ? `${acc.conversion_rate_pct}%` : '—'}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.conversion_value > 0 ? fmtMoney(acc.conversion_value) : '—'}</td>}
                                        {/* CPA */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.cpa != null ? fmtMoney(acc.cpa) : '—'}</td>
                                        {/* ROAS */}
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            {acc.roas_pct != null
                                                ? <span style={{ color: acc.roas_pct >= 400 ? C.success : acc.roas_pct >= 200 ? C.accentBlue : C.warning }}>{acc.roas_pct.toFixed(0)}%</span>
                                                : '—'}
                                        </td>
                                        {/* Pacing — progress bars */}
                                        <td style={{ ...TD, minWidth: 120 }}>
                                            {acc.pacing?.status === 'no_data' ? (
                                                <span style={{ fontSize: 10, color: C.w30 }}>Brak danych</span>
                                            ) : (
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 100 }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: C.w40 }}>
                                                        <span>Budżet</span>
                                                        <span>{Math.round(pacingPct)}%</span>
                                                    </div>
                                                    <PacingProgressBar pct={pacingPct} color={pacingColor} height={4} />
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: C.w40 }}>
                                                        <span>Miesiąc</span>
                                                        <span>{acc.pacing?.days_elapsed}/{acc.pacing?.days_in_month}d</span>
                                                    </div>
                                                    <PacingProgressBar pct={acc.pacing?.month_progress_pct || 0} color={C.accentBlue} height={3} />
                                                </div>
                                            )}
                                        </td>
                                        {/* Płatności */}
                                        <td style={{ ...TD, textAlign: 'center', position: 'relative' }}>
                                            <span
                                                style={{ cursor: 'default' }}
                                                onMouseEnter={() => setHoveredBilling(acc.client_id)}
                                                onMouseLeave={() => setHoveredBilling(null)}
                                                onClick={e => e.stopPropagation()}
                                            >
                                                {!billing
                                                    ? <RefreshCw size={11} style={{ color: C.w20, animation: 'spin 1s linear infinite' }} />
                                                    : <CreditCard size={14} style={{ color: billingColor }} />
                                                }
                                                {hoveredBilling === acc.client_id && billing && <BillingTooltip status={billing} />}
                                            </span>
                                        </td>
                                        {/* Zmiany */}
                                        <td style={{ ...TD, textAlign: 'right', cursor: 'pointer' }} onClick={(e) => handleDeepLink(acc, '/action-history', e)} title="Otwórz historię zmian">
                                            <span style={{ color: acc.external_changes > 0 ? C.warning : C.w50 }}>
                                                {acc.total_changes}
                                            </span>
                                            {acc.external_changes > 0 && <div style={{ fontSize: 10, color: C.warning }}>{acc.external_changes} zewn.</div>}
                                            {acc.change_breakdown && Object.keys(acc.change_breakdown).length > 0 && (
                                                <div style={{ fontSize: 9, color: C.w30, marginTop: 1 }}>
                                                    {Object.entries(acc.change_breakdown).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(', ')}
                                                </div>
                                            )}
                                        </td>
                                        {/* Rekomendacje Google */}
                                        <td style={{ ...TD, textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                                            {acc.google_recs_pending > 0 ? (
                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                                                    <span
                                                        style={{ color: C.accentBlue, fontWeight: 500, cursor: 'pointer' }}
                                                        onClick={(e) => handleDeepLink(acc, '/recommendations', e)}
                                                    >
                                                        {acc.google_recs_pending} rek.
                                                    </span>
                                                    <button
                                                        onClick={(e) => handleDismissRecs(acc.client_id, e)}
                                                        disabled={dismissingAll === acc.client_id}
                                                        title="Ukryj w aplikacji (nie wpływa na Google Ads)"
                                                        style={{
                                                            background: C.w04, border: B.subtle, borderRadius: R.sm,
                                                            cursor: 'pointer', padding: '2px 6px',
                                                            color: C.w40, fontSize: 9, opacity: dismissingAll === acc.client_id ? 0.3 : 1,
                                                        }}
                                                    >
                                                        <EyeOff size={10} />
                                                    </button>
                                                </div>
                                            ) : <span style={{ color: C.w20, fontSize: 11 }}>Brak</span>}
                                        </td>
                                        {/* Sync */}
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            <SyncIndicator lastSyncedAt={acc.last_synced_at} syncing={syncing} />
                                        </td>
                                        {/* Actions */}
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                                <a href={googleAdsUrl(acc.google_customer_id)} target="_blank" rel="noopener noreferrer"
                                                    onClick={e => e.stopPropagation()} title="Otwórz w Google Ads"
                                                    style={{ color: C.w20, padding: 2 }}>
                                                    <ExternalLink size={13} />
                                                </a>
                                                <ArrowRight size={14} style={{ color: C.w20 }} />
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                    </div>
                )}
            </div>

            {/* MCC Shared Lists only (no per-account) */}
            <div className={CARD} style={{ marginTop: S['3xl'], overflow: 'hidden' }}>
                <button onClick={() => setSharedOpen(p => !p)} style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                    padding: '12px 16px', background: 'none', border: 'none',
                    color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500,
                }}>
                    {sharedOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <Shield size={14} style={{ color: C.accentPurple }} />
                    Listy wykluczeń MCC
                    {sharedLists && <span style={{ fontSize: 11, color: C.w40, marginLeft: 4 }}>({sharedLists.length})</span>}
                </button>
                {sharedOpen && (
                    <div style={{ borderTop: B.card }}>
                        {!sharedLists ? (
                            <div style={{ padding: 24, textAlign: 'center', color: C.w30, fontSize: 12 }}>
                                <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite', marginBottom: 4 }} />
                                <div>Ładowanie...</div>
                            </div>
                        ) : sharedLists.length === 0 ? (
                            <div style={{ padding: 24, textAlign: 'center', color: C.w30, fontSize: 12 }}>
                                Brak list wykluczeń na poziomie MCC. Listy zarządzane z poziomu konta managera pojawią się tutaj po synchronizacji.
                            </div>
                        ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: B.card }}>
                                        <th style={TH}>Nazwa listy</th>
                                        <th style={{ ...TH, textAlign: 'right' }}>Słów</th>
                                        <th style={TH}>Typ</th>
                                        <th style={TH}>Źródło</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {sharedLists.map(nkl => (
                                        <tr key={nkl.id} style={{ borderBottom: `1px solid ${C.w05}` }}>
                                            <td style={TD}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                    <List size={12} style={{ color: C.accentPurple, flexShrink: 0 }} />
                                                    {nkl.name}
                                                </div>
                                                {nkl.description && <div style={{ fontSize: 10, color: C.w30, marginTop: 1 }}>{nkl.description}</div>}
                                            </td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{nkl.member_count}</td>
                                            <td style={TD_DIM}>Wykluczające słowa</td>
                                            <td style={TD_DIM}>{nkl.source === 'GOOGLE_ADS_SYNC' ? 'Google' : 'Lokalna'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                )}
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
    )
}
