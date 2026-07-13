# -*- coding: utf-8 -*-
"""
Regenere le bloc `const RESULTATS = [...]` de index.html depuis les vrais
conseils regles en production. Lance chaque nuit par GitHub Actions
(.github/workflows/update-results.yml) avec DATABASE_URL en secret.

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
    "1 lyga": "🇱🇹",
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


def update_html(path: str, results: list[dict], period_stats: dict, period_series: dict) -> None:
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
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"[Site] {len(results)} resultats + stats/courbes jour/semaine/mois/annee ecrits dans {path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html",
    )
    update_html(target, fetch_results(), fetch_period_stats(), fetch_period_series())
