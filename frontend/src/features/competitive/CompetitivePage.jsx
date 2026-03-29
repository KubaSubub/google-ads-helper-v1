import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
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

function ImpressionShareBadge({ value }) {
  if (value == null) return <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>;
  const pct = Number(value) * 100;
  const color = pct >= 30 ? '#4ADE80' : pct >= 15 ? '#FBBF24' : '#F87171';
  return (
    <span style={{ color, fontWeight: 600, fontFamily: 'monospace', fontSize: 12 }}>
      {pct.toFixed(1)}%
    </span>
  );
}

export default function CompetitivePage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState([]);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    getAuctionInsights(selectedClientId, allParams)
      .then((data) => setInsights(Array.isArray(data) ? data : []))
      .catch(() => showToast && showToast('Błąd ładowania danych konkurencji', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Konkurencja" subtitle={`Analiza ${days} dni`} />

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="animate-spin" style={{ color: '#4F8EF7' }} />
        </div>
      ) : (
        <>
          {/* Auction Insights table */}
          <div style={{ marginBottom: 8, fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Auction Insights
          </div>
          <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>
            {insights.length === 0 ? (
              <EmptyState message="Brak danych Auction Insights" />
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
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
                  {insights.map((row, i) => {
                    const isSelf = row.is_self === true || row.is_self === 1;
                    return (
                      <tr
                        key={i}
                        style={{
                          borderTop: '1px solid rgba(255,255,255,0.05)',
                          background: isSelf ? 'rgba(79,142,247,0.08)' : 'transparent',
                        }}
                      >
                        <td style={{ ...TD_DIM, fontWeight: isSelf ? 700 : 400 }}>
                          {row.display_domain || '—'}
                          {isSelf && (
                            <span style={{
                              marginLeft: 8,
                              fontSize: 10,
                              fontWeight: 600,
                              color: '#4F8EF7',
                              background: 'rgba(79,142,247,0.15)',
                              borderRadius: 4,
                              padding: '1px 6px',
                              verticalAlign: 'middle',
                            }}>
                              Ty
                            </span>
                          )}
                        </td>
                        <td style={{ ...TD, textAlign: 'right' }}>
                          <ImpressionShareBadge value={row.impression_share} />
                        </td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.overlap_rate)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.position_above_rate)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.outranking_share)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.top_of_page_rate)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.abs_top_of_page_rate)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Competitor trends placeholder */}
          <div style={{ marginBottom: 8, fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
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
