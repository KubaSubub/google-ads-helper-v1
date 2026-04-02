import { useState, useEffect, useMemo } from 'react';
import { Loader2, Search, Ban } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import {
  getPlacementPerformance,
  getTopicPerformance,
  getAudiencePerformance,
  addPlacementExclusion,
} from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

const TABS = [
  { id: 'placements', label: 'Placements' },
  { id: 'topics', label: 'Topics' },
  { id: 'audiences', label: 'Audiences' },
];

function fmt(micros) {
  if (micros == null) return '\u2014';
  return (micros / 1e6).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(val) {
  if (val == null) return '\u2014';
  return Number(val).toLocaleString('pl-PL');
}

function fmtPct(val) {
  if (val == null) return '\u2014';
  return `${(Number(val) * 100).toFixed(2)}%`;
}

function KpiCard({ label, value, accent }) {
  return (
    <div
      className="v2-card"
      style={{
        flex: 1,
        minWidth: 160,
        borderRadius: 12,
        padding: '18px 20px',
        borderLeft: `3px solid ${accent || C.accentBlue}`,
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>{value}</div>
    </div>
  );
}

export default function VideoPage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [activeTab, setActiveTab] = useState('placements');
  const [loading, setLoading] = useState(false);
  const [placements, setPlacements] = useState([]);
  const [topics, setTopics] = useState([]);
  const [audiences, setAudiences] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [excludingId, setExcludingId] = useState(null);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    Promise.all([
      getPlacementPerformance(selectedClientId, allParams).catch(() => []),
      getTopicPerformance(selectedClientId, allParams).catch(() => []),
      getAudiencePerformance(selectedClientId, allParams).catch(() => []),
    ])
      .then(([p, t, a]) => {
        setPlacements(Array.isArray(p) ? p : []);
        setTopics(Array.isArray(t) ? t : []);
        setAudiences(Array.isArray(a) ? a : []);
      })
      .catch(() => showToast && showToast('B\u0142\u0105d \u0142adowania danych Video', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  // --- KPI aggregates ---
  const totalVideoViews = placements.reduce((s, r) => s + (Number(r.video_views) || 0), 0);
  const totalCostMicros = placements.reduce((s, r) => s + (Number(r.cost_micros) || 0), 0);
  const totalImpressions = placements.reduce((s, r) => s + (Number(r.impressions) || 0), 0);
  const totalConversions = placements.reduce((s, r) => s + (Number(r.conversions) || 0), 0);
  const viewRate = totalImpressions > 0 ? totalVideoViews / totalImpressions : null;
  const avgCpv = totalVideoViews > 0 ? totalCostMicros / totalVideoViews : null;

  // --- Compute per-row CPV median for high-CPV highlighting ---
  const cpvValues = useMemo(() => {
    const vals = placements
      .map((r) => (Number(r.video_views) || 0) > 0 ? (Number(r.cost_micros) || 0) / (Number(r.video_views) || 1) : null)
      .filter((v) => v != null);
    if (vals.length === 0) return { median: 0 };
    vals.sort((a, b) => a - b);
    const mid = Math.floor(vals.length / 2);
    const median = vals.length % 2 !== 0 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
    return { median };
  }, [placements]);

  // --- Filtered placements ---
  const filteredPlacements = useMemo(() => {
    if (!searchQuery.trim()) return placements;
    const q = searchQuery.toLowerCase();
    return placements.filter((r) => {
      const url = (r.placement_url || r.placement || '').toLowerCase();
      const type = (r.placement_type || '').toLowerCase();
      return url.includes(q) || type.includes(q);
    });
  }, [placements, searchQuery]);

  // --- Exclude placement handler ---
  const handleExclude = async (row) => {
    if (!row.campaign_id || !selectedClientId) {
      showToast && showToast('Brak ID kampanii \u2014 nie mo\u017cna wykluczy\u0107', 'error');
      return;
    }
    const url = row.placement_url || row.placement;
    if (!url) return;
    const rowKey = `${row.campaign_id}-${url}`;
    setExcludingId(rowKey);
    try {
      await addPlacementExclusion(selectedClientId, row.campaign_id, url);
      showToast && showToast(`Wykluczono: ${url}`, 'success');
      setPlacements((prev) => prev.filter((r) => {
        const rUrl = r.placement_url || r.placement;
        return !(r.campaign_id === row.campaign_id && rUrl === url);
      }));
    } catch {
      showToast && showToast('B\u0142\u0105d wykluczania placementu', 'error');
    } finally {
      setExcludingId(null);
    }
  };

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Video / YouTube" subtitle={`Analiza ${days} dni`} />

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="animate-spin" style={{ color: C.warning }} />
        </div>
      ) : (
        <>
          {/* KPI summary row */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
            <KpiCard label="Video views" value={fmtNum(totalVideoViews)} accent="#7B5CE0" />
            <KpiCard label="Koszt (PLN)" value={fmt(totalCostMicros)} accent="#FBBF24" />
            <KpiCard label="View Rate" value={viewRate != null ? fmtPct(viewRate) : '\u2014'} accent="#4F8EF7" />
            <KpiCard label="Konwersje" value={totalConversions.toFixed(2)} accent="#4ADE80" />
            <KpiCard label="\u015Ar. CPV (PLN)" value={avgCpv != null ? fmt(avgCpv) : '\u2014'} accent="#F87171" />
          </div>

          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
            {TABS.map((tab) => {
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '6px 18px',
                    borderRadius: 999,
                    border: active ? '1px solid #FBBF24' : B.medium,
                    background: active ? 'rgba(251,191,36,0.15)' : 'transparent',
                    color: active ? C.warning : C.textSecondary,
                    fontSize: 13,
                    fontWeight: active ? 600 : 400,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {tab.label}
                </button>
              );
            })}

            {/* Search input — only visible on placements tab */}
            {activeTab === 'placements' && (
              <div style={{ marginLeft: 'auto', position: 'relative', minWidth: 220 }}>
                <Search
                  size={14}
                  style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: C.w30, pointerEvents: 'none' }}
                />
                <input
                  type="text"
                  placeholder="Szukaj placementu..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 12px 7px 30px',
                    borderRadius: 8,
                    border: B.medium,
                    background: C.w04,
                    color: '#fff',
                    fontSize: 12,
                    outline: 'none',
                  }}
                />
              </div>
            )}
          </div>

          <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>

            {/* --- Placements --- */}
            {activeTab === 'placements' && (
              filteredPlacements.length === 0
                ? <EmptyState message={searchQuery ? 'Brak wynik\u00f3w dla tego wyszukiwania' : 'Brak danych o placementach video'} />
                : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={TH}>URL / Placement</th>
                        <th style={TH}>Typ</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Klikni\u0119cia</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Wy\u015bwietlenia</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Video views</th>
                        <th style={{ ...TH, textAlign: 'right' }}>View Rate</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Koszt (PLN)</th>
                        <th style={{ ...TH, textAlign: 'right' }}>\u015Ar. CPV (PLN)</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                        <th style={{ ...TH, textAlign: 'center' }}>Akcja</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredPlacements.map((row, i) => {
                        const views = Number(row.video_views) || 0;
                        const impr = Number(row.impressions) || 0;
                        const rowViewRate = impr > 0 ? views / impr : null;
                        const rowCpv = views > 0 ? (Number(row.cost_micros) || 0) / views : null;
                        const isHighCpv = rowCpv != null && cpvValues.median > 0 && rowCpv > cpvValues.median * 1.5;
                        const rowUrl = row.placement_url || row.placement || '';
                        const rowKey = `${row.campaign_id}-${rowUrl}`;
                        return (
                          <tr key={i} style={{ borderTop: `1px solid ${C.w05}` }}>
                            <td style={TD_DIM} title={rowUrl}>{rowUrl || '\u2014'}</td>
                            <td style={TD}>{row.placement_type || '\u2014'}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.clicks)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.impressions)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.video_views)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{rowViewRate != null ? fmtPct(rowViewRate) : '\u2014'}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.cost_micros)}</td>
                            <td style={{
                              ...TD,
                              textAlign: 'right',
                              color: isHighCpv ? C.danger : TD.color,
                              fontWeight: isHighCpv ? 600 : 'normal',
                            }}>
                              {rowCpv != null ? fmt(rowCpv) : '\u2014'}
                              {isHighCpv && <span title="Wysoki CPV" style={{ marginLeft: 4, fontSize: 10 }}>!</span>}
                            </td>
                            <td style={{ ...TD, textAlign: 'right' }}>
                              {row.conversions != null ? Number(row.conversions).toFixed(2) : '\u2014'}
                            </td>
                            <td style={{ ...TD, textAlign: 'center' }}>
                              <button
                                onClick={() => handleExclude(row)}
                                disabled={excludingId === rowKey}
                                title="Wyklucz placement"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                  padding: '4px 10px',
                                  borderRadius: 6,
                                  border: '1px solid rgba(248,113,113,0.3)',
                                  background: C.dangerBg,
                                  color: C.danger,
                                  fontSize: 11,
                                  fontWeight: 500,
                                  cursor: excludingId === rowKey ? 'wait' : 'pointer',
                                  opacity: excludingId === rowKey ? 0.5 : 1,
                                  transition: 'all 0.15s',
                                }}
                              >
                                {excludingId === rowKey
                                  ? <Loader2 size={12} className="animate-spin" />
                                  : <Ban size={12} />}
                                Wyklucz
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )
            )}

            {/* --- Topics --- */}
            {activeTab === 'topics' && (
              topics.length === 0
                ? <EmptyState message="Brak danych o tematach" />
                : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={TH}>Temat</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Modyfikator stawki</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Klikni\u0119cia</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Wy\u015bwietlenia</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Koszt (PLN)</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topics.map((row, i) => (
                        <tr key={i} style={{ borderTop: `1px solid ${C.w05}` }}>
                          <td style={TD_DIM}>{row.topic_path || row.topic || '\u2014'}</td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {row.bid_modifier != null
                              ? `${(Number(row.bid_modifier) * 100).toFixed(0)}%`
                              : '\u2014'}
                          </td>
                          <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.clicks)}</td>
                          <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.impressions)}</td>
                          <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.cost_micros)}</td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {row.conversions != null ? Number(row.conversions).toFixed(2) : '\u2014'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
            )}

            {/* --- Audiences --- */}
            {activeTab === 'audiences' && (
              audiences.length === 0
                ? <EmptyState message="Brak danych o odbiorcach" />
                : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={TH}>Odbiorcy</th>
                        <th style={TH}>Typ</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Koszt (PLN)</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                        <th style={{ ...TH, textAlign: 'right' }}>CPA</th>
                        <th style={{ ...TH, textAlign: 'right' }}>ROAS</th>
                        <th style={{ ...TH, textAlign: 'center' }}>Anomalia</th>
                      </tr>
                    </thead>
                    <tbody>
                      {audiences.map((row, i) => {
                        const cost = row.cost_micros != null ? row.cost_micros / 1e6 : null;
                        const conv = row.conversions != null ? Number(row.conversions) : null;
                        const cpa = cost != null && conv != null && conv > 0 ? cost / conv : null;
                        const roas =
                          row.conversion_value_micros != null && cost != null && cost > 0
                            ? row.conversion_value_micros / 1e6 / cost
                            : null;
                        return (
                          <tr key={i} style={{ borderTop: `1px solid ${C.w05}` }}>
                            <td style={TD_DIM}>{row.audience_name || '\u2014'}</td>
                            <td style={TD}>{row.audience_type || '\u2014'}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>
                              {cost != null
                                ? cost.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                : '\u2014'}
                            </td>
                            <td style={{ ...TD, textAlign: 'right' }}>
                              {conv != null ? conv.toFixed(2) : '\u2014'}
                            </td>
                            <td style={{ ...TD, textAlign: 'right' }}>
                              {cpa != null
                                ? cpa.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                : '\u2014'}
                            </td>
                            <td style={{ ...TD, textAlign: 'right' }}>
                              {roas != null ? roas.toFixed(2) : '\u2014'}
                            </td>
                            <td style={{ ...TD, textAlign: 'center' }}>
                              {row.anomaly
                                ? <span style={{ color: C.danger, fontWeight: 600, fontSize: 12 }}>!</span>
                                : <span style={{ color: C.w20, fontSize: 12 }}>{'\u2014'}</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )
            )}

          </div>
        </>
      )}
    </div>
  );
}
