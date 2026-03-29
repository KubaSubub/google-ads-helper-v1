import { useState, useCallback } from 'react'
import {
    Loader2, AlertTriangle, Target, Layers, CalendarDays, Hash, FileText, Globe,
    GitBranch, Clock, Users, Zap, BarChart3, Activity, Crosshair, GraduationCap,
    Briefcase, ShieldCheck, PieChart, Headphones, Link2, Star,
    Shuffle, Settings2, ChevronRight, Pin,
} from 'lucide-react'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import EmptyState from '../../components/EmptyState'
import { ErrorMessage } from '../../components/UI'
import { CARD, TH, TD, TD_DIM } from '../../constants/designTokens'
import { CAMP_TYPES, CAMP_LABELS } from '../../constants/campaignTypes'
import useAuditData from './hooks/useAuditData'
import BentoCard from './components/BentoCard'

// Section components
import WastedSpendSection from './components/sections/WastedSpendSection'
import DaypartingSection from './components/sections/DaypartingSection'
import MatchTypeSection from './components/sections/MatchTypeSection'
import NgramSection from './components/sections/NgramSection'
import RsaSection from './components/sections/RsaSection'
import LandingPageSection from './components/sections/LandingPageSection'
import HourlyDaypartingSection from './components/sections/HourlyDaypartingSection'
import AccountStructureSection from './components/sections/AccountStructureSection'
import BiddingAdvisorSection from './components/sections/BiddingAdvisorSection'
import AdGroupHealthSection from './components/sections/AdGroupHealthSection'
import SmartBiddingHealthSection from './components/sections/SmartBiddingHealthSection'
import ParetoSection from './components/sections/ParetoSection'
import ScalingSection from './components/sections/ScalingSection'
import TargetVsActualSection from './components/sections/TargetVsActualSection'
import LearningStatusSection from './components/sections/LearningStatusSection'
import PortfolioHealthSection from './components/sections/PortfolioHealthSection'
import ConversionQualitySection from './components/sections/ConversionQualitySection'
import DemographicsSection from './components/sections/DemographicsSection'
import AudiencePerfSection from './components/sections/AudiencePerfSection'
import MissingExtSection from './components/sections/MissingExtSection'
import ExtPerfSection from './components/sections/ExtPerfSection'
import PmaxCannibalizationSection from './components/sections/PmaxCannibalizationSection'

export default function AuditCenterPage() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days, setFilter } = useFilter()
    const { data, prevData, loading, error, ngramSize, setNgramSize, reload } = useAuditData(selectedClientId, allParams)
    const [activeSection, setActiveSection] = useState(null)

    const LS_KEY = 'audit-center-pinned'
    const [pinnedKeys, setPinnedKeys] = useState(() => {
        try { return JSON.parse(localStorage.getItem(LS_KEY)) || [] } catch { return [] }
    })
    const togglePin = useCallback((key) => {
        setPinnedKeys(prev => {
            const next = prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
            localStorage.setItem(LS_KEY, JSON.stringify(next))
            return next
        })
    }, [])
    const unpinAll = useCallback(() => {
        setPinnedKeys([])
        localStorage.removeItem(LS_KEY)
    }, [])

    const campFilter = allParams.campaign_type || 'ALL'

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (error) return <ErrorMessage message={error} onRetry={reload} />

    // Extract numeric values for period comparison
    // Returns { current, previous } or null if not comparable
    // upIsGood: true = higher is better (scores), false = lower is better (waste, issues)
    const comparisonDefs = {
        waste:              { cur: () => data.waste?.total_waste_usd,                     prev: () => prevData.waste?.total_waste_usd,                     upIsGood: false },
        bidding:            { cur: () => data.bidding?.changes_needed,                    prev: () => prevData.bidding?.changes_needed,                    upIsGood: false },
        convHealth:         { cur: () => data.convHealth?.score,                          prev: () => prevData.convHealth?.score,                          upIsGood: true },
        convQuality:        { cur: () => data.convQuality?.quality_score,                 prev: () => prevData.convQuality?.quality_score,                 upIsGood: true },
        smartBidding:       { cur: () => data.smartBidding?.summary?.critical,            prev: () => prevData.smartBidding?.summary?.critical,            upIsGood: false },
        learningStatus:     { cur: () => data.learningStatus?.learning_count,             prev: () => prevData.learningStatus?.learning_count,             upIsGood: false },
        adGroupHealth:      { cur: () => data.adGroupHealth?.details?.length,             prev: () => prevData.adGroupHealth?.details?.length,             upIsGood: false },
        demographics:       { cur: () => data.demographics?.anomalies?.length,            prev: () => prevData.demographics?.anomalies?.length,            upIsGood: false },
        pmaxCannibalization:{ cur: () => data.pmaxCannibalization?.summary?.total_overlap, prev: () => prevData.pmaxCannibalization?.summary?.total_overlap, upIsGood: false },
        missingExt:         { cur: () => data.missingExt?.campaigns?.length,              prev: () => prevData.missingExt?.campaigns?.length,              upIsGood: false },
    }

    function getChangePct(key) {
        const def = comparisonDefs[key]
        if (!def) return null
        const cur = def.cur()
        const prev = def.prev()
        if (cur == null || prev == null || typeof cur !== 'number' || typeof prev !== 'number') return null
        if (prev === 0 && cur === 0) return null
        const pct = prev === 0 ? 100 : ((cur - prev) / Math.abs(prev)) * 100
        return { pct: Math.round(pct), upIsGood: def.upIsGood }
    }

    // Card definitions
    const cards = [
        { key: 'waste', title: 'Zmarnowany budżet', icon: AlertTriangle, cat: 'budget', types: ['SEARCH','PERFORMANCE_MAX','SHOPPING'],
          value: data.waste ? `${data.waste.total_waste_usd?.toFixed(0) || 0} zł` : '—', sub: data.waste ? `${data.waste.waste_pct}% spend · ${data.waste.categories?.length || 0} kategorii` : '',
          status: data.waste ? (data.waste.waste_pct > 3 ? 'danger' : data.waste.waste_pct > 1 ? 'warning' : 'ok') : 'neutral' },
        { key: 'bidding', title: 'Strategia bidowania', icon: Target, cat: 'budget', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.bidding ? `${data.bidding.changes_needed || 0} zmian` : '—', sub: data.bidding ? `${data.bidding.total_campaigns || 0} kampanii` : '',
          status: data.bidding ? (data.bidding.changes_needed > 2 ? 'danger' : data.bidding.changes_needed > 0 ? 'warning' : 'ok') : 'neutral' },
        { key: 'convHealth', title: 'Zdrowie konwersji', icon: AlertTriangle, cat: 'quality', types: ['SEARCH','PERFORMANCE_MAX','SHOPPING','DISPLAY','VIDEO'],
          value: data.convHealth ? `${data.convHealth.score}/100` : '—', sub: data.convHealth ? `${data.convHealth.total_campaigns} kampanii` : '',
          status: data.convHealth ? (data.convHealth.score >= 80 ? 'ok' : data.convHealth.score >= 50 ? 'warning' : 'danger') : 'neutral' },
        { key: 'convQuality', title: 'Jakość konwersji', icon: ShieldCheck, cat: 'quality', types: ['SEARCH','PERFORMANCE_MAX','SHOPPING'],
          value: data.convQuality ? `${data.convQuality.quality_score}/100` : '—', sub: data.convQuality ? `${data.convQuality.issues?.length || 0} problemów` : '',
          status: data.convQuality ? (data.convQuality.quality_score >= 80 ? 'ok' : data.convQuality.quality_score >= 50 ? 'warning' : 'danger') : 'neutral' },
        { key: 'targetVsActual', title: 'Target vs Rzeczywistość', icon: Crosshair, cat: 'budget', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.targetVsActual ? `${data.targetVsActual.items?.length || 0} kampanii` : '—', sub: 'Smart Bidding', status: 'info' },
        { key: 'smartBidding', title: 'Smart Bidding', icon: Zap, cat: 'budget', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.smartBidding ? `${data.smartBidding.summary?.critical || 0} kryt.` : '—', sub: data.smartBidding ? `${data.smartBidding.summary?.low_volume || 0} niski wolumen` : '',
          status: data.smartBidding?.summary?.critical > 0 ? 'danger' : data.smartBidding?.summary?.low_volume > 0 ? 'warning' : 'ok' },
        { key: 'matchType', title: 'Dopasowania', icon: Layers, cat: 'search', types: ['SEARCH'],
          value: data.matchType ? `${data.matchType.match_types?.length || 0} typów` : '—', sub: data.matchType ? `${data.matchType.total_keywords || 0} keywords` : '', status: 'info' },
        { key: 'dayparting', title: 'Harmonogram tygodnia', icon: CalendarDays, cat: 'search', types: ['SEARCH'],
          value: data.daypart ? 'Aktywne' : '—', sub: 'Analiza dni tygodnia', status: 'info' },
        { key: 'hourly', title: 'Harmonogram godzinowy', icon: Clock, cat: 'search', types: ['SEARCH'],
          value: data.hourly ? 'Heatmapa' : '—', sub: '0-23h', status: 'info' },
        { key: 'ngram', title: 'N-gramy', icon: Hash, cat: 'search', types: ['SEARCH'],
          value: data.ngram ? `${data.ngram.total} wyników` : '—', sub: `${ngramSize}-gramy`, status: 'info' },
        { key: 'rsa', title: 'Reklamy RSA', icon: FileText, cat: 'search', types: ['SEARCH'],
          value: data.rsa ? `${data.rsa.ad_groups?.length || 0} grup` : '—', sub: 'Analiza wariantów', status: 'info' },
        { key: 'landing', title: 'Strony docelowe', icon: Globe, cat: 'search', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.landing ? `${data.landing.pages?.length || 0} URL` : '—', sub: 'Wydajność landing pages', status: 'info' },
        { key: 'structure', title: 'Struktura konta', icon: GitBranch, cat: 'quality', types: ['SEARCH','PERFORMANCE_MAX','SHOPPING'],
          value: data.structure?.issues?.length ? `${data.structure.issues.length} problemów` : 'OK', sub: 'Audyt struktury',
          status: data.structure?.issues?.length > 0 ? 'warning' : 'ok' },
        { key: 'adGroupHealth', title: 'Zdrowie grup reklam', icon: Users, cat: 'quality', types: ['SEARCH'],
          value: data.adGroupHealth ? `${data.adGroupHealth.details?.length || 0} prob.` : '—', sub: data.adGroupHealth ? `z ${data.adGroupHealth.total_ad_groups} grup` : '',
          status: data.adGroupHealth?.details?.length > 0 ? 'warning' : 'ok' },
        { key: 'pareto', title: 'Pareto 80/20', icon: BarChart3, cat: 'search', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.pareto ? `${data.pareto.campaign_pareto?.top_campaigns_for_80pct || '?'} kamp.` : '—', sub: '80% wartości', status: 'info' },
        { key: 'scaling', title: 'Okazje do skalowania', icon: Activity, cat: 'search', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.scaling ? `${data.scaling.opportunities?.length || 0} kampanii` : '—', sub: 'Potencjał wzrostu',
          status: data.scaling?.opportunities?.length > 0 ? 'ok' : 'neutral' },
        { key: 'learningStatus', title: 'Status nauki', icon: GraduationCap, cat: 'budget', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.learningStatus ? `${data.learningStatus.learning_count || 0} w nauce` : '—', sub: data.learningStatus ? `z ${data.learningStatus.total_smart_bidding || 0}` : '',
          status: data.learningStatus?.learning_count > 0 ? 'warning' : 'ok' },
        { key: 'portfolioHealth', title: 'Strategie portfelowe', icon: Briefcase, cat: 'budget', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.portfolioHealth ? `${data.portfolioHealth.total_portfolios || 0} portfeli` : '—', sub: 'Portfolio bidding', status: 'info' },
        { key: 'demographics', title: 'Demografia', icon: PieChart, cat: 'search', types: ['SEARCH','DISPLAY','VIDEO'],
          value: data.demographics ? `${data.demographics.anomalies?.length || 0} anomalii` : '—', sub: 'CPA per segment',
          status: data.demographics?.anomalies?.length > 0 ? 'warning' : 'ok' },
        { key: 'pmaxCannibalization', title: 'Kanibalizacja PMax↔Search', icon: Shuffle, cat: 'pmax', types: ['PERFORMANCE_MAX','SEARCH'],
          value: data.pmaxCannibalization?.summary ? `${data.pmaxCannibalization.summary.total_overlap} fraz` : '—', sub: 'Pokrywające się frazy',
          status: data.pmaxCannibalization?.summary?.total_overlap > 0 ? 'warning' : 'ok' },
        { key: 'bidModifiers', title: 'Modyfikatory stawek', icon: Settings2, cat: 'budget', types: ['SEARCH','DISPLAY','VIDEO'],
          value: data.bidModData?.modifiers ? `${data.bidModData.modifiers.length} aktywnych` : '—', sub: 'Urządzenia, lokalizacje, harmonogram', status: 'info' },
        { key: 'googleRecs', title: 'Rekomendacje Google', icon: Star, cat: 'quality', types: ['SEARCH','PERFORMANCE_MAX','SHOPPING','DISPLAY','VIDEO'],
          value: data.googleRecsData?.recommendations ? `${data.googleRecsData.recommendations.length} nowych` : '—', sub: 'Natywne sugestie Google',
          status: data.googleRecsData?.recommendations?.length > 3 ? 'warning' : 'info' },
        { key: 'convValueRules', title: 'Reguły wartości', icon: Settings2, cat: 'cross', types: ['SEARCH','PERFORMANCE_MAX','SHOPPING'],
          value: data.convValueRulesData?.rules ? `${data.convValueRulesData.rules.length} reguł` : '—', sub: 'Value rules', status: 'info' },
        { key: 'offlineConversions', title: 'Konwersje offline', icon: Target, cat: 'cross', types: ['SEARCH','PERFORMANCE_MAX'],
          value: data.offlineConvData?.total ? `${data.offlineConvData.total} uploadów` : '—', sub: 'GCLID imports', status: 'info' },
        { key: 'audiencesList', title: 'Lista odbiorców', icon: Users, cat: 'cross', types: ['SEARCH','DISPLAY','VIDEO','PERFORMANCE_MAX'],
          value: data.audiencesListData?.total ? `${data.audiencesListData.total} segm.` : '—', sub: 'Remarketing, in-market, affinity', status: 'info' },
        { key: 'audiencePerf', title: 'Wydajność odbiorców', icon: Headphones, cat: 'cross', types: ['SEARCH','DISPLAY','VIDEO','PERFORMANCE_MAX'],
          value: data.audiencePerf?.audiences ? `${data.audiencePerf.audiences.length} segm.` : '—', sub: 'Performance per audience', status: 'info' },
        { key: 'missingExt', title: 'Brakujące rozszerzenia', icon: Link2, cat: 'quality', types: ['SEARCH'],
          value: data.missingExt?.campaigns ? `${data.missingExt.campaigns.length} kamp.` : '—', sub: 'Kampanie bez rozszerzeń',
          status: data.missingExt?.campaigns?.length > 0 ? 'warning' : 'ok' },
        { key: 'extPerf', title: 'Wydajność rozszerzeń', icon: Star, cat: 'quality', types: ['SEARCH'],
          value: data.extPerf?.types ? `${data.extPerf.types.length} typów` : '—', sub: 'Extension performance', status: 'info' },
    ]

    const baseFiltered = campFilter === 'ALL' ? cards : cards.filter(c => c.types.includes(campFilter))
    const filteredCards = [...baseFiltered].sort((a, b) => {
        const aPinned = pinnedKeys.includes(a.key) ? 0 : 1
        const bPinned = pinnedKeys.includes(b.key) ? 0 : 1
        return aPinned - bPinned
    })
    const alerts = cards.filter(c => c.status === 'danger')
    const warnings = cards.filter(c => c.status === 'warning')

    // Section drill-down renderer
    function renderSection(key) {
        const sectionMap = {
            waste: <WastedSpendSection data={data.waste} clientId={selectedClientId} showToast={showToast} />,
            dayparting: <DaypartingSection data={data.daypart} />,
            hourly: <HourlyDaypartingSection data={data.hourly} />,
            matchType: <MatchTypeSection data={data.matchType} />,
            ngram: <NgramSection data={data.ngram} ngramSize={ngramSize} setNgramSize={setNgramSize} />,
            rsa: <RsaSection data={data.rsa} />,
            landing: <LandingPageSection data={data.landing} />,
            structure: <AccountStructureSection data={data.structure} />,
            bidding: <BiddingAdvisorSection data={data.bidding} />,
            adGroupHealth: <AdGroupHealthSection data={data.adGroupHealth} />,
            smartBidding: <SmartBiddingHealthSection data={data.smartBidding} />,
            pareto: <ParetoSection data={data.pareto} />,
            scaling: <ScalingSection data={data.scaling} />,
            targetVsActual: <TargetVsActualSection data={data.targetVsActual} />,
            learningStatus: <LearningStatusSection data={data.learningStatus} />,
            portfolioHealth: <PortfolioHealthSection data={data.portfolioHealth} />,
            convQuality: <ConversionQualitySection data={data.convQuality} />,
            demographics: <DemographicsSection data={data.demographics} />,
            pmaxCannibalization: <PmaxCannibalizationSection data={data.pmaxCannibalization} />,
            audiencePerf: <AudiencePerfSection data={data.audiencePerf} />,
            missingExt: <MissingExtSection data={data.missingExt} />,
            extPerf: <ExtPerfSection data={data.extPerf} />,
        }

        // Inline sections without dedicated components
        if (key === 'convHealth' && data.convHealth) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                        <div style={{ padding: '10px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', flex: '1 1 120px' }}>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Score</div>
                            <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Syne', color: data.convHealth.score >= 80 ? '#4ADE80' : data.convHealth.score >= 50 ? '#FBBF24' : '#F87171' }}>{data.convHealth.score}</div>
                        </div>
                        <div style={{ padding: '10px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', flex: '1 1 120px' }}>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Kampanie</div>
                            <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0' }}>{data.convHealth.total_campaigns}</div>
                        </div>
                    </div>
                    {data.convHealth.campaigns?.length > 0 && (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead><tr>{['Kampania','Typ','Koszt','Konwersje','CVR','Score','Problemy'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Kampania' || h === 'Problemy' ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                            <tbody>{data.convHealth.campaigns.map((c, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: '#F0F0F0', fontWeight: 500, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.campaign_type}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.cost_usd} zł</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.conversions}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.conv_rate_pct}%</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.score >= 80 ? '#4ADE80' : c.score >= 50 ? '#FBBF24' : '#F87171', fontWeight: 600 }}>{c.score}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'left', fontSize: 11 }}>{c.issues?.join(', ') || '—'}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'bidModifiers' && data.bidModData?.modifiers) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Kampania','Typ','Urządzenie/Lokalizacja','Modifier'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                        <tbody>{data.bidModData.modifiers.map((m, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, color: '#F0F0F0', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.campaign_name || '—'}</td>
                                <td style={{ ...TD_DIM, fontSize: 10, textTransform: 'uppercase' }}>{m.modifier_type}</td>
                                <td style={TD}>{m.device_type || m.location_name || (m.day_of_week ? `${m.day_of_week} ${m.start_hour}-${m.end_hour}h` : '—')}</td>
                                <td style={{ ...TD, color: m.bid_modifier > 1 ? '#4ADE80' : m.bid_modifier < 1 ? '#F87171' : '#F0F0F0', fontWeight: 600 }}>
                                    {m.bid_modifier != null ? `${m.bid_modifier > 1 ? '+' : ''}${((m.bid_modifier - 1) * 100).toFixed(0)}%` : '—'}
                                </td>
                            </tr>
                        ))}</tbody>
                    </table>
                </div>
            )
        }
        if (key === 'googleRecs' && data.googleRecsData?.recommendations) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {data.googleRecsData.recommendations.length === 0 ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak nowych rekomendacji Google.</p> : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Typ','Kampania','Impact','Status'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{data.googleRecsData.recommendations.map((r, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontSize: 11, color: '#F0F0F0' }}>{r.type}</td>
                                    <td style={{ ...TD, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.campaign_name || '—'}</td>
                                    <td style={TD}>{typeof r.impact_estimate === 'object' ? JSON.stringify(r.impact_estimate) : r.impact_estimate || '—'}</td>
                                    <td style={{ ...TD, color: r.status === 'ACTIVE' ? '#4ADE80' : r.dismissed ? '#F87171' : '#FBBF24', fontSize: 10 }}>{r.dismissed ? 'Odrzucona' : r.status}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'convValueRules' && data.convValueRulesData?.rules) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {data.convValueRulesData.rules.length === 0 ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak reguł wartości konwersji.</p> : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Warunek','Wartość','Typ akcji','Wartość','Status'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{data.convValueRulesData.rules.map((r, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD_DIM, fontSize: 10, textTransform: 'uppercase' }}>{r.condition_type || '—'}</td>
                                    <td style={TD}>{r.condition_value || '—'}</td>
                                    <td style={TD_DIM}>{r.action_type || '—'}</td>
                                    <td style={TD}>{r.action_type === 'ADD' && r.action_value_micros != null ? `+${(r.action_value_micros/1e6).toFixed(2)} zł` : r.action_type === 'MULTIPLY' && r.action_multiplier != null ? `×${r.action_multiplier}` : '—'}</td>
                                    <td style={{ ...TD_DIM, fontSize: 10 }}>{r.status}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'offlineConversions') {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {!data.offlineConvData?.conversions || data.offlineConvData.conversions.length === 0
                        ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak uploadowanych konwersji offline.</p>
                        : <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['GCLID','Konwersja','Data','Wartość','Status'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{data.offlineConvData.conversions.map((c, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontSize: 10, fontFamily: 'monospace', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.gclid}</td>
                                    <td style={TD}>{c.conversion_name || '—'}</td>
                                    <td style={TD_DIM}>{c.conversion_time}</td>
                                    <td style={TD}>{c.conversion_value != null ? `${c.conversion_value} zł` : '—'}</td>
                                    <td style={{ ...TD, fontSize: 10, color: c.status === 'UPLOADED' ? '#4ADE80' : c.status === 'FAILED' ? '#F87171' : '#FBBF24' }}>{c.status}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    }
                </div>
            )
        }
        if (key === 'audiencesList') {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {!data.audiencesListData?.audiences || data.audiencesListData.audiences.length === 0
                        ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak odbiorców.</p>
                        : <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Nazwa','Typ','Status','Członków'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{data.audiencesListData.audiences.map((a, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: '#F0F0F0' }}>{a.name}</td>
                                    <td style={{ ...TD_DIM, fontSize: 10, textTransform: 'uppercase' }}>{a.type || '—'}</td>
                                    <td style={{ ...TD, fontSize: 10, color: a.status === 'ENABLED' ? '#4ADE80' : 'rgba(255,255,255,0.4)' }}>{a.status}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.member_count != null ? a.member_count.toLocaleString('pl-PL') : '—'}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    }
                </div>
            )
        }
        return sectionMap[key] || <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', padding: 16 }}>Brak danych dla tej sekcji.</p>
    }

    if (loading) {
        return (
            <div style={{ maxWidth: 1400 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 20 }}>
                    Centrum audytu
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
                    <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            </div>
        )
    }

    // Drill-down view
    if (activeSection) {
        const card = cards.find(c => c.key === activeSection)
        const Icon = card?.icon || AlertTriangle
        return (
            <div style={{ maxWidth: 1400 }}>
                <div style={{ marginBottom: 16 }}>
                    <button onClick={() => setActiveSection(null)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginBottom: 8 }}>
                        <ChevronRight size={14} style={{ color: '#4F8EF7', transform: 'rotate(180deg)' }} />
                        <span style={{ fontSize: 12, color: '#4F8EF7' }}>Centrum audytu</span>
                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>›</span>
                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{card?.title}</span>
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Icon size={18} style={{ color: '#4F8EF7' }} />
                        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>{card?.title}</h1>
                    </div>
                </div>
                <div className={CARD}>
                    {renderSection(activeSection)}
                </div>
            </div>
        )
    }

    // Bento grid view
    return (
        <div style={{ maxWidth: 1400 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Centrum audytu
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Analiza {days} dni — {filteredCards.length} sekcji{pinnedKeys.length > 0 ? ` · ${pinnedKeys.length} przypiętych` : ''}
                    </p>
                </div>
                {pinnedKeys.length > 0 && (
                    <button onClick={unpinAll} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        padding: '5px 12px', borderRadius: 999, fontSize: 11, fontFamily: 'DM Sans', fontWeight: 500,
                        cursor: 'pointer', border: '1px solid rgba(79,142,247,0.2)', background: 'rgba(79,142,247,0.06)',
                        color: '#4F8EF7', transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(79,142,247,0.12)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'rgba(79,142,247,0.06)' }}
                    >
                        <Pin size={11} />
                        Odpinij wszystkie
                    </button>
                )}
            </div>

            <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
                {CAMP_TYPES.map(t => (
                    <button key={t} onClick={() => setFilter('campaignType', t)} style={{
                        padding: '5px 14px', borderRadius: 999, fontSize: 12, fontFamily: 'DM Sans', fontWeight: 500,
                        cursor: 'pointer', border: 'none', transition: 'all 0.15s',
                        background: campFilter === t ? '#4F8EF7' : 'transparent',
                        color: campFilter === t ? '#FFFFFF' : 'rgba(255,255,255,0.5)',
                        outline: campFilter === t ? 'none' : '1px solid rgba(255,255,255,0.12)',
                    }}>{CAMP_LABELS[t]}</button>
                ))}
            </div>

            {alerts.length > 0 && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', marginBottom: 16,
                    borderRadius: 8, background: 'rgba(248,113,113,0.06)', border: '1px solid rgba(248,113,113,0.2)',
                }}>
                    <AlertTriangle size={16} style={{ color: '#F87171', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: '#F87171' }}>
                        {alerts.length} {alerts.length === 1 ? 'problem wymaga' : 'problemy wymagają'} uwagi: {alerts.map(a => a.title).join(', ')}
                    </span>
                </div>
            )}
            {warnings.length > 0 && alerts.length === 0 && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', marginBottom: 16,
                    borderRadius: 8, background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.2)',
                }}>
                    <AlertTriangle size={16} style={{ color: '#FBBF24', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: '#FBBF24' }}>
                        {warnings.length} {warnings.length === 1 ? 'ostrzeżenie' : 'ostrzeżeń'}: {warnings.map(a => a.title).join(', ')}
                    </span>
                </div>
            )}

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 12,
            }}>
                {filteredCards.map(card => (
                    <BentoCard key={card.key} card={card} onClick={() => setActiveSection(card.key)}
                        pinned={pinnedKeys.includes(card.key)} onTogglePin={togglePin}
                        changePct={getChangePct(card.key)} />
                ))}
            </div>
        </div>
    )
}
