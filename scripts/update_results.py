# -*- coding: utf-8 -*-
"""
Regenere les blocs de donnees live de index.html (RESULTATS, PERIOD_STATS,
PERIOD_SERIES, PERF_STATS) depuis les vrais paris regles en production.
Lance chaque nuit par GitHub Actions (.github/workflows/update-results.yml)
avec DATABASE_URL en secret.

Aucun secret dans ce fichier : la connexion vient de l'environnement.
"""
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

N_MATCHES = 20  # matchs regles (chacun peut donner jusqu'a 3 entrees : conseil/value/player pick cote)
BASE_UNIT_EUR = 200  # doit rester synchro avec ai/staking.py BASE_UNIT_EUR
PARIS_TZ = ZoneInfo("Europe/Paris")

# Drapeau par competition (fallback ⚽ si inconnue)
COMPETITION_FLAGS = {
    "coupe du monde": "🏆",
    "k league": "🇰🇷",
    "j1 league": "🇯🇵",
    "j2 league": "🇯🇵",
    "allsvenskan": "🇸🇪",
    "superettan": "🇸🇪",
    "eliteserien": "🇳🇴",
    "obos": "🇳🇴",
    "veikkausliiga": "🇫🇮",
    "ykkosliiga": "🇫🇮",
    "ykkonen": "🇫🇮",
    "besta deild": "🇮🇸",
    "urvalsdeild": "🇮🇸",
    "premier division": "🇮🇪",
    "first division": "🇮🇪",
    "a lyga": "🇱🇹",
    "meistriliiga": "🇪🇪",
    "esiliiga": "🇪🇪",
    "virsliga": "🇱🇻",
    "eerste divisie": "🇳🇱",
    "eredivisie": "🇳🇱",
    "serie a": "🇧🇷",
    "serie b": "🇧🇷",
    "brasileir": "🇧🇷",
    "mls": "🇺🇸",
    "usl": "🇺🇸",
    "liga profesional": "🇦🇷",
    "primera nacional": "🇦🇷",
    "liga mx": "🇲🇽",
    "chinese super league": "🇨🇳",
    "super league": "🇨🇳",
    "npl": "🇦🇺",
    "a-league": "🇦🇺",
    "saudi": "🇸🇦",
    "erovnuli": "🇬🇪",
    "champions league": "🏆",
    "europa": "🏆",
    "conference": "🏆",
    "botola": "🇲🇦",
    "azadegan": "🇮🇷",
    "ettan": "🇸🇪",
    "division 2 -": "🇸🇪",
    "damallsvenskan": "🇸🇪",
    "copa chile": "🇨🇱",
    "copa venezuela": "🇻🇪",
    "division intermedia": "🇵🇾",
    "1 lyga": "🇱🇹",
    "erovnuli": "🇬🇪",
}


def _flag(competition: str) -> str:
    c = (competition or "").lower()
    for key, flag in COMPETITION_FLAGS.items():
        if key in c:
            return flag
    return "⚽"


def _short_pick(conseil: str) -> str:
    s = (conseil or "").strip()
    s = re.sub(r"^Double chance\s+", "", s, flags=re.IGNORECASE)
    return s


def _paris_datetime(value):
    """Convertit un timestamp (avec ou sans fuseau) en datetime Paris.
    C'est la date/heure de REGLEMENT (result_updated_at) qui fait foi pour
    les bilans jour/semaine/mois/annee, pas la date de publication (cf
    daily_bilan.py et sa note sur result_updated_at vs date de publication)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS_TZ)
    return dt.astimezone(PARIS_TZ)


def _paris_calendar_date(value):
    dt = _paris_datetime(value)
    return dt.date() if dt else None


def fetch_period_stats() -> dict:
    """Bilan EN COURS (pas la periode passee complete comme daily_bilan.py)
    pour jour / semaine (lundi->aujourd'hui) / mois (1er->aujourd'hui),
    au sens ou le bot les regle deja (result_updated_at), pas au sens
    "publie ce jour-la" -- coherent avec send_daily/weekly/monthly_bilan."""
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT resultat, pnl, result_updated_at
        FROM paris
        WHERE resultat IN ('GAGNE','PERDU','REMBOURSE')
          AND result_updated_at IS NOT NULL AND result_updated_at <> ''
        ORDER BY result_updated_at DESC
        LIMIT 1000
        """,
    )
    rows = cur.fetchall()
    conn.close()

    today = datetime.now(PARIS_TZ).date()
    week_start = today - timedelta(days=today.weekday())  # lundi
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    boundaries = {"jour": today, "semaine": week_start, "mois": month_start, "annee": year_start}
    buckets = {k: {"n": 0, "g": 0, "p": 0, "r": 0, "pnl_eur": 0.0} for k in boundaries}

    for resultat, pnl, result_updated_at in rows:
        d = _paris_calendar_date(result_updated_at)
        if d is None or d > today:
            continue
        pnl_val = float(pnl or 0)
        for key, start in boundaries.items():
            if d < start:
                continue
            b = buckets[key]
            b["n"] += 1
            b["pnl_eur"] += pnl_val
            if resultat == "GAGNE":
                b["g"] += 1
            elif resultat == "PERDU":
                b["p"] += 1
            elif resultat == "REMBOURSE":
                b["r"] += 1

    out = {}
    for key, b in buckets.items():
        decides = b["g"] + b["p"]
        out[key] = {
            "n": b["n"],
            "g": b["g"],
            "p": b["p"],
            "r": b["r"],
            "winrate": round(b["g"] / decides * 100) if decides else 0,
            "pnl": round(b["pnl_eur"] / BASE_UNIT_EUR, 2),
        }
    return out


JOURS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MOIS_FR = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]


def fetch_period_series() -> dict:
    """Courbe cumulee du PnL par periode, pour le graphique du site :
    jour -> par heure (00h..23h), semaine -> par jour (Lun..Dim),
    mois -> par jour du mois, annee -> par mois (Jan..Dec). Meme source
    (result_updated_at, en unites) que fetch_period_stats -- juste eclate
    en points de courbe au lieu d'un seul total."""
    import calendar
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pnl, result_updated_at
        FROM paris
        WHERE resultat IN ('GAGNE','PERDU','REMBOURSE')
          AND result_updated_at IS NOT NULL AND result_updated_at <> ''
        ORDER BY result_updated_at DESC
        LIMIT 5000
        """,
    )
    rows = cur.fetchall()
    conn.close()

    now = datetime.now(PARIS_TZ)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    n_days_month = calendar.monthrange(today.year, today.month)[1]

    heures = [0.0] * 24
    semaine = [0.0] * 7
    mois = [0.0] * n_days_month
    annee = [0.0] * 12

    for pnl, result_updated_at in rows:
        dt = _paris_datetime(result_updated_at)
        if dt is None or dt.date() > today:
            continue
        d = dt.date()
        pnl_u = float(pnl or 0) / BASE_UNIT_EUR
        if d == today:
            heures[dt.hour] += pnl_u
        if week_start <= d <= today:
            semaine[d.weekday()] += pnl_u
        if month_start <= d <= today:
            mois[d.day - 1] += pnl_u
        if year_start <= d <= today:
            annee[d.month - 1] += pnl_u

    def cumulative_points(values, labels):
        points, running = [], 0.0
        for v, label in zip(values, labels):
            running += v
            points.append({"label": label, "pnl": round(running, 2)})
        return points

    return {
        "jour": cumulative_points(heures, [f"{h:02d}h" for h in range(24)]),
        "semaine": cumulative_points(semaine, JOURS_FR),
        "mois": cumulative_points(mois, [str(i + 1) for i in range(n_days_month)]),
        "annee": cumulative_points(annee, MOIS_FR),
    }


def _cat(selection: str) -> str:
    """Meme classifieur que daily_bilan.py::_cat -- il n'existe pas de FK
    entre offensive_player_picks (categorie) et player_pick_settlements
    (juste un pick_key = hash(joueur|selection)) : on retrouve la categorie
    d'un settlement par mots-cles sur son texte de selection."""
    s = (selection or "").lower()
    if "passe" in s:
        return "passeur"
    if "decisif" in s or "décisif" in s:
        return "decisif"
    return "buteur"


def _pnl_fixed(result: str, cote, stake) -> float:
    if result == "GAGNE":
        return (float(cote or 0) - 1) * float(stake or 0)
    if result == "PERDU":
        return -float(stake or 0)
    return 0.0


def fetch_results() -> list[dict]:
    """Jusqu'a 3 entrees independantes par match regle (conseil / value bet /
    player pick COTE uniquement -- jamais le mode pourcentage, qui n'a pas de
    prix de marche a encaisser) : chacune a son propre resultat et son propre
    PnL, jamais un badge global unique (un value bet peut perdre alors que le
    conseil du meme match gagne)."""
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.fixture_id, p.home, p.away,
               p.conseil, COALESCE(NULLIF(p.cote_reelle,0), p.cote_interne),
               p.resultat, COALESCE(p.mise,1), COALESCE(p.pnl,0),
               p.value_bet, p.value_cote, p.value_result, COALESCE(p.value_stake_eur,0),
               COALESCE(NULLIF(p.competition,''), pf.league, '')
        FROM paris p
        LEFT JOIN programme_fixtures pf ON pf.fixture_id = p.fixture_id
        WHERE p.result_updated_at IS NOT NULL AND p.result_updated_at <> ''
          AND (
            p.resultat IN ('GAGNE','PERDU','REMBOURSE')
            OR p.value_result IN ('GAGNE','PERDU')
            OR EXISTS (
              SELECT 1 FROM offensive_player_picks o
              WHERE o.fixture_id = p.fixture_id AND o.display_mode = 'cote' AND o.market_odd > 1.01
            )
          )
        ORDER BY p.result_updated_at DESC
        LIMIT %s
        """,
        (N_MATCHES,),
    )
    fixtures = cur.fetchall()
    fixture_ids = [str(r[0]) for r in fixtures]

    player_by_fixture: dict = {}
    settlements_by_fixture: dict = {}
    if fixture_ids:
        placeholders = ",".join(["%s"] * len(fixture_ids))
        cur.execute(
            f"""SELECT fixture_id, category, selection_label, market_odd, stake_eur, combined_score
                FROM offensive_player_picks
                WHERE fixture_id IN ({placeholders}) AND display_mode = 'cote' AND market_odd > 1.01
                ORDER BY combined_score DESC""",
            tuple(fixture_ids),
        )
        for fid, category, label, odd, stake, _score in cur.fetchall():
            fid = str(fid)
            if fid not in player_by_fixture:  # 1er vu = meilleur combined_score
                player_by_fixture[fid] = {
                    "category": category, "label": label,
                    "cote": float(odd or 0), "stake": float(stake or 0),
                }
        cur.execute(
            f"""SELECT fixture_id, selection, result FROM player_pick_settlements
                WHERE fixture_id IN ({placeholders})""",
            tuple(fixture_ids),
        )
        for fid, selection, result in cur.fetchall():
            settlements_by_fixture.setdefault(str(fid), []).append((selection, result))
    conn.close()

    out = []
    for fixture_id, home, away, conseil, cote, resultat, mise, pnl, \
            value_bet, value_cote, value_result, value_stake, competition in reversed(fixtures):
        fixture_id = str(fixture_id)
        flag = _flag(competition)
        match = f"{home} – {away}"

        if conseil and resultat in ("GAGNE", "PERDU", "REMBOURSE"):
            # paris.mise/paris.pnl sont stockes en EUROS en base (mise =
            # advice_stake.stake_eur, cf football/predictions.py).
            out.append({
                "flag": flag, "match": match, "pick": _short_pick(conseil),
                "cote": round(float(cote or 0), 2),
                "r": {"GAGNE": "G", "PERDU": "P"}.get(resultat, "R"),
                "mise": round(float(mise or BASE_UNIT_EUR) / BASE_UNIT_EUR, 2),
                "pnl": round(float(pnl or 0) / BASE_UNIT_EUR, 2),
                "type": "conseil",
            })

        if value_bet and value_result in ("GAGNE", "PERDU"):
            v_pnl = _pnl_fixed(value_result, value_cote, value_stake)
            out.append({
                "flag": flag, "match": match, "pick": _short_pick(value_bet),
                "cote": round(float(value_cote or 0), 2),
                "r": {"GAGNE": "G", "PERDU": "P"}.get(value_result, "R"),
                "mise": round(float(value_stake or BASE_UNIT_EUR) / BASE_UNIT_EUR, 2),
                "pnl": round(v_pnl / BASE_UNIT_EUR, 2),
                "type": "value",
            })

        pick_info = player_by_fixture.get(fixture_id)
        if pick_info:
            result = next(
                (r for selection, r in settlements_by_fixture.get(fixture_id, [])
                 if _cat(selection) == pick_info["category"]),
                None,
            )
            if result in ("GAGNE", "PERDU", "REMBOURSE"):
                p_pnl = _pnl_fixed(result, pick_info["cote"], pick_info["stake"])
                out.append({
                    "flag": flag, "match": match, "pick": pick_info["label"],
                    "cote": round(pick_info["cote"], 2),
                    "r": {"GAGNE": "G", "PERDU": "P"}.get(result, "R"),
                    "mise": round(pick_info["stake"] / BASE_UNIT_EUR, 2),
                    "pnl": round(p_pnl / BASE_UNIT_EUR, 2),
                    "type": "player",
                })

    return out


# Copie de football/predictions.py::COTE_AVOID_BANDS -- doit rester synchro.
# hi=None : pas de borne haute. Sert a marquer les "zones bloquees" dans le
# tableau public de performance par marche.
COTE_AVOID_BANDS = {
    "double_chance": [(1.50, 2.00), (2.50, None)],
    "winner": [(4.00, None)],
    "total_goals": [(3.00, None)],
    "both_teams_to_score": [(1.50, 3.00)],
}

# Bandes de cote du tableau public -- memes bornes que jobs/weekly_roi_report.py
ODDS_BANDS = [
    (0.0, 1.50, "< 1.50"),
    (1.50, 1.70, "1.50-1.70"),
    (1.70, 2.00, "1.70-2.00"),
    (2.00, 2.50, "2.00-2.50"),
    (2.50, 3.00, "2.50-3.00"),
    (3.00, 4.00, "3.00-4.00"),
    (4.00, 99.0, "4.00+"),
]

MARKET_FR = {
    "double_chance": "Double chance",
    "winner": "Vainqueur",
    "total_goals": "Buts (over/under)",
    "both_teams_to_score": "Les deux marquent",
    "handicap": "Handicap",
    "scorer": "Buteur",
    "assist": "Passeur",
}


def _is_blocked(market_type: str, odd: float) -> bool:
    for lo, hi in COTE_AVOID_BANDS.get(market_type, []):
        if odd >= lo and (hi is None or odd < hi):
            return True
    return False


def fetch_perf_stats() -> dict:
    """Stats de performance publiques : ROI global depuis le lancement,
    classement par sport, tableau marche x bande de cote (avec zones
    bloquees), meilleur/pire pick + top ligue du mois, taux de reussite des
    player picks mode pourcentage. Tout depuis les paris regles reels."""
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()

    # ── Global + par sport + marche x bande (tous les conseils regles) ──
    cur.execute(
        """
        SELECT sport, market_type,
               COALESCE(NULLIF(cote_reelle,0), cote_interne),
               resultat, COALESCE(mise,0), COALESCE(pnl,0), result_updated_at
        FROM paris
        WHERE resultat IN ('GAGNE','PERDU','REMBOURSE')
          AND result_updated_at IS NOT NULL AND result_updated_at <> ''
        """,
    )
    rows = cur.fetchall()

    today = datetime.now(PARIS_TZ).date()
    month_start = today.replace(day=1)

    g = {"n": 0, "w": 0, "l": 0, "stake": 0.0, "pnl": 0.0, "since": None}
    sports: dict = {}
    markets: dict = {}
    for sport, market_type, cote, resultat, mise, pnl, rud in rows:
        d = _paris_calendar_date(rud)
        if d is None:
            continue
        won = resultat == "GAGNE"
        lost = resultat == "PERDU"
        g["n"] += 1
        g["w"] += won
        g["l"] += lost
        g["stake"] += float(mise or 0)
        g["pnl"] += float(pnl or 0)
        if g["since"] is None or d < g["since"]:
            g["since"] = d

        sp = (sport or "football").lower()
        s = sports.setdefault(sp, {"n": 0, "w": 0, "l": 0, "stake": 0.0, "pnl": 0.0})
        s["n"] += 1
        s["w"] += won
        s["l"] += lost
        s["stake"] += float(mise or 0)
        s["pnl"] += float(pnl or 0)

        mt = market_type or "winner"
        odd = float(cote or 0)
        for lo, hi, label in ODDS_BANDS:
            if lo <= odd < hi:
                key = (mt, label)
                m = markets.setdefault(key, {"n": 0, "w": 0, "l": 0, "pnl": 0.0,
                                             "blocked": _is_blocked(mt, (lo + min(hi, 9.0)) / 2)})
                m["n"] += 1
                m["w"] += won
                m["l"] += lost
                m["pnl"] += float(pnl or 0)
                break

    # ── Highlights du mois (meilleur/pire pick, top ligue) ──
    cur.execute(
        """
        SELECT p.home, p.away, p.conseil,
               COALESCE(NULLIF(p.cote_reelle,0), p.cote_interne),
               COALESCE(p.pnl,0), COALESCE(NULLIF(p.competition,''), pf.league, ''),
               p.result_updated_at
        FROM paris p
        LEFT JOIN programme_fixtures pf ON pf.fixture_id = p.fixture_id
        WHERE p.resultat IN ('GAGNE','PERDU')
          AND p.conseil IS NOT NULL AND p.conseil <> ''
          AND p.result_updated_at IS NOT NULL AND p.result_updated_at <> ''
        """,
    )
    best = worst = None
    leagues: dict = {}
    for home, away, conseil, cote, pnl, competition, rud in cur.fetchall():
        d = _paris_calendar_date(rud)
        if d is None or not (month_start <= d <= today):
            continue
        pnl = float(pnl or 0)
        entry = {
            "match": f"{home} – {away}", "pick": _short_pick(conseil),
            "cote": round(float(cote or 0), 2), "pnl": round(pnl / BASE_UNIT_EUR, 2),
            "flag": _flag(competition), "league": competition or "",
        }
        if pnl > 0 and (best is None or pnl > best["_raw"]):
            best = {**entry, "_raw": pnl}
        if pnl < 0 and (worst is None or pnl < worst["_raw"]):
            worst = {**entry, "_raw": pnl}
        if competition:
            lg = leagues.setdefault(competition, {"pnl": 0.0, "n": 0})
            lg["pnl"] += pnl
            lg["n"] += 1
    top_league = None
    if leagues:
        name, lg = max(leagues.items(), key=lambda kv: kv[1]["pnl"])
        if lg["pnl"] > 0:
            top_league = {"league": name, "flag": _flag(name),
                          "pnl": round(lg["pnl"] / BASE_UNIT_EUR, 2), "n": lg["n"]}

    # ── Player picks mode pourcentage (taux de reussite, pas de PnL) ──
    cur.execute(
        """
        SELECT o.category, s.selection, s.result
        FROM player_pick_settlements s
        JOIN offensive_player_picks o ON o.fixture_id = s.fixture_id
        WHERE o.display_mode = 'percent' AND s.result IN ('GAGNE','PERDU')
        """,
    )
    pp = {"n": 0, "w": 0}
    for category, selection, result in cur.fetchall():
        if _cat(selection) != category:
            continue
        pp["n"] += 1
        pp["w"] += result == "GAGNE"
    conn.close()

    def pack(d):
        decides = d["w"] + d["l"]
        return {
            "n": d["n"], "w": d["w"], "l": d["l"],
            "winrate": round(d["w"] / decides * 100) if decides else 0,
            "roi": round(d["pnl"] / d["stake"] * 100, 1) if d["stake"] else 0,
            "pnl": round(d["pnl"] / BASE_UNIT_EUR, 2),
        }

    market_rows = []
    for (mt, band), m in sorted(markets.items(), key=lambda kv: (-kv[1]["n"],)):
        decides = m["w"] + m["l"]
        market_rows.append({
            "market": MARKET_FR.get(mt, mt), "band": band, "n": m["n"],
            "winrate": round(m["w"] / decides * 100) if decides else 0,
            "pnl": round(m["pnl"] / BASE_UNIT_EUR, 2),
            "blocked": m["blocked"],
        })

    blocked_bands = []
    for mt, bands in COTE_AVOID_BANDS.items():
        for lo, hi in bands:
            blocked_bands.append({
                "market": MARKET_FR.get(mt, mt),
                "band": f"{lo:.2f}+" if hi is None else f"{lo:.2f}-{hi:.2f}",
            })

    for entry in (best, worst):
        if entry:
            entry.pop("_raw", None)

    return {
        "global": {**pack(g), "since": g["since"].isoformat() if g["since"] else ""},
        "sports": [{"sport": sp, **pack(s)} for sp, s in
                   sorted(sports.items(), key=lambda kv: -kv[1]["n"])],
        "markets": market_rows,
        "blocked_bands": blocked_bands,
        "highlights": {"best": best, "worst": worst, "top_league": top_league},
        "percent_picks": {"n": pp["n"],
                          "winrate": round(pp["w"] / pp["n"] * 100) if pp["n"] else 0},
    }


def render_perf_block(perf: dict) -> str:
    import json
    return "const PERF_STATS = " + json.dumps(perf, ensure_ascii=False) + ";"


def render_block(results: list[dict]) -> str:
    lines = ["const RESULTATS = ["]
    for r in results:
        match = r["match"].replace('"', "'")
        pick = r["pick"].replace('"', "'")
        lines.append(
            f'  {{flag:"{r["flag"]}", match:"{match}", pick:"{pick}", '
            f'cote:{r["cote"]:.2f}, r:"{r["r"]}", mise:{r["mise"]:.2f}, pnl:{r["pnl"]:.2f}, type:"{r["type"]}"}},'
        )
    lines.append("];")
    return "\n".join(lines)


def render_period_block(stats: dict) -> str:
    parts = [
        f'{key}:{{n:{s["n"]}, g:{s["g"]}, p:{s["p"]}, r:{s["r"]}, '
        f'winrate:{s["winrate"]}, pnl:{s["pnl"]:.2f}}}'
        for key, s in stats.items()
    ]
    return "const PERIOD_STATS = {" + ", ".join(parts) + "};"


def render_series_block(series: dict) -> str:
    def pts(points):
        items = ", ".join(f'{{label:"{p["label"]}", pnl:{p["pnl"]:.2f}}}' for p in points)
        return f"[{items}]"

    parts = [f"{key}:{pts(points)}" for key, points in series.items()]
    return "const PERIOD_SERIES = {" + ", ".join(parts) + "};"


def update_html(path: str, results: list[dict], period_stats: dict,
                period_series: dict, perf_stats: dict) -> None:
    with open(path, encoding="utf-8") as f:
        html = f.read()
    html, n1 = re.subn(r"const RESULTATS = \[.*?\];", render_block(results), html, count=1, flags=re.DOTALL)
    if n1 != 1:
        raise SystemExit(f"bloc RESULTATS introuvable dans {path}")
    html, n2 = re.subn(r"const PERIOD_STATS = \{.*?\};", render_period_block(period_stats), html, count=1, flags=re.DOTALL)
    if n2 != 1:
        raise SystemExit(f"bloc PERIOD_STATS introuvable dans {path}")
    html, n3 = re.subn(r"const PERIOD_SERIES = \{.*?\};", render_series_block(period_series), html, count=1, flags=re.DOTALL)
    if n3 != 1:
        raise SystemExit(f"bloc PERIOD_SERIES introuvable dans {path}")
    html, n4 = re.subn(r"const PERF_STATS = \{.*?\};", lambda _: render_perf_block(perf_stats), html, count=1, flags=re.DOTALL)
    if n4 != 1:
        raise SystemExit(f"bloc PERF_STATS introuvable dans {path}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"[Site] {len(results)} resultats + stats/courbes/performance ecrits dans {path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html",
    )
    update_html(target, fetch_results(), fetch_period_stats(),
                fetch_period_series(), fetch_perf_stats())
