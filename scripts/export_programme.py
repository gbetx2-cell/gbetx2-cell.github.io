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

Note (27/07/2026) : le cron GitHub Actions ("*/10 * * * *") est declenche de
facon tres irreguliere en pratique sur ce repo (ecarts constates de 80 a
100+ min) -- limitation connue de la plateforme sur les workflows planifies
a faible activite, pas un bug de ce script. sync-site-public.yml redeclenche
desormais ce workflow immediatement apres chaque sync (cf ce fichier cote
prive) pour limiter l'impact. Un echec ponctuel de connexion DB (transitoire,
confirme non-reproductible en test direct le 27/07/2026) reste possible --
le prochain declenchement (auto ou cron naturel) reessaie normalement.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")
UTC = timezone.utc

# COMP_WINDOWS dupliqué depuis ai/comp_windows.py (30/07/2026, bug confirmé en
# prod : import top-level "from ai.comp_windows import COMP_WINDOWS" cassait
# TOUTE exécution du script côté repo public -- le module ai/ n'existe que
# côté repo privé, jamais copié par sync-site-public.yml. Résultat : le cron
# update-programme.yml échouait à 100% depuis ~11h29 UTC (confirmé via l'API
# GitHub Actions), programme.json restait fige sur les données de 09h22 UTC
# pendant que tous les fixs suivants de la journée (garde-fou TBD, texte
# no-bet, cache RapidAPI, graphique bilan, filtre programme_date) se
# propageaient bien en code source mais jamais en donnees reelles. Même
# raison que _get_programme_window_sql_where() ci-dessous (déjà embarquée
# le même jour pour éviter ce piège) -- gardé synchronisé manuellement avec
# la source de vérité ai/comp_windows.py.
COMP_WINDOWS: dict[str, tuple[int, int]] = {
    "football": (5, 30),
    "tennis": (30, 45),
    "nba": (30, 45),
    "nhl": (30, 45),
    "baseball": (30, 45),
    "nfl": (30, 90),
    "wnba": (30, 45),
    "f1": (15, 180),
}


def _get_programme_window_sql_where(days_back: int = 0) -> tuple[str, tuple]:
    """
    Retourne la clause WHERE et les paramètres pour SQL (fenêtre J 08h-J+1 07h59).

    Fenêtre J 08h00 Paris → J+1 07h59:59 Paris = J 06h00 UTC → J+1 05h59:59 UTC.
    Embarqué ici (pas d'import utils/) pour compatibilité repo public sans dépendances.

    days_back (02/09/2026, demande explicite : "corrige la fenetre pour que
    ca reste visible" -- bug confirme en direct : les resultats MLB de la
    veille au soir (kickoff US = nuit cote Paris) disparaissaient de la page
    Publications des que la fenetre roulait a 08h Paris, alors qu'ils
    restaient corrects en base) : recule uniquement le DEBUT de la fenetre
    de N jours supplementaires, sans toucher la fin (day_start_paris+1j
    07h59) -- utilise par fetch_publications() (days_back=1, fenetre 48h)
    pour garder un match regle visible toute la journee suivant son
    reglement, sans elargir programme.html (days_back=0 par defaut, jamais
    touche -- page "programme du jour", volontairement etroite, cf
    commentaire "nettoyage retrospectif" plus haut).

    Returns:
        (where_clause, params_tuple) pour utilisation dans cur.execute()
    """
    now_paris = datetime.now(PARIS_TZ)

    # Bug corrige le 05/08/2026 (confirme en direct : 3 publications MLB
    # fraiches de 00h05-00h10 absentes de publications.json, ET tout le
    # reste de la journee deja publiee aussi disparu -- live:0, done:0).
    # Entre minuit et 08h00 Paris, "now_paris.replace(hour=8)" tombe dans
    # le FUTUR (aujourd'hui 8h, alors qu'on est avant), decalant toute la
    # fenetre en avant (aujourd'hui 8h -> demain 8h) au lieu de rester
    # ancree sur le jour programme en cours (hier 8h -> aujourd'hui 8h).
    # Meme garde que _programme_date_today() (deja correcte), jamais
    # appliquee ici avant ce fix.
    day_start_paris = now_paris.replace(hour=8, minute=0, second=0, microsecond=0)
    if now_paris < day_start_paris and (day_start_paris - now_paris).total_seconds() > 300:
        day_start_paris -= timedelta(days=1)

    # Bornes en heure Paris
    window_start_paris = day_start_paris - timedelta(days=days_back)
    window_end_paris = (day_start_paris + timedelta(days=1)).replace(
        hour=7, minute=59, second=59, microsecond=999999
    )

    # Conversion en UTC
    window_start_utc = window_start_paris.astimezone(UTC)
    window_end_utc = window_end_paris.astimezone(UTC)

    # Format ISO pour comparaison SQL
    start_iso = window_start_utc.isoformat()
    end_iso = window_end_utc.isoformat()

    where_clause = "kickoff_at::timestamp BETWEEN %s AND %s"
    params = (start_iso, end_iso)

    return where_clause, params

# Duplique depuis tg_bot/league_flags.py::LEAGUE_FLAG_EMOJI (23/08/2026,
# demande explicite : "remet le drapeaux de la ligue pour chaque
# publication" -- COMPETITION_FLAGS ci-dessous, base sur une simple
# recherche de sous-chaine dans le NOM de la ligue, ne couvrait aucune
# grande ligue domestique (Premier League, La Liga, Bundesliga, Ligue 1,
# Serie A italienne...) -- tout match sur ces ligues retombait sur le
# drapeau ballon generique "⚽", qui semble absent au client. Meme raison
# de duplication que COMP_WINDOWS/REFONTE_MARKET_LABELS plus haut : ce
# fichier tourne cote repo PUBLIC (sync-site-public.yml), tg_bot/ n'existe
# que cote repo prive. Cle = league_id (deja disponible sur chaque
# fixture), beaucoup plus fiable que le matching par nom.
LEAGUE_FLAG_EMOJI: dict[int, str] = {
    1:   "🌍", 6:   "🌍", 2:   "🇪🇺", 3:   "🇪🇺", 848: "🇪🇺", 4:   "🇪🇺",
    960: "🇪🇺", 531: "🇪🇺", 15:  "🌐", 13:  "🌎", 14:  "🌎", 12:  "🌍",
    39:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 40:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 41:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 42:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 45:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 48:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    61:  "🇫🇷", 62:  "🇫🇷", 63:  "🇫🇷", 66:  "🇫🇷", 65:  "🇫🇷",
    140: "🇪🇸", 141: "🇪🇸", 143: "🇪🇸", 142: "🇪🇸",
    78:  "🇩🇪", 79:  "🇩🇪", 80:  "🇩🇪", 81:  "🇩🇪",
    135: "🇮🇹", 136: "🇮🇹", 137: "🇮🇹", 547: "🇮🇹",
    94:  "🇵🇹", 96:  "🇵🇹", 97:  "🇵🇹",
    88:  "🇳🇱", 89:  "🇳🇱", 90:  "🇳🇱",
    144: "🇧🇪", 145: "🇧🇪",
    203: "🇹🇷", 204: "🇹🇷", 205: "🇹🇷",
    235: "🇷🇺",
    179: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    197: "🇬🇷",
    333: "🇺🇦",
    218: "🇦🇹",
    207: "🇨🇭",
    119: "🇩🇰",
    113: "🇸🇪",
    103: "🇳🇴",
    244: "🇫🇮",
    106: "🇵🇱",
    345: "🇨🇿",
    210: "🇭🇷",
    286: "🇷🇸",
    283: "🇷🇴",
    307: "🇸🇦",
    71:  "🇧🇷", 72:  "🇧🇷", 73:  "🇧🇷",
    128: "🇦🇷", 130: "🇦🇷", 131: "🇦🇷",
    265: "🇨🇱",
    239: "🇨🇴",
    268: "🇺🇾",
    281: "🇵🇪",
    240: "🇨🇴",
    242: "🇵🇾",
    243: "🇪🇨",
    241: "🇨🇴",
    253: "🇺🇸", 254: "🇺🇸",
    261: "🇨🇦",
    262: "🇲🇽", 263: "🇲🇽",
    98:  "🇯🇵", 99:  "🇯🇵",
    292: "🇰🇷", 293: "🇰🇷",
    169: "🇨🇳",
    188: "🇦🇺",
    288: "🇿🇦",
    200: "🇲🇦",
    298: "🇹🇭",
    202: "🇹🇳",
    233: "🇪🇬",
    570: "🇬🇭",
    387: "🇯🇴",
    290: "🇮🇷",
    323: "🇮🇳",
    909: "🇺🇸", 5:   "🇪🇺", 8:   "🌍", 9:   "🌎", 11:  "🌎", 16:  "🌎",
    17:  "🌏", 20:  "🌍", 22:  "🌎", 44:  "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 64:  "🇫🇷", 75:  "🇧🇷",
    82:  "🇩🇪", 95:  "🇵🇹", 114: "🇸🇪", 116: "🇧🇾", 147: "🇧🇪", 164: "🇮🇸",
    186: "🇩🇿", 206: "🇹🇷", 250: "🇵🇾", 296: "🇹🇭", 299: "🇻🇪", 301: "🇦🇪",
    327: "🇬🇪", 329: "🇪🇪", 344: "🇧🇴", 362: "🇱🇹", 365: "🇱🇻", 367: "🇫🇴",
    403: "🇸🇳", 475: "🇧🇷", 479: "🇨🇦", 528: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 624: "🇧🇷", 1032: "🇦🇷",
    357: "🇮🇪",
}

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
# programme_fixtures comme les autres sports.
# Le "football" garde son drapeau par ligue ; les autres ont une icone
# fixe par sport.
PROGRAMME_SPORTS = ("football", "baseball", "nba", "nhl", "nfl", "tennis", "wnba")
SPORT_ICON = {"baseball": "⚾", "nba": "🏀", "nhl": "🏒", "nfl": "🏈", "tennis": "🎾", "wnba": "🏀"}

# Sports ou paris.conseil n'est jamais une info independante : c'est soit un
# mirroir du value bet ("Victoire X"), soit un mirroir du player pick ("Total
# sets..."), jamais un 3e pari distinct (cf daily_bilan.py::
# SPORTS_VALUE_BET_IS_CONSEIL, meme diagnostic 22/07/2026). Afficher item
# "conseil" en plus de value_bet/player_picks pour ces sports produisait un
# doublon (meme info sous 2 etiquettes) ou pire, un player pick affiche a
# tort sous le libelle "Conseil" quand aucun value bet n'avait passe les
# criteres -- signale par l'utilisateur comme peu clair cote client.
SPORTS_CONSEIL_IS_MIRROR = {"nba", "nhl", "baseball", "wnba", "nfl"}

# "tennis" retire de SPORTS_CONSEIL_IS_MIRROR le 22/08/2026 (bug confirme
# en production, demande explicite : "le tennis des fois ne montre pas
# notre pronostic au client sur le site"). L'hypothese "conseil == mirroir
# du value bet" est FAUSSE pour tennis : tennis/predictions.py stocke
# value_bet_txt UNIQUEMENT pour un edge "Total sets" (marche distinct,
# souvent absent), jamais pour le pick vainqueur principal (pick, stocke
# dans conseil avec market_type="winner"). Supprimer "conseil" faisait
# donc disparaitre le SEUL pick reellement publie sur Telegram des que ce
# match n'avait ni edge Total sets ni player pick -- rien n'etait alors
# affiche au client alors qu'un vrai pick existait. Les autres sports de
# cette liste n'ont pas ete reverifies -- limiter le changement a tennis,
# seul sport dont la fausse hypothese a ete confirmee ce jour.

# Bug corrige le 06/08/2026 (confirme en direct : Texas Rangers -1.5 regle
# GAGNÉ en base mais jamais affiche comme "Terminé" sur Publications, reste
# indefiniment "en cours") : paris.resultat/value_result contiennent DEUX
# graphies -- "GAGNE" (tennis, wnba conseil, etc.) et "GAGNÉ" avec accent
# (_check_mlb/_check_nfl/_check_f1 dans results_tracker.py). Meme bug deja
# corrige dans scripts/export_site_results.py::RESULTAT_GAGNE le 03/08/2026,
# jamais reporte ici (fichier different, meme colonne DB) -- ce fichier
# filtrait uniquement 'GAGNE' partout, silencieusement "en cours" pour tout
# match MLB/NFL/F1 gagnant.
RESULTAT_GAGNE = ("GAGNE", "GAGNÉ")
SPORT_LABEL = {"football": "Football", "baseball": "Baseball (MLB)",
               "nba": "Basketball (NBA)", "nhl": "Hockey (NHL)", "nfl": "Football US (NFL)",
               "tennis": "Tennis", "wnba": "Basketball (WNBA)"}

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

# Duplique ici (21/08/2026, demande explicite : "toute les value ne sont pas
# sur le site" -- les lignes "💎 VALUE BET" du moteur refonte, formattees par
# football/refonte_publication_preview.py::format_value_bet_lines et fusionnees
# dans le caption Telegram, n'etaient jamais persistees dans une colonne lue
# par ce script -- seule refonte_value_bet_settlements (DB) les garde) plutot
# qu'importe football/refonte_publication_preview.py : meme raison que
# COMP_WINDOWS plus haut, le module football/ n'existe que cote repo prive,
# jamais copie par le cote public. MARKET_DISPLAY_ORDER/MARKET_LABELS/
# _SELECTION_LABELS source de verite : football/refonte_publication_preview.py.
REFONTE_MARKET_DISPLAY_ORDER = ["1x2", "over25", "btts", "corners", "cards"]
REFONTE_MARKET_LABELS = {
    "1x2": "1X2", "over25": "Over/Under 2.5", "btts": "BTTS",
    "corners": "Corners O/U 9.5", "cards": "Cartons O/U 3.5",
}
REFONTE_SELECTION_LABELS = {
    "H": "{home}", "D": "Match nul", "A": "{away}",
    "over": "Plus de 2.5 buts", "under": "Moins de 2.5 buts",
    "yes": "Les deux équipes marquent", "no": "Les deux équipes ne marquent pas",
    "corners_over": "Plus de 9.5 corners", "corners_under": "Moins de 9.5 corners",
    "cards_over": "Plus de 3.5 cartons", "cards_under": "Moins de 3.5 cartons",
}

# LDC/Europa/Conference/Libertadores/Sudamericana (25/08/2026) -- duplique
# ici pour la meme raison que COMP_WINDOWS/REFONTE_* ci-dessus : source de
# verite football/elo_cross_competition.py::CUP_ELO_ONLY_LEAGUE_IDS, module
# qui n'existe que cote repo prive.
CROSS_COMPETITION_LEAGUE_IDS = {2, 3, 848, 11, 13}


def _flag(league: str, league_id: int | None = None) -> str:
    if league_id and league_id in LEAGUE_FLAG_EMOJI:
        return LEAGUE_FLAG_EMOJI[league_id]
    c = (league or "").lower()
    for key, flag in COMPETITION_FLAGS.items():
        if key in c:
            return flag
    return "⚽"


def _sport_icon(sport: str, league: str, league_id: int | None = None) -> str:
    return _flag(league, league_id) if sport == "football" else SPORT_ICON.get(sport, "🏅")


_TENNIS_PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "players")
_TENNIS_PHOTO_EXTS = (".png", ".webp", ".jpg")


def _tennis_player_photo_path(player_name: str) -> str | None:
    """Chemin relatif (depuis site/) vers la photo deja en cache pour ce
    joueur, ou None si pas de correspondance/pas encore telechargee.

    24/08/2026 (demande explicite : "on arrete d'utiliser allsportsapi ...
    est-ce que c'est possible") : nom de fichier base sur
    normalize_player_name() (meme cle que players_tennis.player_key,
    tennis_elo_utils, generer_pari_tennis -- LA cle canonique utilisee
    partout ailleurs dans le bot pour identifier un joueur), plus jamais
    l'id numerique AllSportsAPI. Avant ce fix, CE lookup lui-meme appelait
    asa.get_rankings() EN DIRECT a chaque generation du site pour
    convertir nom -> id AllSportsAPI -- des que ce compte etait en
    rate-limit (confirme en direct le 24/08/2026, HTTP 429), la fonction
    retournait un dict vide et TOUTES les photos deja en cache devenaient
    invisibles sur le site, pas seulement les manquantes. Lookup desormais
    100% hors-ligne (lecture disque seule, aucun appel reseau)."""
    try:
        from tennis_elo_utils import normalize_player_name
    except Exception:
        return None
    key = normalize_player_name(player_name or "")
    if not key:
        return None
    for ext in _TENNIS_PHOTO_EXTS:
        if os.path.exists(os.path.join(_TENNIS_PHOTO_DIR, f"{key}{ext}")):
            return f"assets/players/{key}{ext}"
    return None


# Duplique depuis tg_bot/format_v2.py::strip_market_labels (07/08/2026,
# bug confirme : ce script (repo public, cf note COMP_WINDOWS ci-dessus)
# n'a jamais applique ce nettoyage -- Publications affichait donc "Total —
# Plus de 9,5" (prefixe brut) pour MLB/WNBA alors que le bot Telegram et
# export_site_results.py (repo prive) affichaient deja "Plus de 9,5" nettoye.
# Meme raison que ai/comp_windows.py : import top-level depuis tg_bot cassait
# tout le script cote public (module absent), donc copie locale plutot
# qu'import.
_MARKET_LABEL_PATTERNS = [
    (re.compile(r"^Vainqueur 1ère manche — (.+)$"), r"\1 (1ère manche)"),
    (re.compile(r"^Total 1ère manche — (.+)$"), r"\1 (1ère manche)"),
    (re.compile(r"^Vainqueur 1ère mi-temps — (.+)$"), r"\1 (1ère mi-temps)"),
    (re.compile(r"^Total 1ère mi-temps — (.+)$"), r"\1 (1ère mi-temps)"),
    (re.compile(r"^Total équipe (.+?) — (.+)$"), r"\1 \2"),
    (re.compile(r"^Écart de points — (.+)$"), r"\1"),
    (re.compile(r"^Total — (.+)$"), r"\1"),
    (re.compile(r"^Vainqueur — (.+)$"), r"\1"),
]


def _strip_market_labels(text: str) -> str:
    if not text:
        return text
    prefix = ""
    body = text
    if body.startswith("Combiné : "):
        prefix = "Combiné : "
        body = body[len(prefix):]
    legs = body.split(" + ")
    cleaned_legs = []
    for leg in legs:
        cleaned = leg
        for pattern, repl in _MARKET_LABEL_PATTERNS:
            if pattern.match(cleaned):
                cleaned = pattern.sub(repl, cleaned)
                break
        cleaned_legs.append(cleaned)
    return prefix + " + ".join(cleaned_legs)


def _short_pick(conseil: str) -> str:
    cleaned = re.sub(r"^Double chance\s+", "", (conseil or "").strip(), flags=re.IGNORECASE)
    return _strip_market_labels(cleaned)


def _cat(selection: str) -> str:
    """Meme classifieur que daily_bilan.py::_cat / scripts/export_site_results.py::_cat
    -- pas de FK entre offensive_player_picks (categorie) et
    player_pick_settlements (juste un pick_key = hash(joueur|selection)) : on
    retrouve la categorie d'un settlement par mots-cles sur son texte."""
    s = (selection or "").lower()
    if "passe" in s:
        return "passeur"
    if "decisif" in s or "décisif" in s:
        return "decisif"
    return "buteur"


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

# Sports sans compositions officielles confirmées avant match (cf.
# ai/comp_windows.py docstring : tennis n'a "pas de compo officielle" ;
# wnba n'a qu'un roster d'effectif, jamais un starting lineup titulaire
# confirme comme NBA/NHL/NFL/foot). Le libelle generique de
# REASON_AFTER_T20_BLOCKED ("Compositions arrivées trop tard") est donc
# trompeur pour ces sports -- overrides ici (30/07/2026, audit demande
# explicite suite a une capture d'ecran site reelle).
_NO_COMPOSITIONS_SPORTS = {"tennis", "wnba"}
NO_BET_REASONS_FR_OVERRIDE = {
    "REASON_AFTER_T20_BLOCKED": "Analyse non finalisée à temps",
}


def _no_bet_label(reason_code: str, sport: str) -> str:
    if sport in _NO_COMPOSITIONS_SPORTS and reason_code in NO_BET_REASONS_FR_OVERRIDE:
        return NO_BET_REASONS_FR_OVERRIDE[reason_code]
    return NO_BET_REASONS_FR.get(reason_code, NO_BET_GENERIC_FR)


def fetch_programme(days_back: int = 0) -> list[dict]:
    import psycopg2

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL manquant")
    conn = psycopg2.connect(db, connect_timeout=10)
    cur = conn.cursor()

    programme_date = _programme_date_today()
    placeholders_sport = ",".join(["%s"] * len(PROGRAMME_SPORTS))

    # Filtre fenêtre temporelle: J 08h → J+1 07h59 (nettoyage rétrospectif, ex: Wimbledon hors fenêtre)
    # days_back : voir docstring de _get_programme_window_sql_where() -- 0 ici
    # (comportement inchangé pour programme.html), fetch_publications() passe
    # 1 pour garder les résultats réglés visibles au-delà du rollover 08h Paris.
    window_where, window_params = _get_programme_window_sql_where(days_back=days_back)

    # Filtre par programme_date retire le 30/07/2026 (audit demande explicite,
    # confirme en direct : match Bronzetti/Ibragimova publie sur Telegram mais
    # invisible du site). programme_date est fige a la date de PREMIERE
    # detection du match (le scan tourne plusieurs jours a l'avance) et n'est
    # jamais rafraichi une fois les noms des joueurs connus (seul le cas
    # TBD -> vrai nom l'est, cf tennis/predictions.py) -- un match detecte le
    # 28/07 mais qui se joue le 30/07 restait donc invisible du site tout en
    # etant normalement publie par le pipeline (qui, lui, ne regarde que
    # kickoff_at). Le filtre window_where ci-dessous fait deja tout le travail
    # de restriction a la fenetre du jour, de facon fiable (base sur l'heure
    # reelle du match, jamais perimee) : programme_date devenait redondant et
    # etait la seule source du bug. programme_date (variable Python) reste
    # utilisee plus bas pour la requete Coup du Jour (daily_flags), une table
    # differente, non affectee par ce retrait.
    cur.execute(
        f"""
        SELECT fixture_id, home, away, league, kickoff_at, publish_status, sport,
               league_id, home_team_id, away_team_id
        FROM programme_fixtures
        WHERE sport IN ({placeholders_sport})
          AND {window_where}
        ORDER BY kickoff_at ASC
        LIMIT 300
        """,
        (*PROGRAMME_SPORTS, *window_params),
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
    for fixture_id, home, away, league, kickoff_at, publish_status, sport, league_id, home_team_id, away_team_id in rows:
        item = {
            # fixture_id (21/07/2026) : necessaire cote client pour deriver
            # l'ID ESPN et interroger le score en direct pendant le match
            # (remplace "En cours" -- voir programme.html::espnEventInfo).
            "fixture_id": str(fixture_id),
            "flag": _sport_icon(sport, league, int(league_id) if league_id else None),
            "league": league or "",
            "sport": sport or "football",
            "sport_label": SPORT_LABEL.get(sport, sport or "Football"),
            "match": f"{home} – {away}",
            "kickoff_at": kickoff_at,
            "published": publish_status == "published",
        }
        # league_id + logos (13/08/2026, chantier "live score foot via ESPN") :
        # necessaire cote client pour resoudre le slug ESPN
        # (FOOTBALL_LEAGUE_SLUGS) et afficher les vrais blasons -- deja stockes
        # sur programme_fixtures depuis la creation de la ligne, aucun appel
        # API supplementaire. media.api-sports.io/football/teams/{id}.png est
        # l'URL publique stable utilisee partout ailleurs dans le bot pour un
        # logo d'equipe (cf normalize_team()).
        if sport == "football":
            if league_id:
                item["league_id"] = int(league_id)
            if home_team_id:
                item["home_logo"] = f"https://media.api-sports.io/football/teams/{int(home_team_id)}.png"
            if away_team_id:
                item["away_logo"] = f"https://media.api-sports.io/football/teams/{int(away_team_id)}.png"
        elif sport == "tennis":
            # Photos joueurs (13/08/2026, demande explicite "recupere celle
            # d'ESPN le maximum et installe un systeme pour completer... avec
            # un rythme de 95/jours") : jobs/tennis_player_photos.py telecharge
            # en amont dans site/assets/players/{allsportsapi_id}.{ext} -- ici
            # on resout juste le nom -> id (classement AllSportsAPI deja en
            # cache memoire 1h) puis verifie si le fichier local existe deja.
            # Chemin relatif omis (pas de champ) si aucune photo en cache --
            # le client affiche alors des initiales, jamais d'image inventee.
            home_photo = _tennis_player_photo_path(home)
            away_photo = _tennis_player_photo_path(away)
            if home_photo:
                item["home_photo"] = home_photo
            if away_photo:
                item["away_photo"] = away_photo
        if coup_fixture_id and str(fixture_id) == coup_fixture_id:
            item["coup"] = True
        if publish_status != "published" and str(fixture_id) in no_bet_by_fixture:
            code = no_bet_by_fixture[str(fixture_id)]
            item["no_bet_reason"] = _no_bet_label(code, sport)
        if publish_status == "published":
            cur.execute(
                """SELECT conseil, COALESCE(NULLIF(cote_reelle,0), cote_interne),
                          value_bet, value_cote, resultat, score, value_result,
                          lineup_source, COALESCE(mise,0), COALESCE(value_stake_eur,0)
                   FROM paris WHERE fixture_id = %s
                   ORDER BY created_at DESC LIMIT 1""",
                (fixture_id,),
            )
            row = cur.fetchone()
            if row:
                (conseil, cote, value_bet, value_cote, resultat, score, value_result,
                 lineup_source, conseil_mise, value_mise) = row
                if conseil and sport not in SPORTS_CONSEIL_IS_MIRROR:
                    item["conseil"] = _short_pick(conseil)
                    item["conseil_cote"] = round(float(cote or 0), 2)
                    # Mise (22/08/2026, demande explicite "rajoute les mises
                    # dans les publications") : paris.mise est deja en EUROS
                    # (football/predictions.py::sauvegarder_pari, mise=
                    # advice_stake.stake_eur) -- jamais recalculee ici, la
                    # valeur figee au moment de la publication reelle.
                    if float(conseil_mise or 0) > 0:
                        item["conseil_mise_eur"] = round(float(conseil_mise), 0)
                # Badge "Compo: ..." (11/08/2026, chantier ESPN palier 2) --
                # purement informatif, n'affecte aucun calcul. Uniquement
                # pour foot (seul sport avec cette colonne renseignee).
                if sport == "football" and lineup_source:
                    item["lineup_source"] = str(lineup_source)
                if value_bet:
                    item["value_bet"] = _short_pick(value_bet)
                    item["value_cote"] = round(float(value_cote or 0), 2)
                    if float(value_mise or 0) > 0:
                        item["value_mise_eur"] = round(float(value_mise), 0)
                    # Statut propre au value bet (24/07/2026, demande explicite,
                    # confirme en direct : badge global du haut affichait le
                    # resultat du "conseil" -- mirroir du value bet OU d'un
                    # player pick selon le match -- alors qu'un match peut avoir
                    # un value bet ET un player pick sur un AUTRE marche, avec
                    # des issues opposees. Chaque ligne affiche desormais son
                    # propre statut au lieu d'un badge unique ambigu.
                    if (value_result or "").upper() in RESULTAT_GAGNE + ("PERDU",):
                        item["value_result"] = value_result.upper()
                    elif sport in SPORTS_CONSEIL_IS_MIRROR and (resultat or "").upper() in RESULTAT_GAGNE + ("PERDU", "REMBOURSE"):
                        # sport a mirroir : value_result n'est pas toujours
                        # rempli (cf resultat_tracker.py::_send_result_msg),
                        # mais resultat represente ce meme pari quand le
                        # conseil mirrore le value bet (aucun player pick
                        # "Total sets" mirrore a la place).
                        if not (conseil or "").lower().startswith("total sets"):
                            item["value_result"] = resultat.upper()
                if (resultat or "").upper() in RESULTAT_GAGNE + ("PERDU", "REMBOURSE"):
                    item["result"] = resultat.upper()
                    if score:
                        item["score"] = score
            cur.execute(
                """SELECT category, selection_label, display_mode, market_odd, public_probability,
                          COALESCE(stake_eur,0)
                   FROM offensive_player_picks WHERE fixture_id = %s
                   ORDER BY created_at DESC""",
                (fixture_id,),
            )
            player_picks = []
            seen_categories = set()
            for category, label, mode, odd, prob, stake_eur in cur.fetchall():
                if category in seen_categories:
                    continue
                seen_categories.add(category)
                detail = f"cote {float(odd):.2f}" if mode == "cote" and odd else f"{int(prob or 0)}%"
                player_picks.append({
                    "category": CATEGORY_LABEL_FR.get(category, (category or "Pick").replace("_", " ").capitalize()),
                    "label": label,
                    "detail": detail,
                    # "odd" numerique (05/08/2026, bug confirme en direct :
                    # la cote reelle etait deja calculee ici mais jamais
                    # transmise au client -- publications.html passait
                    # `null` en dur pour tous les player picks, cote jamais
                    # affichee malgre "detail" qui la contenait deja en
                    # texte). None pour les picks mode "percent" (pas de
                    # cote marche reelle, jamais de valeur inventee).
                    "odd": float(odd) if mode == "cote" and odd else None,
                    # Mise (22/08/2026) : deja persistee (offensive_player_picks.
                    # stake_eur, remplie par football/predictions.py au calcul
                    # de la caption Telegram) mais jamais lue par ce script --
                    # None en mode "percent" (pas de cote marche, pas de mise
                    # a afficher, meme regle que "odd" juste au-dessus).
                    "mise_eur": round(float(stake_eur), 0) if mode == "cote" and stake_eur else None,
                    "_cat_key": category,
                })
                if len(player_picks) == 2:
                    break
            if player_picks:
                # Statut par player pick football (24/07/2026, meme demande que
                # value_result plus haut) : player_pick_settlements n'a pas de
                # FK directe vers offensive_player_picks, on retrouve le
                # settlement d'une categorie via _cat() sur le texte de
                # selection (meme classifieur que daily_bilan.py::_cat).
                cur.execute(
                    """SELECT selection, result FROM player_pick_settlements
                       WHERE fixture_id = %s""",
                    (fixture_id,),
                )
                settlements_by_cat: dict = {}
                for selection, result in cur.fetchall():
                    if (result or "").upper() in RESULTAT_GAGNE + ("PERDU", "REMBOURSE"):
                        settlements_by_cat[_cat(selection)] = result.upper()
                for pick in player_picks:
                    cat_key = pick.pop("_cat_key", None)
                    result = settlements_by_cat.get(cat_key)
                    if result:
                        pick["result"] = result
            else:
                # MLB/NBA/NHL/NFL/WNBA/Tennis (sport_player_picks) : offensive_
                # player_picks ne couvre que le football (buteur/passeur/decisif).
                # Ajoute le 20/07/2026 -- ces sports n'affichaient jamais leurs
                # player picks sur le site cote "a venir/publie".
                cur.execute(
                    """SELECT player_name, market_label, odd, settlement_status, COALESCE(stake_eur,0)
                       FROM sport_player_picks
                       WHERE fixture_id = %s ORDER BY created_at ASC LIMIT 2""",
                    (fixture_id,),
                )
                for player_name, label, odd, settlement_status, stake_eur in cur.fetchall():
                    # sport_player_picks stocke aussi des paris de MATCH (pas un
                    # joueur nomme) pour le tennis, avec player_name = le nom du
                    # match ("A vs B") au lieu d'un vrai joueur -- detecte via
                    # " vs " (jamais present dans un vrai nom de joueur).
                    #
                    # 26/08/2026, 2 bugs distincts corriges sur ce cas (confirmes
                    # en direct par l'utilisateur) :
                    # 1) "Total sets ..." (marche de MATCH, pas un joueur) sortait
                    #    quand meme sous le badge "Player pick" -- desormais badge
                    #    "Value", label brut sans le nom du match en prefixe (deja
                    #    affiche dans l'entete de la carte).
                    # 2) "Vainqueur du match X" (pick VRAIMENT joueur, juste mal
                    #    prefixe) affichait "A vs B — Vainqueur du match X" --
                    #    desormais "Player pick : Vainqueur du match X", jamais
                    #    le nom du match en prefixe.
                    is_match_level = bool(player_name) and " vs " in player_name
                    is_match_total = is_match_level and (label or "").lower().startswith("total")
                    if is_match_total:
                        pick_label = label
                    elif is_match_level:
                        pick_label = f"Player pick : {label}"
                    else:
                        pick_label = f"{player_name} — {label}" if player_name else label
                    pick = {
                        "category": "Total du match" if is_match_total else "Player pick",
                        "label": pick_label,
                        "kind": "value" if is_match_total else "player",
                        "detail": f"cote {float(odd):.2f}" if odd else "",
                        # "odd" numerique -- meme fix que la branche football
                        # ci-dessus (05/08/2026).
                        "odd": float(odd) if odd else None,
                        # Mise (22/08/2026) -- deja persistee, jamais lue avant.
                        "mise_eur": round(float(stake_eur), 0) if odd and stake_eur else None,
                    }
                    if (settlement_status or "").upper() in RESULTAT_GAGNE + ("PERDU",):
                        pick["result"] = settlement_status.upper()
                    player_picks.append(pick)
            if player_picks:
                item["player_picks"] = player_picks

            # Lignes "💎 VALUE BET" du moteur refonte (1X2/O-U/BTTS/corners/
            # cartons) -- absentes du site jusqu'ici (21/08/2026, demande
            # explicite), persistees uniquement dans refonte_value_bet_settlements
            # une fois le message combine reellement envoye (cf football/
            # predictions.py::_compute_refonte_value_bet_lines). Foot uniquement
            # -- cette table n'existe que pour les ligues domestiques refonte.
            if sport == "football":
                cur.execute(
                    """SELECT market, selection, odd, result, COALESCE(stake_eur,0)
                       FROM refonte_value_bet_settlements
                       WHERE fixture_id = %s""",
                    (fixture_id,),
                )
                _by_market = {market: (selection, odd, result, stake_eur)
                              for market, selection, odd, result, stake_eur in cur.fetchall()}
                refonte_value_bets = []
                for market in REFONTE_MARKET_DISPLAY_ORDER:
                    row = _by_market.get(market)
                    if not row:
                        continue
                    selection, odd, result, stake_eur = row
                    label = REFONTE_SELECTION_LABELS.get(selection, selection)
                    label = label.format(home=home, away=away) if "{" in label else label
                    entry = {
                        "market": REFONTE_MARKET_LABELS.get(market, market),
                        "label": label,
                        "odd": round(float(odd or 0), 2),
                        # Mise (22/08/2026) -- deja persistee (stake_eur fige a
                        # la publication, cf football/refonte_publication_preview.py::
                        # record_selections_shadow), jamais lue par le site avant.
                        "mise_eur": round(float(stake_eur), 0) if stake_eur else None,
                    }
                    if (result or "").upper() in RESULTAT_GAGNE + ("PERDU", "REMBOURSE"):
                        entry["result"] = result.upper()
                    refonte_value_bets.append(entry)
                if refonte_value_bets:
                    item["refonte_value_bets"] = refonte_value_bets

            # Cross-competition (LDC/Europa/Conference/Libertadores/
            # Sudamericana) : ces 5 competitions ne passent JAMAIS par
            # sauvegarder_pari() ni offensive_player_picks (moteur separe,
            # football/refonte_cross_competition.py) -- leurs picks
            # atterrissaient dans refonte_cross_competition_value_bet_
            # settlements / _player_pick_settlements, jamais lus par ce
            # script. Consequence (25/08/2026, signale) : ces matchs
            # apparaissaient sur le site avec clubs + decompte mais sans
            # aucun prono. Reutilise le meme rendu generique deja en place
            # pour value_bet (refonte_value_bets) et player_picks.
            if sport == "football" and int(league_id or 0) in CROSS_COMPETITION_LEAGUE_IDS:
                cur.execute(
                    """SELECT market, selection, odd, result, COALESCE(stake_eur,0)
                       FROM refonte_cross_competition_value_bet_settlements
                       WHERE fixture_id = %s""",
                    (fixture_id,),
                )
                cc_value_bets = []
                for market, selection, odd, result, stake_eur in cur.fetchall():
                    entry = {
                        "market": REFONTE_MARKET_LABELS.get(market, market),
                        "label": REFONTE_SELECTION_LABELS.get(selection, selection).format(home=home, away=away)
                                 if "{" in REFONTE_SELECTION_LABELS.get(selection, selection) else
                                 REFONTE_SELECTION_LABELS.get(selection, selection),
                        "odd": round(float(odd or 0), 2),
                        "mise_eur": round(float(stake_eur), 0) if stake_eur else None,
                    }
                    if (result or "").upper() in RESULTAT_GAGNE + ("PERDU", "REMBOURSE"):
                        entry["result"] = result.upper()
                    cc_value_bets.append(entry)
                if cc_value_bets:
                    item["refonte_value_bets"] = cc_value_bets

                cur.execute(
                    """SELECT player_name, selection, odd, result, COALESCE(stake_eur,0)
                       FROM refonte_cross_competition_player_pick_settlements
                       WHERE fixture_id = %s""",
                    (fixture_id,),
                )
                cc_row = cur.fetchone()
                if cc_row:
                    player_name, selection, odd, result, stake_eur = cc_row
                    pick = {
                        "category": "Player pick",
                        "label": f"{player_name} — {selection}" if player_name else selection,
                        "detail": f"cote {float(odd):.2f}" if odd else "",
                        "odd": float(odd) if odd else None,
                        "mise_eur": round(float(stake_eur), 0) if odd and stake_eur else None,
                    }
                    if (result or "").upper() in RESULTAT_GAGNE + ("PERDU",):
                        pick["result"] = result.upper()
                    item.setdefault("player_picks", []).append(pick)

            # Lignes value bet MLB additionnelles (25/08/2026, demande
            # explicite : "les lignes multiples sur le site [seulement],
            # pas le message telegram") -- meme champ "refonte_value_bets"
            # que le foot ci-dessus (rendu JS deja generique, cf
            # publications.html "renderPick(f, 'value', ...)"), simplement
            # alimente depuis mlb_value_bet_settlements au lieu de
            # refonte_value_bet_settlements. Affiche uniquement les lignes
            # AU-DELA du pick principal deja affiche via paris.conseil
            # (celui-la reste la seule ligne envoyee sur Telegram).
            if sport == "baseball":
                cur.execute(
                    """SELECT market, selection_text, odd, result, COALESCE(stake_eur,0)
                       FROM mlb_value_bet_settlements
                       WHERE fixture_id = %s""",
                    (fixture_id,),
                )
                mlb_value_bets = []
                for market, selection_text, odd, result, stake_eur in cur.fetchall():
                    entry = {
                        "market": market,
                        "label": selection_text,
                        "odd": round(float(odd or 0), 2),
                        "mise_eur": round(float(stake_eur), 0) if stake_eur else None,
                    }
                    if (result or "").upper() in RESULTAT_GAGNE + ("PERDU",):
                        entry["result"] = result.upper()
                    mlb_value_bets.append(entry)
                if mlb_value_bets:
                    item["refonte_value_bets"] = mlb_value_bets
        out.append(item)

    conn.close()
    return out


def fetch_publications() -> dict:
    """Sous-ensemble de fetch_programme() pour la page Publications
    (04/08/2026, chantier "gros chantier 10/10" -- remplace a terme
    programme.html) : ne garde que les fixtures reellement PUBLIEES sur
    Telegram aujourd'hui (05/08/2026, demande explicite : les No Bet ne sont
    pas des publications Telegram, ils ne doivent plus apparaitre sur cette
    page -- seul le flux reellement envoye au canal compte).
    Football reintegre (21/08/2026 -- l'exclusion du 04/08/2026 citait
    "pas de fixture_id exploitable cote client pour le score, cle API
    secrete" : resolu depuis le 13/08/2026 par le chantier "live score foot
    via ESPN" (site/publications.html::resolveFootballEventId), qui
    resout l'event ESPN par similarite de noms d'equipe cote client, sans
    cle secrete -- l'exclusion ici n'avait juste jamais ete retiree apres
    coup, alors que le blocage qu'elle citait n'existe plus).

    "live" = pas encore reglee (pas de cle "result") ; "done" = reglee
    (cle "result" presente). Le statut "live" avant le coup d'envoi est
    affiche cote client comme un decompte exact jusqu'a kickoff_at (present
    dans chaque item), pas un simple "En cours" statique.

    days_back=1 (02/09/2026, demande explicite : "corrige la fenetre pour
    que ca reste visible" -- bug confirme en direct : matchs MLB de la
    veille au soir disparaissaient de "done" des que la fenetre roulait a
    08h Paris) : fenetre 48h au lieu de 24h pour cette page uniquement --
    programme.html (fetch_programme() sans argument, page "programme du
    jour") reste sur la fenetre stricte d'origine."""
    out = {"live": [], "done": []}
    for f in fetch_programme(days_back=1):
        if not f.get("published"):
            continue
        (out["done"] if f.get("result") else out["live"]).append(f)
    return out


def main() -> None:
    target = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "programme.json",
    )

    # Embarque COMP_WINDOWS pour le double indicateur T-30 côté client
    comp_windows_json = {
        sport: {"comp_min": comp_min, "comp_max": comp_max}
        for sport, (comp_min, comp_max) in COMP_WINDOWS.items()
    }

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comp_windows": comp_windows_json,
        "fixtures": fetch_programme(),
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[Programme] {len(data['fixtures'])} match(s) ecrits dans {target}")


if __name__ == "__main__":
    main()
