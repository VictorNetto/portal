// How a report's state reads on screen (D14). The status is draft or sent; after
// that, "Concluído" and the progress are worked out from its vulnerabilities.
import { t } from './i18n'

export const REPORT_STEPS = [
  { key: 'created', at: 'created_at', status: 'draft', label: 'rstatus.created' },
  { key: 'sent', at: 'sent_at', status: 'sent', label: 'rstatus.sent' },
  { key: 'done', at: null, status: 'done', label: 'rstatus.done' },
]

// Done when every vuln is closed: fixed, or its risk assumed by the defense team (D17).
const done = (r) => r.status === 'sent' && r.vuln_count > 0 && (r.closed_count ?? r.fixed_count) === r.vuln_count

// What VulnTimeline needs: the record, with the step it is on as its status.
export const reportTimeline = (r) => ({ ...r, status: done(r) ? 'done' : r.status })

export const reportPillClass = (r) => (done(r) ? 's-fixed' : 's-' + r.status)
export const reportStatusLabel = (r) => t('rstatus.' + (done(r) ? 'done' : r.status))
export const reportProgress = (r) => (
  r.status === 'sent' && r.vuln_count > 0 && !done(r)
    ? t('rstatus.progress', { fixed: r.closed_count ?? r.fixed_count, total: r.vuln_count })
    : ''
)
