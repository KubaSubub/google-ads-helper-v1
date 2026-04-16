// Pure helpers for TrendExplorer — math, CSV export, localStorage presets.

// ─── Correlation ──────────────────────────────────────────────────────────────
export function pearson(x, y) {
    const n = Math.min(x.length, y.length)
    if (n < 2) return null
    let sx = 0, sy = 0
    for (let i = 0; i < n; i++) { sx += x[i]; sy += y[i] }
    const mx = sx / n, my = sy / n
    let num = 0, dx2 = 0, dy2 = 0
    for (let i = 0; i < n; i++) {
        const dx = x[i] - mx
        const dy = y[i] - my
        num += dx * dy
        dx2 += dx * dx
        dy2 += dy * dy
    }
    if (dx2 === 0 || dy2 === 0) return null
    return num / Math.sqrt(dx2 * dy2)
}

// Rolling Pearson over a sliding window. Returns array aligned to `dates` —
// first (window-1) entries are null.
export function rollingCorrelation(data, keyA, keyB, window = 14) {
    const out = []
    for (let i = 0; i < data.length; i++) {
        if (i < window - 1) { out.push({ date: data[i].date, r: null }); continue }
        const slice = data.slice(i - window + 1, i + 1)
        const x = slice.map(d => Number(d[keyA]) || 0)
        const y = slice.map(d => Number(d[keyB]) || 0)
        const r = pearson(x, y)
        out.push({ date: data[i].date, r: r == null ? null : +r.toFixed(3) })
    }
    return out
}

// ─── Linear regression forecast ───────────────────────────────────────────────
// Simple least-squares line fit. Returns { slope, intercept, predict(x) }.
export function linearFit(values) {
    const n = values.length
    if (n < 2) return null
    let sx = 0, sy = 0, sxx = 0, sxy = 0
    for (let i = 0; i < n; i++) {
        sx += i
        sy += values[i]
        sxx += i * i
        sxy += i * values[i]
    }
    const denom = n * sxx - sx * sx
    if (denom === 0) return null
    const slope = (n * sxy - sx * sy) / denom
    const intercept = (sy - slope * sx) / n
    return { slope, intercept, predict: (x) => slope * x + intercept }
}

// Generate `futureDays` forecast points for each metric, dated after the last
// data point. Returns array of { date, __forecast: true, [metric]: predicted }.
export function forecastPoints(data, metrics, futureDays = 7) {
    if (!data.length || !metrics.length) return []
    const lastDate = new Date(data[data.length - 1].date)
    const fits = {}
    for (const m of metrics) {
        const series = data.map(d => Number(d[m]) || 0)
        fits[m] = linearFit(series)
    }
    const out = []
    for (let i = 1; i <= futureDays; i++) {
        const d = new Date(lastDate)
        d.setDate(d.getDate() + i)
        const iso = d.toISOString().slice(0, 10)
        const row = { date: iso, __forecast: true }
        const x = data.length - 1 + i
        for (const m of metrics) {
            const fit = fits[m]
            if (!fit) continue
            row[`${m}__forecast`] = Math.max(0, +fit.predict(x).toFixed(2))
        }
        out.push(row)
    }
    return out
}

// ─── Delta before/after an action marker ──────────────────────────────────────
// Returns { [metric]: { before, after, pctChange } } based on `windowDays`
// days of data on each side of `markerDate`.
export function computeDelta(data, markerDate, metrics, windowDays = 7) {
    const idx = data.findIndex(d => d.date === markerDate)
    if (idx < 0) return null
    const before = data.slice(Math.max(0, idx - windowDays), idx)
    const after = data.slice(idx + 1, idx + 1 + windowDays)
    if (before.length === 0 || after.length === 0) return null
    const out = {}
    for (const m of metrics) {
        const avg = (arr) => arr.reduce((s, r) => s + (Number(r[m]) || 0), 0) / (arr.length || 1)
        const b = avg(before)
        const a = avg(after)
        const pct = b !== 0 ? ((a - b) / b) * 100 : null
        out[m] = {
            before: +b.toFixed(2),
            after: +a.toFixed(2),
            pctChange: pct === null ? null : +pct.toFixed(1),
            samples: { before: before.length, after: after.length },
        }
    }
    return out
}

// ─── Period-over-period alignment ─────────────────────────────────────────────
// Shift each row in `previousData` by `offsetDays` forward so the two periods
// line up on the same X-axis (day-of-period), then merge into `currentData`
// under `__prev_{metric}` keys.
export function mergePeriodOverPeriod(currentData, previousData, metrics) {
    if (!previousData || previousData.length === 0) return currentData
    const byOffset = new Map()
    previousData.forEach((row, i) => byOffset.set(i, row))
    return currentData.map((row, i) => {
        const prev = byOffset.get(i)
        if (!prev) return row
        const merged = { ...row }
        for (const m of metrics) {
            merged[`__prev_${m}`] = prev[m] ?? null
        }
        return merged
    })
}

// ─── localStorage presets ─────────────────────────────────────────────────────
const PRESETS_KEY = 'trendExplorer.presets.v1'

export function loadPresets() {
    try {
        const raw = localStorage.getItem(PRESETS_KEY)
        return raw ? JSON.parse(raw) : {}
    } catch { return {} }
}

export function savePreset(name, preset) {
    const all = loadPresets()
    all[name] = preset
    try { localStorage.setItem(PRESETS_KEY, JSON.stringify(all)) } catch {}
}

export function deletePreset(name) {
    const all = loadPresets()
    delete all[name]
    try { localStorage.setItem(PRESETS_KEY, JSON.stringify(all)) } catch {}
}
