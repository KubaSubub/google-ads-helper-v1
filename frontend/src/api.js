import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
});

function notifyUnauthorized() {
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
}

api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        if (error.response?.status === 401) {
            notifyUnauthorized();
        }
        const message = error.response?.data?.detail || error.message || 'Nieznany blad';
        console.error('API Error:', message);
        return Promise.reject({ message, status: error.response?.status });
    }
);

export default api;

// Auth
export const getAuthStatus = (bootstrap = false) =>
    api.get('/auth/status', { params: bootstrap ? { bootstrap: 1 } : {} });
export const getSetupStatus = () => api.get('/auth/setup-status');
export const getStoredSetupValues = () => api.get('/auth/setup-values');
export const saveSetup = (data) => api.post('/auth/setup', data);
export const getLoginUrl = () => api.get('/auth/login');
export const logout = () => api.post('/auth/logout');

// Clients
export const getClients = () => api.get('/clients/');
export const getClient = (id) => api.get(`/clients/${id}`);
export const updateClient = (id, data) => api.patch(`/clients/${id}`, data);
export const syncClient = (id, days = 90) => api.post('/sync/trigger', null, { params: { client_id: id, days } });
export const discoverClients = (customerIds) =>
    api.post('/clients/discover', null, {
        params: customerIds ? { customer_ids: customerIds } : {},
    });

// Campaigns
export const getCampaigns = (clientId, params = {}) =>
    api.get('/campaigns/', { params: { client_id: clientId, ...params } });
export const updateCampaign = (campaignId, data) =>
    api.patch(`/campaigns/${campaignId}`, data);
export const getCampaignKPIs = (campaignId, days = 30, params = {}) =>
    api.get(`/campaigns/${campaignId}/kpis`, { params: { days, ...params } });
export const getCampaignMetrics = (campaignId, dateFrom, dateTo) => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return api.get(`/campaigns/${campaignId}/metrics`, { params });
};

// Keywords
export const getKeywords = (params = {}) =>
    api.get('/keywords/', { params: typeof params === 'object' ? params : { campaign_id: params } });

// Ad Groups (lightweight lookup)
export const getAdGroups = (params = {}) =>
    api.get('/keywords/ad-groups/', { params });

// Negative Keywords
export const getNegativeKeywords = (params = {}) =>
    api.get('/keywords/negative-keywords/', { params });
export const addNegativeKeyword = (data) =>
    api.post('/keywords/negative-keywords/', data);
export const removeNegativeKeyword = (id) =>
    api.delete(`/keywords/negative-keywords/${id}`);

// Negative Keyword Lists
export const getNegativeKeywordLists = (params = {}) =>
    api.get('/keywords/negative-keyword-lists/', { params });
export const createNegativeKeywordList = (data) =>
    api.post('/keywords/negative-keyword-lists/', data);
export const getNegativeKeywordListDetail = (listId) =>
    api.get(`/keywords/negative-keyword-lists/${listId}`);
export const deleteNegativeKeywordList = (listId) =>
    api.delete(`/keywords/negative-keyword-lists/${listId}`);
export const addToNegativeKeywordList = (listId, data) =>
    api.post(`/keywords/negative-keyword-lists/${listId}/items`, data);
export const removeFromNegativeKeywordList = (listId, itemId) =>
    api.delete(`/keywords/negative-keyword-lists/${listId}/items/${itemId}`);
export const applyNegativeKeywordList = (listId, data) =>
    api.post(`/keywords/negative-keyword-lists/${listId}/apply`, data);

// Search Terms
export const getSegmentedSearchTerms = (clientId, params = {}) =>
    api.get('/search-terms/segmented', { params: { client_id: clientId, ...params } });
export const getSearchTerms = (clientIdOrParams, params = {}) => {
    if (typeof clientIdOrParams === 'object') {
        return api.get('/search-terms/', { params: clientIdOrParams });
    }
    return api.get('/search-terms/', { params: { client_id: clientIdOrParams, ...params } });
};

// Recommendations
export const getRecommendations = (clientId, params = {}) => {
    const queryParams = typeof params === 'number'
        ? { client_id: clientId, days: params }
        : { client_id: clientId, ...params };
    return api.get('/recommendations/', { params: queryParams });
};
export const getRecommendationsSummary = (clientId, params = {}) =>
    api.get('/recommendations/summary', { params: { client_id: clientId, ...params } });
export const applyRecommendation = (id, clientId, dryRun = false) =>
    api.post(`/recommendations/${id}/apply`, null, {
        params: { client_id: clientId, dry_run: dryRun },
    });
export const dismissRecommendation = (id, clientId) =>
    api.post(`/recommendations/${id}/dismiss`, null, {
        params: { client_id: clientId },
    });

// Actions
export const getActionHistory = (clientId, params = {}) =>
    api.get('/actions/', { params: { client_id: clientId, ...params } });
export const revertAction = (actionLogId, clientId) =>
    api.post(`/actions/revert/${actionLogId}`, null, {
        params: { client_id: clientId },
    });

// Analytics
export const getDashboardKPIs = (clientId, params = {}) =>
    api.get('/analytics/dashboard-kpis', { params: { client_id: clientId, ...params } });
export const getKPIs = (clientId) =>
    api.get('/analytics/kpis', { params: { client_id: clientId } });
export const getQualityScoreAudit = (clientId) =>
    api.get('/analytics/quality-score-audit', { params: { client_id: clientId } });
export const getForecast = (campaignId, metric = 'cost', forecastDays = 7) =>
    api.get('/analytics/forecast', {
        params: {
            campaign_id: campaignId,
            metric: metric === 'cost' ? 'cost_micros' : metric === 'cpc' ? 'avg_cpc_micros' : metric,
            forecast_days: forecastDays,
        },
    });
export const getCampaignAnalytics = (clientId) =>
    api.get('/analytics/campaigns', { params: { client_id: clientId } });
export const getAnomalies = (clientId, status = 'unresolved') =>
    api.get('/analytics/anomalies', { params: { client_id: clientId, status } });
export const resolveAnomaly = (alertId, clientId) =>
    api.post(`/analytics/anomalies/${alertId}/resolve`, null, {
        params: { client_id: clientId },
    });
export const detectAnomalies = (clientId) =>
    api.post('/analytics/detect', null, {
        params: { client_id: clientId },
    });
export const getCorrelationMatrix = (data) =>
    api.post('/analytics/correlation', data);

// Export
export const exportSearchTerms = (clientId, format = 'xlsx') =>
    api.get('/export/search-terms', {
        params: { client_id: clientId, format },
        responseType: 'blob',
    });
export const exportKeywords = (clientId, format = 'xlsx') =>
    api.get('/export/keywords', {
        params: { client_id: clientId, format },
        responseType: 'blob',
    });

// Sync
export const getSyncStatus = () => api.get('/sync/status');

// Semantic
export const getSemanticClusters = (params) =>
    api.get('/semantic/clusters', { params });

// Health
export const getHealth = () => api.get('/health');

// V2 Analytics
export const getTrends = (clientId, params = {}) =>
    api.get('/analytics/trends', { params: { client_id: clientId, ...params } });
export const getHealthScore = (clientId, params = {}) =>
    api.get('/analytics/health-score', { params: { client_id: clientId, ...params } });
export const getCampaignTrends = (clientId, days = 7, params = {}) =>
    api.get('/analytics/campaign-trends', { params: { client_id: clientId, days, ...params } });
export const getBudgetPacing = (clientId, params = {}) =>
    api.get('/analytics/budget-pacing', { params: { client_id: clientId, ...params } });
export const getImpressionShare = (clientId, params = {}) =>
    api.get('/analytics/impression-share', { params: { client_id: clientId, ...params } });
export const getDeviceBreakdown = (clientId, params = {}) =>
    api.get('/analytics/device-breakdown', { params: { client_id: clientId, ...params } });
export const getGeoBreakdown = (clientId, params = {}) =>
    api.get('/analytics/geo-breakdown', { params: { client_id: clientId, ...params } });

// SEARCH Optimization
export const getDayparting = (clientId, params = {}) =>
    api.get('/analytics/dayparting', { params: { client_id: clientId, ...params } });
export const getRsaAnalysis = (clientId, params = {}) =>
    api.get('/analytics/rsa-analysis', { params: { client_id: clientId, ...params } });
export const getNgramAnalysis = (clientId, params = {}) =>
    api.get('/analytics/ngram-analysis', { params: { client_id: clientId, ...params } });
export const getMatchTypeAnalysis = (clientId, params = {}) =>
    api.get('/analytics/match-type-analysis', { params: { client_id: clientId, ...params } });
export const getLandingPages = (clientId, params = {}) =>
    api.get('/analytics/landing-pages', { params: { client_id: clientId, ...params } });
export const getWastedSpend = (clientId, params = {}) =>
    api.get('/analytics/wasted-spend', { params: { client_id: clientId, ...params } });
export const getAccountStructure = (clientId) =>
    api.get('/analytics/account-structure', { params: { client_id: clientId } });
export const getBiddingAdvisor = (clientId, params = {}) =>
    api.get('/analytics/bidding-advisor', { params: { client_id: clientId, ...params } });
export const getHourlyDayparting = (clientId, params = {}) =>
    api.get('/analytics/hourly-dayparting', { params: { client_id: clientId, ...params } });

// Analytics — new endpoints (B2, B3, A3, G2)
export const getSearchTermTrends = (clientId, params = {}) =>
    api.get('/analytics/search-term-trends', { params: { client_id: clientId, ...params } });
export const getCloseVariants = (clientId, params = {}) =>
    api.get('/analytics/close-variants', { params: { client_id: clientId, ...params } });
export const getConversionHealth = (clientId, params = {}) =>
    api.get('/analytics/conversion-health', { params: { client_id: clientId, ...params } });
export const getKeywordExpansion = (clientId, params = {}) =>
    api.get('/analytics/keyword-expansion', { params: { client_id: clientId, ...params } });

// GAP Analysis endpoints
export const getAdGroupHealth = (clientId, params = {}) =>
    api.get('/analytics/ad-group-health', { params: { client_id: clientId, ...params } });
export const getSmartBiddingHealth = (clientId, params = {}) =>
    api.get('/analytics/smart-bidding-health', { params: { client_id: clientId, ...params } });
export const getParetoAnalysis = (clientId, params = {}) =>
    api.get('/analytics/pareto-analysis', { params: { client_id: clientId, ...params } });
export const getScalingOpportunities = (clientId, params = {}) =>
    api.get('/analytics/scaling-opportunities', { params: { client_id: clientId, ...params } });
export const getChangeImpact = (clientId, params = {}) =>
    api.get('/analytics/change-impact', { params: { client_id: clientId, ...params } });
export const getBidStrategyImpact = (clientId, params = {}) =>
    api.get('/analytics/bid-strategy-impact', { params: { client_id: clientId, ...params } });
export const getTargetVsActual = (clientId, params = {}) =>
    api.get('/analytics/target-vs-actual', { params: { client_id: clientId, ...params } });
export const getBidStrategyReport = (clientId, params = {}) =>
    api.get('/analytics/bid-strategy-report', { params: { client_id: clientId, ...params } });
export const getLearningStatus = (clientId, params = {}) =>
    api.get('/analytics/learning-status', { params: { client_id: clientId, ...params } });
export const getPortfolioHealth = (clientId, params = {}) =>
    api.get('/analytics/portfolio-health', { params: { client_id: clientId, ...params } });
export const getConversionQuality = (clientId, params = {}) =>
    api.get('/analytics/conversion-quality', { params: { client_id: clientId, ...params } });
export const getDemographics = (clientId, params = {}) =>
    api.get('/analytics/demographics', { params: { client_id: clientId, ...params } });

// Phase D — PMax, Audience, Extensions
export const getPmaxChannels = (clientId, params = {}) =>
    api.get('/analytics/pmax-channels', { params: { client_id: clientId, ...params } });
export const getAssetGroupPerformance = (clientId, params = {}) =>
    api.get('/analytics/asset-group-performance', { params: { client_id: clientId, ...params } });
export const getPmaxSearchThemes = (clientId, params = {}) =>
    api.get('/analytics/pmax-search-themes', { params: { client_id: clientId, ...params } });
export const getAudiencePerformance = (clientId, params = {}) =>
    api.get('/analytics/audience-performance', { params: { client_id: clientId, ...params } });
export const getMissingExtensions = (clientId, params = {}) =>
    api.get('/analytics/missing-extensions', { params: { client_id: clientId, ...params } });
export const getExtensionPerformance = (clientId, params = {}) =>
    api.get('/analytics/extension-performance', { params: { client_id: clientId, ...params } });

// AI Agent
export const getAgentStatus = () => api.get('/agent/status');

// Reports
export const getReports = (clientId, params = {}) =>
    api.get('/reports/', { params: { client_id: clientId, ...params } });
export const getReport = (reportId) =>
    api.get(`/reports/${reportId}`);

// History
export const getChangeHistory = (clientId, params = {}) =>
    api.get('/history/', { params: { client_id: clientId, ...params } });
export const getUnifiedTimeline = (clientId, params = {}) =>
    api.get('/history/unified', { params: { client_id: clientId, ...params } });
export const getHistoryFilters = (clientId) =>
    api.get('/history/filters', { params: { client_id: clientId } });
