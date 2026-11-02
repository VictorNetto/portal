// How a report's state reads on screen (D14). The status is draft or sent; after
// that, "Concluído" and the progress are worked out from its vulnerabilities.
import { t } from './i18n'

const done = (r) => r.status === 'sent' && r.vuln_count > 0 && r.fixed_count === r.vuln_count

export const reportPillClass = (r) => (done(r) ? 's-fixed' : 's-' + r.status)
export const reportStatusLabel = (r) => t('rstatus.' + (done(r) ? 'done' : r.status))
export const reportProgress = (r) => (
  r.status === 'sent' && r.vuln_count > 0 && !done(r)
    ? t('rstatus.progress', { fixed: r.fixed_count, total: r.vuln_count })
    : ''
)
