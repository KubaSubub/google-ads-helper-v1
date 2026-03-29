import { useState, useEffect, useMemo } from 'react';
import { Loader2, TrendingUp, TrendingDown, Minus, ArrowUpDown, ChevronUp, ChevronDown, BarChart3, Users } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { useFilter } from '../../contexts/FilterContext';
import { getBenchmarks, getClientComparison } from '../../api';
import { PageHeader } from '../../components/UI';
import EmptyState from '../../components/EmptyState';
import { TH, TD, TD_DIM } from '../../constants/designTokens';

// ─── Metric display config ──────────────────────────────────────────────────
const METRIC_CONFIG = {
  ctr:  { label: 'CTR',  unit: '%', goodDir: 'higher', fmt: (v) => v.toFixed(2) + '%' },
  cpc:  { label: 'CPC',  unit: 'PLN', goodDir: 'lower',  fmt: (v) => v.toFixed(2) + ' PLN' },
  cpa:  { label: 'CPA',  unit: 'PLN', goodDir: 'lower',  fmt: (v) => v.toFixed(2) + ' PLN' },
  cvr:  { label: 'CVR',  unit: '%', goodDir: 'higher', fmt: (v) => v.toFixed(2) + '%' },
  roas: { label: 'ROAS', unit: 'x', goodDir: 'higher', fmt: (v) => v.toFixed(2) + 'x' },
};

// ─── Verdict badge ──────────────────────────────────────────────────────────
function VerdictBadge({ verdict }) {
  const map = {
    above:  { label: 'Powyzej',  color: '#4ADE80', bg: 'rgba(74,222,128,0.12)', icon: TrendingUp },
    below:  { label: 'Ponizej',  color: '#F87171', bg: 'rgba(248,113,113,0.12)', icon: TrendingDown },
    on_par: { label: 'W normie', color: '#FBBF24', bg: 'rgba(251,191,36,0.12)', icon: Minus },
  };
  const cfg = map[verdict] || map.on_par;
  const Icon = cfg.icon;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 999,
      fontSize: 11, fontWeight: 600,
      color: cfg.color, background: cfg.bg,
    }}>
      <Icon size={12} /> {cfg.label}
    </span>
  );
}

// ─── Comparison bar (client vs benchmark) ───────────────────────────────────
function ComparisonBar({ clientVal, benchVal, goodDir }) {
  if (clientVal == null || benchVal == null) return null;
  const maxVal = Math.max(clientVal, benchVal, 0.01);

  const isGood = goodDir === 'higher'
    ? clientVal >= benchVal
    : clientVal <= benchVal;

  const clientColor = isGood ? '#4ADE80' : '#F87171';
  const benchColor = 'rgba(255,255,255,0.15)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 160 }}>
      {/* Client bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', width: 50, textAlign: 'right' }}>Klient</span>
        <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
          <div style={{
            width: `${Math.min((clientVal / maxVal) * 100, 100)}%`,
            height: '100%', borderRadius: 4, background: clientColor,
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>
      {/* Benchmark bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', width: 50, textAlign: 'right' }}>Branza</span>
        <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
          <div style={{
            width: `${Math.min((benchVal / maxVal) * 100, 100)}%`,
            height: '100%', borderRadius: 4, background: benchColor,
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>
    </div>
  );
}

// ─── Metric card for industry benchmark ─────────────────────────────────────
function BenchmarkMetricCard({ item }) {
  const cfg = METRIC_CONFIG[item.metric];
  if (!cfg) return null;

  const isGood = item.verdict === 'above';
  const isBad = item.verdict === 'below';
  const accentColor = isGood ? '#4ADE80' : isBad ? '#F87171' : '#FBBF24';

  return (
    <div
      className="v2-card"
      style={{
        borderRadius: 12,
        padding: '20px 22px',
        borderLeft: `3px solid ${accentColor}`,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>
          {cfg.label}
        </span>
        <VerdictBadge verdict={item.verdict} />
      </div>

      {/* Values row */}
      <div style={{ display: 'flex', gap: 24 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>
            Twoj wynik
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: accentColor }}>
            {cfg.fmt(item.client_value)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>
            Srednia branzy
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: 'rgba(255,255,255,0.6)' }}>
            {cfg.fmt(item.benchmark_value)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>
            Roznica
          </div>
          <div style={{
            fontSize: 20, fontWeight: 700, fontFamily: 'Syne',
            color: item.pct_diff > 0 ? (cfg.goodDir === 'higher' ? '#4ADE80' : '#F87171') : (cfg.goodDir === 'higher' ? '#F87171' : '#4ADE80'),
          }}>
            {item.pct_diff > 0 ? '+' : ''}{item.pct_diff}%
          </div>
        </div>
      </div>

      {/* Bar */}
      <ComparisonBar clientVal={item.client_value} benchVal={item.benchmark_value} goodDir={cfg.goodDir} />
    </div>
  );
}

// ─── KPI Summary Card ───────────────────────────────────────────────────────
function SummaryKpi({ label, value, accent, icon: Icon }) {
  return (
    <div
      className="v2-card"
      style={{
        flex: 1, minWidth: 160,
        borderRadius: 12, padding: '18px 20px',
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

// ─── Tab 1: Industry Benchmarks ─────────────────────────────────────────────
function IndustryTab({ selectedClientId, days, showToast }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!selectedClientId) return;
    setLoading(true);
    getBenchmarks(selectedClientId, { days })
      .then((res) => setData(res))
      .catch(() => showToast && showToast('Blad ladowania benchmarkow', 'error'))
      .finally(() => setLoading(false));
  }, [selectedClientId, days]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <Loader2 size={32} className="animate-spin" style={{ color: '#4F8EF7' }} />
      </div>
    );
  }

  if (!data || data.error || !data.comparison?.length) {
    return <EmptyState message="Brak danych do porownania z benchmarkami" />;
  }

  const aboveCount = data.comparison.filter((c) => c.verdict === 'above').length;
  const belowCount = data.comparison.filter((c) => c.verdict === 'below').length;

  return (
    <>
      {/* Industry info + summary KPIs */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <SummaryKpi
          label="Branza"
          value={data.industry || 'Brak'}
          accent="#7B5CE0"
        />
        <SummaryKpi
          label="Powyzej benchmarku"
          value={`${aboveCount} / ${data.comparison.length}`}
          accent="#4ADE80"
          icon={TrendingUp}
        />
        <SummaryKpi
          label="Ponizej benchmarku"
          value={`${belowCount} / ${data.comparison.length}`}
          accent="#F87171"
          icon={TrendingDown}
        />
      </div>

      {/* Metric cards grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(340, 1fr))',
        gap: 16,
        marginBottom: 24,
      }}>
        {data.comparison.map((item) => (
          <BenchmarkMetricCard key={item.metric} item={item} />
        ))}
      </div>
    </>
  );
}

// ─── Tab 2: Client Comparison (MCC) ─────────────────────────────────────────
function ClientComparisonTab({ days, showToast }) {
  const [loading, setLoading] = useState(false);
  const [clients, setClients] = useState([]);
  const [sortKey, setSortKey] = useState('roas');
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    setLoading(true);
    getClientComparison({ days })
      .then((res) => setClients(Array.isArray(res) ? res : []))
      .catch(() => showToast && showToast('Blad ladowania porownania klientow', 'error'))
      .finally(() => setLoading(false));
  }, [days]);

  const sorted = useMemo(() => {
    const arr = [...clients];
    arr.sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return sortAsc ? av - bv : bv - av;
    });
    return arr;
  }, [clients, sortKey, sortAsc]);

  // Find best/worst per metric column
  const extremes = useMemo(() => {
    if (clients.length < 2) return {};
    const metrics = ['ctr', 'cpc', 'cpa', 'cvr', 'roas', 'cost_usd', 'conversions'];
    const result = {};
    metrics.forEach((m) => {
      const vals = clients.map((c) => c[m] ?? 0);
      result[m] = { min: Math.min(...vals), max: Math.max(...vals) };
    });
    return result;
  }, [clients]);

  function isBest(metric, val) {
    if (!extremes[metric] || clients.length < 2) return false;
    const goodDir = METRIC_CONFIG[metric]?.goodDir;
    if (goodDir === 'lower') return val === extremes[metric].min && val < extremes[metric].max;
    return val === extremes[metric].max && val > extremes[metric].min;
  }

  function isWorst(metric, val) {
    if (!extremes[metric] || clients.length < 2) return false;
    const goodDir = METRIC_CONFIG[metric]?.goodDir;
    if (goodDir === 'lower') return val === extremes[metric].max && val > extremes[metric].min;
    return val === extremes[metric].min && val < extremes[metric].max;
  }

  function handleSort(key) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  }

  function SortHeader({ label, col, align }) {
    const active = sortKey === col;
    return (
      <th
        style={{ ...TH, textAlign: align || 'right', cursor: 'pointer', userSelect: 'none' }}
        onClick={() => handleSort(col)}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
          {label}
          {active ? (
            sortAsc ? <ChevronUp size={10} /> : <ChevronDown size={10} />
          ) : (
            <ArrowUpDown size={9} style={{ opacity: 0.3 }} />
          )}
        </span>
      </th>
    );
  }

  function CellVal({ metric, val, fmt }) {
    const best = isBest(metric, val);
    const worst = isWorst(metric, val);
    let color = 'rgba(255,255,255,0.8)';
    let bg = 'transparent';
    if (best) { color = '#4ADE80'; bg = 'rgba(74,222,128,0.08)'; }
    if (worst) { color = '#F87171'; bg = 'rgba(248,113,113,0.08)'; }
    return (
      <td style={{ ...TD, textAlign: 'right', color, background: bg, fontWeight: best || worst ? 700 : 400 }}>
        {fmt ? fmt(val) : val}
      </td>
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <Loader2 size={32} className="animate-spin" style={{ color: '#4F8EF7' }} />
      </div>
    );
  }

  if (clients.length === 0) {
    return <EmptyState message="Brak klientow do porownania" />;
  }

  return (
    <div className="v2-card" style={{ borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
          <thead>
            <tr>
              <th style={{ ...TH, width: 32 }}>#</th>
              <SortHeader label="Klient" col="client_name" align="left" />
              <SortHeader label="Branza" col="industry" align="left" />
              <SortHeader label="Wydatki" col="cost_usd" />
              <SortHeader label="Konwersje" col="conversions" />
              <SortHeader label="CTR" col="ctr" />
              <SortHeader label="CPC" col="cpc" />
              <SortHeader label="CPA" col="cpa" />
              <SortHeader label="CVR" col="cvr" />
              <SortHeader label="ROAS" col="roas" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((c, i) => (
              <tr key={c.client_id} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ ...TD_DIM, textAlign: 'center', fontSize: 11 }}>{i + 1}</td>
                <td style={{ ...TD, textAlign: 'left', fontWeight: 600, color: '#fff' }}>
                  {c.client_name}
                </td>
                <td style={{ ...TD_DIM, textAlign: 'left' }}>
                  {c.industry || '—'}
                </td>
                <CellVal metric="cost_usd" val={c.cost_usd} fmt={(v) => `${v.toLocaleString('pl-PL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} PLN`} />
                <CellVal metric="conversions" val={c.conversions} fmt={(v) => v.toFixed(1)} />
                <CellVal metric="ctr" val={c.ctr} fmt={(v) => v.toFixed(2) + '%'} />
                <CellVal metric="cpc" val={c.cpc} fmt={(v) => v.toFixed(2)} />
                <CellVal metric="cpa" val={c.cpa} fmt={(v) => v.toFixed(2)} />
                <CellVal metric="cvr" val={c.cvr} fmt={(v) => v.toFixed(2) + '%'} />
                <CellVal metric="roas" val={c.roas} fmt={(v) => v.toFixed(2) + 'x'} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────
const TABS = [
  { key: 'industry', label: 'Benchmarki branzowe', icon: BarChart3 },
  { key: 'mcc', label: 'Porownanie klientow', icon: Users },
];

export default function BenchmarksPage() {
  const { selectedClientId, showToast } = useApp();
  const { days } = useFilter();
  const [activeTab, setActiveTab] = useState('industry');

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader title="Benchmarki" subtitle={`Analiza ${days} dni`} />

      {/* Tab pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {TABS.map((tab) => {
          const active = activeTab === tab.key;
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '7px 16px', borderRadius: 999,
                fontSize: 12, fontWeight: 500, cursor: 'pointer',
                border: active ? '1px solid rgba(79,142,247,0.5)' : '1px solid rgba(255,255,255,0.1)',
                background: active ? 'rgba(79,142,247,0.12)' : 'rgba(255,255,255,0.04)',
                color: active ? '#4F8EF7' : 'rgba(255,255,255,0.55)',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={13} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'industry' && (
        <IndustryTab selectedClientId={selectedClientId} days={days} showToast={showToast} />
      )}
      {activeTab === 'mcc' && (
        <ClientComparisonTab days={days} showToast={showToast} />
      )}
    </div>
  );
}
