-- Production reference migration.
-- Applied as: create_tfm_gold_worker_memory_v1

create table if not exists public.tfm_market_snapshots (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    bar_time timestamptz not null,
    source text not null default 'vercel_gold_api',
    symbol text not null default 'GC=F',
    timeframe text not null default '1m',
    price numeric not null,
    feed_state text,
    regime text,
    atr numeric,
    atr_pct numeric,
    features jsonb not null default '{}'::jsonb,
    raw_signal jsonb not null default '{}'::jsonb,
    constraint tfm_market_snapshots_unique_bar unique (source, symbol, timeframe, bar_time)
);

create table if not exists public.tfm_signal_decisions (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    snapshot_id uuid not null references public.tfm_market_snapshots(id) on delete cascade,
    bar_time timestamptz not null,
    strategy_version text not null,
    action text not null check (action in ('BUY','SELL','FLAT')),
    long_score integer not null check (long_score between 0 and 100),
    short_score integer not null check (short_score between 0 and 100),
    confidence integer not null check (confidence between 0 and 100),
    entry_price numeric,
    stop_price numeric,
    target_price numeric,
    reward_to_risk numeric,
    rationale jsonb not null default '{}'::jsonb,
    constraint tfm_signal_decisions_unique_strategy unique (snapshot_id, strategy_version)
);

create table if not exists public.tfm_paper_trades (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    strategy_version text not null,
    symbol text not null default 'GC=F',
    timeframe text not null default '1m',
    decision_id uuid references public.tfm_signal_decisions(id) on delete set null,
    side text not null check (side in ('BUY','SELL')),
    status text not null default 'OPEN' check (status in ('OPEN','CLOSED')),
    opened_at timestamptz not null default now(),
    opened_bar_time timestamptz not null,
    entry_price numeric not null,
    stop_price numeric not null,
    target_price numeric not null,
    initial_risk_points numeric not null check (initial_risk_points > 0),
    closed_at timestamptz,
    closed_bar_time timestamptz,
    exit_price numeric,
    exit_reason text,
    pnl_points numeric,
    pnl_r numeric,
    metadata jsonb not null default '{}'::jsonb
);

create unique index if not exists tfm_one_open_trade_per_strategy
    on public.tfm_paper_trades(strategy_version, symbol, timeframe)
    where status = 'OPEN';

create table if not exists public.tfm_decision_outcomes (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    decision_id uuid not null references public.tfm_signal_decisions(id) on delete cascade,
    horizon_minutes integer not null check (horizon_minutes > 0),
    target_time timestamptz not null,
    evaluated_bar_time timestamptz not null,
    price_at_horizon numeric not null,
    raw_return_bps numeric not null,
    directional_return_bps numeric,
    constraint tfm_decision_outcomes_unique_horizon unique(decision_id, horizon_minutes)
);

create table if not exists public.tfm_worker_runs (
    id uuid primary key default gen_random_uuid(),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'STARTED'
        check (status in ('STARTED','SUCCESS','SKIPPED','ERROR')),
    worker_version text not null,
    source_bar_time timestamptz,
    action_taken text,
    message text,
    metrics jsonb not null default '{}'::jsonb
);

create table if not exists public.tfm_agent_state (
    agent_key text primary key,
    strategy_version text not null,
    symbol text not null default 'GC=F',
    timeframe text not null default '1m',
    auto_enabled boolean not null default true,
    last_run_at timestamptz,
    last_bar_time timestamptz,
    consecutive_losses integer not null default 0,
    closed_trades integer not null default 0,
    wins integer not null default 0,
    losses integer not null default 0,
    cumulative_pnl_points numeric not null default 0,
    cumulative_pnl_r numeric not null default 0,
    risk_paused_until timestamptz,
    updated_at timestamptz not null default now()
);

alter table public.tfm_market_snapshots enable row level security;
alter table public.tfm_signal_decisions enable row level security;
alter table public.tfm_paper_trades enable row level security;
alter table public.tfm_decision_outcomes enable row level security;
alter table public.tfm_worker_runs enable row level security;
alter table public.tfm_agent_state enable row level security;
