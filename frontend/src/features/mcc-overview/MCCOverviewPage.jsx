import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    RefreshCw, TrendingUp, TrendingDown, ArrowRight,
    AlertTriangle, CheckCircle, Minus, Bell, ExternalLink,
    ChevronDown, ChevronRight, ChevronUp, Shield, List,
} from 'lucide-react'
import { getMccOverview, getMccNegativeKeywordLists, syncClient } from '../../api'
import { useApp } from '../../contexts/AppContext'
import { CARD, TH, TD, TD_DIM, STATUS_COLORS } from '../../constants/designTokens'

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
    if (pct == null) return <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>
    const isUp = pct > 0
    const Icon = isUp ? TrendingUp : TrendingDown
    const color = isUp ? '#FBBF24' : '#4ADE80'
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color }}>
            <Icon size={12} />
            {Math.abs(pct).toFixed(1)}%
        </span>
    )
}

function StatusPill({ label, color }) {
    return (
        <span
            style={{
                display: 'inline-block',
                padding: '2px 8px',
                borderRadius: 999,
                fontSize: 10,
                fontWeight: 500,
                background: color.border,
                color: color.valueFill,
                border: `1px solid ${color.border}`,
            }}
        >
            {label}
        </span>
    )
}

function SyncIndicator({ lastSyncedAt, syncing }) {
    if (syncing) {
        return <RefreshCw size={13} style={{ color: '#4F8EF7', animation: 'spin 1s linear infinite' }} />
    }
    if (!lastSyncedAt) {
        return <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11 }}>Nigdy</span>
    }
    const ago = Date.now() - new Date(lastSyncedAt).getTime()
    const hours = Math.floor(ago / 3_600_000)
    const label = hours < 1 ? '<1h' : `${hours}h`
    const stale = hours > 6
    return (
        <span style={{ fontSize: 11, color: stale ? '#FBBF24' : 'rgba(255,255,255,0.5)' }}>
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
            marginBottom: 6, padding: '8px 10px', borderRadius: 8, minWidth: 140,
            background: '#1a1d24', border: '1px solid rgba(255,255,255,0.12)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)', zIndex: 10,
            fontSize: 11, color: 'rgba(255,255,255,0.7)',
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
        <th
            style={{ ...TH, textAlign: align || 'left', cursor: 'pointer', userSelect: 'none' }}
            onClick={() => onSort(field)}
        >
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

function googleAdsUrl(googleCustomerId) {
    const clean = googleCustomerId?.replace(/-/g, '') || ''
    return `https://ads.google.com/aw/overview?ocid=${clean}`
}

export default function MCCOverviewPage() {
    const navigate = useNavigate()
    const { setSelectedClientId, showToast } = useApp()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [syncingIds, setSyncingIds] = useState(new Set())
    const [nklData, setNklData] = useState(null)
    const [nklOpen, setNklOpen] = useState(false)
    const [sortBy, setSortBy] = useState('spend_30d_usd')
    const [sortDir, setSortDir] = useState('desc')
    const [hoveredHealth, setHoveredHealth] = useState(null)

    const load = useCallback(async () => {
        try {
            setLoading(true)
            const result = await getMccOverview()
            setData(result)
        } catch (err) {
            showToast?.('Błąd ładowania MCC overview', 'error')
        } finally {
            setLoading(false)
        }
    }, [showToast])

    useEffect(() => { load() }, [load])

    useEffect(() => {
        if (nklOpen && !nklData) {
            getMccNegativeKeywordLists()
                .then(setNklData)
                .catch(() => showToast?.('Błąd ładowania list NKL', 'error'))
        }
    }, [nklOpen, nklData, showToast])

    const handleSort = (field) => {
        if (sortBy === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(field)
            setSortDir('desc')
        }
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
            setSyncingIds(prev => {
                const next = new Set(prev)
                next.delete(clientId)
                return next
            })
        }
    }

    const handleSyncAll = async () => {
        if (!data?.accounts?.length) return
        const staleThreshold = 6 * 60 * 60 * 1000
        const stale = data.accounts.filter(acc => {
            if (!acc.last_synced_at) return true
            return Date.now() - new Date(acc.last_synced_at).getTime() > staleThreshold
        })
        if (stale.length === 0) {
            showToast?.('Wszystkie konta aktualne', 'info')
            return
        }
        for (const acc of stale.slice(0, 3)) {
            handleSync(acc.client_id, { stopPropagation: () => {} })
        }
    }

    const rawAccounts = data?.accounts || []

    const accounts = useMemo(() => {
        const sorted = [...rawAccounts]
        sorted.sort((a, b) => {
            let va, vb
            if (sortBy === 'health') {
                va = a.health?.score ?? -1
                vb = b.health?.score ?? -1
            } else {
                va = a[sortBy] ?? -Infinity
                vb = b[sortBy] ?? -Infinity
            }
            return sortDir === 'asc' ? va - vb : vb - va
        })
        return sorted
    }, [rawAccounts, sortBy, sortDir])

    // Aggregated totals
    const totalSpend = accounts.reduce((s, a) => s + (a.spend_30d_usd || 0), 0)
    const totalConv = accounts.reduce((s, a) => s + (a.conversions_30d || 0), 0)
    const totalChanges = accounts.reduce((s, a) => s + (a.total_changes_30d || 0), 0)
    const totalRecs = accounts.reduce((s, a) => s + (a.google_recs_pending || 0), 0)

    return (
        <div style={{ padding: '24px 32px', maxWidth: 1400 }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#fff', margin: 0 }}>
                        Wszystkie konta
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', margin: '4px 0 0' }}>
                        Przegląd MCC — {accounts.length} {accounts.length === 1 ? 'konto' : 'kont'}
                    </p>
                </div>
                <button
                    onClick={handleSyncAll}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '7px 14px', borderRadius: 8,
                        background: 'rgba(79,142,247,0.1)',
                        border: '1px solid rgba(79,142,247,0.2)',
                        color: '#4F8EF7', fontSize: 12, fontWeight: 500,
                        cursor: 'pointer',
                    }}
                >
                    <RefreshCw size={13} />
                    Synchronizuj nieaktualne
                </button>
            </div>

            {/* Summary KPI strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
                {[
                    { label: 'Wydatki 30d', value: `$${totalSpend.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` },
                    { label: 'Konwersje 30d', value: totalConv.toLocaleString('en-US', { maximumFractionDigits: 1 }) },
                    { label: 'Zmiany 30d', value: totalChanges },
                    { label: 'Rek. Google', value: totalRecs },
                ].map(kpi => (
                    <div key={kpi.label} className={CARD} style={{ padding: '14px 16px' }}>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                            {kpi.label}
                        </div>
                        <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>
                            {kpi.value}
                        </div>
                    </div>
                ))}
            </div>

            {/* Accounts table */}
            <div className={CARD} style={{ overflow: 'visible' }}>
                {loading ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)' }}>
                        <RefreshCw size={20} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
                        <div style={{ fontSize: 12 }}>Ładowanie kont...</div>
                    </div>
                ) : accounts.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>
                        Brak kont. Dodaj klienta w ustawieniach.
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                <SortHeader label="Konto" field="client_name" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                                <SortHeader label="Wydatki 30d" field="spend_30d_usd" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
                                <SortHeader label="Conv." field="conversions_30d" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="right" />
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
                                return (
                                    <tr
                                        key={acc.client_id}
                                        onClick={() => handleRowClick(acc)}
                                        style={{
                                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                                            cursor: 'pointer',
                                            transition: 'background 0.15s',
                                        }}
                                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                    >
                                        <td style={TD}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <div>
                                                    <div style={{ fontWeight: 500, color: '#fff', fontSize: 13 }}>{acc.client_name}</div>
                                                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>{acc.google_customer_id}</div>
                                                </div>
                                                {acc.unresolved_alerts > 0 && (
                                                    <span
                                                        title={`${acc.unresolved_alerts} aktywnych alertów`}
                                                        onClick={(e) => handleDeepLink(acc, '/alerts', e)}
                                                        style={{ cursor: 'pointer' }}
                                                    >
                                                        <Bell size={13} style={{ color: '#F87171' }} />
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            <div>${acc.spend_30d_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                                            <SpendChange pct={acc.spend_change_pct} />
                                        </td>
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            {acc.conversions_30d != null
                                                ? acc.conversions_30d.toLocaleString('en-US', { maximumFractionDigits: 1 })
                                                : '—'}
                                        </td>
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            {acc.cpa_usd != null
                                                ? `$${acc.cpa_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                                : <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>}
                                        </td>
                                        <td style={{ ...TD, textAlign: 'right' }}>
                                            {acc.roas_pct != null
                                                ? <span style={{ color: acc.roas_pct >= 400 ? '#4ADE80' : acc.roas_pct >= 200 ? '#4F8EF7' : '#FBBF24' }}>
                                                    {acc.roas_pct.toFixed(0)}%
                                                  </span>
                                                : <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>}
                                        </td>
                                        <td style={TD}>
                                            <StatusPill label={pacing.label} color={pacing.color} />
                                            {acc.pacing?.pacing_pct > 0 && (
                                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginLeft: 6 }}>
                                                    {acc.pacing.pacing_pct}%
                                                </span>
                                            )}
                                        </td>
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
                                            ) : (
                                                <Minus size={14} style={{ color: 'rgba(255,255,255,0.2)' }} />
                                            )}
                                        </td>
                                        <td
                                            style={{ ...TD, textAlign: 'right', cursor: 'pointer' }}
                                            onClick={(e) => handleDeepLink(acc, '/action-history', e)}
                                            title="Otwórz historię zmian"
                                        >
                                            <span style={{ color: acc.external_changes_30d > 0 ? '#FBBF24' : 'rgba(255,255,255,0.5)' }}>
                                                {acc.total_changes_30d}
                                            </span>
                                            {acc.external_changes_30d > 0 && (
                                                <div style={{ fontSize: 10, color: '#FBBF24' }}>
                                                    {acc.external_changes_30d} zewn.
                                                </div>
                                            )}
                                        </td>
                                        <td
                                            style={{ ...TD, textAlign: 'right', cursor: 'pointer' }}
                                            onClick={(e) => handleDeepLink(acc, '/recommendations', e)}
                                            title="Otwórz rekomendacje"
                                        >
                                            {acc.google_recs_pending > 0 ? (
                                                <span style={{ color: '#4F8EF7', fontWeight: 500 }}>{acc.google_recs_pending}</span>
                                            ) : (
                                                <CheckCircle size={13} style={{ color: 'rgba(255,255,255,0.15)' }} />
                                            )}
                                        </td>
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            <SyncIndicator lastSyncedAt={acc.last_synced_at} syncing={syncing} />
                                        </td>
                                        <td style={{ ...TD, textAlign: 'center' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                                <a
                                                    href={googleAdsUrl(acc.google_customer_id)}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    onClick={(e) => e.stopPropagation()}
                                                    title="Otwórz w Google Ads"
                                                    style={{ color: 'rgba(255,255,255,0.2)', padding: 2 }}
                                                >
                                                    <ExternalLink size={13} />
                                                </a>
                                                <ArrowRight size={14} style={{ color: 'rgba(255,255,255,0.2)' }} />
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

            {/* Negative Keyword Lists — collapsible section */}
            <div className={CARD} style={{ marginTop: 16, overflow: 'hidden' }}>
                <button
                    onClick={() => setNklOpen(p => !p)}
                    style={{
                        width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                        padding: '12px 16px', background: 'none', border: 'none',
                        color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500,
                    }}
                >
                    {nklOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <Shield size={14} style={{ color: '#7B5CE0' }} />
                    Listy wykluczających słów kluczowych
                    {nklData && (
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginLeft: 4 }}>
                            ({nklData.length})
                        </span>
                    )}
                </button>
                {nklOpen && (
                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                        {!nklData ? (
                            <div style={{ padding: 24, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                                <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite', marginBottom: 4 }} />
                                <div>Ładowanie...</div>
                            </div>
                        ) : nklData.length === 0 ? (
                            <div style={{ padding: 24, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                                Brak list wykluczających słów kluczowych.
                            </div>
                        ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                        <th style={TH}>Konto</th>
                                        <th style={TH}>Nazwa listy</th>
                                        <th style={{ ...TH, textAlign: 'right' }}>Słów</th>
                                        <th style={TH}>Źródło</th>
                                        <th style={TH}>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {nklData.map(nkl => (
                                        <tr
                                            key={nkl.id}
                                            style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
                                            onClick={() => {
                                                setSelectedClientId(nkl.client_id)
                                                navigate('/keywords')
                                            }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                        >
                                            <td style={TD_DIM}>{nkl.client_name}</td>
                                            <td style={TD}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                    <List size={12} style={{ color: '#7B5CE0', flexShrink: 0 }} />
                                                    {nkl.name}
                                                </div>
                                                {nkl.description && (
                                                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>
                                                        {nkl.description}
                                                    </div>
                                                )}
                                            </td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{nkl.member_count}</td>
                                            <td style={TD_DIM}>
                                                <StatusPill
                                                    label={nkl.source === 'GOOGLE_ADS_SYNC' ? 'Google' : 'Lokalna'}
                                                    color={nkl.source === 'GOOGLE_ADS_SYNC' ? STATUS_COLORS.info : STATUS_COLORS.neutral}
                                                />
                                            </td>
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
                        )}
                    </div>
                )}
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
    )
}
