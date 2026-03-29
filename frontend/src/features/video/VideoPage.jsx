import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import { getPlacementPerformance } from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

function fmt(micros) {
  if (micros == null) return '—';
  return (micros / 1e6).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(val) {
  if (val == null) return '—';
  return Number(val).toLocaleString('pl-PL');
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
        borderLeft: `3px solid ${accent || '#4F8EF7'}`,
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>{value}</div>
    </div>
  );
}

export default function VideoPage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [loading, setLoading] = useState(false);
  const [placements, setPlacements] = useState([]);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    getPlacementPerformance(selectedClientId, allParams)
      .then((data) => setPlacements(Array.isArray(data) ? data : []))
      .catch(() => showToast && showToast('Błąd ładowania danych Video', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  // KPI aggregates
  const totalClicks = placements.reduce((s, r) => s + (Number(r.clicks) || 0), 0);
  const totalCostMicros = placements.reduce((s, r) => s + (Number(r.cost_micros) || 0), 0);
  const totalConversions = placements.reduce((s, r) => s + (Number(r.conversions) || 0), 0);
  const totalVideoViews = placements.reduce((s, r) => s + (Number(r.video_views) || 0), 0);

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Video / YouTube" subtitle={`Analiza ${days} dni`} />

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="animate-spin" style={{ color: '#FBBF24' }} />
        </div>
      ) : (
        <>
          {/* KPI summary row */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
            <KpiCard label="Kliknięcia" value={fmtNum(totalClicks)} accent="#4F8EF7" />
            <KpiCard label="Koszt (PLN)" value={fmt(totalCostMicros)} accent="#FBBF24" />
            <KpiCard label="Konwersje" value={totalConversions.toFixed(2)} accent="#4ADE80" />
            <KpiCard label="Video views" value={fmtNum(totalVideoViews)} accent="#7B5CE0" />
          </div>

          {/* YouTube placements table */}
          <div style={{ marginBottom: 8, fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Placementy YouTube
          </div>
          <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>
            {placements.length === 0 ? (
              <EmptyState message="Brak danych o placementach video" />
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={TH}>URL / Placement</th>
                    <th style={TH}>Typ</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Wyświetlenia</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Koszt (PLN)</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Video views</th>
                  </tr>
                </thead>
                <tbody>
                  {placements.map((row, i) => (
                    <tr key={i} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={TD_DIM}>{row.placement_url || row.placement || '—'}</td>
                      <td style={TD}>{row.placement_type || '—'}</td>
                      <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.clicks)}</td>
                      <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.impressions)}</td>
                      <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.cost_micros)}</td>
                      <td style={{ ...TD, textAlign: 'right' }}>
                        {row.conversions != null ? Number(row.conversions).toFixed(2) : '—'}
                      </td>
                      <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.video_views)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Creative performance placeholder */}
          <div style={{ marginBottom: 8, fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Wyniki kreacji
          </div>
          <div className="v2-card" style={{ borderRadius: 12 }}>
            <EmptyState message="Analiza kreacji video — wkrótce" />
          </div>
        </>
      )}
    </div>
  );
}
