-- Market Intelligence + Learning Memory v1
-- Production migration applied as create_tfm_market_learning_memory_v1.

create table if not exists public.tfm_market_watchlist (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  symbol text not null,
  label text,
  category text not null default 'WATCH'
    check (category in ('CORE','OPPORTUNITY','GOLD','MACRO','WATCH')),
  reason text,
  is_active boolean not null default true,
  constraint tfm_market_watchlist_owner_symbol unique(owner_id, symbol)
);

create table if not exists public.tfm_source_bookmarks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  source_key text not null,
  title text not null,
  url text not null,
  source_type text,
  authority text,
  notes text,
  query_context text
);

create table if not exists public.tfm_learning_progress (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  lesson_id text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  status text not null default 'NOT_STARTED'
    check (status in ('NOT_STARTED','IN_PROGRESS','COMPLETED')),
  started_at timestamptz,
  completed_at timestamptz,
  quiz_score numeric check (quiz_score is null or (quiz_score between 0 and 100)),
  notes text,
  takeaway text,
  constraint tfm_learning_progress_owner_lesson unique(owner_id, lesson_id)
);

create table if not exists public.tfm_learning_settings (
  owner_id uuid primary key default auth.uid(),
  updated_at timestamptz not null default now(),
  daily_minutes integer not null default 20 check (daily_minutes between 5 and 180),
  monthly_learning_budget numeric not null default 0 check (monthly_learning_budget >= 0),
  current_track text not null default 'beginner_investor',
  prefer_free_first boolean not null default true
);

create table if not exists public.tfm_daily_brief_reads (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid(),
  brief_date date not null default current_date,
  created_at timestamptz not null default now(),
  read_at timestamptz,
  takeaway text,
  brief_snapshot jsonb not null default '{}'::jsonb,
  constraint tfm_daily_brief_reads_owner_date unique(owner_id, brief_date)
);

alter table public.tfm_market_watchlist enable row level security;
alter table public.tfm_source_bookmarks enable row level security;
alter table public.tfm_learning_progress enable row level security;
alter table public.tfm_learning_settings enable row level security;
alter table public.tfm_daily_brief_reads enable row level security;

-- Production RLS policies grant authenticated users CRUD only where owner_id = auth.uid().
