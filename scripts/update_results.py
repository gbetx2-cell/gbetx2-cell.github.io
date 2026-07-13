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

N_RESULTS = 20

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
            # Mise reelle en unites (ai/staking.py : 1 unite = BASE_UNIT_EUR,
            # variable par palier d'edge -- jamais 1u fixe) et PnL reel deja
            # calcule en prod (database.py update_resultat), pas recalcule
            # a partir de la cote pour eviter toute divergence.
            "mise": round(float(mise or 1), 2),
            "pnl": round(float(pnl or 0), 2),
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


def update_html(path: str, results: list[dict]) -> None:
    with open(path, encoding="utf-8") as f:
        html = f.read()
    block = render_block(results)
    new_html, n = re.subn(r"const RESULTATS = \[.*?\];", block, html, count=1, flags=re.DOTALL)
    if n != 1:
        raise SystemExit(f"bloc RESULTATS introuvable dans {path}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_html)
    print(f"[Site] {len(results)} resultats reels ecrits dans {path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html",
    )
    update_html(target, fetch_results())
