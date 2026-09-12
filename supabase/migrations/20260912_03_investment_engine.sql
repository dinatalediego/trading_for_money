-- Investment Engine v1
-- Production migration applied as create_tfm_investment_engine_v1.

create table if not exists public.tfm_investment_accounts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  name text not null,
  institution text,
  account_type text not null default 'broker'
    check (account_type in ('broker','cash','exchange','retirement','other')),
  currency text not null default 'USD',
  is_active boolean not null default true
);

create table if not exists public.tfm_investment_positions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  account_id uuid references public.tfm_investment_accounts(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  symbol text not null,
  asset_name text,
  bucket text not null check (bucket in ('CORE','OPPORTUNITY','CASH','GOLD_LAB')),
  asset_class text not null default 'equity'
    check (asset_class in ('equity','etf','bond','cash','commodity','crypto','fund','other')),
  quantity numeric not null default 0,
  avg_cost numeric,
  manual_price numeric,
  currency text not null default 'USD',
  target_weight numeric check (target_weight is null or (target_weight between 0 and 1)),
  thesis text,
  invalidation text,
  is_active boolean not null default true,
  constraint tfm_investment_positions_unique_symbol_account unique(owner_id, account_id, symbol)
);

create table if not exists public.tfm_investment_transactions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  account_id uuid references public.tfm_investment_accounts(id) on delete cascade,
  position_id uuid references public.tfm_investment_positions(id) on delete set null,
  created_at timestamptz not null default now(),
  trade_date timestamptz not null default now(),
  transaction_type text not null
    check (transaction_type in ('BUY','SELL','DEPOSIT','WITHDRAWAL','DIVIDEND','FEE','INTEREST','ADJUSTMENT')),
  symbol text,
  quantity numeric,
  price numeric,
  amount numeric,
  currency text not null default 'USD',
  notes text
);

create table if not exists public.tfm_investment_goals (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  name text not null,
  target_amount numeric not null check (target_amount > 0),
  target_date date,
  currency text not null default 'USD',
  priority integer not null default 1 check (priority between 1 and 5),
  notes text,
  is_active boolean not null default true
);

create table if not exists public.tfm_investment_settings (
  owner_id uuid primary key default auth.uid(),
  updated_at timestamptz not null default now(),
  base_currency text not null default 'USD',
  monthly_contribution numeric not null default 0 check (monthly_contribution >= 0),
  target_core numeric not null default 0.70 check (target_core between 0 and 1),
  target_opportunity numeric not null default 0.15 check (target_opportunity between 0 and 1),
  target_gold_lab numeric not null default 0.05 check (target_gold_lab between 0 and 1),
  target_cash numeric not null default 0.10 check (target_cash between 0 and 1),
  constraint tfm_investment_settings_weights check (
    abs((target_core + target_opportunity + target_gold_lab + target_cash) - 1.0) < 0.000001
  )
);

alter table public.tfm_investment_accounts enable row level security;
alter table public.tfm_investment_positions enable row level security;
alter table public.tfm_investment_transactions enable row level security;
alter table public.tfm_investment_goals enable row level security;
alter table public.tfm_investment_settings enable row level security;

-- RLS policies in production allow authenticated users to access only rows where owner_id = auth.uid().
-- Gold research-memory tables expose read-only SELECT to authenticated users; writes remain service/worker-side.
