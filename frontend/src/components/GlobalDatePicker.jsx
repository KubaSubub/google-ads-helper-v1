import { useState, useRef, useEffect, useMemo } from 'react'
import { Calendar, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { useFilter, DATE_PRESETS } from '../contexts/FilterContext'

const DAYS_PL = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd']
const MONTHS_PL = [
    'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień',
]

function getPresetLabel(filters) {
    const preset = DATE_PRESETS.find(p => p.value === filters.period)
    if (preset) return preset.label

    const fmt = (d) => {
        const date = new Date(d + 'T00:00:00')
        const day = date.getDate()
        const month = MONTHS_PL[date.getMonth()].slice(0, 3).toLowerCase()
        const year = date.getFullYear()
        return `${day} ${month} ${year}`
    }
    return `${fmt(filters.dateFrom)} – ${fmt(filters.dateTo)}`
}

function getDaysInMonth(year, month) {
    return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfWeek(year, month) {
    const day = new Date(year, month, 1).getDay()
    return day === 0 ? 6 : day - 1
}

function toDateStr(year, month, day) {
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function MiniCalendar({ dateFrom, dateTo, onSelectDate }) {
    const [viewYear, setViewYear] = useState(() => {
        const d = dateTo ? new Date(dateTo + 'T00:00:00') : new Date()
        return d.getFullYear()
    })
    const [viewMonth, setViewMonth] = useState(() => {
        const d = dateTo ? new Date(dateTo + 'T00:00:00') : new Date()
        return d.getMonth()
    })

    const prevMonth = () => {
        if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) }
        else setViewMonth(m => m - 1)
    }
    const nextMonth = () => {
        if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) }
        else setViewMonth(m => m + 1)
    }

    const daysInMonth = getDaysInMonth(viewYear, viewMonth)
    const firstDay = getFirstDayOfWeek(viewYear, viewMonth)
    const todayStr = new Date().toISOString().slice(0, 10)

    const weeks = useMemo(() => {
        const rows = []
        let row = []
        for (let i = 0; i < firstDay; i++) row.push(null)
        for (let d = 1; d <= daysInMonth; d++) {
            row.push(d)
            if (row.length === 7) { rows.push(row); row = [] }
        }
        if (row.length > 0) {
            while (row.length < 7) row.push(null)
            rows.push(row)
        }
        return rows
    }, [viewYear, viewMonth, firstDay, daysInMonth])

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <button onClick={prevMonth} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, borderRadius: 6, color: 'rgba(255,255,255,0.4)' }} className="hover:bg-white/5">
                    <ChevronLeft size={16} />
                </button>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#FFFFFF' }}>
                    {MONTHS_PL[viewMonth]} {viewYear}
                </span>
                <button onClick={nextMonth} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, borderRadius: 6, color: 'rgba(255,255,255,0.4)' }} className="hover:bg-white/5">
                    <ChevronRight size={16} />
                </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0, textAlign: 'center' }}>
                {DAYS_PL.map(d => (
                    <div key={d} style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', padding: '4px 0', fontWeight: 500 }}>{d}</div>
                ))}
                {weeks.flat().map((day, i) => {
                    if (day === null) return <div key={`e${i}`} style={{ padding: '4px 0' }} />

                    const dateStr = toDateStr(viewYear, viewMonth, day)
                    const isFrom = dateStr === dateFrom
                    const isTo = dateStr === dateTo
                    const isInRange = dateFrom && dateTo && dateStr >= dateFrom && dateStr <= dateTo
                    const isToday = dateStr === todayStr
                    const isEndpoint = isFrom || isTo

                    return (
                        <button
                            key={`d${day}`}
                            onClick={() => onSelectDate(dateStr)}
                            style={{
                                width: '100%',
                                padding: '5px 0',
                                fontSize: 11,
                                fontWeight: isEndpoint ? 600 : 400,
                                color: isEndpoint ? '#FFFFFF' : isInRange ? '#4F8EF7' : 'rgba(255,255,255,0.6)',
                                background: isEndpoint ? '#4F8EF7' : isInRange ? 'rgba(79,142,247,0.1)' : 'transparent',
                                border: 'none',
                                borderRadius: isFrom ? '6px 0 0 6px' : isTo ? '0 6px 6px 0' : 0,
                                cursor: 'pointer',
                                position: 'relative',
                                transition: 'background 0.1s',
                            }}
                            className={!isEndpoint && !isInRange ? 'hover:bg-white/5' : ''}
                        >
                            {day}
                            {isToday && !isEndpoint && (
                                <span style={{
                                    position: 'absolute', bottom: 1, left: '50%', transform: 'translateX(-50%)',
                                    width: 3, height: 3, borderRadius: '50%', background: '#4F8EF7',
                                }} />
                            )}
                        </button>
                    )
                })}
            </div>
        </div>
    )
}

export default function GlobalDatePicker() {
    const { filters, setFilter } = useFilter()
    const [open, setOpen] = useState(false)
    const [selecting, setSelecting] = useState(null) // null | 'from'
    const [tempFrom, setTempFrom] = useState(null)
    const ref = useRef(null)

    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false)
        }
        const escHandler = (e) => { if (e.key === 'Escape') setOpen(false) }
        document.addEventListener('mousedown', handler)
        document.addEventListener('keydown', escHandler)
        return () => {
            document.removeEventListener('mousedown', handler)
            document.removeEventListener('keydown', escHandler)
        }
    }, [open])

    const handlePresetClick = (value) => {
        setFilter('period', value)
        setSelecting(null)
        setTempFrom(null)
        setOpen(false)
    }

    const handleDateClick = (dateStr) => {
        if (!selecting || selecting !== 'from') {
            setTempFrom(dateStr)
            setSelecting('from')
        } else {
            const from = tempFrom <= dateStr ? tempFrom : dateStr
            const to = tempFrom <= dateStr ? dateStr : tempFrom
            setFilter('dateFrom', from)
            setFilter('dateTo', to)
            setSelecting(null)
            setTempFrom(null)
            setOpen(false)
        }
    }

    const displayFrom = selecting === 'from' && tempFrom ? tempFrom : filters.dateFrom
    const displayTo = selecting === 'from' && tempFrom ? tempFrom : filters.dateTo

    return (
        <div ref={ref} style={{ position: 'relative' }}>
            <button
                onClick={() => setOpen(o => !o)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 14px',
                    borderRadius: 10,
                    background: open ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${open ? 'rgba(79,142,247,0.4)' : 'rgba(255,255,255,0.08)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                }}
                className="hover:bg-white/[0.06]"
            >
                <Calendar size={15} style={{ color: '#4F8EF7', flexShrink: 0 }} />
                <span style={{ fontSize: 13, fontWeight: 500, color: '#FFFFFF', whiteSpace: 'nowrap' }}>
                    {getPresetLabel(filters)}
                </span>
                <ChevronDown size={14} style={{ color: 'rgba(255,255,255,0.4)', flexShrink: 0, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
            </button>

            {open && (
                <div style={{
                    position: 'absolute',
                    top: 'calc(100% + 8px)',
                    right: 0,
                    zIndex: 50,
                    display: 'flex',
                    borderRadius: 12,
                    background: '#1A1D24',
                    border: '1px solid rgba(255,255,255,0.1)',
                    boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
                    overflow: 'hidden',
                    minWidth: 460,
                }}>
                    {/* Left: Presets */}
                    <div style={{
                        width: 170,
                        padding: 12,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 2,
                        borderRight: '1px solid rgba(255,255,255,0.07)',
                        flexShrink: 0,
                    }}>
                        <div style={{ fontSize: 9, fontWeight: 500, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '4px 10px 6px' }}>
                            Szybki wybór
                        </div>
                        {DATE_PRESETS.map((preset, i) => {
                            const active = filters.period === preset.value
                            return (
                                <button
                                    key={preset.value}
                                    onClick={() => handlePresetClick(preset.value)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        width: '100%',
                                        padding: '7px 10px',
                                        borderRadius: 6,
                                        fontSize: 12,
                                        fontWeight: active ? 500 : 400,
                                        color: active ? '#4F8EF7' : 'rgba(255,255,255,0.6)',
                                        background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
                                        border: active ? '1px solid rgba(79,142,247,0.4)' : '1px solid transparent',
                                        cursor: 'pointer',
                                        textAlign: 'left',
                                        transition: 'all 0.1s',
                                    }}
                                    className={!active ? 'hover:bg-white/[0.04]' : ''}
                                >
                                    {preset.label}
                                </button>
                            )
                        })}
                    </div>

                    {/* Right: Calendar */}
                    <div style={{ flex: 1, padding: 16 }}>
                        <MiniCalendar
                            dateFrom={displayFrom}
                            dateTo={displayTo}
                            onSelectDate={handleDateClick}
                        />
                        {selecting === 'from' && (
                            <div style={{
                                marginTop: 8,
                                padding: '6px 10px',
                                borderRadius: 6,
                                background: 'rgba(79,142,247,0.1)',
                                fontSize: 11,
                                color: 'rgba(255,255,255,0.5)',
                                textAlign: 'center',
                            }}>
                                Kliknij datę końcową zakresu
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
