-- ============================================================================
-- FinanceOps360 :: Read-only role for the API / AI copilot
--
-- The FastAPI backend (including the AI SQL copilot) connects as this role so
-- it can never modify data, even if a generated query slips past the SQL
-- guardrails. Writes are only possible via the admin role used by
-- python/db_loader.py and python/persist.py.
--
-- Applied by python/persist.py after schema + views are created (and after
-- any re-load, so grants always cover the current set of relations).
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'financeops_ro') THEN
        CREATE ROLE financeops_ro LOGIN PASSWORD 'financeops';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO financeops_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO financeops_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO financeops_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO financeops_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO financeops_ro;
