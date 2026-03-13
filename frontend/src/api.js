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
export const getCampaigns = (clientId) =>
    api.get('/campaigns/', { params: { client_id: clientId } });
export const updateCampaign = (campaignId, data) =>
    api.patch(`/campaigns/${campaignId}`, data);
export const getCampaignKPIs = (campaignId, days = 30) =>
    api.get(`/campaigns/${campaignId}/kpis`, { params: { days } });
export const getCampaignMetrics = (campaignId, dateFrom, dateTo) => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return api.get(`/campaigns/${campaignId}/metrics`, { params });
};

// Keywords
export const getKeywords = (params = {}) =>
    api.get('/keywords/', { params: typeof params === 'object' ? params : { campaign_id: params } });

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
export const getDayparting = (clientId, days = 30) =>
    api.get('/analytics/dayparting', { params: { client_id: clientId, days } });
export const getRsaAnalysis = (clientId) =>
    api.get('/analytics/rsa-analysis', { params: { client_id: clientId } });
export const getNgramAnalysis = (clientId, params = {}) =>
    api.get('/analytics/ngram-analysis', { params: { client_id: clientId, ...params } });
export const getMatchTypeAnalysis = (clientId, days = 30) =>
    api.get('/analytics/match-type-analysis', { params: { client_id: clientId, days } });
export const getLandingPages = (clientId, days = 30) =>
    api.get('/analytics/landing-pages', { params: { client_id: clientId, days } });
export const getWastedSpend = (clientId, days = 30) =>
    api.get('/analytics/wasted-spend', { params: { client_id: clientId, days } });
export const getAccountStructure = (clientId) =>
    api.get('/analytics/account-structure', { params: { client_id: clientId } });
export const getBiddingAdvisor = (clientId, days = 30) =>
    api.get('/analytics/bidding-advisor', { params: { client_id: clientId, days } });
export const getHourlyDayparting = (clientId, days = 7) =>
    api.get('/analytics/hourly-dayparting', { params: { client_id: clientId, days } });

// History
export const getChangeHistory = (clientId, params = {}) =>
    api.get('/history/', { params: { client_id: clientId, ...params } });
export const getUnifiedTimeline = (clientId, params = {}) =>
    api.get('/history/unified', { params: { client_id: clientId, ...params } });
export const getHistoryFilters = (clientId) =>
    api.get('/history/filters', { params: { client_id: clientId } });
