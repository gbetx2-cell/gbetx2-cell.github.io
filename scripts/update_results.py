# -*- coding: utf-8 -*-
"""
Regenere le bloc `const RESULTATS = [...]` de site/index.html depuis les
vrais conseils regles en production (audit du 12/07/2026 : le bloc etait
code en dur avec des donnees de demonstration, perimees des le lancement).

Usage :
    DATABASE_URL=postgresql://... python scripts/export_site_results.py [chemin/index.html]

Par defaut, met a jour site/index.html du repo courant. Pour publier :
relancer sur le clone du repo public gbetx2-cell.github.io puis push.

Auto-synchronise vers scripts/update_results.py sur le repo public a chaque
push touchant ce fichier (cf .github/workflows/sync-site-public.yml,
26/07/2026) -- plus besoin de relancer manuellement sur un clone. Les crons
publics update-results.yml/update-programme.yml sont eux-memes redeclenches
automatiquement juste apres, sequentiellement (fix collision 26/07/2026).
"""
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

N_MATCHES = 80  # matchs regles (chacun peut donner jusqu'a 3 entrees : conseil/value/player pick cote)
# 80 au lieu de 20 (30/07/2026, point 3 pagination) : alimente le "Voir plus"
# cote client (site/index.html), qui affiche par defaut les 20 derniers et
# etend en arriere dans l'historique deja charge, sans nouvel appel serveur.
BASE_UNIT_EUR = 200  # doit rester synchro avec ai/staking.py BASE_UNIT_EUR
PARIS_TZ = ZoneInfo("Europe/Paris")

# Bankroll de depart affichee sur le site (points F/G du backlog, 21/07/2026 --
# choix utilisateur, pas une valeur reelle geree en base : il n'existe pas de
# ledger bankroll separe, la bankroll = ce montant + la somme cumulee des pnl
# reels de `paris` depuis le tout premier pari regle).
BANKROLL_INITIAL_EUR = 10000

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


# Icone par sport (23/07/2026, confirme en direct sur le site public) :
# _flag() ne sait matcher que des noms de competition FOOTBALL et retombe
# sur "⚽" par defaut -- tennis/baseball/etc n'ont pas de competition dans
# COMPETITION_FLAGS, donc affichaient TOUJOURS le ballon de foot. Priorite
# a l'icone sport pour tout ce qui n'est pas football.
SPORT_ICON = {"baseball": "⚾", "nba": "🏀", "nhl": "🏒", "nfl": "🏈",
              "tennis": "🎾", "wnba": "🏀"}

# Sports ou value_bet est le MEME pari que "conseil" (jamais une 2e mise
# independante comme en football) -- doit rester synchro avec
# betting_rules.SPORTS_VALUE_BET_IS_CONSEIL. Sans ce filtre, fetch_results()
# affichait chaque pick de ces sports DEUX FOIS ("Conseil" + "Value bet"
# identiques, confirme en direct sur le site public le 23/07/2026).
#
# Copie locale VOLONTAIRE, pas un import (26/07/2026) : ce fichier est aussi
# synchronise tel quel vers scripts/update_results.py sur le repo public
# (cf .github/workflows/sync-site-public.yml), execute la-bas de facon
# totalement autonome par son propre cron GitHub Actions, sans acces au
# reste de ce repo prive -- un `from betting_rules import ...` y crasherait.
# Si cette liste change un jour, la mettre a jour ICI ET dans betting_rules.py.
# "mlb" ajoute le 29/07/2026 (meme bug/fix que betting_rules.py -- paris.sport
# vaut "baseball" mais sport_player_picks.sport vaut "mlb" pour le meme sport).
SPORTS_VALUE_BET_IS_CONSEIL = {"tennis", "nba", "nhl", "baseball", "mlb", "wnba", "nfl"}


def _flag(competition: str, sport: str = "") -> str:
    icon = SPORT_ICON.get((sport or "").lower())
    if icon:
        return icon
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
          AND NOT (market_type IN ('total_points', 'player_pick_only'))
        ORDER BY result_updated_at DESC
        LIMIT 1000
        """,
    )
    rows = cur.fetchall()

    # Player picks (26/07/2026, confirme en direct : "AUJOURD'HUI" affichait
    # "Aucun conseil regle" malgre de vrais gains tennis du jour -- le pnl du
    # "conseil" est fige a 0 pour le tennis (cf database.py::update_resultat,
    # _HORS_PNL), le vrai pnl vient des player picks, jamais lus ici avant ce
    # fix. Meme principe que fetch_perf_stats()/fetch_bankroll() plus bas.
    cur.execute(
        """
        SELECT odd, COALESCE(stake_eur,0), settlement_status,
               COALESCE(NULLIF(settled_at,''), created_at)
        FROM sport_player_picks
        WHERE settlement_status IN ('GAGNE','PERDU')
        """,
    )
    pick_rows = cur.fetchall()
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

    for odd, stake_eur, status, settled_or_created in pick_rows:
        d = _paris_calendar_date(settled_or_created)
        if d is None or d > today:
            continue
        pnl_val = _pnl_fixed(status, float(odd or 0), float(stake_eur or 0))
        for key, start in boundaries.items():
            if d < start:
                continue
            b = buckets[key]
            b["n"] += 1
            b["pnl_eur"] += pnl_val
            if status == "GAGNE":
                b["g"] += 1
            elif status == "PERDU":
                b["p"] += 1

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
          AND NOT (market_type IN ('total_points', 'player_pick_only'))
        ORDER BY result_updated_at DESC
        LIMIT 5000
        """,
    )
    rows = cur.fetchall()

    # Player picks (26/07/2026) : meme principe que fetch_period_stats()
    # ci-dessus -- sans ca, la courbe "Evolution du bilan" ignorait tout le
    # PnL tennis (fige a 0 cote conseil, reel uniquement cote player picks).
    cur.execute(
        """
        SELECT odd, COALESCE(stake_eur,0), settlement_status,
               COALESCE(NULLIF(settled_at,''), created_at)
        FROM sport_player_picks
        WHERE settlement_status IN ('GAGNE','PERDU')
        """,
    )
    pick_rows = cur.fetchall()
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

    def _bucket_pnl(pnl_eur, dt):
        d = dt.date()
        pnl_u = pnl_eur / BASE_UNIT_EUR
        if d == today:
            heures[dt.hour] += pnl_u
        if week_start <= d <= today:
            semaine[d.weekday()] += pnl_u
        if month_start <= d <= today:
            mois[d.day - 1] += pnl_u
        if year_start <= d <= today:
            annee[d.month - 1] += pnl_u

    for pnl, result_updated_at in rows:
        dt = _paris_datetime(result_updated_at)
        if dt is None or dt.date() > today:
            continue
        _bucket_pnl(float(pnl or 0), dt)

    for odd, stake_eur, status, settled_or_created in pick_rows:
        dt = _paris_datetime(settled_or_created)
        if dt is None or dt.date() > today:
            continue
        _bucket_pnl(_pnl_fixed(status, float(odd or 0), float(stake_eur or 0)), dt)

    # Troncature aux buckets futurs (30/07/2026, audit demande explicite) :
    # les tableaux heures/semaine/mois/annee ci-dessus contiennent toujours
    # 24/7/N/12 cases (les cases futures restent a 0.0), mais on ne doit
    # jamais tracer de cumul au-dela de l'instant present -- sinon la
    # courbe "avance" a plat jusqu'a la fin de l'axe (bug confirme en
    # capture : ligne plate de 12h31 a 23h alors qu'aucune donnee n'existe
    # encore pour l'apres-midi). now_idx = index du dernier bucket qui a
    # deja commence (heure en cours, jour de semaine en cours, etc.).
    now_idx_jour = now.hour
    now_idx_semaine = today.weekday()
    now_idx_mois = today.day - 1
    now_idx_annee = today.month - 1

    def cumulative_points(values, labels, now_idx):
        points, running = [], 0.0
        for i, (v, label) in enumerate(zip(values, labels)):
            if i > now_idx:
                break  # bucket futur, pas encore commence -- jamais trace
            running += v
            points.append({"label": label, "pnl": round(running, 2)})
        return points

    # now_frac : fraction exacte (Europe/Paris, jamais l'heure serveur
    # brute -- meme correctif que la fenetre programme du 30/07/2026) de la
    # periode ecoulee jusqu'a maintenant. Sert cote client a positionner le
    # DERNIER point exactement a l'instant present sur l'axe fixe (00h-24h,
    # Lun-Dim, 1er-dernier jour du mois, Jan-Dec), au lieu de l'accrocher a
    # la graduation la plus proche. A minuit pile (now_frac=0.0 pour jour),
    # le point se positionne en tout debut d'axe avec un cumul reparti a 0
    # (nouvelle journee, tableaux heures/etc. deja reinitialises ci-dessus) :
    # aucune transition bizarre, juste un nouvel axe qui commence a vide.
    seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
    now_frac_jour = seconds_of_day / 86400
    days_into_week = (today - week_start).days
    now_frac_semaine = (days_into_week + seconds_of_day / 86400) / 7
    now_frac_mois = ((today.day - 1) + seconds_of_day / 86400) / n_days_month
    days_in_year = 366 if calendar.isleap(today.year) else 365
    day_of_year = (today - year_start).days
    now_frac_annee = (day_of_year + seconds_of_day / 86400) / days_in_year

    return {
        "jour": cumulative_points(heures, [f"{h:02d}h" for h in range(24)], now_idx_jour),
        "semaine": cumulative_points(semaine, JOURS_FR, now_idx_semaine),
        "mois": cumulative_points(mois, [str(i + 1) for i in range(n_days_month)], now_idx_mois),
        "annee": cumulative_points(annee, MOIS_FR, now_idx_annee),
        "now_frac": {
            "jour": round(now_frac_jour, 6),
            "semaine": round(now_frac_semaine, 6),
            "mois": round(now_frac_mois, 6),
            "annee": round(now_frac_annee, 6),
        },
        "total_buckets": {"jour": 24, "semaine": 7, "mois": n_days_month, "annee": 12},
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


# Copie locale VOLONTAIRE de betting_rules.pnl_fixed, memes raisons que
# SPORTS_VALUE_BET_IS_CONSEIL plus haut (fichier synchronise standalone vers
# le repo public, pas d'import possible).
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
               COALESCE(NULLIF(p.competition,''), pf.league, ''),
               p.market_type, p.sport
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
            OR EXISTS (
              SELECT 1 FROM sport_player_picks sp
              WHERE sp.fixture_id = p.fixture_id AND sp.settlement_status IN ('GAGNE','PERDU')
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

        cur.execute(
            f"""SELECT fixture_id, player_name, market_label, odd, stake_eur, settlement_status
                FROM sport_player_picks
                WHERE fixture_id IN ({placeholders}) AND settlement_status IN ('GAGNE','PERDU')
                ORDER BY fixture_id""",
            tuple(fixture_ids),
        )
        sport_picks_by_fixture: dict = {}
        for fid, player_name, market_label, odd, stake, status in cur.fetchall():
            sport_picks_by_fixture.setdefault(str(fid), []).append({
                "label": f"{player_name} — {market_label}", "cote": float(odd or 0),
                "stake": float(stake or 0), "result": status,
            })
    else:
        sport_picks_by_fixture = {}
    conn.close()

    out = []
    for fixture_id, home, away, conseil, cote, resultat, mise, pnl, \
            value_bet, value_cote, value_result, value_stake, competition, market_type, sport \
            in reversed(fixtures):
        fixture_id = str(fixture_id)
        flag = _flag(competition, sport)
        match = f"{home} – {away}"
        sport_l = (sport or "").lower()

        # market_type IN (total_points, player_pick_only) (23/07/2026) :
        # ce "conseil" est en realite le mirroir d'un player pick (aucun
        # value bet publie sur ce match), deja affiche separement plus bas
        # via sport_picks_by_fixture -- l'inclure ici aussi doublait
        # l'affichage du MEME pari (meme diagnostic que daily_bilan.py::
        # _is_pure_value_row, applique ici au mirroir player pick).
        #
        # sport_l in SPORTS_VALUE_BET_IS_CONSEIL (23/07/2026, confirme en
        # direct sur le site public) : pour ces sports, value_bet decrit le
        # MEME pari que "conseil" (jamais une 2e mise independante comme en
        # football, cf results_tracker.py::_send_result_msg). Sans ce garde,
        # chaque pick tennis/MLB/etc avec un value bet apparaissait DEUX FOIS
        # dans "Derniers picks" (une fois "Conseil", une fois "Value bet",
        # memes match/cote/resultat) -- le bloc value ci-dessous suffit deja.
        if (conseil and resultat in ("GAGNE", "PERDU", "REMBOURSE")
                and market_type not in ("total_points", "player_pick_only")
                and not (sport_l in SPORTS_VALUE_BET_IS_CONSEIL and value_bet)):
            # paris.mise/paris.pnl sont stockes en EUROS en base (mise =
            # advice_stake.stake_eur, cf football/predictions.py).
            out.append({
                "flag": flag, "match": match, "pick": _short_pick(conseil),
                "cote": round(float(cote or 0), 2),
                "r": {"GAGNE": "G", "PERDU": "P"}.get(resultat, "R"),
                "mise": round(float(mise or BASE_UNIT_EUR) / BASE_UNIT_EUR, 2),
                "pnl": round(float(pnl or 0) / BASE_UNIT_EUR, 2),
                "type": "conseil", "sport": sport_l,
            })

        # REMBOURSE ajoute (26/07/2026, confirme en direct : Lorenzo Musetti
        # vs Matteo Arnaldi, rembourse, invisible partout -- le bloc conseil
        # est saute pour les sports mirroir (dedup, cf plus haut), et ce
        # bloc value ne prenait que GAGNE/PERDU, jamais REMBOURSE. Un match
        # tennis rembourse avec value bet devenait invisible sur les deux
        # blocs a la fois.
        if value_bet and value_result in ("GAGNE", "PERDU", "REMBOURSE"):
            v_pnl = _pnl_fixed(value_result, value_cote, value_stake)
            out.append({
                "flag": flag, "match": match, "pick": _short_pick(value_bet),
                "cote": round(float(value_cote or 0), 2),
                "r": {"GAGNE": "G", "PERDU": "P"}.get(value_result, "R"),
                "mise": round(float(value_stake or BASE_UNIT_EUR) / BASE_UNIT_EUR, 2),
                "pnl": round(v_pnl / BASE_UNIT_EUR, 2),
                "type": "value", "sport": sport_l,
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
                    "type": "player", "sport": sport_l,
                })

        # Player picks MLB/NBA/WNBA/NHL/NFL/Tennis (sport_player_picks) --
        # meme principe que le player pick football ci-dessus, mais 0 a 3
        # entrees possibles par match (pas de plafond a 1 comme buteur/
        # passeur football, cf commit 3b1f35b/results_tracker settlement).
        for sp in sport_picks_by_fixture.get(fixture_id, []):
            p_pnl = _pnl_fixed(sp["result"], sp["cote"], sp["stake"])
            out.append({
                "flag": flag, "match": match, "pick": sp["label"],
                "cote": round(sp["cote"], 2),
                "r": {"GAGNE": "G", "PERDU": "P"}.get(sp["result"], "R"),
                "mise": round(sp["stake"] / BASE_UNIT_EUR, 2),
                "pnl": round(p_pnl / BASE_UNIT_EUR, 2),
                "type": "player", "sport": sport_l,
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
    "total_points": "Buts (over/under)",
    "both_teams_to_score": "Les deux marquent",
    "handicap": "Handicap",
    "scorer": "Buteur",
    "assist": "Passeur",
    "player_pick_only": "Pronostic joueur",
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
    # Exclut les lignes baseball "3 picks bundles" (market_type='total_points',
    # conseil = texte du meilleur edge parmi jusqu'a 3 player picks) -- remplacees
    # plus bas par TOUTES les lignes sport_player_picks correspondantes, pour ne
    # compter chaque pick individuel qu'une seule fois (21/07/2026, architecture
    # "3 picks bundles" MLB, option B : pas de changement de schema paris).
    cur.execute(
        """
        SELECT sport, market_type,
               COALESCE(NULLIF(cote_reelle,0), cote_interne),
               resultat, COALESCE(mise,0), COALESCE(pnl,0), result_updated_at
        FROM paris
        WHERE resultat IN ('GAGNE','PERDU','REMBOURSE')
          AND result_updated_at IS NOT NULL AND result_updated_at <> ''
          AND NOT (market_type IN ('total_points', 'player_pick_only'))
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

    # ── Player picks individuels (sport_player_picks) : remplace les lignes
    # paris exclues ci-dessus (market_type total_points/player_pick_only) par
    # les picks reellement bundles (jusqu'a 3 par ligne paris pour le
    # baseball, tous visibles ici au lieu du seul meilleur edge). Jamais les
    # deux sources a la fois pour le meme pick.
    # Generalise le 23/07/2026 (etait code en dur sport='mlb' -- tennis (37
    # picks regles) et WNBA (7) etaient donc invisibles des stats perf/
    # classement du site, alors que fetch_results() (liste brute) les
    # affichait deja correctement. Meme diagnostic que daily_bilan.py::
    # _is_pure_player_pick_row, applique ici cote site.
    SPORT_LABEL_MAP = {"mlb": "baseball"}
    MARKET_TYPE_FOR_SPORT = {"baseball": "total_points", "wnba": "total_points"}
    cur.execute(
        """
        SELECT sport, market_label, odd, COALESCE(stake_eur,0), settlement_status
        FROM sport_player_picks
        WHERE settlement_status IN ('GAGNE','PERDU')
        """,
    )
    for sp_raw, market_label, odd, stake_eur, status in cur.fetchall():
        sp = SPORT_LABEL_MAP.get(sp_raw, sp_raw)
        mt = MARKET_TYPE_FOR_SPORT.get(sp, "player_pick_only")
        won = status == "GAGNE"
        lost = status == "PERDU"
        odd = float(odd or 0)
        stake_eur = float(stake_eur or 0)
        pnl_pick = _pnl_fixed(status, odd, stake_eur)

        g["n"] += 1
        g["w"] += won
        g["l"] += lost
        g["stake"] += stake_eur
        g["pnl"] += pnl_pick

        s = sports.setdefault(sp, {"n": 0, "w": 0, "l": 0, "stake": 0.0, "pnl": 0.0})
        s["n"] += 1
        s["w"] += won
        s["l"] += lost
        s["stake"] += stake_eur
        s["pnl"] += pnl_pick

        for lo, hi, label in ODDS_BANDS:
            if lo <= odd < hi:
                key = (mt, label)
                m = markets.setdefault(key, {"n": 0, "w": 0, "l": 0, "pnl": 0.0,
                                             "blocked": _is_blocked(mt, (lo + min(hi, 9.0)) / 2)})
                m["n"] += 1
                m["w"] += won
                m["l"] += lost
                m["pnl"] += pnl_pick
                break

    # ── Highlights du mois (meilleur/pire pick, top ligue) ──
    cur.execute(
        """
        SELECT p.home, p.away, p.conseil,
               COALESCE(NULLIF(p.cote_reelle,0), p.cote_interne),
               COALESCE(p.pnl,0), COALESCE(NULLIF(p.competition,''), pf.league, ''),
               p.result_updated_at, p.sport
        FROM paris p
        LEFT JOIN programme_fixtures pf ON pf.fixture_id = p.fixture_id
        WHERE p.resultat IN ('GAGNE','PERDU')
          AND p.conseil IS NOT NULL AND p.conseil <> ''
          AND p.result_updated_at IS NOT NULL AND p.result_updated_at <> ''
        """,
    )
    best = worst = None
    leagues: dict = {}
    for home, away, conseil, cote, pnl, competition, rud, sport in cur.fetchall():
        d = _paris_calendar_date(rud)
        if d is None or not (month_start <= d <= today):
            continue
        pnl = float(pnl or 0)
        entry = {
            "match": f"{home} – {away}", "pick": _short_pick(conseil),
            "cote": round(float(cote or 0), 2), "pnl": round(pnl / BASE_UNIT_EUR, 2),
            "flag": _flag(competition, sport), "league": competition or "",
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
        "bankroll": fetch_bankroll(),
    }


def fetch_bankroll() -> dict:
    """Bankroll = BANKROLL_INITIAL_EUR + somme cumulee des pnl reels regles
    (paris.pnl + sport_player_picks, en EUR), du plus ancien pari regle au
    plus recent -- pas de table dediee, on derive tout de la meme source que
    fetch_perf_stats.

    Generalise le 23/07/2026 : ne lisait que paris.pnl, qui exclut ou
    sous-compte les player picks (pnl fige a 0 pour tennis -- cf
    database.py::update_resultat, _HORS_PNL -- et un seul pick sur 3
    represente pour le "bundle" baseball). La bankroll affichee au public
    etait donc fausse pour tout sport avec player picks, tennis en tete
    (son PNL reel provient presque entierement des player picks)."""
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
          AND NOT (market_type IN ('total_points', 'player_pick_only'))
        """,
    )
    rows = cur.fetchall()

    # COALESCE(settled_at, created_at) : settled_at n'a jamais ete retrofit
    # sur l'historique (cf database.py::update_sport_player_pick_settlement,
    # ajoute le 21/07/2026) -- un filtre strict sur settled_at fait
    # silencieusement disparaitre 20 des 37 picks tennis regles (surtout des
    # gains, +2962EUR ignores) au lieu de les dater approximativement.
    cur.execute(
        """
        SELECT odd, COALESCE(stake_eur,0), settlement_status,
               COALESCE(NULLIF(settled_at,''), created_at)
        FROM sport_player_picks
        WHERE settlement_status IN ('GAGNE','PERDU')
        """,
    )
    pick_rows = cur.fetchall()
    conn.close()

    daily: dict = {}
    for pnl, rud in rows:
        d = _paris_calendar_date(rud)
        if d is None:
            continue
        daily[d] = daily.get(d, 0.0) + float(pnl or 0)
    for odd, stake_eur, status, settled_or_created in pick_rows:
        d = _paris_calendar_date(settled_or_created)
        if d is None:
            continue
        pnl_pick = _pnl_fixed(status, float(odd or 0), float(stake_eur or 0))
        daily[d] = daily.get(d, 0.0) + pnl_pick

    series = []
    running = float(BANKROLL_INITIAL_EUR)
    for d in sorted(daily):
        running += daily[d]
        series.append({"date": d.isoformat(), "value": round(running, 2)})

    current = round(running, 2)
    pnl_total = round(current - BANKROLL_INITIAL_EUR, 2)
    pct = round(pnl_total / BANKROLL_INITIAL_EUR * 100, 2) if BANKROLL_INITIAL_EUR else 0
    return {
        "initial": BANKROLL_INITIAL_EUR,
        "current": current,
        "pnl": pnl_total,
        "pct": pct,
        "series": series,
    }


def render_perf_block(perf: dict) -> str:
    import json
    return "const PERF_STATS = " + json.dumps(perf, ensure_ascii=False) + ";"


def render_block(results: list[dict]) -> str:
    lines = ["const RESULTATS = ["]
    for r in results:
        match = r["match"].replace('"', "'")
        pick = r["pick"].replace('"', "'")
        sport = r.get("sport", "")
        lines.append(
            f'  {{flag:"{r["flag"]}", match:"{match}", pick:"{pick}", '
            f'cote:{r["cote"]:.2f}, r:"{r["r"]}", mise:{r["mise"]:.2f}, pnl:{r["pnl"]:.2f}, '
            f'type:"{r["type"]}", sport:"{sport}"}},'
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

    def num_dict(d):
        items = ", ".join(f"{key}:{value}" for key, value in d.items())
        return f"{{{items}}}"

    # now_frac/total_buckets (30/07/2026) : dicts de nombres (fraction de
    # periode ecoulee, taille d'axe fixe), pas des listes de points -- format
    # different de jour/semaine/mois/annee, gere separement ici.
    parts = []
    for key, value in series.items():
        if key in ("now_frac", "total_buckets"):
            parts.append(f"{key}:{num_dict(value)}")
        else:
            parts.append(f"{key}:{pts(value)}")
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
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "index.html",
    )
    update_html(target, fetch_results(), fetch_period_stats(),
                fetch_period_series(), fetch_perf_stats())
