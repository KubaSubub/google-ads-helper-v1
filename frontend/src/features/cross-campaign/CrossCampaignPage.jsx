import { useState, useEffect, useMemo } from 'react';
import {
  Loader2, AlertTriangle, ArrowRight, Shuffle, ChevronDown, ChevronUp,
  DollarSign, TrendingUp, Layers, Search,
} from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import {
  getKeywordOverlap,
  getBudgetAllocation,
  getCampaignComparison,
  getCampaigns,
} from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

// ── Formatters ───────────────────────────────────────────────────────────────
const fmtCost = (v) => (typeof v === 'number' ? v.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '\u2014');
const fmtInt = (v) => (typeof v === 'number' ? v.toLocaleString('pl-PL') : '\u2014');
const fmtPct = (v) => (typeof v === 'number' ? v.toFixed(1) + '%' : '\u2014');

const TABS = [
  { id: 'overlap', label: 'Nak\u0142adanie s\u0142\u00f3w' },
  { id: 'budget', label: 'Alokacja bud\u017cetu' },
  { id: 'comparison', label: 'Por\u00f3wnanie' },
];

// ── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, accent, icon: Icon }) {
  return (
    <div
      className="v2-card"
      style={{
        flex: 1,
        minWidth: 180,
        borderRadius: 12,
        padding: '18px 20px',
        borderLeft: `3px solid ${accent || '#4F8EF7'}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          {label}
        </span>
        {Icon && (
          <div style={{ width: 22, height: 22, borderRadius: 6, background: `${accent}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon size={11} style={{ color: accent }} />
          </div>
        )}
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>{value}</div>
    </div>
  );
}

// ── Priority badge ───────────────────────────────────────────────────────────
function PriorityBadge({ priority }) {
  const color = priority === 'high' ? '#F87171' : '#FBBF24';
  return (
    <span style={{
      fontSize: 10, padding: '2px 8px', borderRadius: 999,
      background: `${color}1A`, color,
      fontFamily: 'DM Sans, sans-serif', fontWeight: 600,
    }}>
      {priority === 'high' ? 'Wysoki' : 'Średni'}
    </span>
  );
}

// ── Expandable keyword row ───────────────────────────────────────────────────
function OverlapRow({ item, expanded, onToggle }) {
  return (
    <>
      <tr
        onClick={onToggle}
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
      >
        <td style={TD_DIM}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            <span style={{ fontWeight: 600, color: '#fff', fontFamily: 'DM Sans' }}>{item.keyword_text}</span>
          </div>
        </td>
        <td style={{ ...TD, textAlign: 'center' }}>
          <span style={{
            fontSize: 11, fontWeight: 700, fontFamily: 'Syne',
            color: item.campaign_count >= 3 ? '#F87171' : '#FBBF24',
          }}>
            {item.campaign_count}
          </span>
        </td>
        <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(item.total_clicks)}</td>
        <td style={{ ...TD, textAlign: 'right' }}>${fmtCost(item.total_cost_usd)}</td>
        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(item.total_conversions)}</td>
        <td style={{ ...TD, textAlign: 'right' }}>
          <span style={{ color: item.estimated_waste_usd > 0 ? '#F87171' : 'rgba(255,255,255,0.45)' }}>
            ${fmtCost(item.estimated_waste_usd)}
          </span>
        </td>
      </tr>
      {expanded && item.campaigns?.map((c, j) => (
        <tr key={j} style={{ borderTop: '1px solid rgba(255,255,255,0.03)', background: 'rgba(255,255,255,0.02)' }}>
          <td style={{ ...TD_DIM, paddingLeft: 36 }}>
            <span style={{ fontSize: 11 }}>{c.campaign_name}</span>
            <span style={{
              marginLeft: 8, fontSize: 10, padding: '1px 6px', borderRadius: 999,
              background: 'rgba(79,142,247,0.1)', color: '#4F8EF7',
            }}>
              {c.match_type}
            </span>
          </td>
          <td style={{ ...TD_DIM, textAlign: 'center', fontSize: 11 }}>QS: {c.quality_score || '\u2014'}</td>
          <td style={{ ...TD_DIM, textAlign: 'right' }}>{fmtInt(c.clicks)}</td>
          <td style={{ ...TD_DIM, textAlign: 'right' }}>${fmtCost(c.cost_usd)}</td>
          <td style={{ ...TD_DIM, textAlign: 'right' }}>{fmtCost(c.conversions)}</td>
          <td style={{ ...TD_DIM, textAlign: 'right' }}>\u2014</td>
        </tr>
      ))}
    </>
  );
}

// ── Suggestion card (donor -> recipient) ─────────────────────────────────────
function SuggestionCard({ s }) {
  if (s.type === 'review_spend') {
    return (
      <div
        className="v2-card"
        style={{
          borderRadius: 12, padding: '16px 20px', marginBottom: 12,
          borderLeft: '3px solid #F87171',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <AlertTriangle size={14} style={{ color: '#F87171' }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: '#F87171' }}>Zerowe konwersje</span>
          <PriorityBadge priority={s.priority} />
        </div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', lineHeight: 1.5 }}>
          <strong style={{ color: '#fff' }}>{s.campaign_name}</strong>{' '}
          wydala ${fmtCost(s.cost_usd)} bez konwersji. Rozważ wstrzymanie lub optymalizację.
        </div>
      </div>
    );
  }

  return (
    <div
      className="v2-card"
      style={{
        borderRadius: 12, padding: '16px 20px', marginBottom: 12,
        borderLeft: '3px solid #4F8EF7',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Shuffle size={14} style={{ color: '#4F8EF7' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Realokacja budżetu</span>
        <PriorityBadge priority={s.priority} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        {/* Donor */}
        <div style={{
          flex: 1, minWidth: 200, padding: '12px 16px', borderRadius: 10,
          background: 'rgba(248,113,113,0.06)', border: '1px solid rgba(248,113,113,0.15)',
        }}>
          <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
            Donor (wysoki CPA)
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 2 }}>{s.donor_campaign_name}</div>
          <div style={{ fontSize: 12, color: '#F87171', fontFamily: 'monospace' }}>CPA: ${fmtCost(s.donor_cpa_usd)}</div>
        </div>

        {/* Arrow */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <ArrowRight size={18} style={{ color: '#4F8EF7' }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: '#4F8EF7', fontFamily: 'Syne' }}>
            ${fmtCost(s.suggested_move_usd)}/d
          </span>
        </div>

        {/* Recipient */}
        <div style={{
          flex: 1, minWidth: 200, padding: '12px 16px', borderRadius: 10,
          background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.15)',
        }}>
          <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
            Odbiorca (niski CPA)
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 2 }}>{s.recipient_campaign_name}</div>
          <div style={{ fontSize: 12, color: '#4ADE80', fontFamily: 'monospace' }}>CPA: ${fmtCost(s.recipient_cpa_usd)}</div>
          {s.recipient_budget_lost_is > 0 && (
            <div style={{ fontSize: 10, color: '#FBBF24', marginTop: 2 }}>
              Budget lost IS: {s.recipient_budget_lost_is.toFixed(1)}%
            </div>
          )}
        </div>
      </div>
      <div style={{ marginTop: 10, fontSize: 11, color: 'rgba(255,255,255,0.45)', lineHeight: 1.4 }}>
        Szacowane oszczędności CPA: <strong style={{ color: '#4ADE80' }}>${fmtCost(s.estimated_cpa_savings_usd)}</strong>
      </div>
    </div>
  );
}

// ── Campaign KPI card for budget tab ─────────────────────────────────────────
function CampaignKpiCard({ cm, maxCost }) {
  const costBarPct = maxCost > 0 ? Math.min((cm.cost_usd / maxCost) * 100, 100) : 0;
  const roasColor = cm.roas >= 4 ? '#4ADE80' : cm.roas >= 2 ? '#FBBF24' : '#F87171';
  const cpaColor = cm.conversions > 0 ? (cm.cpa_usd <= 20 ? '#4ADE80' : cm.cpa_usd <= 50 ? '#FBBF24' : '#F87171') : 'rgba(255,255,255,0.3)';

  return (
    <div
      className="v2-card"
      style={{ borderRadius: 12, padding: '14px 16px', minWidth: 260 }}
    >
      <div style={{ fontSize: 12, fontWeight: 600, color: '#fff', marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {cm.campaign_name}
      </div>
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 10, textTransform: 'uppercase' }}>
        {cm.campaign_type}
      </div>
      {/* Cost bar */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'rgba(255,255,255,0.4)', marginBottom: 3 }}>
          <span>Koszt</span>
          <span style={{ color: '#fff', fontFamily: 'monospace' }}>${fmtCost(cm.cost_usd)}</span>
        </div>
        <div style={{ width: '100%', height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
          <div style={{ width: `${costBarPct}%`, height: '100%', borderRadius: 2, background: '#4F8EF7', transition: 'width 0.3s' }} />
        </div>
      </div>
      {/* Metrics row */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase' }}>CPA</div>
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'Syne', color: cpaColor }}>
            {cm.conversions > 0 ? `$${fmtCost(cm.cpa_usd)}` : '\u2014'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase' }}>ROAS</div>
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'Syne', color: roasColor }}>
            {cm.roas > 0 ? cm.roas.toFixed(2) + 'x' : '\u2014'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase' }}>Conv</div>
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>
            {fmtCost(cm.conversions)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase' }}>CTR</div>
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>
            {fmtPct(cm.ctr)}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Comparison metric row ────────────────────────────────────────────────────
const COMPARISON_METRICS = [
  { key: 'campaign_type', label: 'Typ kampanii', fmt: (v) => v || '\u2014' },
  { key: 'status', label: 'Status', fmt: (v) => v || '\u2014' },
  { key: 'bidding_strategy', label: 'Strategia lic.', fmt: (v) => v || '\u2014' },
  { key: 'budget_daily_usd', label: 'Budżet dzienny', fmt: (v) => `$${fmtCost(v)}`, type: 'money' },
  { key: 'impressions', label: 'Wyświetlenia', fmt: fmtInt, type: 'higher-better' },
  { key: 'clicks', label: 'Kliknięcia', fmt: fmtInt, type: 'higher-better' },
  { key: 'ctr', label: 'CTR', fmt: (v) => fmtPct(v), type: 'higher-better' },
  { key: 'cost_usd', label: 'Koszt', fmt: (v) => `$${fmtCost(v)}`, type: 'money' },
  { key: 'cpc_usd', label: 'CPC', fmt: (v) => `$${fmtCost(v)}`, type: 'lower-better' },
  { key: 'conversions', label: 'Konwersje', fmt: (v) => fmtCost(v), type: 'higher-better' },
  { key: 'cpa_usd', label: 'CPA', fmt: (v) => `$${fmtCost(v)}`, type: 'lower-better' },
  { key: 'conversion_value_usd', label: 'Wartość konwersji', fmt: (v) => `$${fmtCost(v)}`, type: 'higher-better' },
  { key: 'roas', label: 'ROAS', fmt: (v) => typeof v === 'number' ? v.toFixed(2) + 'x' : '\u2014', type: 'higher-better' },
  { key: 'cvr', label: 'CVR', fmt: (v) => fmtPct(v), type: 'higher-better' },
  { key: 'avg_impression_share', label: 'Udział w wyśw.', fmt: (v) => fmtPct(v), type: 'higher-better' },
  { key: 'avg_budget_lost_is', label: 'IS lost (budżet)', fmt: (v) => fmtPct(v), type: 'lower-better' },
  { key: 'avg_rank_lost_is', label: 'IS lost (rank)', fmt: (v) => fmtPct(v), type: 'lower-better' },
];

function getBestIdx(values, type) {
  if (!type || type === 'money') return -1;
  const numeric = values.map((v) => (typeof v === 'number' ? v : null));
  const valid = numeric.filter((v) => v !== null && v > 0);
  if (valid.length < 2) return -1;
  if (type === 'higher-better') {
    const maxVal = Math.max(...valid);
    return numeric.indexOf(maxVal);
  }
  // lower-better
  const minVal = Math.min(...valid);
  return numeric.indexOf(minVal);
}

// =============================================================================
// Main page component
// =============================================================================
export default function CrossCampaignPage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [activeTab, setActiveTab] = useState('overlap');
  const [loading, setLoading] = useState(false);

  // Tab 1: Keyword overlap
  const [overlap, setOverlap] = useState(null);
  const [expandedKw, setExpandedKw] = useState(new Set());
  const [overlapSearch, setOverlapSearch] = useState('');

  // Tab 2: Budget allocation
  const [budget, setBudget] = useState(null);

  // Tab 3: Campaign comparison
  const [allCampaigns, setAllCampaigns] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [comparison, setComparison] = useState(null);
  const [compLoading, setCompLoading] = useState(false);

  // ── Load overlap + budget data together ──
  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    Promise.all([
      getKeywordOverlap(selectedClientId).catch(() => null),
      getBudgetAllocation(selectedClientId, allParams).catch(() => null),
      getCampaigns(selectedClientId, { limit: 100 }).catch(() => []),
    ])
      .then(([ov, ba, camps]) => {
        setOverlap(ov);
        setBudget(ba);
        const list = Array.isArray(camps) ? camps : camps?.items || camps?.campaigns || [];
        setAllCampaigns(list);
        setSelectedIds(new Set());
        setComparison(null);
      })
      .catch(() => showToast && showToast('Błąd ładowania danych cross-campaign', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  // ── Load comparison on demand ──
  function loadComparison() {
    if (!selectedClientId || selectedIds.size < 2) return;
    setCompLoading(true);
    getCampaignComparison(selectedClientId, Array.from(selectedIds), allParams)
      .then((data) => setComparison(data))
      .catch(() => showToast && showToast('Błąd ładowania porównania', 'error'))
      .finally(() => setCompLoading(false));
  }

  // ── Toggle campaign checkbox ──
  function toggleCampaign(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 20) next.add(id);
      return next;
    });
  }

  // ── Filtered overlap keywords ──
  const filteredOverlap = useMemo(() => {
    if (!overlap?.overlapping_keywords) return [];
    if (!overlapSearch.trim()) return overlap.overlapping_keywords;
    const q = overlapSearch.trim().toLowerCase();
    return overlap.overlapping_keywords.filter((k) => k.keyword_text.includes(q));
  }, [overlap, overlapSearch]);

  // ── KPI summary values ──
  const totalOverlaps = overlap?.total_overlaps || 0;
  const totalWaste = overlap?.total_wasted_cost_usd || 0;
  const budgetSuggestions = budget?.suggestions || [];
  const totalSavings = budgetSuggestions.reduce(
    (sum, s) => sum + (s.estimated_cpa_savings_usd || 0), 0,
  );
  const maxCost = useMemo(() => {
    if (!budget?.campaigns?.length) return 0;
    return Math.max(...budget.campaigns.map((c) => c.cost_usd));
  }, [budget]);

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Analiza cross-campaign" subtitle={`Analiza ${days} dni`} />

      {/* ── KPI row ── */}
      {!loading && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
          <KpiCard
            label="Nakładające się słowa"
            value={totalOverlaps}
            accent="#FBBF24"
            icon={Layers}
          />
          <KpiCard
            label="Potencjalne straty"
            value={`$${fmtCost(totalWaste)}`}
            accent="#F87171"
            icon={AlertTriangle}
          />
          <KpiCard
            label="Sugestie realokacji"
            value={budgetSuggestions.filter((s) => s.type === 'reallocation').length}
            accent="#4F8EF7"
            icon={Shuffle}
          />
          <KpiCard
            label="Potencjał oszczędności CPA"
            value={totalSavings > 0 ? `$${fmtCost(totalSavings)}` : '\u2014'}
            accent="#4ADE80"
            icon={DollarSign}
          />
        </div>
      )}

      {/* ── Tab switcher ── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {TABS.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '6px 18px',
                borderRadius: 999,
                border: active ? '1px solid #4F8EF7' : '1px solid rgba(255,255,255,0.1)',
                background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
                color: active ? '#4F8EF7' : 'rgba(255,255,255,0.55)',
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
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="animate-spin" style={{ color: '#4F8EF7' }} />
        </div>
      ) : (
        <>
          {/* ═══════════════════════════════════════════════════════════════════
              TAB 1 — Keyword Overlap
             ═══════════════════════════════════════════════════════════════════ */}
          {activeTab === 'overlap' && (
            <>
              {/* Search bar */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Nakładające się słowa kluczowe
                </div>
                {totalOverlaps > 0 && (
                  <div style={{ position: 'relative', width: 220 }}>
                    <Search
                      size={13}
                      style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.3)', pointerEvents: 'none' }}
                    />
                    <input
                      type="text"
                      placeholder="Szukaj słowa..."
                      value={overlapSearch}
                      onChange={(e) => setOverlapSearch(e.target.value)}
                      style={{
                        width: '100%', padding: '6px 10px 6px 30px', borderRadius: 8,
                        border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)',
                        color: '#fff', fontSize: 12, outline: 'none',
                      }}
                    />
                  </div>
                )}
              </div>

              <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden' }}>
                {filteredOverlap.length === 0 ? (
                  <EmptyState message={overlapSearch ? 'Brak wyników' : 'Brak nakładających się słów kluczowych'} />
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={TH}>Słowo kluczowe</th>
                        <th style={{ ...TH, textAlign: 'center' }}>Kampanie</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Koszt</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Szac. strata</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredOverlap.map((item, i) => (
                        <OverlapRow
                          key={i}
                          item={item}
                          expanded={expandedKw.has(i)}
                          onToggle={() => {
                            setExpandedKw((prev) => {
                              const next = new Set(prev);
                              if (next.has(i)) next.delete(i);
                              else next.add(i);
                              return next;
                            });
                          }}
                        />
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              TAB 2 — Budget Allocation
             ═══════════════════════════════════════════════════════════════════ */}
          {activeTab === 'budget' && (
            <>
              {/* Suggestions */}
              {budgetSuggestions.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
                    Sugestie realokacji
                  </div>
                  {budgetSuggestions.map((s, i) => (
                    <SuggestionCard key={i} s={s} />
                  ))}
                </div>
              )}

              {/* Campaign KPI grid */}
              <div style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
                Kampanie wg kosztu ({budget?.period_days || days} dni)
              </div>
              {(!budget?.campaigns || budget.campaigns.length === 0) ? (
                <div className="v2-card" style={{ borderRadius: 12 }}>
                  <EmptyState message="Brak danych o kampaniach" />
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                  {budget.campaigns.map((cm) => (
                    <CampaignKpiCard key={cm.campaign_id} cm={cm} maxCost={maxCost} />
                  ))}
                </div>
              )}

              {/* Summary row */}
              {budget?.campaigns?.length > 0 && (
                <div className="v2-card" style={{ borderRadius: 12, padding: '14px 20px', marginTop: 16, display: 'flex', gap: 24, flexWrap: 'wrap', borderLeft: '3px solid #4F8EF7' }}>
                  <div>
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase' }}>Łączny koszt</div>
                    <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>${fmtCost(budget.total_cost_usd)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase' }}>Średni CPA</div>
                    <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>${fmtCost(budget.avg_cpa_usd)}</div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              TAB 3 — Campaign Comparison
             ═══════════════════════════════════════════════════════════════════ */}
          {activeTab === 'comparison' && (
            <>
              {/* Campaign selector */}
              <div style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
                Wybierz kampanie do porównania (min. 2, maks. 20)
              </div>

              <div className="v2-card" style={{ borderRadius: 12, padding: '12px 16px', marginBottom: 16, maxHeight: 260, overflowY: 'auto' }}>
                {allCampaigns.length === 0 ? (
                  <EmptyState message="Brak dostępnych kampanii" />
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 6 }}>
                    {allCampaigns.map((c) => {
                      const id = c.id || c.campaign_id;
                      const checked = selectedIds.has(id);
                      return (
                        <label
                          key={id}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
                            borderRadius: 8, cursor: 'pointer',
                            background: checked ? 'rgba(79,142,247,0.08)' : 'transparent',
                            border: checked ? '1px solid rgba(79,142,247,0.25)' : '1px solid transparent',
                            transition: 'all 0.15s',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleCampaign(id)}
                            style={{ accentColor: '#4F8EF7' }}
                          />
                          <span style={{ fontSize: 12, color: checked ? '#fff' : 'rgba(255,255,255,0.6)', fontWeight: checked ? 600 : 400 }}>
                            {c.name || c.campaign_name}
                          </span>
                          <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginLeft: 'auto' }}>
                            {c.campaign_type}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Compare button */}
              <div style={{ marginBottom: 20 }}>
                <button
                  onClick={loadComparison}
                  disabled={selectedIds.size < 2 || compLoading}
                  style={{
                    padding: '8px 24px', borderRadius: 999, border: 'none',
                    background: selectedIds.size < 2 ? 'rgba(255,255,255,0.08)' : '#4F8EF7',
                    color: selectedIds.size < 2 ? 'rgba(255,255,255,0.3)' : '#fff',
                    fontSize: 13, fontWeight: 600, cursor: selectedIds.size < 2 ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 8,
                    transition: 'all 0.15s',
                  }}
                >
                  {compLoading && <Loader2 size={14} className="animate-spin" />}
                  Porównaj ({selectedIds.size})
                </button>
              </div>

              {/* Comparison table */}
              {comparison?.campaigns?.length > 0 && (
                <div className="v2-card" style={{ borderRadius: 12, overflow: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ ...TH, position: 'sticky', left: 0, background: '#111318', zIndex: 2, minWidth: 160 }}>
                          Metryka
                        </th>
                        {comparison.campaigns.map((c) => (
                          <th
                            key={c.campaign_id}
                            style={{ ...TH, textAlign: 'right', minWidth: 140 }}
                            title={c.campaign_name}
                          >
                            <div style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'right' }}>
                              {c.campaign_name}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {COMPARISON_METRICS.map((m) => {
                        const values = comparison.campaigns.map((c) => c[m.key]);
                        const bestIdx = getBestIdx(values, m.type);
                        return (
                          <tr key={m.key} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                            <td style={{ ...TD_DIM, position: 'sticky', left: 0, background: '#111318', zIndex: 1, fontFamily: 'DM Sans', fontSize: 12 }}>
                              {m.label}
                            </td>
                            {comparison.campaigns.map((c, idx) => (
                              <td
                                key={c.campaign_id}
                                style={{
                                  ...TD,
                                  textAlign: 'right',
                                  fontWeight: idx === bestIdx ? 700 : 400,
                                  color: idx === bestIdx ? '#4ADE80' : 'rgba(255,255,255,0.8)',
                                }}
                              >
                                {m.fmt(c[m.key])}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {comparison && comparison.campaigns?.length === 0 && (
                <div className="v2-card" style={{ borderRadius: 12 }}>
                  <EmptyState message="Brak danych dla wybranych kampanii" />
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
