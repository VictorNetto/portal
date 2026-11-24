"""What an API key may do (D13). Each key carries a list of these; an endpoint
names the scope it needs. Keys never reach the session (UI) endpoints."""

VULNS_READ = "vulns:read"      # read vulnerabilities and their evidence
VULNS_WRITE = "vulns:write"    # create vulnerabilities
RVS_WRITE = "rvs:write"        # see the RVS queue and set RVS IDs
REPORTS_READ = "reports:read"  # read reports and their evidence
EXPORTS = "exports"            # download PDF / Word / Excel files
VULNS_IMPORT = "vulns:import"  # with vulns:write: create with past status, dates and numbers

ALL = (VULNS_READ, VULNS_WRITE, VULNS_IMPORT, RVS_WRITE, REPORTS_READ, EXPORTS)
