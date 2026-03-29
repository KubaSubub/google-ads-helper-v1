import { useState } from 'react'
import {
    Loader2, AlertTriangle, Target, Layers, CalendarDays, Hash, FileText, Globe,
    GitBranch, Clock, Users, Zap, BarChart3, Activity, Crosshair, GraduationCap,
    Briefcase, ShieldCheck, PieChart, Radio, Box, Search, Headphones, Link2, Star,
    Shuffle, Settings2, ChevronRight,
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
import PmaxChannelsSection from './components/sections/PmaxChannelsSection'
import AssetGroupsSection from './components/sections/AssetGroupsSection'
import SearchThemesSection from './components/sections/SearchThemesSection'
import AudiencePerfSection from './components/sections/AudiencePerfSection'
import MissingExtSection from './components/sections/MissingExtSection'
import ExtPerfSection from './components/sections/ExtPerfSection'
import PmaxCannibalizationSection from './components/sections/PmaxCannibalizationSection'

export default function AuditCenterPage() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days, setFilter } = useFilter()
    const { data, loading, error, ngramSize, setNgramSize, reload } = useAuditData(selectedClientId, allParams)
    const [activeSection, setActiveSection] = useState(null)

    const campFilter = allParams.campaign_type || 'ALL'

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (error) return <ErrorMessage message={error} onRetry={reload} />

    // Card definitions
    const cards = [
        { key: 'waste', title: 'Zmarnowany budżet', icon: AlertTriangle, cat: 'budget', types: ['SEARCH','PMAX','SHOPPING'],
          value: data.waste ? `${data.waste.total_waste_usd?.toFixed(0) || 0} zł` : '—', sub: data.waste ? `${data.waste.waste_pct}% spend · ${data.waste.categories?.length || 0} kategorii` : '',
          status: data.waste ? (data.waste.waste_pct > 3 ? 'danger' : data.waste.waste_pct > 1 ? 'warning' : 'ok') : 'neutral' },
        { key: 'bidding', title: 'Strategia bidowania', icon: Target, cat: 'budget', types: ['SEARCH','PMAX'],
          value: data.bidding ? `${data.bidding.changes_needed || 0} zmian` : '—', sub: data.bidding ? `${data.bidding.total_campaigns || 0} kampanii` : '',
          status: data.bidding ? (data.bidding.changes_needed > 2 ? 'danger' : data.bidding.changes_needed > 0 ? 'warning' : 'ok') : 'neutral' },
        { key: 'convHealth', title: 'Zdrowie konwersji', icon: AlertTriangle, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING','DISPLAY','VIDEO'],
          value: data.convHealth ? `${data.convHealth.score}/100` : '—', sub: data.convHealth ? `${data.convHealth.total_campaigns} kampanii` : '',
          status: data.convHealth ? (data.convHealth.score >= 80 ? 'ok' : data.convHealth.score >= 50 ? 'warning' : 'danger') : 'neutral' },
        { key: 'convQuality', title: 'Jakość konwersji', icon: ShieldCheck, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING'],
          value: data.convQuality ? `${data.convQuality.quality_score}/100` : '—', sub: data.convQuality ? `${data.convQuality.issues?.length || 0} problemów` : '',
          status: data.convQuality ? (data.convQuality.quality_score >= 80 ? 'ok' : data.convQuality.quality_score >= 50 ? 'warning' : 'danger') : 'neutral' },
        { key: 'targetVsActual', title: 'Target vs Rzeczywistość', icon: Crosshair, cat: 'budget', types: ['SEARCH','PMAX'],
          value: data.targetVsActual ? `${data.targetVsActual.items?.length || 0} kampanii` : '—', sub: 'Smart Bidding', status: 'info' },
        { key: 'smartBidding', title: 'Smart Bidding', icon: Zap, cat: 'budget', types: ['SEARCH','PMAX'],
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
        { key: 'landing', title: 'Strony docelowe', icon: Globe, cat: 'search', types: ['SEARCH','PMAX'],
          value: data.landing ? `${data.landing.pages?.length || 0} URL` : '—', sub: 'Wydajność landing pages', status: 'info' },
        { key: 'structure', title: 'Struktura konta', icon: GitBranch, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING'],
          value: data.structure?.issues?.length ? `${data.structure.issues.length} problemów` : 'OK', sub: 'Audyt struktury',
          status: data.structure?.issues?.length > 0 ? 'warning' : 'ok' },
        { key: 'adGroupHealth', title: 'Zdrowie grup reklam', icon: Users, cat: 'quality', types: ['SEARCH'],
          value: data.adGroupHealth ? `${data.adGroupHealth.details?.length || 0} prob.` : '—', sub: data.adGroupHealth ? `z ${data.adGroupHealth.total_ad_groups} grup` : '',
          status: data.adGroupHealth?.details?.length > 0 ? 'warning' : 'ok' },
        { key: 'pareto', title: 'Pareto 80/20', icon: BarChart3, cat: 'search', types: ['SEARCH','PMAX'],
          value: data.pareto ? `${data.pareto.campaign_pareto?.top_campaigns_for_80pct || '?'} kamp.` : '—', sub: '80% wartości', status: 'info' },
        { key: 'scaling', title: 'Okazje do skalowania', icon: Activity, cat: 'search', types: ['SEARCH','PMAX'],
          value: data.scaling ? `${data.scaling.opportunities?.length || 0} kampanii` : '—', sub: 'Potencjał wzrostu',
          status: data.scaling?.opportunities?.length > 0 ? 'ok' : 'neutral' },
        { key: 'learningStatus', title: 'Status nauki', icon: GraduationCap, cat: 'budget', types: ['SEARCH','PMAX'],
          value: data.learningStatus ? `${data.learningStatus.learning_count || 0} w nauce` : '—', sub: data.learningStatus ? `z ${data.learningStatus.total_smart_bidding || 0}` : '',
          status: data.learningStatus?.learning_count > 0 ? 'warning' : 'ok' },
        { key: 'portfolioHealth', title: 'Strategie portfelowe', icon: Briefcase, cat: 'budget', types: ['SEARCH','PMAX'],
          value: data.portfolioHealth ? `${data.portfolioHealth.total_portfolios || 0} portfeli` : '—', sub: 'Portfolio bidding', status: 'info' },
        { key: 'demographics', title: 'Demografia', icon: PieChart, cat: 'search', types: ['SEARCH','DISPLAY','VIDEO'],
          value: data.demographics ? `${data.demographics.anomalies?.length || 0} anomalii` : '—', sub: 'CPA per segment',
          status: data.demographics?.anomalies?.length > 0 ? 'warning' : 'ok' },
        { key: 'pmaxChannels', title: 'Kanały PMax', icon: Radio, cat: 'pmax', types: ['PMAX'],
          value: data.pmaxChannels?.channels ? `${data.pmaxChannels.channels.length} kanałów` : '—', sub: 'Rozkład budżetu', status: 'info' },
        { key: 'assetGroups', title: 'Grupy zasobów PMax', icon: Box, cat: 'pmax', types: ['PMAX'],
          value: data.assetGroups?.groups ? `${data.assetGroups.groups.length} grup` : '—', sub: 'Asset groups', status: 'info' },
        { key: 'searchThemes', title: 'Tematy PMax', icon: Search, cat: 'pmax', types: ['PMAX'],
          value: 'Sygnały', sub: 'Tematy i odbiorcy', status: 'info' },
        { key: 'pmaxCannibalization', title: 'Kanibalizacja PMax↔Search', icon: Shuffle, cat: 'pmax', types: ['PMAX','SEARCH'],
          value: data.pmaxCannibalization?.summary ? `${data.pmaxCannibalization.summary.total_overlap} fraz` : '—', sub: 'Pokrywające się frazy',
          status: data.pmaxCannibalization?.summary?.total_overlap > 0 ? 'warning' : 'ok' },
        { key: 'auctionInsights', title: 'Auction Insights', icon: Crosshair, cat: 'cross', types: ['SEARCH'],
          value: data.auctionData?.total_competitors ? `${data.auctionData.total_competitors} konk.` : '—', sub: 'Widoczność konkurencji', status: 'info' },
        { key: 'shoppingGroups', title: 'Grupy produktów', icon: Box, cat: 'cross', types: ['SHOPPING'],
          value: data.shoppingData?.groups ? `${data.shoppingData.groups.length} grup` : '—', sub: 'Shopping hierarchy', status: 'info' },
        { key: 'placementPerf', title: 'Miejsca docelowe', icon: Globe, cat: 'cross', types: ['DISPLAY','VIDEO'],
          value: data.placementData?.placements ? `${data.placementData.placements.length} miejsc` : '—', sub: 'Display/Video placements', status: 'info' },
        { key: 'topicPerf', title: 'Tematy Display/Video', icon: Layers, cat: 'cross', types: ['DISPLAY','VIDEO'],
          value: data.topicData?.topics ? `${data.topicData.topics.length} tematów` : '—', sub: 'Wydajność tematów', status: 'info' },
        { key: 'bidModifiers', title: 'Modyfikatory stawek', icon: Settings2, cat: 'budget', types: ['SEARCH','DISPLAY','VIDEO'],
          value: data.bidModData?.modifiers ? `${data.bidModData.modifiers.length} aktywnych` : '—', sub: 'Urządzenia, lokalizacje, harmonogram', status: 'info' },
        { key: 'googleRecs', title: 'Rekomendacje Google', icon: Star, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING','DISPLAY','VIDEO'],
          value: data.googleRecsData?.recommendations ? `${data.googleRecsData.recommendations.length} nowych` : '—', sub: 'Natywne sugestie Google',
          status: data.googleRecsData?.recommendations?.length > 3 ? 'warning' : 'info' },
        { key: 'convValueRules', title: 'Reguły wartości', icon: Settings2, cat: 'cross', types: ['SEARCH','PMAX','SHOPPING'],
          value: data.convValueRulesData?.rules ? `${data.convValueRulesData.rules.length} reguł` : '—', sub: 'Value rules', status: 'info' },
        { key: 'offlineConversions', title: 'Konwersje offline', icon: Target, cat: 'cross', types: ['SEARCH','PMAX'],
          value: data.offlineConvData?.total ? `${data.offlineConvData.total} uploadów` : '—', sub: 'GCLID imports', status: 'info' },
        { key: 'audiencesList', title: 'Lista odbiorców', icon: Users, cat: 'cross', types: ['SEARCH','DISPLAY','VIDEO','PMAX'],
          value: data.audiencesListData?.total ? `${data.audiencesListData.total} segm.` : '—', sub: 'Remarketing, in-market, affinity', status: 'info' },
        { key: 'audiencePerf', title: 'Wydajność odbiorców', icon: Headphones, cat: 'cross', types: ['SEARCH','DISPLAY','VIDEO','PMAX'],
          value: data.audiencePerf?.audiences ? `${data.audiencePerf.audiences.length} segm.` : '—', sub: 'Performance per audience', status: 'info' },
        { key: 'missingExt', title: 'Brakujące rozszerzenia', icon: Link2, cat: 'quality', types: ['SEARCH'],
          value: data.missingExt?.campaigns ? `${data.missingExt.campaigns.length} kamp.` : '—', sub: 'Kampanie bez rozszerzeń',
          status: data.missingExt?.campaigns?.length > 0 ? 'warning' : 'ok' },
        { key: 'extPerf', title: 'Wydajność rozszerzeń', icon: Star, cat: 'quality', types: ['SEARCH'],
          value: data.extPerf?.types ? `${data.extPerf.types.length} typów` : '—', sub: 'Extension performance', status: 'info' },
    ]

    const filteredCards = campFilter === 'ALL' ? cards : cards.filter(c => c.types.includes(campFilter))
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
            pmaxChannels: <PmaxChannelsSection data={data.pmaxChannels} trends={data.pmaxTrends} />,
            assetGroups: <AssetGroupsSection data={data.assetGroups} />,
            searchThemes: <SearchThemesSection data={data.searchThemes} />,
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
        if (key === 'auctionInsights' && data.auctionData?.competitors) {
            return (
                <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
                    {data.auctionData.competitors.length === 0
                        ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', padding: '12px 0' }}>Brak danych. Uruchom sync.</p>
                        : <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                {['Domena','IS %','Overlap %','Poz. wyżej %','Outranking %','Top %','Abs. top %'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Domena' ? 'left' : 'right' }}>{h}</th>)}
                            </tr></thead>
                            <tbody>{data.auctionData.competitors.map((c, i) => (
                                <tr key={i} style={c.is_self ? { borderBottom: '1px solid rgba(79,142,247,0.15)', background: 'rgba(79,142,247,0.04)' } : { borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: c.is_self ? '#4F8EF7' : '#F0F0F0', fontWeight: c.is_self ? 600 : 400 }}>{c.display_domain} {c.is_self && <span style={{ fontSize: 9, opacity: 0.5 }}>(Ty)</span>}</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.impression_share >= 30 ? '#4ADE80' : c.impression_share >= 15 ? '#FBBF24' : '#F87171' }}>{c.impression_share}%</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.overlap_rate}%</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.position_above_rate}%</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.outranking_share >= 40 ? '#4ADE80' : 'rgba(255,255,255,0.6)' }}>{c.outranking_share}%</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.top_of_page_rate}%</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.abs_top_of_page_rate}%</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    }
                </div>
            )
        }
        if (key === 'shoppingGroups' && data.shoppingData?.groups) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {data.shoppingData.groups.length === 0 ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak grup produktów.</p> : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Grupa','Typ','Bid','Kliknięcia','Impr.','Koszt','Konw.'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Grupa' ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                            <tbody>{data.shoppingData.groups.map((g, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: '#F0F0F0' }}>{g.case_value || '—'}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right', fontSize: 10 }}>{g.case_value_type}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.bid_micros != null ? `${(g.bid_micros/1e6).toFixed(2)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.clicks}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{g.impressions}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.cost_micros != null ? `${(g.cost_micros/1e6).toFixed(0)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.conversions}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'placementPerf' && data.placementData?.placements) {
            return (
                <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['URL/Placement','Typ','Kliknięcia','Impr.','Koszt','Konw.','Video views'].map(h => <th key={h} style={{ ...TH, textAlign: h.startsWith('URL') ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                        <tbody>{data.placementData.placements.slice(0,20).map((p, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, color: '#F0F0F0', maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.placement_url || '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right', fontSize: 10 }}>{p.placement_type}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{p.clicks}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{p.impressions}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{p.cost_micros != null ? `${(p.cost_micros/1e6).toFixed(0)} zł` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{p.conversions}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{p.video_views || '—'}</td>
                            </tr>
                        ))}</tbody>
                    </table>
                </div>
            )
        }
        if (key === 'topicPerf' && data.topicData?.topics) {
            return (
                <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Temat','Bid mod.','Kliknięcia','Impr.','Koszt','Konw.'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Temat' ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                        <tbody>{data.topicData.topics.map((t, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, color: '#F0F0F0' }}>{t.topic_path || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.bid_modifier != null ? `${(t.bid_modifier * 100).toFixed(0)}%` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.clicks}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{t.impressions}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.cost_micros != null ? `${(t.cost_micros/1e6).toFixed(0)} zł` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.conversions}</td>
                            </tr>
                        ))}</tbody>
                    </table>
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
                        Analiza {days} dni — {filteredCards.length} sekcji
                    </p>
                </div>
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
                    <BentoCard key={card.key} card={card} onClick={() => setActiveSection(card.key)} />
                ))}
            </div>
        </div>
    )
}
