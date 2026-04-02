import { useState, useEffect, useMemo } from 'react';
import { Loader2, Search, Trophy, Users, TrendingUp } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import { getAuctionInsights } from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

function fmtPct(val) {
  if (val == null) return '—';
  return (Number(val) * 100).toFixed(1) + '%';
}

function pctVal(val) {
  if (val == null) return 0;
  return Number(val) * 100;
}

// ─── KPI Card ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, accent, icon: Icon }) {
  return (
    <div
      className="v2-card"
      style={{
        flex: 1,
        minWidth: 180,
        borderRadius: 12,
        padding: '18px 20px',
        borderLeft: `3px solid ${accent || C.accentBlue}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
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

// ─── Horizontal bar for metric visualization ─────────────────────────────────
function MetricBar({ value, maxValue, color }) {
  if (value == null || maxValue <= 0) return <span style={{ color: C.w30 }}>—</span>;
  const pct = Number(value) * 100;
  const widthPct = Math.min((pct / maxValue) * 100, 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
      <span style={{ fontSize: 12, fontFamily: 'monospace', color: C.w80, minWidth: 44, textAlign: 'right' }}>
        {pct.toFixed(1)}%
      </span>
      <div style={{ width: 80, height: 6, borderRadius: 3, background: C.w06, overflow: 'hidden', flexShrink: 0 }}>
        <div
          style={{
            width: `${widthPct}%`,
            height: '100%',
            borderRadius: 3,
            background: color,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </div>
  );
}

// ─── Impression share badge (reused for own-row highlight) ───────────────────
function ImpressionShareBar({ value, maxValue, isSelf }) {
  if (value == null) return <span style={{ color: C.w30 }}>—</span>;
  const pct = Number(value) * 100;
  const widthPct = maxValue > 0 ? Math.min((pct / maxValue) * 100, 100) : 0;
  const color = isSelf ? C.accentBlue : pct >= 30 ? C.success : pct >= 15 ? C.warning : C.danger;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
      <span style={{ fontSize: 12, fontFamily: 'monospace', color, fontWeight: isSelf ? 700 : 500, minWidth: 44, textAlign: 'right' }}>
        {pct.toFixed(1)}%
      </span>
      <div style={{ width: 80, height: 6, borderRadius: 3, background: C.w06, overflow: 'hidden', flexShrink: 0 }}>
        <div
          style={{
            width: `${widthPct}%`,
            height: '100%',
            borderRadius: 3,
            background: color,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </div>
  );
}

export default function CompetitivePage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    getAuctionInsights(selectedClientId, allParams)
      .then((data) => setInsights(Array.isArray(data) ? data : []))
      .catch(() => showToast && showToast('Błąd ładowania danych konkurencji', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  // ── Sorted by impression share descending ──
  const sorted = useMemo(() => {
    return [...insights].sort((a, b) => {
      const aVal = a.impression_share != null ? Number(a.impression_share) : -1;
      const bVal = b.impression_share != null ? Number(b.impression_share) : -1;
      return bVal - aVal;
    });
  }, [insights]);

  // ── Filtered by search query ──
  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return sorted;
    const q = searchQuery.trim().toLowerCase();
    return sorted.filter((row) => {
      const domain = (row.display_domain || '').toLowerCase();
      return domain.includes(q);
    });
  }, [sorted, searchQuery]);

  // ── KPI computations ──
  const selfRow = useMemo(() => insights.find((r) => r.is_self === true || r.is_self === 1), [insights]);
  const competitorCount = insights.length > 0 ? (selfRow ? insights.length - 1 : insights.length) : 0;

  const selfImprShare = selfRow?.impression_share != null ? pctVal(selfRow.impression_share) : null;
  const selfOutranking = selfRow?.outranking_share != null ? pctVal(selfRow.outranking_share) : null;

  // Position among all (1-indexed, based on impression share)
  const selfPosition = useMemo(() => {
    if (!selfRow) return null;
    const idx = sorted.findIndex((r) => r.is_self === true || r.is_self === 1);
    return idx >= 0 ? idx + 1 : null;
  }, [sorted, selfRow]);

  // Max values for bar proportional widths
  const maxImprShare = useMemo(() => Math.max(...insights.map((r) => pctVal(r.impression_share)), 1), [insights]);
  const maxOverlap = useMemo(() => Math.max(...insights.map((r) => pctVal(r.overlap_rate)), 1), [insights]);
  const maxOutranking = useMemo(() => Math.max(...insights.map((r) => pctVal(r.outranking_share)), 1), [insights]);

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Konkurencja" subtitle={`Analiza ${days} dni`} />

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="animate-spin" style={{ color: C.accentBlue }} />
        </div>
      ) : (
        <>
          {/* ── KPI header row ── */}
          {insights.length > 0 && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
              <KpiCard
                label="Twój udział w wyświetleniach"
                value={selfImprShare != null ? `${selfImprShare.toFixed(1)}%` : '—'}
                accent="#4F8EF7"
                icon={TrendingUp}
              />
              <KpiCard
                label="Twój outranking share"
                value={selfOutranking != null ? `${selfOutranking.toFixed(1)}%` : '—'}
                accent="#7B5CE0"
                icon={Trophy}
              />
              <KpiCard
                label="Liczba konkurentów"
                value={competitorCount}
                accent="#FBBF24"
                icon={Users}
              />
            </div>
          )}

          {/* ── Competitive position summary ── */}
          {selfPosition != null && insights.length > 0 && (
            <div
              className="v2-card"
              style={{
                borderRadius: 12,
                padding: '14px 20px',
                marginBottom: 20,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                borderLeft: '3px solid #4F8EF7',
              }}
            >
              <Trophy size={16} style={{ color: C.accentBlue, flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: C.w70 }}>
                Jesteś na pozycji{' '}
                <span style={{ fontWeight: 700, color: C.accentBlue, fontFamily: 'Syne' }}>
                  {selfPosition}
                </span>
                {' '}z{' '}
                <span style={{ fontWeight: 700, color: '#fff', fontFamily: 'Syne' }}>
                  {insights.length}
                </span>
                {' '}konkurentów pod względem impression share
              </span>
            </div>
          )}

          {/* ── Section label + search ── */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Auction Insights
            </div>
            {insights.length > 0 && (
              <div style={{ position: 'relative', width: 220 }}>
                <Search
                  size={13}
                  style={{
                    position: 'absolute',
                    left: 10,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: C.w30,
                    pointerEvents: 'none',
                  }}
                />
                <input
                  type="text"
                  placeholder="Szukaj domeny..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px 6px 30px',
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

          {/* ── Auction Insights table ── */}
          <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>
            {filtered.length === 0 ? (
              <EmptyState message={searchQuery ? 'Brak wyników dla podanej frazy' : 'Brak danych Auction Insights'} />
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ ...TH, width: 32 }}>#</th>
                    <th style={TH}>Domena / Konkurent</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Udział w wyświetleniach</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Overlap rate</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Position above rate</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Outranking share</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Top of page rate</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Abs. top of page</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((row, i) => {
                    const isSelf = row.is_self === true || row.is_self === 1;
                    // Find rank in the full sorted list (not filtered)
                    const rankInSorted = sorted.findIndex((r) => r === row);
                    const rank = rankInSorted >= 0 ? rankInSorted + 1 : i + 1;
                    return (
                      <tr
                        key={i}
                        style={{
                          borderTop: `1px solid ${C.w05}`,
                          background: isSelf ? 'rgba(79,142,247,0.08)' : 'transparent',
                        }}
                      >
                        {/* Rank */}
                        <td style={{ ...TD_DIM, textAlign: 'center', fontSize: 11, fontWeight: 500 }}>
                          {rank}
                        </td>
                        {/* Domain */}
                        <td style={{ ...TD_DIM, fontWeight: isSelf ? 700 : 400, color: isSelf ? C.accentBlue : TD_DIM.color }}>
                          {row.display_domain || '—'}
                          {isSelf && (
                            <span style={{
                              marginLeft: 8,
                              fontSize: 10,
                              fontWeight: 600,
                              color: C.accentBlue,
                              background: C.infoBg,
                              borderRadius: 4,
                              padding: '1px 6px',
                              verticalAlign: 'middle',
                            }}>
                              Ty
                            </span>
                          )}
                        </td>
                        {/* Impression share with bar */}
                        <td style={{ ...TD, textAlign: 'right' }}>
                          <ImpressionShareBar value={row.impression_share} maxValue={maxImprShare} isSelf={isSelf} />
                        </td>
                        {/* Overlap rate with bar */}
                        <td style={{ ...TD, textAlign: 'right' }}>
                          <MetricBar value={row.overlap_rate} maxValue={maxOverlap} color="#7B5CE0" />
                        </td>
                        {/* Position above rate */}
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.position_above_rate)}</td>
                        {/* Outranking share with bar */}
                        <td style={{ ...TD, textAlign: 'right' }}>
                          <MetricBar value={row.outranking_share} maxValue={maxOutranking} color="#4ADE80" />
                        </td>
                        {/* Top of page rate */}
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.top_of_page_rate)}</td>
                        {/* Abs top of page rate */}
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.abs_top_of_page_rate)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Competitor trends placeholder */}
          <div style={{ marginBottom: 8, fontSize: 11, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Trendy konkurencji
          </div>
          <div className="v2-card" style={{ borderRadius: 12 }}>
            <EmptyState message="Trendy konkurencji — wkrótce" />
          </div>
        </>
      )}
    </div>
  );
}
