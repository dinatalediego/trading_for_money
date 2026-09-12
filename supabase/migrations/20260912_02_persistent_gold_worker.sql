-- Production reference migration.
-- Applied as: enable_http_for_tfm_gold_worker + create_persistent_postgres_gold_worker_v1

create extension if not exists http with schema extensions;
create extension if not exists pg_cron with schema extensions;

create or replace function public.tfm_run_gold_worker()
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_run_id uuid;
    v_http extensions.http_response;
    v_payload jsonb;
    v_latest jsonb;
    v_last_bar jsonb;
    v_bar_time timestamptz;
    v_price numeric;
    v_signal text;
    v_long_score int;
    v_short_score int;
    v_confidence int;
    v_snapshot_id uuid;
    v_decision_id uuid;
    v_state public.tfm_agent_state%rowtype;
    v_trade public.tfm_paper_trades%rowtype;
    v_has_trade boolean := false;
    v_action text := 'FLAT';
    v_exit_reason text;
    v_exit_price numeric;
    v_pnl_points numeric;
    v_pnl_r numeric;
    v_won boolean;
    v_next_losses int;
    v_horizon int;
    v_dec record;
    v_hbar record;
    v_raw_bps numeric;
    v_directional_bps numeric;
    v_outcomes_written int := 0;
    v_score int;
    v_entry numeric;
    v_stop numeric;
    v_target numeric;
    v_risk numeric;
begin
    insert into public.tfm_worker_runs(worker_version, status)
    values ('postgres_v1', 'STARTED')
    returning id into v_run_id;

    select *
    into v_http
    from extensions.http_get(
      'https://trading-for-money-z2rp.vercel.app/api/gold?interval=1m&range=1d'
    );

    if v_http.status <> 200 then
        raise exception 'gold api status %: %', v_http.status, left(v_http.content, 500);
    end if;

    v_payload := v_http.content::jsonb;
    v_latest := v_payload -> 'latest';
    v_last_bar := (v_payload -> 'bars') -> -1;

    v_bar_time := (v_latest ->> 'bar_time_utc')::timestamptz;
    v_price := (v_latest ->> 'price')::numeric;
    v_signal := v_latest ->> 'signal';
    v_long_score := (v_latest ->> 'long_score')::int;
    v_short_score := (v_latest ->> 'short_score')::int;
    v_confidence := case
        when v_signal = 'BUY' then v_long_score
        when v_signal = 'SELL' then v_short_score
        else greatest(v_long_score, v_short_score)
    end;

    insert into public.tfm_market_snapshots(
        bar_time, source, symbol, timeframe, price, feed_state, regime,
        atr, atr_pct, features, raw_signal
    )
    values (
        v_bar_time,'vercel_gold_api','GC=F','1m',v_price,
        v_latest ->> 'feed_state',v_latest ->> 'regime',
        nullif(v_latest ->> 'atr','')::numeric,
        nullif(v_latest ->> 'atr_pct','')::numeric,
        jsonb_build_object(
            'ema_fast', v_latest -> 'ema_fast',
            'ema_slow', v_latest -> 'ema_slow',
            'wave', v_latest -> 'wave',
            'squeeze', v_latest -> 'squeeze',
            'structure', v_latest -> 'structure'
        ),
        v_latest
    )
    on conflict (source, symbol, timeframe, bar_time)
    do update set
        price=excluded.price,feed_state=excluded.feed_state,regime=excluded.regime,
        atr=excluded.atr,atr_pct=excluded.atr_pct,features=excluded.features,
        raw_signal=excluded.raw_signal
    returning id into v_snapshot_id;

    insert into public.tfm_signal_decisions(
        snapshot_id,bar_time,strategy_version,action,long_score,short_score,
        confidence,entry_price,stop_price,target_price,reward_to_risk,rationale
    )
    values (
        v_snapshot_id,v_bar_time,'gold_scalper_v1',v_signal,
        v_long_score,v_short_score,v_confidence,
        nullif(v_latest #>> '{plan,entry}','')::numeric,
        nullif(v_latest #>> '{plan,stop}','')::numeric,
        nullif(v_latest #>> '{plan,target}','')::numeric,
        nullif(v_latest #>> '{plan,reward_to_risk}','')::numeric,
        jsonb_build_object(
            'regime',v_latest -> 'regime',
            'feed_state',v_latest -> 'feed_state',
            'wave',v_latest -> 'wave',
            'squeeze',v_latest -> 'squeeze',
            'structure',v_latest -> 'structure'
        )
    )
    on conflict (snapshot_id,strategy_version)
    do update set
        action=excluded.action,long_score=excluded.long_score,
        short_score=excluded.short_score,confidence=excluded.confidence,
        entry_price=excluded.entry_price,stop_price=excluded.stop_price,
        target_price=excluded.target_price,reward_to_risk=excluded.reward_to_risk,
        rationale=excluded.rationale
    returning id into v_decision_id;

    select * into v_state
    from public.tfm_agent_state
    where agent_key='gold_scalper_v1'
    for update;

    select * into v_trade
    from public.tfm_paper_trades
    where strategy_version='gold_scalper_v1'
      and symbol='GC=F' and timeframe='1m' and status='OPEN'
    limit 1
    for update;
    v_has_trade := found;

    if v_has_trade then
        if v_trade.side='BUY' then
            if (v_last_bar ->> 'low')::numeric <= v_trade.stop_price then
                v_exit_reason:='STOP'; v_exit_price:=v_trade.stop_price;
            elsif (v_last_bar ->> 'high')::numeric >= v_trade.target_price then
                v_exit_reason:='TARGET'; v_exit_price:=v_trade.target_price;
            elsif v_signal='SELL' then
                v_exit_reason:='OPPOSITE_SIGNAL'; v_exit_price:=v_price;
            end if;
        else
            if (v_last_bar ->> 'high')::numeric >= v_trade.stop_price then
                v_exit_reason:='STOP'; v_exit_price:=v_trade.stop_price;
            elsif (v_last_bar ->> 'low')::numeric <= v_trade.target_price then
                v_exit_reason:='TARGET'; v_exit_price:=v_trade.target_price;
            elsif v_signal='BUY' then
                v_exit_reason:='OPPOSITE_SIGNAL'; v_exit_price:=v_price;
            end if;
        end if;

        if v_exit_reason is not null then
            v_pnl_points := (case when v_trade.side='BUY' then 1 else -1 end)
                            * (v_exit_price-v_trade.entry_price);
            v_pnl_r := v_pnl_points/v_trade.initial_risk_points;
            v_won := v_pnl_points>0;
            v_next_losses := case when v_won then 0 else v_state.consecutive_losses+1 end;

            update public.tfm_paper_trades
            set status='CLOSED',closed_at=now(),closed_bar_time=v_bar_time,
                exit_price=v_exit_price,exit_reason=v_exit_reason,
                pnl_points=v_pnl_points,pnl_r=v_pnl_r
            where id=v_trade.id;

            update public.tfm_agent_state
            set consecutive_losses=v_next_losses,
                closed_trades=closed_trades+1,
                wins=wins+case when v_won then 1 else 0 end,
                losses=losses+case when v_won then 0 else 1 end,
                cumulative_pnl_points=cumulative_pnl_points+v_pnl_points,
                cumulative_pnl_r=cumulative_pnl_r+v_pnl_r,
                risk_paused_until=case
                    when v_next_losses>=4 then now()+interval '60 minutes'
                    when v_won then null else risk_paused_until end,
                updated_at=now()
            where agent_key='gold_scalper_v1';

            v_action:='CLOSE_'||v_exit_reason;
            v_has_trade:=false;
        else
            v_action:='HOLD_'||v_trade.side;
        end if;
    end if;

    if not v_has_trade
       and v_state.auto_enabled
       and coalesce(v_state.risk_paused_until,'-infinity'::timestamptz)<=now()
       and (v_latest ->> 'feed_state')='LIVEISH'
       and v_signal in ('BUY','SELL')
    then
        v_score:=case when v_signal='BUY' then v_long_score else v_short_score end;
        v_entry:=nullif(v_latest #>> '{plan,entry}','')::numeric;
        v_stop:=nullif(v_latest #>> '{plan,stop}','')::numeric;
        v_target:=nullif(v_latest #>> '{plan,target}','')::numeric;

        if v_score>=75 and v_entry is not null and v_stop is not null and v_target is not null then
            v_risk:=abs(v_entry-v_stop);
            if v_risk>0 then
                begin
                    insert into public.tfm_paper_trades(
                        strategy_version,symbol,timeframe,decision_id,side,
                        opened_at,opened_bar_time,entry_price,stop_price,target_price,
                        initial_risk_points,metadata
                    )
                    values (
                        'gold_scalper_v1','GC=F','1m',v_decision_id,v_signal,
                        now(),v_bar_time,v_entry,v_stop,v_target,v_risk,
                        jsonb_build_object(
                            'long_score',v_long_score,'short_score',v_short_score,
                            'regime',v_latest -> 'regime','worker','postgres_v1'
                        )
                    );
                    v_action:='OPEN_'||v_signal;
                exception when unique_violation then
                    v_action:='SKIP_DUPLICATE_OPEN';
                end;
            end if;
        end if;
    end if;

    for v_dec in
        select d.id,d.bar_time,d.action,d.entry_price
        from public.tfm_signal_decisions d
        where d.bar_time>=v_bar_time-interval '3 hours'
          and d.bar_time<=v_bar_time and d.entry_price is not null
    loop
        foreach v_horizon in array array[5,15,60]
        loop
            if v_dec.bar_time+make_interval(mins=>v_horizon)<=v_bar_time
               and not exists (
                   select 1 from public.tfm_decision_outcomes o
                   where o.decision_id=v_dec.id and o.horizon_minutes=v_horizon
               )
            then
                select to_timestamp((b ->> 'time')::bigint),
                       (b ->> 'close')::numeric
                into v_hbar
                from jsonb_array_elements(v_payload -> 'bars') b
                where to_timestamp((b ->> 'time')::bigint)
                      >=v_dec.bar_time+make_interval(mins=>v_horizon)
                order by to_timestamp((b ->> 'time')::bigint)
                limit 1;

                if v_hbar.f1 is not null then
                    v_raw_bps:=((v_hbar.f2/v_dec.entry_price)-1)*10000;
                    v_directional_bps:=case
                        when v_dec.action='BUY' then v_raw_bps
                        when v_dec.action='SELL' then -v_raw_bps
                        else null end;

                    insert into public.tfm_decision_outcomes(
                        decision_id,horizon_minutes,target_time,evaluated_bar_time,
                        price_at_horizon,raw_return_bps,directional_return_bps
                    )
                    values (
                        v_dec.id,v_horizon,
                        v_dec.bar_time+make_interval(mins=>v_horizon),
                        v_hbar.f1,v_hbar.f2,v_raw_bps,v_directional_bps
                    )
                    on conflict (decision_id,horizon_minutes) do nothing;
                    if found then v_outcomes_written:=v_outcomes_written+1; end if;
                end if;
            end if;
        end loop;
    end loop;

    update public.tfm_agent_state
    set last_run_at=now(),last_bar_time=v_bar_time,updated_at=now()
    where agent_key='gold_scalper_v1';

    update public.tfm_worker_runs
    set finished_at=now(),status='SUCCESS',source_bar_time=v_bar_time,
        action_taken=v_action,message='gold worker cycle completed',
        metrics=jsonb_build_object(
            'price',v_price,'signal',v_signal,'long_score',v_long_score,
            'short_score',v_short_score,'outcomes_written',v_outcomes_written
        )
    where id=v_run_id;

    return jsonb_build_object(
        'ok',true,'run_id',v_run_id,'bar_time',v_bar_time,'price',v_price,
        'signal',v_signal,'action',v_action,'outcomes_written',v_outcomes_written
    );
exception when others then
    if v_run_id is not null then
        update public.tfm_worker_runs
        set finished_at=now(),status='ERROR',action_taken='ERROR',message=sqlerrm
        where id=v_run_id;
    end if;
    raise;
end;
$$;

revoke all on function public.tfm_run_gold_worker() from public, anon, authenticated;
grant execute on function public.tfm_run_gold_worker() to postgres, service_role;

select cron.schedule(
    'tfm_gold_worker_every_minute',
    '* * * * *',
    'select public.tfm_run_gold_worker();'
);
