# -*- coding: utf-8 -*-
"""
Genere programme.json : la liste programme du jour (meme liste que l'admin,
figee a 08h00 Paris via programme_fixtures.programme_date) avec, pour chaque
match, un compte a rebours (cote client, JS) jusqu'a T-30, le contenu de la
publication une fois sortie, puis le resultat final (GAGNE/PERDU/REMBOURSE)
une fois le match regle. Lance par .github/workflows/update-programme.yml
(cron ~10 min, gate sur le secret DATABASE_URL, absent = skip silencieux).

Contrairement a update_results.py (historique, une fois par nuit), ce script
tourne frequemment pour rafraichir l'etat (publication, resultat) en direct.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")

COMPETITION_FLAGS = {
    "coupe du monde": "🏆", "k league": "🇰🇷", "j1 league": "🇯🇵", "j2 league": "🇯🇵",
    "allsvenskan": "🇸🇪", "superettan": "🇸🇪", "eliteserien": "🇳🇴", "obos": "🇳🇴",
    "veikkausliiga": "🇫🇮", "ykkosliiga": "🇫🇮", "ykkonen": "🇫🇮", "besta deild": "🇮🇸",
    "urvalsdeild": "🇮🇸", "premier division": "🇮🇪", "first division": "🇮🇪",
    "a lyga": "🇱🇹", "1 lyga": "🇱🇹", "meistriliiga": "🇪🇪", "esiliiga": "🇪🇪",
    "virsliga": "🇱🇻", "eerste divisie": "🇳🇱", "eredivisie": "🇳🇱", "serie a": "🇧🇷",
    "serie b": "🇧🇷", "brasileir": "🇧🇷", "mls": "🇺🇸", "usl": "🇺🇸",
    "liga profesional": "🇦🇷", "primera nacional": "🇦🇷", "liga mx": "🇲🇽",
    "chinese super league": "🇨🇳", "super league": "🇨🇳", "npl": "🇦🇺", "a-league": "🇦🇺",
    "saudi": "🇸🇦", "erovnuli": "🇬🇪", "champions league": "🏆", "europa": "🏆",
    "conference": "🏆", "liga pro": "🇪🇨",
}


def _flag(league: str) -> str:
    c = (league or "").lower()
    for key, flag in COMPETITION_FLAGS.items():
        if key in c:
            return flag
    return "⚽"


def _short_pick(conseil: str) -> str:
    return re.sub(r"^Double chance\s+", "", (conseil or "").strip(), flags=re.IGNORECASE)


def _programme_date_today() -> str:
    """Meme fenetre '8h' que l'admin (daily_summary._programme_window) :
    jour Paris qui commence a 08h00, avec garde de 5 min si le script tourne
    juste avant 08h00 (evite de retomber sur la date de la veille)."""
    now = datetime.now(PARIS_TZ)
    day_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < day_start and (day_start - now).total_seconds() > 300:
        day_start -= timedelta(days=1)
    return day_start.strftime("%Y-%m-%d")


def fetch_programme() -> list[dict]:
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT fixture_id, home, away, league, kickoff_at, publish_status
        FROM programme_fixtures
        WHERE programme_date = %s AND sport = 'football'
        ORDER BY kickoff_at ASC
        LIMIT 300
        """,
        (_programme_date_today(),),
    )
    rows = cur.fetchall()

    out = []
    for fixture_id, home, away, league, kickoff_at, publish_status in rows:
        item = {
            "flag": _flag(league),
            "league": league or "",
            "match": f"{home} – {away}",
            "kickoff_at": kickoff_at,
            "published": publish_status == "published",
        }
        if publish_status == "published":
            cur.execute(
                """SELECT conseil, COALESCE(NULLIF(cote_reelle,0), cote_interne),
                          value_bet, value_cote, resultat, score
                   FROM paris WHERE fixture_id = %s
                   ORDER BY created_at DESC LIMIT 1""",
                (fixture_id,),
            )
            row = cur.fetchone()
            if row:
                conseil, cote, value_bet, value_cote, resultat, score = row
                if conseil:
                    item["conseil"] = _short_pick(conseil)
                    item["conseil_cote"] = round(float(cote or 0), 2)
                if value_bet:
                    item["value_bet"] = _short_pick(value_bet)
                    item["value_cote"] = round(float(value_cote or 0), 2)
                if (resultat or "").upper() in ("GAGNE", "PERDU", "REMBOURSE"):
                    item["result"] = resultat.upper()
                    if score:
                        item["score"] = score
            cur.execute(
                """SELECT category, selection_label, display_mode, market_odd, public_probability
                   FROM offensive_player_picks WHERE fixture_id = %s
                   ORDER BY created_at DESC""",
                (fixture_id,),
            )
            for category, label, mode, odd, prob in cur.fetchall():
                if category not in ("buteur", "passeur"):
                    continue
                key = f"pick_{category}"
                if key in item:
                    continue
                if mode == "cote" and odd:
                    item[key] = f"{label} (cote {float(odd):.2f})"
                else:
                    item[key] = f"{label} ({int(prob or 0)}%)"
        out.append(item)

    conn.close()
    return out


def main() -> None:
    target = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "programme.json",
    )
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixtures": fetch_programme(),
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[Programme] {len(data['fixtures'])} match(s) ecrit(s) dans {target}")


if __name__ == "__main__":
    main()
