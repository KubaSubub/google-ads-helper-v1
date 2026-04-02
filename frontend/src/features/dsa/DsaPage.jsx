import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import {
  getDsaTargets,
  getDsaCoverage,
  getDsaHeadlines,
  getDsaSearchOverlap,
} from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

const TABS = [
  { id: 'targets', label: 'Cele DSA' },
  { id: 'headlines', label: 'Naglowki' },
  { id: 'overlap', label: 'DSA vs Search' },
];

function fmt(micros) {
  if (micros == null) return '\u2014';
  return (micros / 1e6).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(val) {
  if (val == null) return '\u2014';
  return Number(val).toLocaleString('pl-PL');
}

function fmtUsd(val) {
  if (val == null) return '\u2014';
  return Number(val).toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(val) {
  if (val == null) return '\u2014';
  return `${Number(val).toFixed(2)}%`;
}

const TARGET_TYPE_LABELS = {
  URL_CONTAINS: 'URL zawiera',
  CATEGORY: 'Kategoria',
  ALL_WEBPAGES: 'Wszystkie strony',
  PAGE_FEED: 'Feed stron',
};

export default function DsaPage() {
  const { selectedClientId, showToast } = useApp();
  const { allParams, days } = useFilter();

  const [activeTab, setActiveTab] = useState('targets');
  const [loading, setLoading] = useState(false);
  const [targets, setTargets] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [headlines, setHeadlines] = useState({ headlines: [] });
  const [overlap, setOverlap] = useState({ overlapping_terms: [] });

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    Promise.all([
      getDsaTargets(selectedClientId, allParams).catch(() => []),
      getDsaCoverage(selectedClientId).catch(() => null),
      getDsaHeadlines(selectedClientId, allParams).catch(() => ({ headlines: [] })),
      getDsaSearchOverlap(selectedClientId, allParams).catch(() => ({ overlapping_terms: [] })),
    ])
      .then(([t, c, h, o]) => {
        setTargets(Array.isArray(t) ? t : []);
        setCoverage(c);
        setHeadlines(h && h.headlines ? h : { headlines: [] });
        setOverlap(o && o.overlapping_terms ? o : { overlapping_terms: [] });
      })
      .catch(() => showToast && showToast('Blad ladowania danych DSA', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, JSON.stringify(allParams)]);

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Dynamic Search Ads" subtitle={`Analiza ${days} dni`} />

      {/* Coverage summary */}
      {coverage && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
          <div className="v2-card" style={{ padding: '12px 20px', borderRadius: 10, flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              Kampanie DSA
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: C.accentBlue }}>
              {coverage.dsa_campaign_count}
            </div>
          </div>
          <div className="v2-card" style={{ padding: '12px 20px', borderRadius: 10, flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              Kampanie Search
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: C.w80 }}>
              {coverage.total_search_campaigns}
            </div>
          </div>
          <div className="v2-card" style={{ padding: '12px 20px', borderRadius: 10, flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              Cele DSA
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: C.accentPurple }}>
              {targets.length}
            </div>
          </div>
          <div className="v2-card" style={{ padding: '12px 20px', borderRadius: 10, flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              Nakladanie fraz
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: C.warning }}>
              {overlap.overlap_count || 0}
            </div>
          </div>
        </div>
      )}

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
                border: active ? '1px solid #4F8EF7' : B.medium,
                background: active ? C.infoBg : 'transparent',
                color: active ? C.accentBlue : C.textSecondary,
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
          <Loader2 size={32} className="animate-spin" style={{ color: C.accentBlue }} />
        </div>
      ) : (
        <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden' }}>

          {/* -- Targets tab -- */}
          {activeTab === 'targets' && (
            targets.length === 0
              ? <EmptyState message="Brak celow DSA" />
              : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={TH}>Typ celu</th>
                      <th style={TH}>Wartosc</th>
                      <th style={TH}>Status</th>
                      <th style={TH}>Kampania</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Klikniecia</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Wyswietlenia</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Koszt</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                      <th style={{ ...TH, textAlign: 'right' }}>CTR</th>
                      <th style={{ ...TH, textAlign: 'right' }}>CPA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {targets.map((row, i) => (
                      <tr key={i} style={{ borderTop: `1px solid ${C.w05}` }}>
                        <td style={TD}>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            fontWeight: 500,
                            background: row.target_type === 'URL_CONTAINS'
                              ? C.infoBg
                              : row.target_type === 'CATEGORY'
                                ? 'rgba(123,92,224,0.15)'
                                : C.w07,
                            color: row.target_type === 'URL_CONTAINS'
                              ? C.accentBlue
                              : row.target_type === 'CATEGORY'
                                ? C.accentPurple
                                : C.w50,
                          }}>
                            {TARGET_TYPE_LABELS[row.target_type] || row.target_type}
                          </span>
                        </td>
                        <td style={TD_DIM}>{row.target_value}</td>
                        <td style={TD}>
                          <span style={{
                            color: row.status === 'ENABLED' ? C.success : C.warning,
                            fontSize: 11,
                          }}>
                            {row.status}
                          </span>
                        </td>
                        <td style={TD_DIM}>{row.campaign_name || '\u2014'}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.clicks)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.impressions)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtUsd(row.cost_usd)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{row.conversions != null ? Number(row.conversions).toFixed(2) : '\u2014'}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.ctr)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtUsd(row.cpa)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
          )}

          {/* -- Headlines tab -- */}
          {activeTab === 'headlines' && (
            (headlines.headlines || []).length === 0
              ? <EmptyState message="Brak naglowkow DSA" />
              : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={TH}>Wyszukiwana fraza</th>
                      <th style={TH}>Wygenerowany naglowek</th>
                      <th style={TH}>Landing page</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Klikniecia</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Wyswietlenia</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Koszt</th>
                      <th style={{ ...TH, textAlign: 'right' }}>CTR</th>
                      <th style={{ ...TH, textAlign: 'right' }}>Konwersje</th>
                      <th style={{ ...TH, textAlign: 'right' }}>CPA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(headlines.headlines || []).map((row, i) => (
                      <tr key={i} style={{ borderTop: `1px solid ${C.w05}` }}>
                        <td style={TD_DIM}>{row.search_term}</td>
                        <td style={{ ...TD, color: C.accentBlue, fontFamily: 'DM Sans', fontWeight: 500 }}>{row.generated_headline}</td>
                        <td style={{ ...TD_DIM, fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <a href={row.landing_page_url} target="_blank" rel="noopener noreferrer"
                             style={{ color: C.w40, textDecoration: 'none' }}>
                            {row.landing_page_url}
                          </a>
                        </td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.clicks)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.impressions)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtUsd(row.cost_usd)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.ctr)}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{row.conversions != null ? Number(row.conversions).toFixed(2) : '\u2014'}</td>
                        <td style={{ ...TD, textAlign: 'right' }}>{fmtUsd(row.cpa)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
          )}

          {/* -- Overlap tab -- */}
          {activeTab === 'overlap' && (
            (overlap.overlapping_terms || []).length === 0
              ? <EmptyState message="Brak nakladajacych sie fraz DSA i Search" />
              : (
                <>
                  <div style={{ padding: '12px 16px', display: 'flex', gap: 24, borderBottom: `1px solid ${C.w05}` }}>
                    <div style={{ fontSize: 12, color: C.w50 }}>
                      Tylko DSA: <span style={{ color: C.accentBlue, fontWeight: 600 }}>{overlap.dsa_only_count || 0}</span>
                    </div>
                    <div style={{ fontSize: 12, color: C.w50 }}>
                      Tylko Search: <span style={{ color: C.accentPurple, fontWeight: 600 }}>{overlap.search_only_count || 0}</span>
                    </div>
                    <div style={{ fontSize: 12, color: C.w50 }}>
                      Wspolne: <span style={{ color: C.warning, fontWeight: 600 }}>{overlap.overlap_count || 0}</span>
                    </div>
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={TH}>Fraza</th>
                        <th style={{ ...TH, textAlign: 'right' }}>DSA klik.</th>
                        <th style={{ ...TH, textAlign: 'right' }}>DSA koszt</th>
                        <th style={{ ...TH, textAlign: 'right' }}>DSA konw.</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Search klik.</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Search koszt</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Search konw.</th>
                        <th style={{ ...TH, textAlign: 'right' }}>Suma koszt</th>
                        <th style={TH}>Rekomendacja</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(overlap.overlapping_terms || []).map((row, i) => {
                        const isDsaBetter = row.dsa_conversions > row.search_conversions;
                        return (
                          <tr key={i} style={{ borderTop: `1px solid ${C.w05}` }}>
                            <td style={{ ...TD, fontWeight: 500 }}>{row.search_term}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.dsa_clicks)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtUsd(row.dsa_cost_usd)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{Number(row.dsa_conversions).toFixed(2)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtNum(row.search_clicks)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{fmtUsd(row.search_cost_usd)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{Number(row.search_conversions).toFixed(2)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: C.warning }}>{fmtUsd(row.total_cost_usd)}</td>
                            <td style={{
                              ...TD,
                              fontSize: 11,
                              color: isDsaBetter ? C.success : C.danger,
                              maxWidth: 220,
                            }}>
                              {row.recommendation}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </>
              )
          )}
        </div>
      )}
    </div>
  );
}
