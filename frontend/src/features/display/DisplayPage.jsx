import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import {
  getPlacementPerformance,
  getTopicPerformance,
  getAudiencePerformance,
  getBidModifiers,
} from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

const TABS = [
  { id: 'placements', label: 'Placements' },
  { id: 'topics', label: 'Topics' },
  { id: 'audiences', label: 'Audiences' },
  { id: 'bid_modifiers', label: 'Bid Modifiers' },
];

function fmt(micros) {
  if (micros == null) return '—';
  return (micros / 1e6).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(val) {
  if (val == null) return '—';
  return Number(val).toLocaleString('pl-PL');
}

export default function DisplayPage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [activeTab, setActiveTab] = useState('placements');
  const [loading, setLoading] = useState(false);
  const [placements, setPlacements] = useState([]);
  const [topics, setTopics] = useState([]);
  const [audiences, setAudiences] = useState([]);
  const [bidModifiers, setBidModifiers] = useState([]);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    Promise.all([
      getPlacementPerformance(selectedClientId, allParams).catch(() => []),
      getTopicPerformance(selectedClientId, allParams).catch(() => []),
      getAudiencePerformance(selectedClientId, allParams).catch(() => []),
      getBidModifiers(selectedClientId, allParams).catch(() => []),
    ])
      .then(([p, t, a, b]) => {
        setPlacements(Array.isArray(p) ? p : []);
        setTopics(Array.isArray(t) ? t : []);
        setAudiences(Array.isArray(a) ? a : []);
        setBidModifiers(Array.isArray(b) ? b : []);
      })
      .catch(() => showToast && showToast('Błąd ładowania danych Display', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Display" subtitle={`Analiza ${days} dni`} />

      {/* Tab switcher */}
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
        <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden' }}>

          {/* ── Placements ── */}
          {activeTab === 'placements' && (
            placements.length === 0
              ? <EmptyState message="Brak danych o placementach" />
              : (
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
              )
          )}

          {/* ── Topics ── */}
          {activeTab === 'topics' && (
            topics.length === 0
              ? <EmptyState message="Brak danych o tematach" />
              : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={TH}>Temat</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Modyfikator stawki</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Wyświetlenia</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Koszt (PLN)</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topics.map((row, i) => (
                      <tr key={i} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={TD_DIM}>{row.topic_path || row.topic || '—'}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>
                          {row.bid_modifier != null
                            ? `${(Number(row.bid_modifier) * 100).toFixed(0)}%`
                            : '—'}
                        </td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.clicks)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.impressions)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.cost_micros)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>
                          {row.conversions != null ? Number(row.conversions).toFixed(2) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
          )}

          {/* ── Audiences ── */}
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
                        <tr key={i} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                          <td style={TD_DIM}>{row.audience_name || '—'}</td>
                          <td style={TD}>{row.audience_type || '—'}</td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {cost != null
                              ? cost.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                              : '—'}
                          </td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {conv != null ? conv.toFixed(2) : '—'}
                          </td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {cpa != null
                              ? cpa.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                              : '—'}
                          </td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {roas != null ? roas.toFixed(2) : '—'}
                          </td>
                          <td style={{ ...TD, textAlign: 'center' }}>
                            {row.anomaly
                              ? <span style={{ color: '#F87171', fontWeight: 600, fontSize: 12 }}>!</span>
                              : <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 12 }}>—</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )
          )}

          {/* ── Bid Modifiers ── */}
          {activeTab === 'bid_modifiers' && (
            bidModifiers.length === 0
              ? <EmptyState message="Brak modyfikatorów stawek" />
              : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={TH}>Kampania</th>
                      <th style={TH}>Typ modyfikatora</th>
                      <th style={TH}>Urządzenie / Lokalizacja</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Modyfikator</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bidModifiers.map((row, i) => {
                      const val = row.modifier_value != null ? Number(row.modifier_value) : null;
                      return (
                        <tr key={i} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                          <td style={TD_DIM}>{row.campaign_name || '—'}</td>
                          <td style={TD}>{row.modifier_type || '—'}</td>
                          <td style={TD}>{row.device || row.location || '—'}</td>
                          <td style={{ ...TD, textAlign: 'right' }}>
                            {val != null
                              ? `${val >= 0 ? '+' : ''}${(val * 100).toFixed(0)}%`
                              : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )
          )}

        </div>
      )}
    </div>
  );
}
