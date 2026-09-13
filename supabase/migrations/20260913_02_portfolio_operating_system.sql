-- Portfolio Operating System v1
-- Production migration applied as create_tfm_portfolio_operating_system_v1.

create table if not exists public.tfm_investment_constitution (
  owner_id uuid primary key default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  version text not null default 'constitution_v1',
  objective text not null default 'Build long-term wealth through disciplined contributions and compounding.',
  horizon_years integer not null default 10,
  emergency_fund_months integer not null default 6,
  emergency_fund_ready boolean not null default false,
  max_single_position_pct numeric not null default 0.15,
  max_sector_pct numeric not null default 0.30,
  max_opportunity_pct numeric not null default 0.20,
  max_gold_lab_pct numeric not null default 0.05,
  max_drawdown_tolerance_pct numeric not null default 0.25,
  leverage_policy text not null default 'NONE',
  rebalance_method text not null default 'CONTRIBUTIONS_FIRST',
  core_band_pp numeric not null default 0.05,
  opportunity_band_pp numeric not null default 0.03,
  cash_band_pp numeric not null default 0.03,
  gold_lab_band_pp numeric not null default 0.02,
  benchmark_symbol text not null default 'SPY',
  benchmark_window_days integer not null default 60,
  decision_cooldown_hours integer not null default 24,
  opportunity_requires_thesis boolean not null default true,
  gold_live_allowed boolean not null default false,
  notes text
);

create table if not exists public.tfm_portfolio_health_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  engine_version text not null,
  health_score integer not null,
  health_status text not null,
  portfolio_value numeric not null default 0,
  benchmark_symbol text not null default 'SPY',
  benchmark_return numeric,
  portfolio_cost_basis_return numeric,
  input_snapshot jsonb not null default '{}'::jsonb,
  output_snapshot jsonb not null default '{}'::jsonb
);

create table if not exists public.tfm_portfolio_snapshots (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  snapshot_date date not null default current_date,
  created_at timestamptz not null default now(),
  base_currency text not null default 'USD',
  total_value numeric not null default 0,
  total_cost_basis numeric not null default 0,
  unrealized_pnl numeric not null default 0,
  benchmark_symbol text not null default 'SPY',
  benchmark_price numeric,
  bucket_values jsonb not null default '{}'::jsonb,
  position_values jsonb not null default '[]'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  constraint tfm_portfolio_snapshots_owner_date unique(owner_id, snapshot_date)
);

alter table public.tfm_investment_constitution enable row level security;
alter table public.tfm_portfolio_health_runs enable row level security;
alter table public.tfm_portfolio_snapshots enable row level security;

-- Production policies use owner_id = auth.uid() for authenticated CRUD.
