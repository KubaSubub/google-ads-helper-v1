import { useState, useEffect } from 'react'
import {
    getDayparting, getRsaAnalysis, getNgramAnalysis,
    getMatchTypeAnalysis, getLandingPages, getWastedSpend,
    getAccountStructure, getBiddingAdvisor, getHourlyDayparting,
    getConversionHealth, getAdGroupHealth, getSmartBiddingHealth,
    getParetoAnalysis, getScalingOpportunities,
    getTargetVsActual, getLearningStatus,
    getPortfolioHealth, getConversionQuality, getDemographics,
    getPmaxChannels, getPmaxChannelTrends, getAssetGroupPerformance, getPmaxSearchThemes,
    getAudiencePerformance, getMissingExtensions, getExtensionPerformance,
    getPmaxSearchCannibalization,
    getAuctionInsights,
    getShoppingProductGroups,
    getPlacementPerformance,
    getBidModifiers,
    getTopicPerformance,
    getGoogleRecommendations,
    getConversionValueRules,
    getOfflineConversions,
    getAudiencesList,
} from '../../../api'

export default function useAuditData(selectedClientId, allParams) {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [ngramSize, setNgramSize] = useState(1)

    const [data, setData] = useState({
        waste: null, daypart: null, matchType: null, ngram: null,
        rsa: null, landing: null, hourly: null, structure: null,
        bidding: null, convHealth: null, adGroupHealth: null, smartBidding: null,
        pareto: null, scaling: null, targetVsActual: null,
        learningStatus: null, portfolioHealth: null,
        convQuality: null, demographics: null,
        pmaxChannels: null, pmaxTrends: null, assetGroups: null, searchThemes: null,
        pmaxCannibalization: null, audiencePerf: null, missingExt: null, extPerf: null,
        auctionData: null, shoppingData: null, placementData: null,
        topicData: null, bidModData: null, googleRecsData: null,
        convValueRulesData: null, offlineConvData: null, audiencesListData: null,
    })

    useEffect(() => {
        if (selectedClientId) loadAll()
    }, [selectedClientId, allParams])

    useEffect(() => {
        if (selectedClientId) {
            getNgramAnalysis(selectedClientId, { ngram_size: ngramSize, ...allParams })
                .then(ngram => setData(prev => ({ ...prev, ngram })))
                .catch(() => setData(prev => ({ ...prev, ngram: null })))
        }
    }, [ngramSize, selectedClientId, allParams])

    async function loadAll() {
        setLoading(true)
        setError(null)
        try {
            const _catch = (label) => (err) => { console.warn(`[AuditCenter] ${label}`, err); return null }
            const [w, dp, mt, ng, r, lp, hr, st, bd, ch, agh, sb, pa, sc, tva, ls, ph, cq, demo,
                   pch, ptrend, agp, sth, pcann, aud, mex, exp, auct, shopg, plc,
                   topd, bmod, grecs, cvr, oconv, audl] = await Promise.all([
                getWastedSpend(selectedClientId, allParams).catch(_catch('wasted-spend')),
                getDayparting(selectedClientId, allParams).catch(_catch('dayparting')),
                getMatchTypeAnalysis(selectedClientId, allParams).catch(_catch('match-type')),
                getNgramAnalysis(selectedClientId, { ngram_size: ngramSize, ...allParams }).catch(_catch('ngram')),
                getRsaAnalysis(selectedClientId, allParams).catch(_catch('rsa')),
                getLandingPages(selectedClientId, allParams).catch(_catch('landing-pages')),
                getHourlyDayparting(selectedClientId, allParams).catch(_catch('hourly-dayparting')),
                getAccountStructure(selectedClientId).catch(_catch('account-structure')),
                getBiddingAdvisor(selectedClientId, allParams).catch(_catch('bidding-advisor')),
                getConversionHealth(selectedClientId, allParams).catch(_catch('conversion-health')),
                getAdGroupHealth(selectedClientId, allParams).catch(_catch('ad-group-health')),
                getSmartBiddingHealth(selectedClientId, allParams).catch(_catch('smart-bidding')),
                getParetoAnalysis(selectedClientId, allParams).catch(_catch('pareto')),
                getScalingOpportunities(selectedClientId, allParams).catch(_catch('scaling')),
                getTargetVsActual(selectedClientId, allParams).catch(_catch('target-vs-actual')),
                getLearningStatus(selectedClientId).catch(_catch('learning-status')),
                getPortfolioHealth(selectedClientId, allParams).catch(_catch('portfolio-health')),
                getConversionQuality(selectedClientId).catch(_catch('conversion-quality')),
                getDemographics(selectedClientId, allParams).catch(_catch('demographics')),
                getPmaxChannels(selectedClientId, allParams).catch(_catch('pmax-channels')),
                getPmaxChannelTrends(selectedClientId, allParams).catch(_catch('pmax-channel-trends')),
                getAssetGroupPerformance(selectedClientId, allParams).catch(_catch('asset-group')),
                getPmaxSearchThemes(selectedClientId).catch(_catch('pmax-themes')),
                getPmaxSearchCannibalization(selectedClientId, allParams).catch(_catch('pmax-cannibalization')),
                getAudiencePerformance(selectedClientId, allParams).catch(_catch('audience')),
                getMissingExtensions(selectedClientId, allParams).catch(_catch('missing-ext')),
                getExtensionPerformance(selectedClientId, allParams).catch(_catch('ext-performance')),
                getAuctionInsights(selectedClientId, allParams).catch(_catch('auction-insights')),
                getShoppingProductGroups(selectedClientId).catch(_catch('shopping-groups')),
                getPlacementPerformance(selectedClientId, allParams).catch(_catch('placements')),
                getTopicPerformance(selectedClientId, allParams).catch(_catch('topics')),
                getBidModifiers(selectedClientId).catch(_catch('bid-modifiers')),
                getGoogleRecommendations(selectedClientId).catch(_catch('google-recs')),
                getConversionValueRules(selectedClientId).catch(_catch('conv-value-rules')),
                getOfflineConversions(selectedClientId).catch(_catch('offline-conversions')),
                getAudiencesList(selectedClientId).catch(_catch('audiences-list')),
            ])
            setData({
                waste: w, daypart: dp, matchType: mt, ngram: ng,
                rsa: r, landing: lp, hourly: hr, structure: st,
                bidding: bd, convHealth: ch, adGroupHealth: agh, smartBidding: sb,
                pareto: pa, scaling: sc, targetVsActual: tva,
                learningStatus: ls, portfolioHealth: ph,
                convQuality: cq, demographics: demo,
                pmaxChannels: pch, pmaxTrends: ptrend, assetGroups: agp, searchThemes: sth,
                pmaxCannibalization: pcann, audiencePerf: aud, missingExt: mex, extPerf: exp,
                auctionData: auct, shoppingData: shopg, placementData: plc,
                topicData: topd, bidModData: bmod, googleRecsData: grecs,
                convValueRulesData: cvr, offlineConvData: oconv, audiencesListData: audl,
            })
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return { data, loading, error, ngramSize, setNgramSize, reload: loadAll }
}
