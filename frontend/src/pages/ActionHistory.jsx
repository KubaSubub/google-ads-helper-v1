import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../contexts/AppContext';
import { getActionHistory, revertAction, getChangeHistory, getUnifiedTimeline, getHistoryFilters, getChangeImpact, getBidStrategyImpact } from '../api';
import ConfirmationModal from '../components/ConfirmationModal';
import DataTable from '../components/DataTable';
import DiffView from '../components/DiffView';
import EmptyState from '../components/EmptyState';
import DarkSelect from '../components/DarkSelect';
import {
    Undo2, Loader2, ChevronDown, ChevronRight, Download,
    Megaphone, KeyRound, Search, Users, Zap, Globe, Settings2, LayoutGrid
} from 'lucide-react';

const PAGE_SIZE = 50;

const TABS = [
    { key: 'helper', label: 'Nasze akcje' },
    { key: 'external', label: 'Zewnętrzne' },
    { key: 'unified', label: 'Wszystko' },
    { key: 'impact', label: 'Wpływ zmian' },
    { key: 'strategy', label: 'Wpływ strategii licytacji' },
];

const RESOURCE_ICONS = {
    CAMPAIGN: Megaphone,
    AD_GROUP: LayoutGrid,
    AD_GROUP_CRITERION: KeyRound,
    AD_GROUP_AD: Globe,
    CAMPAIGN_BUDGET: Settings2,
    CAMPAIGN_CRITERION: Search,
    keyword: KeyRound,
    campaign: Megaphone,
    search_term: Search,
    ad: Globe,
};

const SOURCE_LABELS = {
    GOOGLE_ADS_WEB_CLIENT: 'Google Ads UI',
    GOOGLE_ADS_API: 'API',
    GOOGLE_ADS_HELPER: 'Helper',
};

const SOURCE_COLORS = {
    GOOGLE_ADS_WEB_CLIENT: { bg: 'rgba(79,142,247,0.12)', text: '#4F8EF7' },
    GOOGLE_ADS_API: { bg: 'rgba(123,92,224,0.12)', text: '#7B5CE0' },
    GOOGLE_ADS_HELPER: { bg: 'rgba(74,222,128,0.12)', text: '#4ADE80' },
};

const OP_LABELS = {
    CREATE: 'Utworzono',
    UPDATE: 'Zmieniono',
    REMOVE: 'Usunięto',
    PAUSE_KEYWORD: 'Wstrzymano keyword',
    ENABLE_KEYWORD: 'Włączono keyword',
    UPDATE_BID: 'Zmieniono stawke',
    SET_KEYWORD_BID: 'Przywrocono stawke',
    ADD_KEYWORD: 'Dodano keyword',
    ADD_NEGATIVE: 'Dodano negative',
    PAUSE_AD: 'Wstrzymano reklamę',
    INCREASE_BUDGET: 'Zwiekszono budzet',
    SET_BUDGET: 'Przywrocono budzet',
    DECREASE_BUDGET: 'Zmniejszono budżet',
};

const STATUS_COLORS = {
    SUCCESS: '#4ADE80',
    FAILED: '#F87171',
    BLOCKED: '#FBBF24',
    DRY_RUN: '#4F8EF7',
    REVERTED: 'rgba(255,255,255,0.35)',
};

const STATUS_TOOLTIPS = {
    SUCCESS: 'Akcja wykonana pomyślnie',
    FAILED: 'Błąd podczas wykonywania akcji',
    BLOCKED: 'Akcja zablokowana przez walidację bezpieczeństwa',
    DRY_RUN: 'Symulacja — akcja nie została wykonana',
    REVERTED: 'Akcja cofnięta do poprzedniego stanu',
};

function groupByDate(entries) {
    const empty = { today: [], yesterday: [], thisWeek: [], older: [] };
    if (!Array.isArray(entries)) return empty;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7);

    const groups = { today: [], yesterday: [], thisWeek: [], older: [] };
    for (const entry of entries) {
        const ts = entry.timestamp || entry.change_date_time || entry.executed_at;
        if (!ts) { groups.older.push(entry); continue; }
        const d = new Date(ts);
        if (isNaN(d.getTime())) { groups.older.push(entry); continue; }
        if (d >= today) groups.today.push(entry);
        else if (d >= yesterday) groups.yesterday.push(entry);
        else if (d >= weekAgo) groups.thisWeek.push(entry);
        else groups.older.push(entry);
    }
    return groups;
}

function getEntityLink(entry) {
    const name = entry.entity_name;
    if (!name) return null;
    const type = (entry.resource_type || entry.entity_type || '').toLowerCase();
    if (type === 'keyword' || type === 'ad_group_criterion') return `/keywords?search=${encodeURIComponent(name)}`;
    if (type === 'campaign') return '/campaigns';
    if (type === 'search_term') return `/search-terms?search=${encodeURIComponent(name)}`;
    return null;
}

function buildDescription(entry) {
    const op = OP_LABELS[entry.operation] || entry.operation;
    const resType = entry.resource_type || '';
    const name = entry.entity_name || entry.campaign_name || '';
    const user = entry.user_email ? ` (${entry.user_email})` : '';

    if (entry.source === 'helper') {
        return `${op}${name ? ': ' + name : ''}`;
    }
    return `${op} ${resType.toLowerCase().replace(/_/g, ' ')}${name ? ' — ' + name : ''}${user}`;
}

// â”€â”€â”€ Timeline Entry Row â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function TimelineEntry({ entry, isExpanded, onToggle, onRevert }) {
    const Icon = RESOURCE_ICONS[entry.resource_type] || Zap;
    const entityLink = getEntityLink(entry);
    const src = entry.client_type || 'GOOGLE_ADS_HELPER';
    const srcColor = SOURCE_COLORS[src] || SOURCE_COLORS.GOOGLE_ADS_API;
    const srcLabel = SOURCE_LABELS[src] || src;
    const ts = entry.timestamp || entry.change_date_time || entry.executed_at;
    const timeStr = ts ? new Date(ts).toLocaleString('pl-PL', {
        hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit',
    }) : '—';

    return (
        <div>
            <div
                onClick={onToggle}
                style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 14px', cursor: 'pointer',
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
                {/* Expand arrow */}
                <div style={{ color: 'rgba(255,255,255,0.25)', flexShrink: 0 }}>
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </div>

                {/* Resource icon */}
                <div style={{
                    width: 28, height: 28, borderRadius: 6,
                    background: 'rgba(255,255,255,0.05)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                }}>
                    <Icon size={14} style={{ color: 'rgba(255,255,255,0.5)' }} />
                </div>

                {/* Description */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                        fontSize: 13, color: '#E0E0E0',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                        {buildDescription(entry)}
                    </div>
                    {entry.campaign_name && entry.source === 'external' && (
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>
                            {entry.campaign_name}
                        </div>
                    )}
                </div>

                {/* Status (helper only) */}
                {entry.status && (
                    <span
                        title={STATUS_TOOLTIPS[entry.status]}
                        style={{
                            fontSize: 10, fontWeight: 600,
                            color: STATUS_COLORS[entry.status] || 'rgba(255,255,255,0.4)',
                        }}
                    >
                        {entry.status}
                    </span>
                )}

                {/* Source badge */}
                <span style={{
                    fontSize: 10, fontWeight: 500,
                    padding: '2px 8px', borderRadius: 999,
                    background: srcColor.bg, color: srcColor.text,
                    whiteSpace: 'nowrap', flexShrink: 0,
                }}>
                    {srcLabel}
                </span>

                {/* Timestamp */}
                <span style={{
                    fontSize: 11, color: 'rgba(255,255,255,0.3)',
                    whiteSpace: 'nowrap', flexShrink: 0, minWidth: 85, textAlign: 'right',
                }}>
                    {timeStr}
                </span>

                {/* Revert button */}
                {entry.can_revert && (
                    <button
                        onClick={(e) => { e.stopPropagation(); onRevert(entry); }}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 3,
                            fontSize: 10, fontWeight: 500,
                            color: '#FBBF24', background: 'none', border: 'none',
                            cursor: 'pointer', flexShrink: 0,
                        }}
                    >
                        <Undo2 size={11} /> Cofnij
                    </button>
                )}
            </div>

            {/* Expanded diff view */}
            {isExpanded && (
                <div style={{ padding: '8px 14px 14px 52px' }}>
                    <DiffView
                        oldJson={entry.old_value_json}
                        newJson={entry.new_value_json}
                        changedFields={entry.changed_fields}
                    />
                </div>
            )}
        </div>
    );
}

// â”€â”€â”€ Timeline Group â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function TimelineGroup({ title, entries, expandedId, onToggle, onRevert }) {
    if (!entries.length) return null;
    return (
        <div style={{ marginBottom: 16 }}>
            <div style={{
                fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                letterSpacing: '0.06em', color: 'rgba(255,255,255,0.25)',
                padding: '8px 14px',
            }}>
                {title} ({entries.length})
            </div>
            <div style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.07)',
                borderRadius: 12, overflow: 'hidden',
            }}>
                {entries.map((entry) => {
                    const id = entry.action_log_id
                        ? `a-${entry.action_log_id}`
                        : `e-${entry.change_event_id || entry.id}`;
                    return (
                        <TimelineEntry
                            key={id}
                            entry={entry}
                            isExpanded={expandedId === id}
                            onToggle={() => onToggle(id)}
                            onRevert={onRevert}
                        />
                    );
                })}
            </div>
        </div>
    );
}

// â”€â”€â”€ Main Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const IMPACT_COLORS = {
    POSITIVE: { bg: 'rgba(74,222,128,0.08)', border: 'rgba(74,222,128,0.2)', text: '#4ADE80', label: 'Poprawa' },
    NEGATIVE: { bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.2)', text: '#F87171', label: 'Pogorszenie' },
    NEUTRAL: { bg: 'rgba(255,255,255,0.03)', border: 'rgba(255,255,255,0.08)', text: 'rgba(255,255,255,0.5)', label: 'Neutralny' },
};

const TD_IMPACT = { padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' };
const TH_IMPACT = { padding: '8px 12px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', whiteSpace: 'nowrap', textAlign: 'left' };

function DeltaPill({ value, inverse }) {
    if (value === 0 || value === undefined) return <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>;
    const positive = inverse ? value < 0 : value > 0;
    return (
        <span style={{ color: positive ? '#4ADE80' : '#F87171', fontWeight: 600 }}>
            {value > 0 ? '+' : ''}{value}%
        </span>
    );
}

function ChangeImpactView({ data }) {
    if (!data?.changes?.length) return <EmptyState message="Brak danych — wykonaj akcje i poczekaj 7 dni na pomiar wpływu" />;
    const { summary } = data;
    return (
        <div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {[{ label: 'Poprawa', value: summary.positive, color: '#4ADE80' },
                  { label: 'Neutralny', value: summary.neutral, color: 'rgba(255,255,255,0.5)' },
                  { label: 'Pogorszenie', value: summary.negative, color: '#F87171' },
                ].map(s => (
                    <div key={s.label} style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', padding: '8px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 2 }}>{s.label}</span>
                        <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: s.color }}>{s.value}</span>
                    </div>
                ))}
            </div>
            <div className="v2-card" style={{ overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Data', 'Akcja', 'Encja', 'Wpływ', 'Koszt Δ', 'Konw. Δ', 'CPA Δ', 'CTR Δ', 'ROAS Δ'].map(h =>
                            <th key={h} style={{ ...TH_IMPACT, textAlign: h === 'Data' || h === 'Akcja' || h === 'Encja' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.changes.map((c, i) => {
                            const ic = IMPACT_COLORS[c.impact] || IMPACT_COLORS.NEUTRAL;
                            return (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: ic.bg }}>
                                    <td style={{ ...TD_IMPACT, fontFamily: 'inherit', whiteSpace: 'nowrap' }}>{new Date(c.executed_at).toLocaleDateString('pl-PL')}</td>
                                    <td style={{ ...TD_IMPACT, fontFamily: 'inherit' }}>{OP_LABELS[c.action_type] || c.action_type}</td>
                                    <td style={{ ...TD_IMPACT, fontFamily: 'inherit', color: '#F0F0F0', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.entity_name || `${c.entity_type} #${c.entity_id}`}</td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right', fontFamily: 'inherit' }}>
                                        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: ic.bg, color: ic.text, border: `1px solid ${ic.border}` }}>{ic.label}</span>
                                    </td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={c.delta?.cost_usd_pct} /></td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={c.delta?.conversions_pct} /></td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={c.delta?.cpa_usd_pct} inverse /></td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={c.delta?.ctr_pct} /></td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={c.delta?.roas_pct} /></td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function StrategyImpactView({ data }) {
    if (!data?.strategy_changes?.length) return <EmptyState message="Brak zmian strategii licytacji w ostatnich 90 dniach" />;
    return (
        <div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {[{ label: 'Poprawa', value: data.summary.positive, color: '#4ADE80' },
                  { label: 'Neutralny', value: data.summary.neutral, color: 'rgba(255,255,255,0.5)' },
                  { label: 'Pogorszenie', value: data.summary.negative, color: '#F87171' },
                ].map(s => (
                    <div key={s.label} style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', padding: '8px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 2 }}>{s.label}</span>
                        <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: s.color }}>{s.value}</span>
                    </div>
                ))}
            </div>
            <div className="v2-card" style={{ overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Data', 'Kampania', 'Stara strategia', 'Nowa strategia', 'Wpływ', 'Konw. Δ', 'CPA Δ', 'ROAS Δ'].map(h =>
                            <th key={h} style={{ ...TH_IMPACT, textAlign: h === 'Data' || h === 'Kampania' || h === 'Stara strategia' || h === 'Nowa strategia' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.strategy_changes.map((s, i) => {
                            const ic = IMPACT_COLORS[s.impact] || IMPACT_COLORS.NEUTRAL;
                            return (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: ic.bg }}>
                                    <td style={{ ...TD_IMPACT, fontFamily: 'inherit', whiteSpace: 'nowrap' }}>{new Date(s.change_date).toLocaleDateString('pl-PL')}</td>
                                    <td style={{ ...TD_IMPACT, fontFamily: 'inherit', color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.campaign_name}</td>
                                    <td style={{ ...TD_IMPACT, color: 'rgba(255,255,255,0.5)' }}>{s.old_strategy || '—'}</td>
                                    <td style={{ ...TD_IMPACT, color: '#4F8EF7' }}>{s.new_strategy || '—'}</td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right', fontFamily: 'inherit' }}>
                                        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: ic.bg, color: ic.text, border: `1px solid ${ic.border}` }}>{ic.label}</span>
                                    </td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={s.delta?.conversions_pct} /></td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={s.delta?.cpa_usd_pct} inverse /></td>
                                    <td style={{ ...TD_IMPACT, textAlign: 'right' }}><DeltaPill value={s.delta?.roas_pct} /></td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default function ActionHistory() {
    const { selectedClientId, showToast } = useApp();

    // Tabs
    const [activeTab, setActiveTab] = useState('helper');

    // Data
    const [helperActions, setHelperActions] = useState([]);
    const [externalEvents, setExternalEvents] = useState([]);
    const [unifiedEntries, setUnifiedEntries] = useState([]);
    const [loading, setLoading] = useState(true);

    // Filters
    const [filterOptions, setFilterOptions] = useState({ resource_types: [], user_emails: [], client_types: [], campaign_names: [] });
    const [filters, setFilters] = useState({
        dateFrom: '', dateTo: '', resourceType: '', userEmail: '', clientType: '', actionType: '', campaignName: '',
    });

    // Impact data (GAP 6A/6B)
    const [impactData, setImpactData] = useState(null);
    const [strategyData, setStrategyData] = useState(null);

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);

    // UI
    const [expandedId, setExpandedId] = useState(null);
    const [revertModal, setRevertModal] = useState(null);
    const [reverting, setReverting] = useState(false);

    // Fetch filter options
    useEffect(() => {
        if (!selectedClientId) return;
        getHistoryFilters(selectedClientId).then(setFilterOptions).catch((err) => console.error('[ActionHistory] filters load failed', err));
    }, [selectedClientId]);

    // Reset page on tab/filter change
    useEffect(() => { setCurrentPage(1); }, [activeTab, filters]);

    // Fetch data
    useEffect(() => {
        if (!selectedClientId) return;
        let cancelled = false;
        (async () => {
            await fetchData(cancelled);
        })();
        return () => { cancelled = true; };
    }, [selectedClientId, activeTab, filters, currentPage]);

    const fetchData = async (cancelled = false) => {
        if (!selectedClientId) return;
        setLoading(true);
        setExpandedId(null);
        const offset = (currentPage - 1) * PAGE_SIZE;
        try {
            const params = {};
            if (filters.dateFrom) params.date_from = filters.dateFrom;
            if (filters.dateTo) params.date_to = filters.dateTo;
            if (filters.resourceType) params.resource_type = filters.resourceType;
            if (filters.campaignName) params.campaign_name = filters.campaignName;

            if (activeTab === 'helper') {
                const data = await getActionHistory(selectedClientId, { limit: PAGE_SIZE, offset, ...params });
                setHelperActions(data.actions || []);
                setTotalCount(data.total || 0);
            } else if (activeTab === 'external') {
                if (filters.userEmail) params.user_email = filters.userEmail;
                if (filters.clientType) params.client_type = filters.clientType;
                const data = await getChangeHistory(selectedClientId, { limit: PAGE_SIZE, offset, ...params });
                setExternalEvents(data.events || []);
                setTotalCount(data.total || 0);
            } else if (activeTab === 'impact') {
                const data = await getChangeImpact(selectedClientId, { days: 60 });
                setImpactData(data);
                setTotalCount(0);
            } else if (activeTab === 'strategy') {
                const data = await getBidStrategyImpact(selectedClientId, { days: 90 });
                setStrategyData(data);
                setTotalCount(0);
            } else {
                const data = await getUnifiedTimeline(selectedClientId, { limit: PAGE_SIZE, offset, ...params });
                setUnifiedEntries(data.entries || []);
                setTotalCount(data.total || 0);
            }
        } catch (err) {
            showToast?.('Błąd ładowania historii', 'error');
        } finally {
            setLoading(false);
        }
    };

    // Revert
    const handleRevert = async () => {
        if (!revertModal) return;
        setReverting(true);
        try {
            const actionId = revertModal.action_log_id || revertModal.id;
            await revertAction(actionId, selectedClientId);
            showToast('Akcja cofnięta', 'success');
            setRevertModal(null);
            await fetchData();
        } catch (err) {
            showToast('Błąd cofania:' + err.message, 'error');
        } finally {
            setReverting(false);
        }
    };

    const canRevert = (action) => {
        if (action.status !== 'SUCCESS') return false;
        if (action.action_type === 'ADD_NEGATIVE') return false;
        const age = Date.now() - new Date(action.executed_at).getTime();
        return age < 24 * 60 * 60 * 1000;
    };

    // Group entries for timeline
    const timelineData = useMemo(() => {
        let entries;
        if (activeTab === 'helper') return null; // uses DataTable
        if (activeTab === 'external') {
            entries = externalEvents.map(e => ({
                ...e,
                source: 'external',
                timestamp: e.change_date_time,
                operation: e.resource_change_operation,
                resource_type: e.change_resource_type,
                old_value_json: e.old_resource_json,
                new_value_json: e.new_resource_json,
                can_revert: false,
            }));
        } else {
            entries = unifiedEntries;
        }
        return groupByDate(entries);
    }, [activeTab, externalEvents, unifiedEntries]);

    // Filtered helper actions
    const filteredHelperActions = useMemo(() => {
        if (!filters.actionType) return helperActions;
        return helperActions.filter(a => a.action_type === filters.actionType);
    }, [helperActions, filters.actionType]);

    // Helper tab columns
    const helperColumns = [
        {
            accessorKey: 'executed_at',
            header: 'Data',
            cell: ({ getValue }) => new Date(getValue()).toLocaleString('pl-PL'),
        },
        {
            accessorKey: 'action_type',
            header: 'Akcja',
            cell: ({ getValue }) => OP_LABELS[getValue()] || getValue(),
        },
        {
            accessorKey: 'entity_name',
            header: 'Encja',
            cell: ({ row }) => {
                const name = row.original.entity_name;
                const type = row.original.entity_type;
                const label = name || `${type} #${row.original.entity_id}`;
                const linkTo = type === 'keyword' ? `/keywords?search=${encodeURIComponent(name || '')}`
                    : type === 'campaign' ? '/campaigns'
                    : type === 'search_term' ? `/search-terms?search=${encodeURIComponent(name || '')}`
                    : null;
                if (linkTo && name) {
                    return <Link to={linkTo} style={{ color: '#4F8EF7', textDecoration: 'none' }} onClick={e => e.stopPropagation()}>{label}</Link>;
                }
                return <span>{label}</span>;
            },
        },
        {
            accessorKey: 'campaign_name',
            header: 'Kampania',
            cell: ({ getValue }) => (
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>{getValue() || '—'}</span>
            ),
        },
        {
            accessorKey: 'status',
            header: 'Status',
            cell: ({ getValue }) => (
                <span
                    title={STATUS_TOOLTIPS[getValue()]}
                    style={{ color: STATUS_COLORS[getValue()] || 'rgba(255,255,255,0.4)', cursor: 'help' }}
                >
                    {getValue()}
                </span>
            ),
        },
        {
            id: 'actions',
            header: '',
            cell: ({ row }) =>
                canRevert(row.original) ? (
                    <button
                        onClick={(e) => { e.stopPropagation(); setRevertModal(row.original); }}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            fontSize: 11, fontWeight: 500,
                            color: '#FBBF24', background: 'none', border: 'none',
                            cursor: 'pointer',
                        }}
                    >
                        <Undo2 size={12} /> Cofnij
                    </button>
                ) : null,
        },
    ];

    // Quick stats computed from helper actions
    const quickStats = useMemo(() => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const todayActions = helperActions.filter(a => new Date(a.executed_at) >= today);
        const success = todayActions.filter(a => a.status === 'SUCCESS').length;
        const reverted = helperActions.filter(a => a.status === 'REVERTED').length;
        const blocked = helperActions.filter(a => a.status === 'BLOCKED').length;
        return { today: todayActions.length, success, reverted, blocked, total: helperActions.length };
    }, [helperActions]);

    const applyDatePreset = (days) => {
        const to = new Date();
        const from = new Date();
        from.setDate(from.getDate() - days);
        setFilters(f => ({
            ...f,
            dateFrom: from.toISOString().slice(0, 10),
            dateTo: to.toISOString().slice(0, 10),
        }));
    };

    const DATE_PRESETS = [
        { label: 'Dzisiaj', days: 0 },
        { label: '7 dni', days: 7 },
        { label: '30 dni', days: 30 },
    ];

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    return (
        <div style={{ maxWidth: 1100 }}>
            {/* Header */}
            <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Historia zmian
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Rejestr wszystkich zmian na koncie Google Ads — z Helpera i zewnętrznych
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    <button
                        onClick={() => { window.location.href = `/api/v1/export/actions?client_id=${selectedClientId}&format=csv`; }}
                        style={{ padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                        <Download size={11} />CSV
                    </button>
                    <button
                        onClick={() => { window.location.href = `/api/v1/export/actions?client_id=${selectedClientId}&format=xlsx`; }}
                        style={{ padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ADE80', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                        <Download size={11} />XLSX
                    </button>
                </div>
            </div>

            {/* Tab bar */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
                {TABS.map(tab => {
                    const active = activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            style={{
                                padding: '6px 16px',
                                borderRadius: 999,
                                fontSize: 12,
                                fontWeight: 500,
                                border: active ? '1px solid rgba(79,142,247,0.4)' : '1px solid rgba(255,255,255,0.1)',
                                background: active ? 'rgba(79,142,247,0.12)' : 'transparent',
                                color: active ? '#4F8EF7' : 'rgba(255,255,255,0.5)',
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                            }}
                        >
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Quick stats banner */}
            {activeTab === 'helper' && helperActions.length > 0 && (
                <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
                    {[
                        { label: 'Dzisiaj', value: quickStats.today, color: '#4F8EF7' },
                        { label: 'Łącznie', value: quickStats.total, color: 'rgba(255,255,255,0.6)' },
                        { label: 'Cofnięte', value: quickStats.reverted, color: '#FBBF24' },
                        { label: 'Zablokowane', value: quickStats.blocked, color: '#F87171' },
                    ].map(s => (
                        <div key={s.label} style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '6px 14px', borderRadius: 10,
                            background: 'rgba(255,255,255,0.03)',
                            border: '1px solid rgba(255,255,255,0.07)',
                        }}>
                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase' }}>{s.label}</span>
                            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: s.color }}>{s.value}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Filter bar */}
            {activeTab !== 'impact' && activeTab !== 'strategy' && (
                <div style={{
                    display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16,
                    padding: '10px 14px',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 10,
                    alignItems: 'center',
                }}>
                    {/* Date presets */}
                    {DATE_PRESETS.map(p => (
                        <button
                            key={p.label}
                            onClick={() => applyDatePreset(p.days)}
                            style={{
                                padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                                border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
                                color: 'rgba(255,255,255,0.5)', cursor: 'pointer', transition: 'all 0.15s',
                            }}
                            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(79,142,247,0.4)'; e.currentTarget.style.color = '#4F8EF7'; }}
                            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = 'rgba(255,255,255,0.5)'; }}
                        >
                            {p.label}
                        </button>
                    ))}
                    <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.08)', margin: '0 2px' }} />
                    <input
                        type="date"
                        value={filters.dateFrom}
                        onChange={e => setFilters(f => ({ ...f, dateFrom: e.target.value }))}
                        style={filterInputStyle}
                        placeholder="Od"
                    />
                    <input
                        type="date"
                        value={filters.dateTo}
                        onChange={e => setFilters(f => ({ ...f, dateTo: e.target.value }))}
                        style={filterInputStyle}
                        placeholder="Do"
                    />
                    {activeTab !== 'helper' && (
                        <>
                            <DarkSelect
                                value={filters.campaignName}
                                onChange={(v) => setFilters(f => ({ ...f, campaignName: v }))}
                                options={[
                                    { value: '', label: 'Kampania' },
                                    ...(filterOptions.campaign_names || []).map(c => ({ value: c, label: c })),
                                ]}
                                placeholder="Kampania"
                                style={{ minWidth: 180 }}
                            />
                            <DarkSelect
                                value={filters.resourceType}
                                onChange={(v) => setFilters(f => ({ ...f, resourceType: v }))}
                                options={[
                                    { value: '', label: 'Typ zasobu' },
                                    ...(filterOptions.resource_types || []).map(t => ({ value: t, label: t.replace(/_/g, ' ') })),
                                ]}
                                placeholder="Typ zasobu"
                                style={{ minWidth: 140 }}
                            />
                        </>
                    )}
                    {activeTab === 'helper' && (
                        <DarkSelect
                            value={filters.actionType}
                            onChange={(v) => setFilters(f => ({ ...f, actionType: v }))}
                            options={[
                                { value: '', label: 'Typ akcji' },
                                ...Object.entries(OP_LABELS)
                                    .filter(([k]) => !['CREATE', 'UPDATE', 'REMOVE'].includes(k))
                                    .map(([k, v]) => ({ value: k, label: v })),
                            ]}
                            placeholder="Typ akcji"
                            style={{ minWidth: 160 }}
                        />
                    )}
                    {activeTab === 'external' && (
                        <>
                            <DarkSelect
                                value={filters.userEmail}
                                onChange={(v) => setFilters(f => ({ ...f, userEmail: v }))}
                                options={[
                                    { value: '', label: 'Użytkownik' },
                                    ...(filterOptions.user_emails || []).map(e => ({ value: e, label: e })),
                                ]}
                                placeholder="Użytkownik"
                                style={{ minWidth: 140 }}
                            />
                            <DarkSelect
                                value={filters.clientType}
                                onChange={(v) => setFilters(f => ({ ...f, clientType: v }))}
                                options={[
                                    { value: '', label: 'Źródło' },
                                    ...(filterOptions.client_types || []).map(t => ({ value: t, label: SOURCE_LABELS[t] || t })),
                                ]}
                                placeholder="Źródło"
                                style={{ minWidth: 120 }}
                            />
                        </>
                    )}
                    {(filters.dateFrom || filters.dateTo || filters.resourceType || filters.userEmail || filters.clientType || filters.actionType || filters.campaignName) && (
                        <button
                            onClick={() => setFilters({ dateFrom: '', dateTo: '', resourceType: '', userEmail: '', clientType: '', actionType: '', campaignName: '' })}
                            style={{
                                fontSize: 11, color: '#F87171', background: 'none',
                                border: 'none', cursor: 'pointer', padding: '4px 8px',
                            }}
                        >
                            Wyczyść filtry
                        </button>
                    )}
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                    <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            )}

            {/* Helper tab — existing DataTable */}
            {!loading && activeTab === 'helper' && (
                <DataTable
                    data={filteredHelperActions}
                    columns={helperColumns}
                    searchable
                    emptyMessage="Brak wykonanych akcji Helper"
                />
            )}

            {/* Impact tab (GAP 6A) */}
            {!loading && activeTab === 'impact' && impactData && (
                <ChangeImpactView data={impactData} />
            )}

            {/* Strategy impact tab (GAP 6B) */}
            {!loading && activeTab === 'strategy' && strategyData && (
                <StrategyImpactView data={strategyData} />
            )}

            {/* External / Unified tabs — Timeline */}
            {!loading && activeTab !== 'helper' && activeTab !== 'impact' && activeTab !== 'strategy' && timelineData && (
                <>
                    <TimelineGroup
                        title="Dzisiaj"
                        entries={timelineData.today}
                        expandedId={expandedId}
                        onToggle={id => setExpandedId(prev => prev === id ? null : id)}
                        onRevert={setRevertModal}
                    />
                    <TimelineGroup
                        title="Wczoraj"
                        entries={timelineData.yesterday}
                        expandedId={expandedId}
                        onToggle={id => setExpandedId(prev => prev === id ? null : id)}
                        onRevert={setRevertModal}
                    />
                    <TimelineGroup
                        title="Ten tydzień"
                        entries={timelineData.thisWeek}
                        expandedId={expandedId}
                        onToggle={id => setExpandedId(prev => prev === id ? null : id)}
                        onRevert={setRevertModal}
                    />
                    <TimelineGroup
                        title="Starsze"
                        entries={timelineData.older}
                        expandedId={expandedId}
                        onToggle={id => setExpandedId(prev => prev === id ? null : id)}
                        onRevert={setRevertModal}
                    />
                    {!timelineData.today.length && !timelineData.yesterday.length &&
                     !timelineData.thisWeek.length && !timelineData.older.length && (
                        <EmptyState message="Brak zdarzeń dla wybranych filtrów" />
                    )}
                </>
            )}

            {/* Pagination */}
            {!loading && totalCount > PAGE_SIZE && activeTab !== 'impact' && activeTab !== 'strategy' && (
                <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    marginTop: 16, padding: '8px 14px',
                    background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 10,
                }}>
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>
                        {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, totalCount)} z {totalCount}
                    </span>
                    <div style={{ display: 'flex', gap: 6 }}>
                        <button
                            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                            disabled={currentPage <= 1}
                            style={{
                                padding: '4px 12px', borderRadius: 6, fontSize: 11, fontWeight: 500,
                                border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
                                color: currentPage <= 1 ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.6)',
                                cursor: currentPage <= 1 ? 'default' : 'pointer',
                            }}
                        >
                            ← Poprzednia
                        </button>
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', display: 'flex', alignItems: 'center', padding: '0 6px' }}>
                            {currentPage} / {Math.ceil(totalCount / PAGE_SIZE)}
                        </span>
                        <button
                            onClick={() => setCurrentPage(p => Math.min(Math.ceil(totalCount / PAGE_SIZE), p + 1))}
                            disabled={currentPage >= Math.ceil(totalCount / PAGE_SIZE)}
                            style={{
                                padding: '4px 12px', borderRadius: 6, fontSize: 11, fontWeight: 500,
                                border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
                                color: currentPage >= Math.ceil(totalCount / PAGE_SIZE) ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.6)',
                                cursor: currentPage >= Math.ceil(totalCount / PAGE_SIZE) ? 'default' : 'pointer',
                            }}
                        >
                            Następna →
                        </button>
                    </div>
                </div>
            )}

            {/* Revert modal */}
            <ConfirmationModal
                isOpen={!!revertModal}
                onClose={() => setRevertModal(null)}
                onConfirm={handleRevert}
                title="Cofnij akcję?"
                actionType={revertModal?.action_type || revertModal?.operation}
                entity={revertModal?.entity_name || revertModal?.entity_id}
                reason="Akcja zostanie cofnięta do poprzedniego stanu"
                isLoading={reverting}
            />
        </div>
    );
}

const filterInputStyle = {
    padding: '5px 10px',
    fontSize: 12,
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.04)',
    color: '#E0E0E0',
    outline: 'none',
    minWidth: 100,
};

