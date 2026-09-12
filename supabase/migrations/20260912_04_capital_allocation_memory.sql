-- Capital Allocation Engine Decision Memory v1
-- Production migration applied as create_tfm_capital_allocation_memory_v1.

create table if not exists public.tfm_allocation_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  engine_version text not null,
  base_currency text not null default 'USD',
  contribution_amount numeric not null check (contribution_amount >= 0),
  portfolio_value numeric not null check (portfolio_value >= 0),
  gold_rigor_score integer not null default 0 check (gold_rigor_score between 0 and 100),
  gold_stage text not null default 'DATA_COLLECTION',
  status text not null default 'PROPOSED'
    check (status in ('PROPOSED','ACKNOWLEDGED','DISMISSED')),
  input_snapshot jsonb not null default '{}'::jsonb,
  recommendation_summary jsonb not null default '{}'::jsonb,
  notes text
);

create table if not exists public.tfm_allocation_items (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  run_id uuid not null references public.tfm_allocation_runs(id) on delete cascade,
  created_at timestamptz not null default now(),
  bucket text not null check (bucket in ('CORE','OPPORTUNITY','CASH','GOLD_LAB')),
  amount numeric not null check (amount >= 0),
  pct_of_contribution numeric not null check (pct_of_contribution between 0 and 1),
  priority integer not null default 1,
  rationale text not null,
  guardrail text,
  deployment_mode text not null default 'MANUAL'
    check (deployment_mode in ('MANUAL','RESERVE_ONLY','RESEARCH_ONLY')),
  status text not null default 'PROPOSED'
    check (status in ('PROPOSED','ACKNOWLEDGED','DISMISSED'))
);

alter table public.tfm_allocation_runs enable row level security;
alter table public.tfm_allocation_items enable row level security;

-- Production policies:
-- owner_id = auth.uid() for authenticated SELECT/INSERT/UPDATE/DELETE.
-- Allocation rows are recommendations only and never represent broker execution.
