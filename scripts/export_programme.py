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


# Sports actifs en prod (config.ACTIVE_SPORTS, valeurs "sport" exactes
# utilisees par daily_summary._save_programmed) qui alimentent
# programme_fixtures. tennis/wnba ont rejoint cette liste le 20/07/2026 --
# daily_summary.py::_get_tennis()/_get_wnba() alimentent desormais
# programme_fixtures comme les autres sports (avant cela, rien n'etait
# jamais persiste pour eux, cf ancien commentaire EXTRA_SPORTS ci-dessous).
# Le "football" garde son drapeau par ligue ; les autres ont une icone
# fixe par sport.
PROGRAMME_SPORTS = ("football", "baseball", "nba", "nhl", "nfl", "tennis", "wnba")
SPORT_ICON = {"baseball": "⚾", "nba": "🏀", "nhl": "🏒", "nfl": "🏈", "tennis": "🎾", "wnba": "🏀"}
SPORT_LABEL = {"football": "Football", "baseball": "Baseball (MLB)",
               "nba": "Basketball (NBA)", "nhl": "Hockey (NHL)", "nfl": "Football US (NFL)",
               "tennis": "Tennis", "wnba": "Basketball (WNBA)"}

# Historique (avant le 20/07/2026) : tennis/wnba etaient absents de
# PROGRAMME_SPORTS, donc fetch_tennis_wnba() etait le seul moyen de les
# afficher (picks deja publies aujourd'hui, sans compte a rebours). Ils sont
# maintenant dans PROGRAMME_SPORTS et beneficient du meme traitement "a
# venir" que les autres sports -- cette fonction reste en supplement
# (cle JSON "tennis_wnba" deja consommee par le front-end).
EXTRA_SPORTS = ("tennis", "wnba")

# Libelle FR par categorie de player pick, tous sports confondus (football:
# buteur/passeur/decisif : baseball/basket/hockey/NFL ont leurs propres
# categories, cf baseball/basketball/hockey/nfl/predictions.py).
CATEGORY_LABEL_FR = {
    "buteur": "Buteur", "passeur": "Passeur", "decisif": "Décisif",
    "home_run": "Home run", "runs": "Points marqués",
    "points": "Points", "rebounds": "Rebonds", "assists": "Passes décisives",
    "goal": "But", "assist": "Passe décisive", "point": "Point",
    "touchdown": "Touchdown",
}


def _flag(league: str) -> str:
    c = (league or "").lower()
    for key, flag in COMPETITION_FLAGS.items():
        if key in c:
            return flag
    return "⚽"


def _sport_icon(sport: str, league: str) -> str:
    return _flag(league) if sport == "football" else SPORT_ICON.get(sport, "🏅")


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


def _paris_date_of(value) -> str:
    """Date calendaire Paris (YYYY-MM-DD) d'un timestamp ISO quelconque,
    pour filtrer les picks tennis/wnba "publies aujourd'hui" (pas de fenetre
    8h pour ces sports, juste le jour civil de created_at)."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS_TZ)
    return dt.astimezone(PARIS_TZ).strftime("%Y-%m-%d")


# Codes raison "no bet" affichables publiquement, en francais. Les autres
# codes (quota API, doublons, filtres internes...) tombent sur le libelle
# generique : la transparence porte sur la decision sportive, pas sur la
# plomberie interne. NB: no_bet_logs.is_public_eligible existe mais n'est
# jamais renseigne a 1 en pratique -- cette liste blanche fait foi.
NO_BET_REASONS_FR = {
    "REASON_NO_VALID_PICK": "Aucun pick n'a passé les critères",
    "REASON_AFTER_T20_BLOCKED": "Compositions arrivées trop tard",
    "REASON_LINEUP_SOURCE_UNAVAILABLE": "Compositions officielles indisponibles",
    "REASON_NO_ODDS": "Pas de cote réelle disponible",
    "REASON_ODDS_TOO_LOW": "Cote dans une zone évitée",
    "REASON_NEGATIVE_EDGE": "Pas d'avantage statistique détecté",
    "REASON_VALUE_NOT_CONFIRMED": "Value non confirmée",
    "REASON_TOO_RISKY": "Profil de risque trop élevé",
    "REASON_PLAYER_STATS_UNAVAILABLE": "Statistiques joueurs indisponibles",
    "REASON_COVERAGE_STRICT_BLOCK": "Hors couverture vérifiée",
    "REASON_QUALIFYING_ROUND_EXCLUDED": "Tour de qualification exclu",
    "REASON_MARKET_UNAVAILABLE": "Marché indisponible chez les bookmakers",
    "REASON_DATA_TOO_OLD": "Données trop anciennes",
    "REASON_ANALYSIS_FAILED": "Analyse non aboutie",
}
NO_BET_GENERIC_FR = "Critères de publication non atteints"


def fetch_programme() -> list[dict]:
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()

    programme_date = _programme_date_today()
    placeholders_sport = ",".join(["%s"] * len(PROGRAMME_SPORTS))
    cur.execute(
        f"""
        SELECT fixture_id, home, away, league, kickoff_at, publish_status, sport
        FROM programme_fixtures
        WHERE programme_date = %s AND sport IN ({placeholders_sport})
        ORDER BY kickoff_at ASC
        LIMIT 300
        """,
        (programme_date, *PROGRAMME_SPORTS),
    )
    rows = cur.fetchall()

    # Coup du Jour : 1 pick/jour flague par le bot quand la confiance >= 85
    # (ai/coup_du_jour.py -> daily_flags, value = fixture_id).
    cur.execute(
        "SELECT value FROM daily_flags WHERE flag_date = %s AND flag_key = 'coup_du_jour'",
        (programme_date,),
    )
    coup_row = cur.fetchone()
    coup_fixture_id = str(coup_row[0]) if coup_row and coup_row[0] else None

    # Derniere raison no-bet par fixture du jour (la plus recente fait foi).
    no_bet_by_fixture: dict = {}
    fixture_ids = [str(r[0]) for r in rows]
    if fixture_ids:
        placeholders = ",".join(["%s"] * len(fixture_ids))
        cur.execute(
            f"""SELECT fixture_id, reason_code FROM no_bet_logs
                WHERE fixture_id IN ({placeholders})
                ORDER BY created_at ASC""",
            tuple(fixture_ids),
        )
        for fid, reason_code in cur.fetchall():
            no_bet_by_fixture[str(fid)] = reason_code  # dernier vu = plus recent

    out = []
    for fixture_id, home, away, league, kickoff_at, publish_status, sport in rows:
        item = {
            "flag": _sport_icon(sport, league),
            "league": league or "",
            "sport": sport or "football",
            "sport_label": SPORT_LABEL.get(sport, sport or "Football"),
            "match": f"{home} – {away}",
            "kickoff_at": kickoff_at,
            "published": publish_status == "published",
        }
        if coup_fixture_id and str(fixture_id) == coup_fixture_id:
            item["coup"] = True
        if publish_status != "published" and str(fixture_id) in no_bet_by_fixture:
            code = no_bet_by_fixture[str(fixture_id)]
            item["no_bet_reason"] = NO_BET_REASONS_FR.get(code, NO_BET_GENERIC_FR)
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
            player_picks = []
            seen_categories = set()
            for category, label, mode, odd, prob in cur.fetchall():
                if category in seen_categories:
                    continue
                seen_categories.add(category)
                detail = f"cote {float(odd):.2f}" if mode == "cote" and odd else f"{int(prob or 0)}%"
                player_picks.append({
                    "category": CATEGORY_LABEL_FR.get(category, (category or "Pick").replace("_", " ").capitalize()),
                    "label": label,
                    "detail": detail,
                })
                if len(player_picks) == 2:
                    break
            if not player_picks:
                # MLB/NBA/NHL/NFL/WNBA/Tennis (sport_player_picks) : offensive_
                # player_picks ne couvre que le football (buteur/passeur/decisif).
                # Ajoute le 20/07/2026 -- ces sports n'affichaient jamais leurs
                # player picks sur le site cote "a venir/publie".
                cur.execute(
                    """SELECT player_name, market_label, odd FROM sport_player_picks
                       WHERE fixture_id = %s ORDER BY created_at ASC LIMIT 2""",
                    (fixture_id,),
                )
                for player_name, label, odd in cur.fetchall():
                    player_picks.append({
                        "category": "Player pick",
                        "label": f"{player_name} — {label}" if player_name else label,
                        "detail": f"cote {float(odd):.2f}" if odd else "",
                    })
            if player_picks:
                item["player_picks"] = player_picks
        out.append(item)

    conn.close()
    return out


def fetch_tennis_wnba() -> list[dict]:
    """Picks tennis/wnba publies aujourd'hui (date civile Paris de
    created_at) : pas de compte a rebours possible, juste le pick + son
    resultat des qu'il est regle (cf commentaire EXTRA_SPORTS)."""
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT fixture_id, home, away, sport, conseil,
               COALESCE(NULLIF(cote_reelle,0), cote_interne),
               resultat, score, created_at
        FROM paris
        WHERE sport IN ('tennis','wnba')
        ORDER BY created_at DESC
        LIMIT 60
        """,
    )
    today_civil = datetime.now(PARIS_TZ).strftime("%Y-%m-%d")
    rows = [r for r in cur.fetchall() if _paris_date_of(r[8]) == today_civil]
    fixture_ids = [r[0] for r in rows]

    picks_by_fixture: dict = {}
    if fixture_ids:
        placeholders = ",".join(["%s"] * len(fixture_ids))
        cur.execute(
            f"""SELECT fixture_id, player_name, market_label FROM sport_player_picks
                WHERE fixture_id IN ({placeholders})
                ORDER BY created_at ASC""",
            tuple(fixture_ids),
        )
        for fid, player_name, market_label in cur.fetchall():
            text = f"{player_name} — {market_label}" if player_name else market_label
            picks_by_fixture.setdefault(fid, []).append(text)
    conn.close()

    out = []
    for fixture_id, home, away, sport, conseil, cote, resultat, score, created_at in rows:
        item = {
            "flag": SPORT_ICON.get(sport, "🏅"),
            "sport": sport,
            "sport_label": SPORT_LABEL.get(sport, (sport or "Sport").capitalize()),
            "match": f"{home} – {away}",
            "published_at": created_at,
        }
        if conseil:
            item["conseil"] = _short_pick(conseil)
            item["conseil_cote"] = round(float(cote or 0), 2)
        picks = picks_by_fixture.get(fixture_id)
        if picks:
            item["player_pick_text"] = " · ".join(picks[:2])
        if (resultat or "").upper() in ("GAGNE", "PERDU", "REMBOURSE"):
            item["result"] = resultat.upper()
            if score:
                item["score"] = score
        out.append(item)

    out.reverse()  # chronologique (plus ancien -> plus recent)
    return out


def main() -> None:
    target = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "programme.json",
    )
    tennis_wnba = fetch_tennis_wnba()
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixtures": fetch_programme(),
        "tennis_wnba": tennis_wnba,
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[Programme] {len(data['fixtures'])} match(s) + {len(tennis_wnba)} pick(s) tennis/wnba ecrits dans {target}")


if __name__ == "__main__":
    main()
