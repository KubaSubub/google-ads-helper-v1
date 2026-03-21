import { useState, useEffect, useMemo } from 'react';
import { useApp } from '../contexts/AppContext';
import { getActionHistory, revertAction, getChangeHistory, getUnifiedTimeline, getHistoryFilters } from '../api';
import ConfirmationModal from '../components/ConfirmationModal';
import DataTable from '../components/DataTable';
import DiffView from '../components/DiffView';
import EmptyState from '../components/EmptyState';
import {
    Undo2, Loader2, ChevronDown, ChevronRight,
    Megaphone, KeyRound, Search, Users, Zap, Globe, Settings2, LayoutGrid
} from 'lucide-react';

const TABS = [
    { key: 'helper', label: 'Helper' },
    { key: 'external', label: 'Zewnętrzne' },
    { key: 'unified', label: 'Wszystko' },
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

function groupByDate(entries) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7);

    const groups = { today: [], yesterday: [], thisWeek: [], older: [] };
    for (const entry of entries) {
        const ts = entry.timestamp || entry.change_date_time || entry.executed_at;
        const d = new Date(ts);
        if (d >= today) groups.today.push(entry);
        else if (d >= yesterday) groups.yesterday.push(entry);
        else if (d >= weekAgo) groups.thisWeek.push(entry);
        else groups.older.push(entry);
    }
    return groups;
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
                    <span style={{
                        fontSize: 10, fontWeight: 600,
                        color: STATUS_COLORS[entry.status] || 'rgba(255,255,255,0.4)',
                    }}>
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
export default function ActionHistory() {
    const { selectedClientId, showToast } = useApp();

    // Tabs
    const [activeTab, setActiveTab] = useState('unified');

    // Data
    const [helperActions, setHelperActions] = useState([]);
    const [externalEvents, setExternalEvents] = useState([]);
    const [unifiedEntries, setUnifiedEntries] = useState([]);
    const [loading, setLoading] = useState(true);

    // Filters
    const [filterOptions, setFilterOptions] = useState({ resource_types: [], user_emails: [], client_types: [] });
    const [filters, setFilters] = useState({
        dateFrom: '', dateTo: '', resourceType: '', userEmail: '', clientType: '',
    });

    // UI
    const [expandedId, setExpandedId] = useState(null);
    const [revertModal, setRevertModal] = useState(null);
    const [reverting, setReverting] = useState(false);

    // Fetch filter options
    useEffect(() => {
        if (!selectedClientId) return;
        getHistoryFilters(selectedClientId).then(setFilterOptions).catch(() => {});
    }, [selectedClientId]);

    // Fetch data
    useEffect(() => {
        fetchData();
    }, [selectedClientId, activeTab, filters]);

    const fetchData = async () => {
        if (!selectedClientId) return;
        setLoading(true);
        setExpandedId(null);
        try {
            const params = {};
            if (filters.dateFrom) params.date_from = filters.dateFrom;
            if (filters.dateTo) params.date_to = filters.dateTo;
            if (filters.resourceType) params.resource_type = filters.resourceType;

            if (activeTab === 'helper') {
                const data = await getActionHistory(selectedClientId, { limit: 200 });
                setHelperActions(data.actions || []);
            } else if (activeTab === 'external') {
                if (filters.userEmail) params.user_email = filters.userEmail;
                if (filters.clientType) params.client_type = filters.clientType;
                const data = await getChangeHistory(selectedClientId, { limit: 200, ...params });
                setExternalEvents(data.events || []);
            } else {
                const data = await getUnifiedTimeline(selectedClientId, { limit: 200, ...params });
                setUnifiedEntries(data.entries || []);
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

    // Helper tab columns
    const helperColumns = [
        {
            accessorKey: 'executed_at',
            header: 'Data',
            cell: ({ getValue }) => new Date(getValue()).toLocaleString('pl-PL'),
        },
        { accessorKey: 'action_type', header: 'Akcja' },
        {
            accessorKey: 'entity_name',
            header: 'Encja',
            cell: ({ row }) => {
                const name = row.original.entity_name;
                const type = row.original.entity_type;
                return <span>{name || `${type} #${row.original.entity_id}`}</span>;
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
                <span style={{ color: STATUS_COLORS[getValue()] || 'rgba(255,255,255,0.4)' }}>
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

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    return (
        <div style={{ maxWidth: 1100 }}>
            {/* Header */}
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                    Historia zmian
                </h1>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                    Rejestr wszystkich zmian na koncie Google Ads — z Helpera i zewnętrznych
                </p>
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

            {/* Filter bar (external / unified tabs) */}
            {activeTab !== 'helper' && (
                <div style={{
                    display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16,
                    padding: '10px 14px',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 10,
                }}>
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
                    <select
                        value={filters.resourceType}
                        onChange={e => setFilters(f => ({ ...f, resourceType: e.target.value }))}
                        style={filterInputStyle}
                    >
                        <option value="">Typ zasobu</option>
                        {filterOptions.resource_types.map(t => (
                            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                        ))}
                    </select>
                    {activeTab === 'external' && (
                        <>
                            <select
                                value={filters.userEmail}
                                onChange={e => setFilters(f => ({ ...f, userEmail: e.target.value }))}
                                style={filterInputStyle}
                            >
                                <option value="">Użytkownik</option>
                                {filterOptions.user_emails.map(e => (
                                    <option key={e} value={e}>{e}</option>
                                ))}
                            </select>
                            <select
                                value={filters.clientType}
                                onChange={e => setFilters(f => ({ ...f, clientType: e.target.value }))}
                                style={filterInputStyle}
                            >
                                <option value="">Źródło</option>
                                {filterOptions.client_types.map(t => (
                                    <option key={t} value={t}>{SOURCE_LABELS[t] || t}</option>
                                ))}
                            </select>
                        </>
                    )}
                    {(filters.dateFrom || filters.dateTo || filters.resourceType || filters.userEmail || filters.clientType) && (
                        <button
                            onClick={() => setFilters({ dateFrom: '', dateTo: '', resourceType: '', userEmail: '', clientType: '' })}
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
                    data={helperActions}
                    columns={helperColumns}
                    searchable
                    emptyMessage="Brak wykonanych akcji Helper"
                />
            )}

            {/* External / Unified tabs — Timeline */}
            {!loading && activeTab !== 'helper' && timelineData && (
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

