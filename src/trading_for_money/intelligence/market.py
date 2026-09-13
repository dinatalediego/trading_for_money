from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus

import numpy as np
import pandas as pd


DEFAULT_MARKET_UNIVERSE = {
    "SPY": {"label": "S&P 500", "group": "benchmark"},
    "QQQ": {"label": "Nasdaq 100", "group": "growth"},
    "IWM": {"label": "Russell 2000", "group": "small_caps"},
    "GLD": {"label": "Gold", "group": "gold"},
    "TLT": {"label": "Long Treasuries", "group": "rates"},
    "UUP": {"label": "US Dollar", "group": "fx"},
    "XLK": {"label": "Technology", "group": "sector"},
    "XLF": {"label": "Financials", "group": "sector"},
    "XLE": {"label": "Energy", "group": "sector"},
    "XLI": {"label": "Industrials", "group": "sector"},
    "XLV": {"label": "Health Care", "group": "sector"},
    "XLY": {"label": "Consumer Discretionary", "group": "sector"},
    "XLP": {"label": "Consumer Staples", "group": "sector"},
}


LEARNING_PATH = [
    {
        "lesson_id": "L01",
        "month": 1,
        "sequence": 1,
        "title": "Qué significa invertir",
        "provider": "Investor.gov",
        "duration_minutes": 25,
        "level": "Fundamentos",
        "objective": "Distinguir ahorro, inversión, horizonte y riesgo.",
        "url": "https://www.investor.gov/introduction-investing",
        "free": True,
        "assignment": "Escribe tu horizonte, meta y por qué invertirás cada mes.",
    },
    {
        "lesson_id": "L02",
        "month": 1,
        "sequence": 2,
        "title": "Asset allocation y diversificación",
        "provider": "Investor.gov",
        "duration_minutes": 30,
        "level": "Fundamentos",
        "objective": "Entender por qué CORE, Opportunity y Cash tienen trabajos distintos.",
        "url": "https://www.investor.gov/introduction-investing/getting-started/asset-allocation",
        "free": True,
        "assignment": "Explica en una frase el propósito de cada bucket de Capital OS.",
    },
    {
        "lesson_id": "L03",
        "month": 1,
        "sequence": 3,
        "title": "Costos, productos y ETFs",
        "provider": "Investor.gov",
        "duration_minutes": 30,
        "level": "Fundamentos",
        "objective": "Entender fees, liquidez y por qué costos pequeños importan.",
        "url": "https://www.investor.gov/introduction-investing/investing-basics/investment-products",
        "free": True,
        "assignment": "Compara el costo total de invertir US$100 y US$200 en tu plataforma.",
    },
    {
        "lesson_id": "L04",
        "month": 2,
        "sequence": 4,
        "title": "Mercados y mecánica de órdenes",
        "provider": "IBKR Traders' Academy",
        "duration_minutes": 45,
        "level": "Mercados",
        "objective": "Aprender market, limit, bid/ask, spread y ejecución.",
        "url": "https://www.interactivebrokers.com/campus/traders-academy/finance-courses/",
        "free": True,
        "assignment": "Haz una operación simulada y explica el spread observado.",
    },
    {
        "lesson_id": "L05",
        "month": 2,
        "sequence": 5,
        "title": "Paper trading y disciplina",
        "provider": "IBKR Traders' Academy",
        "duration_minutes": 45,
        "level": "Mercados",
        "objective": "Usar simulación para separar aprendizaje de riesgo financiero.",
        "url": "https://www.interactivebrokers.com/campus/traders-academy/finance-courses/",
        "free": True,
        "assignment": "Registra una decisión antes de conocer el resultado.",
    },
    {
        "lesson_id": "L06",
        "month": 3,
        "sequence": 6,
        "title": "Present value y valuación",
        "provider": "MIT OpenCourseWare",
        "duration_minutes": 60,
        "level": "Finanzas",
        "objective": "Relacionar tasas de descuento con valoración de activos.",
        "url": "https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/",
        "free": True,
        "assignment": "Explica por qué una tasa de descuento mayor reduce el valor presente.",
    },
    {
        "lesson_id": "L07",
        "month": 3,
        "sequence": 7,
        "title": "Risk, return y portfolio theory",
        "provider": "MIT OpenCourseWare",
        "duration_minutes": 75,
        "level": "Finanzas",
        "objective": "Entender retorno esperado, volatilidad, correlación y diversificación.",
        "url": "https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/",
        "free": True,
        "assignment": "Compara el rol de SPY, Gold y Cash en un portfolio.",
    },
    {
        "lesson_id": "L08",
        "month": 4,
        "sequence": 8,
        "title": "Leer 10-K y 10-Q en EDGAR",
        "provider": "SEC EDGAR",
        "duration_minutes": 45,
        "level": "Research",
        "objective": "Ir de una narrativa de mercado al documento primario de la empresa.",
        "url": "https://www.sec.gov/search-filings",
        "free": True,
        "assignment": "Busca el último 10-Q de una empresa que sigues y guarda la fuente.",
    },
    {
        "lesson_id": "L09",
        "month": 4,
        "sequence": 9,
        "title": "Datos macro con FRED",
        "provider": "Federal Reserve Bank of St. Louis",
        "duration_minutes": 45,
        "level": "Macro",
        "objective": "Leer tasas, inflación, curva y yields reales desde fuentes oficiales.",
        "url": "https://fred.stlouisfed.org/",
        "free": True,
        "assignment": "Relaciona 10Y real yield con una semana de movimientos en oro.",
    },
]


SOURCE_REGISTRY = [
    {
        "key": "sec_edgar",
        "name": "SEC EDGAR",
        "authority": "Primary",
        "kind": "Filings",
        "description": "10-K, 10-Q, 8-K, insiders y documentos regulatorios de emisores de EE.UU.",
        "base_url": "https://www.sec.gov/search-filings",
        "search_template": "https://www.sec.gov/edgar/search/#/q={query}",
        "keywords": {"10-k", "10-q", "8-k", "filing", "sec", "earnings", "empresa", "company", "insider"},
    },
    {
        "key": "fred",
        "name": "FRED",
        "authority": "Primary",
        "kind": "Macro data",
        "description": "Series macroeconómicas y financieras de fuentes oficiales.",
        "base_url": "https://fred.stlouisfed.org/",
        "search_template": "https://fred.stlouisfed.org/searchresults?st={query}",
        "keywords": {"inflation", "inflación", "rates", "tasas", "yield", "fed", "unemployment", "empleo", "gdp", "pbi", "macro", "real yield"},
    },
    {
        "key": "investor_gov",
        "name": "Investor.gov",
        "authority": "Primary",
        "kind": "Investor education",
        "description": "Educación del inversor de la SEC: riesgo, diversificación, productos y protección.",
        "base_url": "https://www.investor.gov/introduction-investing",
        "search_template": "https://www.investor.gov/search?keys={query}",
        "keywords": {"learn", "aprender", "risk", "riesgo", "etf", "diversification", "diversificación", "fees", "costos", "asset", "allocation", "portfolio", "cartera"},
    },
    {
        "key": "ibkr_academy",
        "name": "IBKR Traders' Academy",
        "authority": "Professional education",
        "kind": "Courses",
        "description": "Cursos gratuitos sobre mercados, plataformas, riesgo, derivados y APIs.",
        "base_url": "https://www.interactivebrokers.com/campus/traders-academy/finance-courses/",
        "search_template": "https://www.interactivebrokers.com/campus/?s={query}",
        "keywords": {"order", "orden", "trading", "broker", "options", "futures", "api", "paper"},
    },
    {
        "key": "mit_ocw",
        "name": "MIT OpenCourseWare",
        "authority": "Academic",
        "kind": "Courses",
        "description": "Finance Theory I: valuación, renta fija, equities, riesgo, CAPM y mercados eficientes.",
        "base_url": "https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/",
        "search_template": "https://ocw.mit.edu/search/?q={query}",
        "keywords": {"valuation", "valuación", "finance", "finanzas", "capm", "portfolio", "asset", "allocation", "present value", "valor presente"},
    },
    {
        "key": "us_treasury",
        "name": "U.S. Treasury",
        "authority": "Primary",
        "kind": "Rates",
        "description": "Datos y publicaciones oficiales del Tesoro de EE.UU.",
        "base_url": "https://home.treasury.gov/",
        "search_template": "https://home.treasury.gov/search?search_api_fulltext={query}",
        "keywords": {"treasury", "yield", "bond", "bono", "debt", "deuda", "rates"},
    },
    {
        "key": "bls",
        "name": "U.S. Bureau of Labor Statistics",
        "authority": "Primary",
        "kind": "Macro data",
        "description": "CPI, empleo, salarios y productividad de EE.UU.",
        "base_url": "https://www.bls.gov/",
        "search_template": "https://www.bls.gov/search/?query={query}",
        "keywords": {"cpi", "inflation", "inflación", "employment", "empleo", "payrolls", "wages", "salarios"},
    },
    {
        "key": "bea",
        "name": "U.S. Bureau of Economic Analysis",
        "authority": "Primary",
        "kind": "Macro data",
        "description": "GDP, PCE, income y cuentas económicas de EE.UU.",
        "base_url": "https://www.bea.gov/",
        "search_template": "https://apps.bea.gov/search/?query={query}",
        "keywords": {"gdp", "pbi", "pce", "income", "consumption", "consumo"},
    },
]


def _return(series: pd.Series, periods: int) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) <= periods:
        return None
    base = float(clean.iloc[-periods - 1])
    latest = float(clean.iloc[-1])
    if base == 0:
        return None
    return latest / base - 1.0


def compute_asset_metrics(
    frame: pd.DataFrame,
    *,
    symbol: str,
    label: str | None = None,
    group: str | None = None,
) -> dict:
    close = pd.to_numeric(frame["close"], errors="coerce").dropna()
    if len(close) < 21:
        raise ValueError(f"{symbol}: at least 21 closes required")

    ret = close.pct_change().dropna()
    ma20 = float(close.tail(20).mean())
    ma50 = float(close.tail(50).mean()) if len(close) >= 50 else None
    price = float(close.iloc[-1])
    vol20 = float(ret.tail(20).std(ddof=1) * np.sqrt(252)) if len(ret) >= 20 else None

    if ma50 is None:
        trend = "warming_up"
    elif price > ma20 > ma50:
        trend = "up"
    elif price < ma20 < ma50:
        trend = "down"
    else:
        trend = "mixed"

    return {
        "symbol": symbol,
        "label": label or symbol,
        "group": group or "asset",
        "price": price,
        "return_1d": _return(close, 1),
        "return_5d": _return(close, 5),
        "return_20d": _return(close, 20),
        "return_60d": _return(close, 60),
        "ma20": ma20,
        "ma50": ma50,
        "vol_20d_annualized": vol20,
        "trend": trend,
        "as_of": frame.index[-1].isoformat() if hasattr(frame.index[-1], "isoformat") else str(frame.index[-1]),
    }


def build_market_regime(metrics: Iterable[dict]) -> dict:
    by_symbol = {m["symbol"]: m for m in metrics}

    def r20(symbol: str) -> float:
        value = by_symbol.get(symbol, {}).get("return_20d")
        return float(value) if value is not None else 0.0

    risk_score = 0
    reasons: list[str] = []

    if r20("QQQ") > r20("SPY"):
        risk_score += 1
        reasons.append("Nasdaq 100 lidera al S&P 500")
    else:
        reasons.append("Nasdaq 100 no lidera al S&P 500")

    if r20("IWM") > 0:
        risk_score += 1
        reasons.append("small caps tienen retorno 20d positivo")
    else:
        reasons.append("small caps no confirman amplitud positiva")

    if r20("XLY") > r20("XLP"):
        risk_score += 1
        reasons.append("consumo discrecional supera a staples")
    else:
        reasons.append("staples igualan o superan a consumo discrecional")

    if r20("TLT") < -0.03:
        risk_score -= 1
        reasons.append("bonos largos muestran presión relevante")

    if risk_score >= 2:
        regime = "RISK_ON"
    elif risk_score <= 0:
        regime = "DEFENSIVE_OR_MIXED"
    else:
        regime = "SELECTIVE_RISK"

    sectors = [
        m for m in metrics
        if m.get("group") == "sector" and m.get("return_20d") is not None
    ]
    sectors.sort(key=lambda x: x["return_20d"], reverse=True)

    leaders = sectors[:3]
    laggards = list(reversed(sectors[-3:])) if sectors else []

    return {
        "regime": regime,
        "risk_score": risk_score,
        "reasons": reasons,
        "leaders": leaders,
        "laggards": laggards,
        "gold_20d": by_symbol.get("GLD", {}).get("return_20d"),
        "dollar_20d": by_symbol.get("UUP", {}).get("return_20d"),
        "bonds_20d": by_symbol.get("TLT", {}).get("return_20d"),
    }


def find_sources(query: str, limit: int = 8) -> list[dict]:
    query_clean = (query or "").strip()
    tokens = {t.lower() for t in query_clean.replace("/", " ").replace("-", " ").split() if t}

    scored = []
    for source in SOURCE_REGISTRY:
        keywords = set(source["keywords"])
        score = len(tokens.intersection(keywords))
        if not tokens:
            score = 1
        if score == 0 and query_clean:
            haystack = (
                source["name"] + " " + source["kind"] + " " + source["description"]
            ).lower()
            score = sum(1 for t in tokens if t in haystack)

        if score > 0 or len(scored) < 3:
            item = {k: v for k, v in source.items() if k != "keywords"}
            item["score"] = score
            item["search_url"] = source["search_template"].format(
                query=quote_plus(query_clean)
            )
            scored.append(item)

    authority_rank = {"Primary": 0, "Academic": 1, "Professional education": 2}
    scored.sort(
        key=lambda x: (
            -x["score"],
            authority_rank.get(x["authority"], 9),
            x["name"],
        )
    )
    return scored[:limit]


def build_daily_brief(
    metrics: list[dict],
    regime: dict,
    macro: list[dict] | None = None,
    headlines: list[dict] | None = None,
) -> dict:
    by_symbol = {m["symbol"]: m for m in metrics}

    def fmt_pct(value: float | None) -> str:
        return "n/d" if value is None else f"{value:+.1%}"

    leaders = regime.get("leaders", [])
    leader_text = (
        ", ".join(f"{x['label']} {fmt_pct(x.get('return_20d'))}" for x in leaders)
        if leaders else "sin suficientes datos sectoriales"
    )

    gold = by_symbol.get("GLD", {})
    qqq = by_symbol.get("QQQ", {})
    spy = by_symbol.get("SPY", {})
    iwm = by_symbol.get("IWM", {})

    observations = [
        f"Régimen: {regime['regime']} (score {regime['risk_score']}).",
        f"Liderazgo sectorial 20d: {leader_text}.",
        (
            "Growth vs mercado: QQQ "
            f"{fmt_pct(qqq.get('return_20d'))} vs SPY {fmt_pct(spy.get('return_20d'))}."
        ),
        (
            "Amplitud aproximada: IWM "
            f"{fmt_pct(iwm.get('return_20d'))} en 20 sesiones."
        ),
        (
            "Oro: GLD "
            f"{fmt_pct(gold.get('return_20d'))} en 20 sesiones; tendencia {gold.get('trend', 'n/d')}."
        ),
    ]

    lesson_focus = "asset allocation"
    if gold.get("return_20d") is not None and abs(gold["return_20d"]) > 0.05:
        lesson_focus = "tasas reales, dólar y oro"
    elif qqq.get("return_20d") is not None and spy.get("return_20d") is not None:
        if qqq["return_20d"] - spy["return_20d"] > 0.03:
            lesson_focus = "growth, duration y tasas de descuento"

    return {
        "headline": f"Mercado: {regime['regime'].replace('_', ' ').title()}",
        "observations": observations,
        "macro": macro or [],
        "headlines": headlines or [],
        "learning_focus": lesson_focus,
        "discipline_note": (
            "El brief informa y prioriza investigación. No crea órdenes ni convierte "
            "una noticia aislada en una recomendación de compra."
        ),
    }
