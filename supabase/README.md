# Supabase

The production research memory currently lives in the existing Supabase project using isolated `tfm_*` tables.

Applied production migrations:

1. `create_tfm_gold_worker_memory_v1`
2. `enable_http_for_tfm_gold_worker`
3. `create_persistent_postgres_gold_worker_v1`

The canonical persistent runtime is PostgreSQL `pg_cron` calling `public.tfm_run_gold_worker()` every minute.

The schema is private-by-default: all `tfm_*` tables have RLS enabled and no anon/authenticated policies.
