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

N_RESULTS = 20
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


def fetch_results() -> list[dict]:
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.home, p.away, p.conseil,
               COALESCE(NULLIF(p.cote_reelle,0), p.cote_interne),
               p.resultat, COALESCE(NULLIF(p.competition,''), pf.league, ''),
               COALESCE(p.mise, 1), COALESCE(p.pnl, 0)
        FROM paris p
        LEFT JOIN programme_fixtures pf ON pf.fixture_id = p.fixture_id
        WHERE p.resultat IN ('GAGNE','PERDU','REMBOURSE')
          AND p.conseil IS NOT NULL AND p.conseil <> ''
        ORDER BY COALESCE(NULLIF(p.result_updated_at,''), p.created_at) DESC
        LIMIT %s
        """,
        (N_RESULTS,),
    )
    rows = cur.fetchall()
    conn.close()
    out = []
    for home, away, conseil, cote, resultat, competition, mise, pnl in reversed(rows):
        out.append({
            "flag": _flag(competition),
            "match": f"{home} – {away}",
            "pick": _short_pick(conseil),
            "cote": round(float(cote or 0), 2),
            "r": {"GAGNE": "G", "PERDU": "P"}.get(resultat, "R"),
            # paris.mise/paris.pnl sont stockes en EUROS en base (mise =
            # advice_stake.stake_eur, cf football/predictions.py) -- on
            # convertit en unites (1u = BASE_UNIT_EUR, ai/staking.py) pour
            # rester coherent avec l'affichage "u" du site.
            "mise": round(float(mise or BASE_UNIT_EUR) / BASE_UNIT_EUR, 2),
            "pnl": round(float(pnl or 0) / BASE_UNIT_EUR, 2),
        })
    return out


def render_block(results: list[dict]) -> str:
    lines = ["const RESULTATS = ["]
    for r in results:
        match = r["match"].replace('"', "'")
        pick = r["pick"].replace('"', "'")
        lines.append(
            f'  {{flag:"{r["flag"]}", match:"{match}", pick:"{pick}", '
            f'cote:{r["cote"]:.2f}, r:"{r["r"]}", mise:{r["mise"]:.2f}, pnl:{r["pnl"]:.2f}}},'
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
