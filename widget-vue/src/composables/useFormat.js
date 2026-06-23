// Shared formatting helpers used across the portal so the UI is consistent.

/**
 * Relative "time ago" with sane unit rollover.
 *  - < 1 min   → "just now"
 *  - < 60 min  → "Xm"
 *  - < 24 h    → "Xh"
 *  - < 7 days  → "Xd"
 *  - >= 7 days → locale date ("Jun 23")
 *
 * Fixes QA #2: previously everything older than an hour showed in hours
 * (e.g. "197h" for an 8-day-old chat).
 */
export function timeAgo(ts) {
  if (!ts) return ''
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return ''
  const diff = Date.now() - then
  if (diff < 0) return 'just now'
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}d`
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/** Seconds → "1m 10s" / "45s" / "2h 5m". */
export function formatDuration(seconds) {
  const s = Math.max(0, Math.round(seconds || 0))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  const h = Math.floor(m / 60)
  return `${h}h ${m % 60}m`
}
