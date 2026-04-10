import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    RefreshCw, TrendingUp, TrendingDown, ArrowRight,
    Bell, ExternalLink, Search,
    ChevronDown, ChevronRight, Shield, List,
    UserPlus, CreditCard, Columns, Globe, Ban,
} from 'lucide-react'
import {
    getMccOverview, getMccSharedLists, getMccSharedListItems,
    syncClient,
    discoverClients,
} from '../../api'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import { LineChart, Line, Tooltip } from 'recharts'
import PacingProgressBar from '../../components/modules/PacingProgressBar'
import { C, B, T, R, S, CARD } from '../../constants/designTokens'

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

function currSym(currency) {
    if (currency === 'USD') return '$'
    if (currency === 'EUR') return '€'
    return 'zł'
}

function fmtMoneyC(n, currency) {
    if (n == null) return '—'
    const formatted = fmtMoney(n)
    const sym = currSym(currency)
    return currency === 'USD' ? `$${formatted}` : `${formatted} ${sym}`
}

function SpendSparkline({ data }) {
    if (!data || data.length < 2) return null
    return (
        <div style={{ display: 'inline-block', verticalAlign: 'middle', marginLeft: 6 }}>
            <LineChart width={56} height={20} data={data}>
                <Tooltip
                    contentStyle={{ background: C.surfaceElevated, border: B.hover, borderRadius: 6, fontSize: 10, padding: '4px 8px' }}
                    formatter={v => [fmtMoney(v), 'Wydatki']}
                    labelFormatter={d => d}
                />
                <Line type="monotone" dataKey="spend" stroke={C.accentBlue} dot={false} strokeWidth={1.5} isAnimationActive={false} />
            </LineChart>
        </div>
    )
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

const PERIODS = [
    { label: '7d', value: 7 },
    { label: '14d', value: 14 },
    { label: '30d', value: 30 },
    { label: 'MTD', value: 'this_month' },
]

export default function MCCOverviewPage() {
    const navigate = useNavigate()
    const { setSelectedClientId, showToast, refreshClients } = useApp()
    const { filters, setFilter, dateParams } = useFilter()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [syncingIds, setSyncingIds] = useState(new Set())
    const [sharedData, setSharedData] = useState(null)
    const [sharedOpen, setSharedOpen] = useState(false)
    const [expandedList, setExpandedList] = useState(null) // { id, type, items, loading }
    const [sortBy, setSortBy] = useState('spend')
    const [sortDir, setSortDir] = useState('desc')
    const [compactMode, setCompactMode] = useState(true)
    const [billingStatuses, setBillingStatuses] = useState({})
    const [hoveredAlert, setHoveredAlert] = useState(null)
    const [hoveredBilling, setHoveredBilling] = useState(null)
    const [selectedIds, setSelectedIds] = useState(new Set())

    const load = useCallback(async () => {
        try {
            setLoading(true)
            const result = await getMccOverview(dateParams)
            setData(result)
        } catch {
            showToast?.('Błąd ładowania MCC overview', 'error')
        } finally {
            setLoading(false)
        }
    }, [showToast, dateParams])

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

    // Lazy load MCC exclusion lists
    useEffect(() => {
        if (sharedOpen && !sharedData) {
            getMccSharedLists().then(setSharedData).catch(() => setSharedData({ keyword_lists: [], placement_lists: [] }))
        }
    }, [sharedOpen, sharedData])

    const toggleListExpand = async (listId, listType) => {
        if (expandedList?.id === listId && expandedList?.type === listType) {
            setExpandedList(null)
            return
        }
        setExpandedList({ id: listId, type: listType, items: null, loading: true })
        try {
            const result = await getMccSharedListItems(listId, listType)
            setExpandedList({ id: listId, type: listType, items: result.items || [], loading: false })
        } catch {
            setExpandedList({ id: listId, type: listType, items: [], loading: false })
        }
    }

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

    // /sync/trigger is a 24-phase full sync. Real measurements show 20-45s per
    // client under contention. Default axios timeout (30s) is not enough —
    // use 3 minutes per client to cover worst case.
    const SYNC_CALL_TIMEOUT_MS = 180_000

    // Shared sync routine. Returns { ok, message } — never throws.
    // `silent=true` suppresses toast (used by bulk flow which shows an aggregate toast).
    const runSync = async (clientId, { silent = false } = {}) => {
        setSyncingIds(prev => new Set(prev).add(clientId))
        try {
            const result = await syncClient(clientId, 30, { timeout: SYNC_CALL_TIMEOUT_MS })
            if (result?.success) {
                if (!silent) showToast?.('Synchronizacja zakończona', 'success')
                return { ok: true }
            }
            const msg = result?.message || 'Synchronizacja nie powiodła się'
            if (!silent) showToast?.(msg, 'error')
            return { ok: false, message: msg }
        } catch (err) {
            const isTimeout = /timeout/i.test(err?.message || '')
            const msg = isTimeout ? 'Synchronizacja przekroczyła limit czasu' : 'Błąd synchronizacji'
            if (!silent) showToast?.(msg, 'error')
            return { ok: false, message: msg }
        } finally {
            setSyncingIds(prev => { const n = new Set(prev); n.delete(clientId); return n })
        }
    }

    const handleSync = async (clientId, e) => {
        e.stopPropagation()
        const result = await runSync(clientId)
        if (result.ok) {
            refreshClients()
            load()
        }
    }

    const handleSyncAll = async () => {
        if (!data?.accounts?.length) return
        if (syncingIds.size > 0) return // prevent re-entry while a sync is running
        const staleThreshold = 6 * 60 * 60 * 1000
        const stale = data.accounts.filter(acc =>
            !acc.last_synced_at || Date.now() - new Date(acc.last_synced_at).getTime() > staleThreshold
        )
        if (!stale.length) { showToast?.('Wszystkie konta aktualne', 'info'); return }

        // Run syncs sequentially. Parallel syncs hit Google Ads API rate limits
        // and SQLite write contention, pushing latency above the axios timeout
        // and causing deterministic failures.
        const targets = stale.slice(0, 3)
        let ok = 0
        let failed = 0
        showToast?.(`Synchronizuję 0/${targets.length}...`, 'info', 120_000)
        for (let i = 0; i < targets.length; i++) {
            const acc = targets[i]
            showToast?.(`Synchronizuję ${i + 1}/${targets.length}: ${acc.client_name}`, 'info', 120_000)
            const res = await runSync(acc.client_id, { silent: true })
            if (res.ok) ok++; else failed++
        }
        if (failed === 0) {
            showToast?.(`Zsynchronizowano ${ok}/${targets.length} kont`, 'success')
        } else {
            showToast?.(`Zsynchronizowano ${ok}/${targets.length} (${failed} z błędami)`, ok > 0 ? 'info' : 'error')
        }
        refreshClients()
        load()
    }

    const handleDiscover = async () => {
        try {
            const result = await discoverClients()
            const added = result?.added || 0
            if (added > 0) {
                showToast?.(`Odkryto ${added} ${added === 1 ? 'nowe konto' : 'nowych kont'}`, 'success')
                refreshClients()
                load()
            } else {
                showToast?.('Brak nowych kont w MCC', 'info')
            }
        } catch {
            showToast?.('Błąd wykrywania kont', 'error')
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
    const hasAnyIS = accounts.some(a => a.search_impression_share_pct != null)
    const uniqueCurrencies = [...new Set(accounts.map(a => a.currency).filter(Boolean))]
    const sharedCurrency = uniqueCurrencies.length === 1 ? uniqueCurrencies[0] : null

    const toggleSelect = (clientId, e) => {
        e.stopPropagation()
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(clientId)) next.delete(clientId)
            else next.add(clientId)
            return next
        })
    }

    const toggleSelectAll = () => {
        if (selectedIds.size === accounts.length) setSelectedIds(new Set())
        else setSelectedIds(new Set(accounts.map(a => a.client_id)))
    }

    const handleBulkSync = async () => {
        if (!selectedIds.size) return
        if (syncingIds.size > 0) return
        const ids = [...selectedIds]
        let ok = 0
        let failed = 0
        for (let i = 0; i < ids.length; i++) {
            showToast?.(`Synchronizuję ${i + 1}/${ids.length}`, 'info', 120_000)
            const res = await runSync(ids[i], { silent: true })
            if (res.ok) ok++; else failed++
        }
        showToast?.(
            failed === 0
                ? `Zsynchronizowano ${ok}/${ids.length} kont`
                : `Zsynchronizowano ${ok}/${ids.length} (${failed} z błędami)`,
            failed === 0 ? 'success' : (ok > 0 ? 'info' : 'error'),
        )
        refreshClients()
        load()
    }

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
                    <div style={{ display: 'flex', gap: 4, marginRight: 8 }}>
                        {PERIODS.map(p => (
                            <button
                                key={p.label}
                                onClick={() => setFilter('period', p.value)}
                                style={{
                                    padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                                    border: `1px solid ${filters.period === p.value ? C.accentBlue : C.w08}`,
                                    background: filters.period === p.value ? C.accentBlueBg : C.w04,
                                    color: filters.period === p.value ? 'white' : C.textPlaceholder,
                                    cursor: 'pointer', transition: 'all 0.15s',
                                }}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                    <button onClick={() => setCompactMode(p => !p)} title={compactMode ? 'Pokaż wszystkie kolumny' : 'Tryb kompaktowy'} style={{
                        display: 'flex', alignItems: 'center', gap: S.sm, padding: '7px 10px',
                        borderRadius: R.md, background: compactMode ? C.infoBg : C.w04, border: compactMode ? B.info : B.subtle,
                        color: compactMode ? C.accentBlue : C.w50, fontSize: 12, cursor: 'pointer',
                    }}>
                        <Columns size={13} />
                    </button>
                    <button onClick={handleSyncAll} disabled={syncingIds.size > 0} style={{
                        display: 'flex', alignItems: 'center', gap: S.sm, padding: '7px 14px',
                        borderRadius: R.md, background: C.infoBg, border: B.info,
                        color: C.accentBlue, fontSize: 12, fontWeight: 500,
                        cursor: syncingIds.size > 0 ? 'wait' : 'pointer',
                        opacity: syncingIds.size > 0 ? 0.6 : 1,
                    }}>
                        <RefreshCw size={13} className={syncingIds.size > 0 ? 'animate-spin' : ''} /> Synchronizuj nieaktualne
                    </button>
                    <button onClick={handleDiscover} style={{
                        display: 'flex', alignItems: 'center', gap: S.sm, padding: '7px 14px',
                        borderRadius: R.md, background: C.w04, border: B.subtle,
                        color: C.w50, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                    }}>
                        <Search size={13} /> Odkryj konta
                    </button>
                </div>
            </div>

            {/* KPI strip */}
            {(() => {
                const kpis = [
                    { label: 'Wydatki', value: sharedCurrency ? fmtMoneyC(totalSpend, sharedCurrency) : fmtMoney(totalSpend) },
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
                {selectedIds.size > 0 && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '8px 16px', background: C.infoBg, borderBottom: B.info,
                    }}>
                        <span style={{ fontSize: 12, color: C.accentBlue, fontWeight: 500 }}>
                            Zaznaczono: {selectedIds.size}
                        </span>
                        <button onClick={handleBulkSync} style={{
                            display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
                            borderRadius: R.md, background: C.w04, border: B.subtle,
                            color: C.accentBlue, fontSize: 11, cursor: 'pointer',
                        }}>
                            <RefreshCw size={11} /> Synchronizuj
                        </button>
                    </div>
                )}
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
                                <th style={{ ...TH, width: 36, textAlign: 'center', padding: '8px 4px' }}>
                                    <input
                                        type="checkbox"
                                        checked={selectedIds.size === accounts.length && accounts.length > 0}
                                        onChange={toggleSelectAll}
                                        style={{ cursor: 'pointer', accentColor: C.accentBlue }}
                                    />
                                </th>
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
                                {hasAnyIS && <SortHeader label="IS" field="search_impression_share_pct" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />}
                                <SortHeader label="Health" field="health_score" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="center" />
                                <th style={{ ...TH, minWidth: 120 }}>Pacing</th>
                                <th style={{ ...TH, textAlign: 'center' }}>Płatności</th>
                                <SortHeader label="Zmiany" field="total_changes" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
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
                                        {/* Checkbox */}
                                        <td style={{ ...TD, textAlign: 'center', width: 36, padding: '8px 4px' }} onClick={e => toggleSelect(acc.client_id, e)}>
                                            <input type="checkbox" checked={selectedIds.has(acc.client_id)} readOnly style={{ cursor: 'pointer', accentColor: C.accentBlue }} />
                                        </td>
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
                                        {/* Wydatki + sparkline */}
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                                                <span>{fmtMoneyC(acc.spend, acc.currency)}</span>
                                                <SpendSparkline data={acc.spend_trend} />
                                            </div>
                                            <SpendChange pct={acc.spend_change_pct} />
                                        </td>
                                        {/* Opcjonalne kolumny */}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.clicks)}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.impressions)}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.ctr_pct != null ? `${acc.ctr_pct}%` : '—'}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.avg_cpc != null ? fmtMoneyC(acc.avg_cpc, acc.currency) : '—'}</td>}
                                        {/* Konwersje */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(acc.conversions, 1)}</td>
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.conversion_rate_pct != null ? `${acc.conversion_rate_pct}%` : '—'}</td>}
                                        {!compactMode && <td style={{ ...TD, textAlign: 'right' }}>{acc.conversion_value > 0 ? fmtMoneyC(acc.conversion_value, acc.currency) : '—'}</td>}
                                        {/* CPA */}
                                        <td style={{ ...TD, textAlign: 'right' }}>{acc.cpa != null ? fmtMoneyC(acc.cpa, acc.currency) : '—'}</td>
                                        {/* ROAS */}
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            {acc.roas_pct != null
                                                ? <span style={{ color: acc.roas_pct >= 400 ? C.success : acc.roas_pct >= 200 ? C.accentBlue : C.warning }}>{acc.roas_pct.toFixed(0)}%</span>
                                                : '—'}
                                        </td>
                                        {/* Impression Share — hidden when no account has IS data */}
                                        {hasAnyIS && (
                                            <td style={{ ...TD, textAlign: 'right' }}>
                                                {acc.search_impression_share_pct != null
                                                    ? <span style={{ color: acc.search_impression_share_pct >= 60 ? C.success : acc.search_impression_share_pct >= 30 ? C.warning : C.danger }}>
                                                        {acc.search_impression_share_pct.toFixed(1)}%
                                                    </span>
                                                    : '—'}
                                            </td>
                                        )}
                                        {/* Health Score */}
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            {acc.health_score != null ? (
                                                <div title={`Health Score: ${acc.health_score}/100`} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                                                    <svg width={24} height={24} viewBox="0 0 24 24">
                                                        <circle cx={12} cy={12} r={10} fill="none" stroke={C.w08} strokeWidth={2.5} />
                                                        <circle cx={12} cy={12} r={10} fill="none"
                                                            stroke={acc.health_score >= 80 ? C.success : acc.health_score >= 50 ? C.warning : C.danger}
                                                            strokeWidth={2.5}
                                                            strokeDasharray={`${acc.health_score * 0.628} 62.8`}
                                                            strokeLinecap="round"
                                                            transform="rotate(-90 12 12)"
                                                        />
                                                        <text x={12} y={12} textAnchor="middle" dominantBaseline="central"
                                                            fill={acc.health_score >= 80 ? C.success : acc.health_score >= 50 ? C.warning : C.danger}
                                                            fontSize={7} fontWeight={600}>
                                                            {acc.health_score}
                                                        </text>
                                                    </svg>
                                                </div>
                                            ) : <span style={{ color: C.w20, fontSize: 11 }}>—</span>}
                                        </td>
                                        {/* Pacing — progress bars with tooltip */}
                                        <td style={{ ...TD, minWidth: 120 }}
                                            title={acc.pacing?.status !== 'no_data' ? `Budżet: ${fmtMoneyC(acc.pacing?.budget, acc.currency)} | Wydano: ${fmtMoneyC(acc.pacing?.spent, acc.currency)}` : undefined}>
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

            {/* MCC Exclusion Lists — keywords + placements */}
            <div className={CARD} style={{ marginTop: S['3xl'], overflow: 'hidden' }}>
                <button onClick={() => setSharedOpen(p => !p)} style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                    padding: '12px 16px', background: 'none', border: 'none',
                    color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500,
                }}>
                    {sharedOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <Shield size={14} style={{ color: C.accentPurple }} />
                    Wykluczenia MCC
                    {sharedData && (
                        <span style={{ fontSize: 11, color: C.w40, marginLeft: 4 }}>
                            ({(sharedData.keyword_lists?.length || 0) + (sharedData.placement_lists?.length || 0)} list)
                        </span>
                    )}
                </button>
                {sharedOpen && (
                    <div style={{ borderTop: B.card }}>
                        {!sharedData ? (
                            <div style={{ padding: 24, textAlign: 'center', color: C.w30, fontSize: 12 }}>
                                <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite', marginBottom: 4 }} />
                                <div>Ładowanie...</div>
                            </div>
                        ) : (
                            <>
                                {/* Negative Keyword Lists */}
                                <div style={{ padding: '10px 16px 4px', display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <Ban size={13} style={{ color: C.accentPurple }} />
                                    <span style={{ fontSize: 12, fontWeight: 600, color: C.w60 }}>Wykluczające frazy MCC</span>
                                    <span style={{ fontSize: 10, color: C.w30 }}>({sharedData.keyword_lists?.length || 0})</span>
                                </div>
                                {(!sharedData.keyword_lists || sharedData.keyword_lists.length === 0) ? (
                                    <div style={{ padding: '8px 16px 16px', color: C.w30, fontSize: 11 }}>
                                        Brak list wykluczających fraz na poziomie MCC. Pojawią się po synchronizacji konta managera.
                                    </div>
                                ) : (
                                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                        <thead>
                                            <tr style={{ borderBottom: B.card }}>
                                                <th style={{ ...TH, width: 28 }}></th>
                                                <th style={TH}>Nazwa listy</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Fraz</th>
                                                <th style={TH}>Źródło</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sharedData.keyword_lists.map(nkl => {
                                                const isExpanded = expandedList?.id === nkl.id && expandedList?.type === 'keyword'
                                                return [
                                                    <tr key={nkl.id} onClick={() => toggleListExpand(nkl.id, 'keyword')}
                                                        style={{ borderBottom: `1px solid ${C.w05}`, cursor: 'pointer' }}
                                                        onMouseEnter={e => e.currentTarget.style.background = C.w03}
                                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                                                        <td style={{ ...TD, textAlign: 'center', padding: '6px 4px' }}>
                                                            {isExpanded ? <ChevronDown size={12} style={{ color: C.w40 }} /> : <ChevronRight size={12} style={{ color: C.w30 }} />}
                                                        </td>
                                                        <td style={TD}>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                                <List size={12} style={{ color: C.accentPurple, flexShrink: 0 }} />
                                                                {nkl.name}
                                                            </div>
                                                            {nkl.description && <div style={{ fontSize: 10, color: C.w30, marginTop: 1, marginLeft: 18 }}>{nkl.description}</div>}
                                                        </td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{nkl.item_count}</td>
                                                        <td style={TD_DIM}>{nkl.source === 'MCC_SYNC' || nkl.source === 'GOOGLE_ADS_SYNC' ? 'Google MCC' : 'Lokalna'}</td>
                                                    </tr>,
                                                    isExpanded && (
                                                        <tr key={`${nkl.id}-items`}>
                                                            <td colSpan={4} style={{ padding: 0, background: 'rgba(79,142,247,0.03)' }}>
                                                                {expandedList?.loading ? (
                                                                    <div style={{ padding: 12, textAlign: 'center', color: C.w30, fontSize: 11 }}>Ładowanie fraz...</div>
                                                                ) : (
                                                                    <div style={{ padding: '8px 16px 8px 44px', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                                                        {expandedList?.items?.length === 0 && <span style={{ color: C.w30, fontSize: 11 }}>Pusta lista</span>}
                                                                        {expandedList?.items?.map(item => (
                                                                            <span key={item.id} style={{
                                                                                display: 'inline-block', padding: '2px 8px', borderRadius: 999,
                                                                                fontSize: 11, background: 'rgba(123,92,224,0.12)', color: C.w70,
                                                                                border: `1px solid rgba(123,92,224,0.2)`,
                                                                            }}>
                                                                                {item.text}
                                                                                <span style={{ marginLeft: 4, fontSize: 9, color: C.w30 }}>{item.match_type}</span>
                                                                            </span>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ),
                                                ]
                                            })}
                                        </tbody>
                                    </table>
                                )}

                                {/* Placement Exclusion Lists */}
                                <div style={{ padding: '14px 16px 4px', display: 'flex', alignItems: 'center', gap: 6, borderTop: B.card }}>
                                    <Globe size={13} style={{ color: C.warning }} />
                                    <span style={{ fontSize: 12, fontWeight: 600, color: C.w60 }}>Wykluczone miejsca docelowe MCC</span>
                                    <span style={{ fontSize: 10, color: C.w30 }}>({sharedData.placement_lists?.length || 0})</span>
                                </div>
                                {(!sharedData.placement_lists || sharedData.placement_lists.length === 0) ? (
                                    <div style={{ padding: '8px 16px 16px', color: C.w30, fontSize: 11 }}>
                                        Brak list wykluczonych miejsc docelowych. Pojawią się po synchronizacji konta managera.
                                    </div>
                                ) : (
                                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                        <thead>
                                            <tr style={{ borderBottom: B.card }}>
                                                <th style={{ ...TH, width: 28 }}></th>
                                                <th style={TH}>Nazwa listy</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Miejsc</th>
                                                <th style={TH}>Źródło</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sharedData.placement_lists.map(pel => {
                                                const isExpanded = expandedList?.id === pel.id && expandedList?.type === 'placement'
                                                return [
                                                    <tr key={pel.id} onClick={() => toggleListExpand(pel.id, 'placement')}
                                                        style={{ borderBottom: `1px solid ${C.w05}`, cursor: 'pointer' }}
                                                        onMouseEnter={e => e.currentTarget.style.background = C.w03}
                                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                                                        <td style={{ ...TD, textAlign: 'center', padding: '6px 4px' }}>
                                                            {isExpanded ? <ChevronDown size={12} style={{ color: C.w40 }} /> : <ChevronRight size={12} style={{ color: C.w30 }} />}
                                                        </td>
                                                        <td style={TD}>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                                <Globe size={12} style={{ color: C.warning, flexShrink: 0 }} />
                                                                {pel.name}
                                                            </div>
                                                            {pel.description && <div style={{ fontSize: 10, color: C.w30, marginTop: 1, marginLeft: 18 }}>{pel.description}</div>}
                                                        </td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{pel.item_count}</td>
                                                        <td style={TD_DIM}>{pel.source === 'MCC_SYNC' || pel.source === 'GOOGLE_ADS_SYNC' ? 'Google MCC' : 'Lokalna'}</td>
                                                    </tr>,
                                                    isExpanded && (
                                                        <tr key={`${pel.id}-items`}>
                                                            <td colSpan={4} style={{ padding: 0, background: 'rgba(251,191,36,0.03)' }}>
                                                                {expandedList?.loading ? (
                                                                    <div style={{ padding: 12, textAlign: 'center', color: C.w30, fontSize: 11 }}>Ładowanie miejsc...</div>
                                                                ) : (
                                                                    <div style={{ padding: '8px 16px 8px 44px' }}>
                                                                        {expandedList?.items?.length === 0 && <span style={{ color: C.w30, fontSize: 11 }}>Pusta lista</span>}
                                                                        {expandedList?.items?.map(item => (
                                                                            <div key={item.id} style={{
                                                                                display: 'flex', alignItems: 'center', gap: 6,
                                                                                padding: '2px 0', fontSize: 11, color: C.w60,
                                                                            }}>
                                                                                <span style={{
                                                                                    fontSize: 9, padding: '1px 5px', borderRadius: 3,
                                                                                    background: item.placement_type === 'WEBSITE' ? 'rgba(251,191,36,0.15)' :
                                                                                        item.placement_type === 'YOUTUBE_CHANNEL' ? 'rgba(248,113,113,0.15)' :
                                                                                        'rgba(79,142,247,0.15)',
                                                                                    color: item.placement_type === 'WEBSITE' ? C.warning :
                                                                                        item.placement_type === 'YOUTUBE_CHANNEL' ? C.danger : C.accentBlue,
                                                                                }}>
                                                                                    {item.placement_type === 'WEBSITE' ? 'WWW' :
                                                                                     item.placement_type === 'YOUTUBE_CHANNEL' ? 'YT' :
                                                                                     item.placement_type === 'YOUTUBE_VIDEO' ? 'YT' :
                                                                                     item.placement_type === 'MOBILE_APP' ? 'APP' : item.placement_type}
                                                                                </span>
                                                                                <span>{item.url}</span>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ),
                                                ]
                                            })}
                                        </tbody>
                                    </table>
                                )}
                            </>
                        )}
                    </div>
                )}
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
    )
}
