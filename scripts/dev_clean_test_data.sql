-- DEV ONLY: removes the users and records the test suites leave behind (e2e-*, pytest-*).
-- Run: docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < scripts/dev_clean_test_data.sql
BEGIN;
CREATE TEMP TABLE tu AS SELECT id FROM users WHERE username LIKE 'e2e-%' OR username LIKE 'pytest-%';
DELETE FROM attachments WHERE uploaded_by IN (SELECT id FROM tu) OR vulnerability_id IN (SELECT id FROM vulnerabilities WHERE created_by IN (SELECT id FROM tu) OR identifier LIKE 'e2e-%' OR identifier LIKE 'pytest-%') OR report_id IN (SELECT id FROM reports WHERE created_by IN (SELECT id FROM tu) OR name LIKE 'e2e-%' OR name LIKE 'pytest-%');
DELETE FROM vulnerability_operators WHERE user_id IN (SELECT id FROM tu);
DELETE FROM vulnerability_viewers WHERE user_id IN (SELECT id FROM tu);
DELETE FROM report_operators WHERE user_id IN (SELECT id FROM tu);
DELETE FROM report_viewers WHERE user_id IN (SELECT id FROM tu);
DELETE FROM vulnerabilities WHERE created_by IN (SELECT id FROM tu) OR identifier LIKE 'e2e-%' OR identifier LIKE 'pytest-%';
DELETE FROM report_sections WHERE report_id IN (SELECT id FROM reports WHERE created_by IN (SELECT id FROM tu) OR name LIKE 'e2e-%' OR name LIKE 'pytest-%');
UPDATE reports SET lock_user_id = NULL WHERE lock_user_id IN (SELECT id FROM tu);
DELETE FROM reports WHERE created_by IN (SELECT id FROM tu) OR name LIKE 'e2e-%' OR name LIKE 'pytest-%';
DELETE FROM audit_logs WHERE api_key_id IN (SELECT id FROM api_keys WHERE created_by IN (SELECT id FROM tu) OR label LIKE 'e2e-%' OR label LIKE 'pytest-%');
DELETE FROM api_keys WHERE created_by IN (SELECT id FROM tu) OR label LIKE 'e2e-%' OR label LIKE 'pytest-%';
DELETE FROM audit_logs WHERE user_id IN (SELECT id FROM tu);
DELETE FROM report_templates WHERE owner_id IN (SELECT id FROM tu) OR name LIKE 'e2e-%' OR name LIKE 'pytest-%';
DELETE FROM users WHERE id IN (SELECT id FROM tu);
SELECT (SELECT count(*) FROM users) users, (SELECT count(*) FROM vulnerabilities WHERE deleted_at IS NULL) live_vulns, (SELECT count(*) FROM reports WHERE deleted_at IS NULL) live_reports;
COMMIT;
