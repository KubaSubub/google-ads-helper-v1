import { useState, useEffect } from 'react'
import {
    getDayparting, getRsaAnalysis, getNgramAnalysis,
    getMatchTypeAnalysis, getLandingPages, getWastedSpend,
    getAccountStructure, getBiddingAdvisor, getHourlyDayparting,
    getConversionHealth, getAdGroupHealth, getSmartBiddingHealth,
    getParetoAnalysis, getScalingOpportunities,
    getTargetVsActual, getLearningStatus,
    getPortfolioHealth, getConversionQuality, getDemographics,
    getAudiencePerformance, getMissingExtensions, getExtensionPerformance,
    getPmaxSearchCannibalization,
    getBidModifiers,
    getGoogleRecommendations,
    getConversionValueRules,
    getOfflineConversions,
    getAudiencesList,
    getDaypartingHeatmap,
} from '../../../api'

// Compute previous period date range: same length window ending 1 day before current start
function computePrevPeriodParams(allParams) {
    const { date_from, date_to, ...rest } = allParams
    if (!date_from || !date_to) return null
    const from = new Date(date_from)
    const to = new Date(date_to)
    const days = Math.max(1, Math.round((to - from) / 86400000))
    const prevTo = new Date(from)
    prevTo.setDate(prevTo.getDate() - 1)
    const prevFrom = new Date(prevTo)
    prevFrom.setDate(prevFrom.getDate() - days + 1)
    return {
        ...rest,
        date_from: prevFrom.toISOString().slice(0, 10),
        date_to: prevTo.toISOString().slice(0, 10),
    }
}

export default function useAuditData(selectedClientId, allParams) {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [ngramSize, setNgramSize] = useState(1)

    const [data, setData] = useState({
        waste: null, daypart: null, matchType: null, ngram: null,
        rsa: null, landing: null, hourly: null, heatmap: null, structure: null,
        bidding: null, convHealth: null, adGroupHealth: null, smartBidding: null,
        pareto: null, scaling: null, targetVsActual: null,
        learningStatus: null, portfolioHealth: null,
        convQuality: null, demographics: null,
        pmaxCannibalization: null, audiencePerf: null, missingExt: null, extPerf: null,
        bidModData: null, googleRecsData: null,
        convValueRulesData: null, offlineConvData: null, audiencesListData: null,
    })

    const [prevData, setPrevData] = useState({})

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

    // Background fetch for previous period (only numeric-value cards)
    async function loadPrevPeriod() {
        const pp = computePrevPeriodParams(allParams)
        if (!pp) { setPrevData({}); return }
        const _catch = (label) => (err) => { console.warn(`[AuditCenter:prev] ${label}`, err); return null }
        const [w, ch, cq, sb, ls, bd, agh, demo, pcann, mex] = await Promise.all([
            getWastedSpend(selectedClientId, pp).catch(_catch('prev-waste')),
            getConversionHealth(selectedClientId, pp).catch(_catch('prev-conv-health')),
            getConversionQuality(selectedClientId).catch(_catch('prev-conv-quality')),
            getSmartBiddingHealth(selectedClientId, pp).catch(_catch('prev-smart-bidding')),
            getLearningStatus(selectedClientId).catch(_catch('prev-learning')),
            getBiddingAdvisor(selectedClientId, pp).catch(_catch('prev-bidding')),
            getAdGroupHealth(selectedClientId, pp).catch(_catch('prev-adgroup-health')),
            getDemographics(selectedClientId, pp).catch(_catch('prev-demographics')),
            getPmaxSearchCannibalization(selectedClientId, pp).catch(_catch('prev-pmax-cann')),
            getMissingExtensions(selectedClientId, pp).catch(_catch('prev-missing-ext')),
        ])
        setPrevData({
            waste: w, convHealth: ch, convQuality: cq, smartBidding: sb,
            learningStatus: ls, bidding: bd, adGroupHealth: agh,
            demographics: demo, pmaxCannibalization: pcann, missingExt: mex,
        })
    }

    async function loadAll() {
        setLoading(true)
        setError(null)
        setPrevData({})
        try {
            const _catch = (label) => (err) => { console.warn(`[AuditCenter] ${label}`, err); return null }
            const [w, dp, mt, ng, r, lp, hr, hm, st, bd, ch, agh, sb, pa, sc, tva, ls, ph, cq, demo,
                   pcann, aud, mex, exp,
                   bmod, grecs, cvr, oconv, audl] = await Promise.all([
                getWastedSpend(selectedClientId, allParams).catch(_catch('wasted-spend')),
                getDayparting(selectedClientId, allParams).catch(_catch('dayparting')),
                getMatchTypeAnalysis(selectedClientId, allParams).catch(_catch('match-type')),
                getNgramAnalysis(selectedClientId, { ngram_size: ngramSize, ...allParams }).catch(_catch('ngram')),
                getRsaAnalysis(selectedClientId, allParams).catch(_catch('rsa')),
                getLandingPages(selectedClientId, allParams).catch(_catch('landing-pages')),
                getHourlyDayparting(selectedClientId, allParams).catch(_catch('hourly-dayparting')),
                getDaypartingHeatmap(selectedClientId, { days: allParams.days || 30 }).catch(_catch('dayparting-heatmap')),
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
                getPmaxSearchCannibalization(selectedClientId, allParams).catch(_catch('pmax-cannibalization')),
                getAudiencePerformance(selectedClientId, allParams).catch(_catch('audience')),
                getMissingExtensions(selectedClientId, allParams).catch(_catch('missing-ext')),
                getExtensionPerformance(selectedClientId, allParams).catch(_catch('ext-performance')),
                getBidModifiers(selectedClientId).catch(_catch('bid-modifiers')),
                getGoogleRecommendations(selectedClientId).catch(_catch('google-recs')),
                getConversionValueRules(selectedClientId).catch(_catch('conv-value-rules')),
                getOfflineConversions(selectedClientId).catch(_catch('offline-conversions')),
                getAudiencesList(selectedClientId).catch(_catch('audiences-list')),
            ])
            setData({
                waste: w, daypart: dp, matchType: mt, ngram: ng,
                rsa: r, landing: lp, hourly: hr, heatmap: hm, structure: st,
                bidding: bd, convHealth: ch, adGroupHealth: agh, smartBidding: sb,
                pareto: pa, scaling: sc, targetVsActual: tva,
                learningStatus: ls, portfolioHealth: ph,
                convQuality: cq, demographics: demo,
                pmaxCannibalization: pcann, audiencePerf: aud, missingExt: mex, extPerf: exp,
                bidModData: bmod, googleRecsData: grecs,
                convValueRulesData: cvr, offlineConvData: oconv, audiencesListData: audl,
            })
            // Fire previous period load in background (non-blocking)
            loadPrevPeriod()
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return { data, prevData, loading, error, ngramSize, setNgramSize, reload: loadAll }
}
