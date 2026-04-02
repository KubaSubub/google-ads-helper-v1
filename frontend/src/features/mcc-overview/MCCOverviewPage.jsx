import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    RefreshCw, TrendingUp, TrendingDown, ArrowRight,
    AlertTriangle, CheckCircle, Minus, Bell, ExternalLink,
    ChevronDown, ChevronRight, ChevronUp, Shield, List,
    UserPlus, X,
} from 'lucide-react'
import {
    getMccOverview, getMccNegativeKeywordLists, getMccSharedLists,
    dismissMccGoogleRecommendations, syncClient,
} from '../../api'
import { useApp } from '../../contexts/AppContext'
import { C, B, T, R, S, CARD, STATUS_COLORS } from '../../constants/designTokens'

const TH = T.th
const TD = T.td
const TD_DIM = T.tdDim

const PACING_STATUS = {
    on_track: { label: 'Na planie', color: STATUS_COLORS.ok },
    underspend: { label: 'Niedowydanie', color: STATUS_COLORS.warning },
    overspend: { label: 'Przekroczenie', color: STATUS_COLORS.danger },
    no_data: { label: 'Brak danych', color: STATUS_COLORS.neutral },
}

const PILLAR_LABELS = {
    performance: 'Wyniki',
    quality: 'Jakość',
    efficiency: 'Efektywność',
    coverage: 'Zasięg',
    stability: 'Stabilność',
    structure: 'Struktura',
}

function healthColor(score) {
    if (score == null) return STATUS_COLORS.neutral
    if (score >= 70) return STATUS_COLORS.ok
    if (score >= 40) return STATUS_COLORS.warning
    return STATUS_COLORS.danger
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

function StatusPill({ label, color }) {
    return (
        <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: R.pill,
            fontSize: 10, fontWeight: 500,
            background: color.border, color: color.valueFill,
            border: `1px solid ${color.border}`,
        }}>
            {label}
        </span>
    )
}

function SyncIndicator({ lastSyncedAt, syncing }) {
    if (syncing) return <RefreshCw size={13} style={{ color: C.accentBlue, animation: 'spin 1s linear infinite' }} />
    if (!lastSyncedAt) return <span style={{ color: C.w30, fontSize: 11 }}>Nigdy</span>
    const ago = Date.now() - new Date(lastSyncedAt).getTime()
    const hours = Math.floor(ago / 3_600_000)
    const label = hours < 1 ? '<1h' : `${hours}h`
    const stale = hours > 6
    return (
        <span style={{ fontSize: 11, color: stale ? C.warning : C.w50 }}>
            {stale && <AlertTriangle size={11} style={{ marginRight: 3, verticalAlign: -1 }} />}
            {label}
        </span>
    )
}

function HealthTooltip({ health }) {
    if (!health?.pillars || Object.keys(health.pillars).length === 0) return null
    return (
        <div style={{
            position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
            marginBottom: 6, padding: '8px 10px', borderRadius: R.md, minWidth: 140,
            background: C.surfaceElevated, border: B.hover,
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)', zIndex: 10,
            fontSize: 11, color: C.w70,
        }}>
            {Object.entries(health.pillars).map(([key, score]) => {
                const hc = healthColor(score)
                return (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '2px 0' }}>
                        <span>{PILLAR_LABELS[key] || key}</span>
                        <span style={{ color: hc.valueFill, fontWeight: 600 }}>{score ?? '—'}</span>
                    </div>
                )
            })}
        </div>
    )
}

function SortHeader({ label, field, sortBy, sortDir, onSort, align }) {
    const active = sortBy === field
    return (
        <th style={{ ...TH, textAlign: align || 'left', cursor: 'pointer', userSelect: 'none' }} onClick={() => onSort(field)}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                {label}
                {active && (sortDir === 'asc'
                    ? <ChevronUp size={10} style={{ opacity: 0.6 }} />
                    : <ChevronDown size={10} style={{ opacity: 0.6 }} />
                )}
            </span>
        </th>
    )
}

function fmtNum(n, decimals = 0) {
    if (n == null) return '—'
    return n.toLocaleString('en-US', { maximumFractionDigits: decimals })
}

function fmtUsd(n) {
    if (n == null) return '—'
    return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function googleAdsUrl(googleCustomerId) {
    const clean = googleCustomerId?.replace(/-/g, '') || ''
    return `https://ads.google.com/aw/overview?ocid=${clean}`
}

// ─────────────────────────────────────────────────────────────────────────────

export default function MCCOverviewPage() {
    const navigate = useNavigate()
    const { setSelectedClientId, showToast } = useApp()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [syncingIds, setSyncingIds] = useState(new Set())
    const [nklData, setNklData] = useState(null)
    const [nklOpen, setNklOpen] = useState(false)
    const [sharedLists, setSharedLists] = useState(null)
    const [sharedOpen, setSharedOpen] = useState(false)
    const [sortBy, setSortBy] = useState('spend_30d_usd')
    const [sortDir, setSortDir] = useState('desc')
    const [hoveredHealth, setHoveredHealth] = useState(null)
    const [dismissingAll, setDismissingAll] = useState(null) // client_id being dismissed

    const load = useCallback(async () => {
        try {
            setLoading(true)
            const result = await getMccOverview()
            setData(result)
        } catch {
            showToast?.('Błąd ładowania MCC overview', 'error')
        } finally {
            setLoading(false)
        }
    }, [showToast])

    useEffect(() => { load() }, [load])

    // Lazy load collapsible sections
    useEffect(() => {
        if (nklOpen && !nklData) {
            getMccNegativeKeywordLists().then(setNklData).catch(() => {})
        }
    }, [nklOpen, nklData])

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

    const handleDismissAll = async (clientId, e) => {
        e.stopPropagation()
        setDismissingAll(clientId)
        try {
            const result = await dismissMccGoogleRecommendations({ client_id: clientId, dismiss_all: true })
            showToast?.(`Odrzucono ${result.dismissed} rekomendacji`, 'success')
            load() // refresh data
        } catch {
            showToast?.('Błąd odrzucania rekomendacji', 'error')
        } finally {
            setDismissingAll(null)
        }
    }

    const rawAccounts = data?.accounts || []

    const accounts = useMemo(() => {
        const sorted = [...rawAccounts]
        sorted.sort((a, b) => {
            let va, vb
            if (sortBy === 'health') { va = a.health?.score ?? -1; vb = b.health?.score ?? -1 }
            else { va = a[sortBy] ?? -Infinity; vb = b[sortBy] ?? -Infinity }
            return sortDir === 'asc' ? va - vb : vb - va
        })
        return sorted
    }, [rawAccounts, sortBy, sortDir])

    // Aggregated totals
    const totalSpend = accounts.reduce((s, a) => s + (a.spend_30d_usd || 0), 0)
    const totalClicks = accounts.reduce((s, a) => s + (a.clicks_30d || 0), 0)
    const totalConv = accounts.reduce((s, a) => s + (a.conversions_30d || 0), 0)
    const totalImpr = accounts.reduce((s, a) => s + (a.impressions_30d || 0), 0)

    return (
        <div style={{ padding: '24px 32px', maxWidth: 1600 }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: S['5xl'] }}>
                <div>
                    <h1 style={T.pageTitle}>Wszystkie konta</h1>
                    <p style={T.pageSubtitle}>
                        Przegląd MCC — {accounts.length} {accounts.length === 1 ? 'konto' : 'kont'}
                    </p>
                </div>
                <button onClick={handleSyncAll} style={{
                    display: 'flex', alignItems: 'center', gap: S.sm, padding: '7px 14px',
                    borderRadius: R.md, background: C.infoBg, border: B.info,
                    color: C.accentBlue, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                }}>
                    <RefreshCw size={13} /> Synchronizuj nieaktualne
                </button>
            </div>

            {/* KPI strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: S.xl, marginBottom: S['4xl'] }}>
                {[
                    { label: 'Wydatki 30d', value: fmtUsd(totalSpend) },
                    { label: 'Kliknięcia', value: fmtNum(totalClicks) },
                    { label: 'Wyświetlenia', value: fmtNum(totalImpr) },
                    { label: 'Konwersje', value: fmtNum(totalConv, 1) },
                    { label: 'Avg. CTR', value: totalImpr > 0 ? `${(totalClicks / totalImpr * 100).toFixed(2)}%` : '—' },
                ].map(kpi => (
                    <div key={kpi.label} className={CARD} style={{ padding: '14px 16px' }}>
                        <div style={T.kpiLabel}>{kpi.label}</div>
                        <div style={{ ...T.kpiValue, fontSize: 18, marginTop: 2 }}>{kpi.value}</div>
                    </div>
                ))}
            </div>

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
                                <SortHeader label="Wydatki" field="spend_30d_usd" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="Kliknięcia" field="clicks_30d" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="Wyśw." field="impressions_30d" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="CTR" field="ctr_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="CPC" field="avg_cpc_usd" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="Conv." field="conversions_30d" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="CVR" field="conversion_rate_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="Wart. konw." field="conversion_value_usd" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="CPA" field="cpa_usd" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="ROAS" field="roas_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <th style={TH}>Pacing</th>
                                <SortHeader label="Health" field="health" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="center" />
                                <SortHeader label="Zmiany" field="total_changes_30d" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="Rek." field="google_recs_pending" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <th style={{ ...TH, textAlign: 'center' }}>Sync</th>
                                <th style={{ ...TH, width: 60 }}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {accounts.map(acc => {
                                const pacing = PACING_STATUS[acc.pacing?.status] || PACING_STATUS.no_data
                                const healthScore = acc.health?.score ?? null
                                const hc = healthColor(healthScore)
                                const syncing = syncingIds.has(acc.client_id)
                                const hasNewAccess = acc.new_access_emails?.length > 0
                                return (
                                    <tr
                                        key={acc.client_id}
                                        onClick={() => handleRowClick(acc)}
                                        style={{ borderBottom: `1px solid ${C.w05}`, cursor: 'pointer', transition: 'background 0.15s' }}
                                        onMouseEnter={e => e.currentTarget.style.background = C.w03}
                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                    >
                                        {/* Konto */}
                                        <td style={TD}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <div>
                                                    <div style={{ fontWeight: 500, color: '#fff', fontSize: 13 }}>{acc.client_name}</div>
                                                    <div style={{ fontSize: 10, color: C.w30, marginTop: 1 }}>{acc.google_customer_id}</div>
                                                </div>
                                                {acc.unresolved_alerts > 0 && (
                                                    <span title={`${acc.unresolved_alerts} alertów`} onClick={(e) => handleDeepLink(acc, '/alerts', e)} style={{ cursor: 'pointer' }}>
                                                        <Bell size={13} style={{ color: C.danger }} />
                                                    </span>
                                                )}
                                                {hasNewAccess && (
                                                    <span title={`Nowe dostępy: ${acc.new_access_emails.join(', ')}`} onClick={(e) => handleDeepLink(acc, '/action-history', e)} style={{ cursor: 'pointer' }}>
                                                        <UserPlus size={13} style={{ color: C.warning }} />
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        {/* Wydatki */}
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            <div>{fmtUsd(acc.spend_30d_usd)}</div>
                                            <SpendChange pct={acc.spend_change_pct} />
                                        </td>
                                        {/* Kliknięcia */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.clicks_30d)}</td>
                                        {/* Wyświetlenia */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.impressions_30d)}</td>
                                        {/* CTR */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.ctr_pct != null ? `${acc.ctr_pct}%` : <span style={{ color: C.w30 }}>—</span>}</td>
                                        {/* CPC */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.avg_cpc_usd != null ? fmtUsd(acc.avg_cpc_usd) : <span style={{ color: C.w30 }}>—</span>}</td>
                                        {/* Konwersje */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.conversions_30d, 1)}</td>
                                        {/* CVR */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.conversion_rate_pct != null ? `${acc.conversion_rate_pct}%` : <span style={{ color: C.w30 }}>—</span>}</td>
                                        {/* Wartość konwersji */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.conversion_value_usd > 0 ? fmtUsd(acc.conversion_value_usd) : <span style={{ color: C.w30 }}>—</span>}</td>
                                        {/* CPA */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.cpa_usd != null ? fmtUsd(acc.cpa_usd) : <span style={{ color: C.w30 }}>—</span>}</td>
                                        {/* ROAS */}
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            {acc.roas_pct != null
                                                ? <span style={{ color: acc.roas_pct >= 400 ? C.success : acc.roas_pct >= 200 ? C.accentBlue : C.warning }}>{acc.roas_pct.toFixed(0)}%</span>
                                                : <span style={{ color: C.w30 }}>—</span>}
                                        </td>
                                        {/* Pacing */}
                                        <td style={TD}>
                                            <StatusPill label={pacing.label} color={pacing.color} />
                                            {acc.pacing?.pacing_pct > 0 && (
                                                <span style={{ fontSize: 10, color: C.w40, marginLeft: 6 }}>{acc.pacing.pacing_pct}%</span>
                                            )}
                                        </td>
                                        {/* Health */}
                                        <td style={{ ...TD, textAlign: 'center', position: 'relative' }}>
                                            {healthScore != null ? (
                                                <span
                                                    onMouseEnter={() => setHoveredHealth(acc.client_id)}
                                                    onMouseLeave={() => setHoveredHealth(null)}
                                                    style={{
                                                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                                        width: 32, height: 32, borderRadius: '50%',
                                                        background: hc.border, color: hc.valueFill,
                                                        fontSize: 12, fontWeight: 600, cursor: 'default',
                                                    }}
                                                >
                                                    {healthScore}
                                                    {hoveredHealth === acc.client_id && <HealthTooltip health={acc.health} />}
                                                </span>
                                            ) : <Minus size={14} style={{ color: C.w20 }} />}
                                        </td>
                                        {/* Zmiany */}
                                        <td style={{ ...TD, textAlign: 'right', cursor: 'pointer' }} onClick={(e) => handleDeepLink(acc, '/action-history', e)} title="Otwórz historię zmian">
                                            <span style={{ color: acc.external_changes_30d > 0 ? C.warning : C.w50 }}>{acc.total_changes_30d}</span>
                                            {acc.external_changes_30d > 0 && <div style={{ fontSize: 10, color: C.warning }}>{acc.external_changes_30d} zewn.</div>}
                                        </td>
                                        {/* Rekomendacje Google + dismiss */}
                                        <td style={{ ...TD, textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                                            {acc.google_recs_pending > 0 ? (
                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 4 }}>
                                                    <span
                                                        style={{ color: C.accentBlue, fontWeight: 500, cursor: 'pointer' }}
                                                        onClick={(e) => handleDeepLink(acc, '/recommendations', e)}
                                                        title="Otwórz rekomendacje"
                                                    >
                                                        {acc.google_recs_pending}
                                                    </span>
                                                    <button
                                                        onClick={(e) => handleDismissAll(acc.client_id, e)}
                                                        disabled={dismissingAll === acc.client_id}
                                                        title="Odrzuć wszystkie rekomendacje Google"
                                                        style={{
                                                            background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                                                            color: C.w30, opacity: dismissingAll === acc.client_id ? 0.3 : 1,
                                                        }}
                                                    >
                                                        <X size={12} />
                                                    </button>
                                                </div>
                                            ) : <CheckCircle size={13} style={{ color: C.w15 }} />}
                                        </td>
                                        {/* Sync */}
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            <SyncIndicator lastSyncedAt={acc.last_synced_at} syncing={syncing} />
                                        </td>
                                        {/* Actions */}
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                                <a href={googleAdsUrl(acc.google_customer_id)} target="_blank" rel="noopener noreferrer"
                                                    onClick={(e) => e.stopPropagation()} title="Otwórz w Google Ads"
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

            {/* MCC Shared Lists */}
            <CollapsibleSection
                open={sharedOpen}
                onToggle={() => setSharedOpen(p => !p)}
                icon={<Shield size={14} style={{ color: C.accentPurple }} />}
                title="Listy wykluczeń MCC"
                count={sharedLists?.length}
            >
                {!sharedLists ? <LoadingPlaceholder /> : sharedLists.length === 0 ? (
                    <EmptyPlaceholder text="Brak list wykluczeń na poziomie MCC." />
                ) : (
                    <NklTable data={sharedLists} onRowClick={(nkl) => { setSelectedClientId(nkl.client_id); navigate('/keywords') }} showLevel />
                )}
            </CollapsibleSection>

            {/* Per-account NKL */}
            <CollapsibleSection
                open={nklOpen}
                onToggle={() => setNklOpen(p => !p)}
                icon={<List size={14} style={{ color: C.w50 }} />}
                title="Listy wykluczeń per konto"
                count={nklData?.length}
            >
                {!nklData ? <LoadingPlaceholder /> : nklData.length === 0 ? (
                    <EmptyPlaceholder text="Brak list wykluczających słów kluczowych." />
                ) : (
                    <NklTable data={nklData} onRowClick={(nkl) => { setSelectedClientId(nkl.client_id); navigate('/keywords') }} />
                )}
            </CollapsibleSection>

            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
    )
}

// ─── Shared sub-components ───────────────────────────────────────────────────

function CollapsibleSection({ open, onToggle, icon, title, count, children }) {
    return (
        <div className={CARD} style={{ marginTop: S['3xl'], overflow: 'hidden' }}>
            <button onClick={onToggle} style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '12px 16px', background: 'none', border: 'none',
                color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500,
            }}>
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                {icon}
                {title}
                {count != null && <span style={{ fontSize: 11, color: C.w40, marginLeft: 4 }}>({count})</span>}
            </button>
            {open && <div style={{ borderTop: B.card }}>{children}</div>}
        </div>
    )
}

function LoadingPlaceholder() {
    return (
        <div style={{ padding: 24, textAlign: 'center', color: C.w30, fontSize: 12 }}>
            <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite', marginBottom: 4 }} />
            <div>Ładowanie...</div>
        </div>
    )
}

function EmptyPlaceholder({ text }) {
    return <div style={{ padding: 24, textAlign: 'center', color: C.w30, fontSize: 12 }}>{text}</div>
}

function NklTable({ data, onRowClick, showLevel }) {
    return (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
                <tr style={{ borderBottom: B.card }}>
                    <th style={TH}>Konto</th>
                    <th style={TH}>Nazwa listy</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Słów</th>
                    <th style={TH}>Źródło</th>
                    {showLevel && <th style={TH}>Poziom</th>}
                    <th style={TH}>Status</th>
                </tr>
            </thead>
            <tbody>
                {data.map(nkl => (
                    <tr key={nkl.id} style={{ borderBottom: `1px solid ${C.w05}`, cursor: 'pointer' }}
                        onClick={() => onRowClick(nkl)}
                        onMouseEnter={e => e.currentTarget.style.background = C.w03}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <td style={TD_DIM}>{nkl.client_name}</td>
                        <td style={TD}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <List size={12} style={{ color: C.accentPurple, flexShrink: 0 }} />
                                {nkl.name}
                            </div>
                            {nkl.description && <div style={{ fontSize: 10, color: C.w30, marginTop: 1 }}>{nkl.description}</div>}
                        </td>
                        <td style={{ ...TD, textAlign: 'right' }}>{nkl.member_count}</td>
                        <td style={TD_DIM}>
                            <StatusPill
                                label={nkl.source === 'GOOGLE_ADS_SYNC' ? 'Google' : 'Lokalna'}
                                color={nkl.source === 'GOOGLE_ADS_SYNC' ? STATUS_COLORS.info : STATUS_COLORS.neutral}
                            />
                        </td>
                        {showLevel && (
                            <td style={TD_DIM}>
                                <StatusPill
                                    label={nkl.level === 'mcc' ? 'MCC' : 'Konto'}
                                    color={nkl.level === 'mcc' ? STATUS_COLORS.info : STATUS_COLORS.neutral}
                                />
                            </td>
                        )}
                        <td style={TD_DIM}>
                            <StatusPill
                                label={nkl.status === 'ENABLED' ? 'Aktywna' : nkl.status}
                                color={nkl.status === 'ENABLED' ? STATUS_COLORS.ok : STATUS_COLORS.neutral}
                            />
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}
