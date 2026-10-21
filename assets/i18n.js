/* G-BET : choix de la langue (drapeaux) + fuseau horaire du pays choisi.
   La page est ecrite en francais (langue par defaut, heure de Paris). Quand une autre langue est choisie,
   chaque texte connu est remplace par sa traduction (dictionnaire D ci-dessous), y compris les textes
   ajoutes plus tard par la page. Un texte absent du dictionnaire reste en francais : jamais de texte
   vide ou casse. Les noms d'equipes/joueurs ne sont jamais touches.
   Ordre des traductions : [en, es, de, it, pt, nl, tr]. */
(function () {
"use strict";

/* ---------- pays proposes : drapeau, langue, format de date, fuseau horaire ----------
   idx = rang de la langue : 0..6 = en, es, de, it, pt, nl, tr (dictionnaire ci-dessous) ; 7.. = langues chargees a la demande
   depuis assets/i18n_<code>.js (zh, ja, ko, ru, pl, ar, hi, id). -1 = francais (langue d'origine de la page). */
const LANGS = ["en", "es", "de", "it", "pt", "nl", "tr", "zh", "ja", "ko", "ru", "pl", "ar", "hi", "id"];
const PAYS = [
  {c: "fr",    nom: "Français · France",              idx: -1, loc: "fr-FR", tz: "Europe/Paris"},
  {c: "be",    nom: "Français · Belgique",            idx: -1, loc: "fr-BE", tz: "Europe/Brussels"},
  {c: "ch-fr", f: "ch", nom: "Français · Suisse",     idx: -1, loc: "fr-CH", tz: "Europe/Zurich"},
  {c: "ca-fr", f: "ca", nom: "Français · Canada",     idx: -1, loc: "fr-CA", tz: "America/Toronto"},
  {c: "ma",    nom: "Français · Maroc",               idx: -1, loc: "fr-MA", tz: "Africa/Casablanca"},
  {c: "dz",    nom: "Français · Algérie",             idx: -1, loc: "fr-DZ", tz: "Africa/Algiers"},
  {c: "tn",    nom: "Français · Tunisie",             idx: -1, loc: "fr-TN", tz: "Africa/Tunis"},
  {c: "sn",    nom: "Français · Sénégal",             idx: -1, loc: "fr-SN", tz: "Africa/Dakar"},
  {c: "ci",    nom: "Français · Côte d'Ivoire",       idx: -1, loc: "fr-CI", tz: "Africa/Abidjan"},
  {c: "gb",    nom: "English · United Kingdom",       idx: 0,  loc: "en-GB", tz: "Europe/London"},
  {c: "us",    nom: "English · United States",        idx: 0,  loc: "en-US", tz: "America/New_York"},
  {c: "ie",    nom: "English · Ireland",              idx: 0,  loc: "en-IE", tz: "Europe/Dublin"},
  {c: "ca",    nom: "English · Canada",               idx: 0,  loc: "en-CA", tz: "America/Toronto"},
  {c: "au",    nom: "English · Australia",            idx: 0,  loc: "en-AU", tz: "Australia/Sydney"},
  {c: "nz",    nom: "English · New Zealand",          idx: 0,  loc: "en-NZ", tz: "Pacific/Auckland"},
  {c: "in",    nom: "English · India",                idx: 0,  loc: "en-IN", tz: "Asia/Kolkata"},
  {c: "za",    nom: "English · South Africa",         idx: 0,  loc: "en-ZA", tz: "Africa/Johannesburg"},
  {c: "ng",    nom: "English · Nigeria",              idx: 0,  loc: "en-NG", tz: "Africa/Lagos"},
  {c: "es",    nom: "Español · España",               idx: 1,  loc: "es-ES", tz: "Europe/Madrid"},
  {c: "mx",    nom: "Español · México",               idx: 1,  loc: "es-MX", tz: "America/Mexico_City"},
  {c: "ar",    nom: "Español · Argentina",            idx: 1,  loc: "es-AR", tz: "America/Argentina/Buenos_Aires"},
  {c: "co",    nom: "Español · Colombia",             idx: 1,  loc: "es-CO", tz: "America/Bogota"},
  {c: "cl",    nom: "Español · Chile",                idx: 1,  loc: "es-CL", tz: "America/Santiago"},
  {c: "pe",    nom: "Español · Perú",                 idx: 1,  loc: "es-PE", tz: "America/Lima"},
  {c: "de",    nom: "Deutsch · Deutschland",          idx: 2,  loc: "de-DE", tz: "Europe/Berlin"},
  {c: "at",    nom: "Deutsch · Österreich",           idx: 2,  loc: "de-AT", tz: "Europe/Vienna"},
  {c: "ch-de", f: "ch", nom: "Deutsch · Schweiz",     idx: 2,  loc: "de-CH", tz: "Europe/Zurich"},
  {c: "it",    nom: "Italiano · Italia",              idx: 3,  loc: "it-IT", tz: "Europe/Rome"},
  {c: "pt",    nom: "Português · Portugal",           idx: 4,  loc: "pt-PT", tz: "Europe/Lisbon"},
  {c: "br",    nom: "Português · Brasil",             idx: 4,  loc: "pt-BR", tz: "America/Sao_Paulo", br: true},
  {c: "nl",    nom: "Nederlands · Nederland",         idx: 5,  loc: "nl-NL", tz: "Europe/Amsterdam"},
  {c: "be-nl", f: "be", nom: "Nederlands · België",   idx: 5,  loc: "nl-BE", tz: "Europe/Brussels"},
  {c: "tr",    nom: "Türkçe · Türkiye",               idx: 6,  loc: "tr-TR", tz: "Europe/Istanbul"},
  {c: "cn",    nom: "中文 · 中国",                      idx: 7,  loc: "zh-CN", tz: "Asia/Shanghai"},
  {c: "jp",    nom: "日本語 · 日本",                    idx: 8,  loc: "ja-JP", tz: "Asia/Tokyo"},
  {c: "kr",    nom: "한국어 · 대한민국",                  idx: 9,  loc: "ko-KR", tz: "Asia/Seoul"},
  {c: "ru",    nom: "Русский · Россия",               idx: 10, loc: "ru-RU", tz: "Europe/Moscow"},
  {c: "pl",    nom: "Polski · Polska",                idx: 11, loc: "pl-PL", tz: "Europe/Warsaw"},
  {c: "sa",    nom: "العربية · السعودية",              idx: 12, loc: "ar-SA-u-ca-gregory-nu-latn", tz: "Asia/Riyadh", rtl: true},
  {c: "ae",    nom: "العربية · الإمارات",              idx: 12, loc: "ar-AE-u-nu-latn", tz: "Asia/Dubai", rtl: true},
  {c: "eg",    nom: "العربية · مصر",                   idx: 12, loc: "ar-EG-u-nu-latn", tz: "Africa/Cairo", rtl: true},
  {c: "in-hi", f: "in", nom: "हिन्दी · भारत",          idx: 13, loc: "hi-IN", tz: "Asia/Kolkata"},
  {c: "id",    nom: "Bahasa Indonesia · Indonesia",   idx: 14, loc: "id-ID", tz: "Asia/Jakarta"},
];
const CLE = "gb_pays";
let code = "fr";
try { code = localStorage.getItem(CLE) || "fr"; } catch (e) {}
let P = PAYS.find(p => p.c === code) || PAYS[0];
const I = P.idx;
const EN_ANGLAIS = I === 0 || I === 7 || I === 8 || I === 9 || I === 13;     // point decimal (1.25) et virgule des milliers
/* langue chargee a la demande : le fichier est ecrit dans la page avant la suite du chargement */
if (I >= 7 && document.readyState === "loading") document.write('<script src="assets/i18n_' + LANGS[I] + '.js"><\/script>');
let LF = null;
const lf = () => LF || (LF = window.GB_L || null);

/* ---------- dictionnaire : francais -> [en, es, de, it, pt, nl, tr] ---------- */
const D = {
  /* en-tete */
  "Paris du jour": ["Today's bets","Apuestas de hoy","Tipps des Tages","Scommesse del giorno","Apostas do dia","Weddenschappen van vandaag","Günün bahisleri"],
  "Résultats": ["Results","Resultados","Ergebnisse","Risultati","Resultados","Resultaten","Sonuçlar"],
  "Aide": ["Help","Ayuda","Hilfe","Aiuto","Ajuda","Help","Yardım"],
  "Se connecter": ["Log in","Iniciar sesión","Anmelden","Accedi","Entrar","Inloggen","Giriş yap"],
  "Rejoindre sur Telegram": ["Join on Telegram","Unirse en Telegram","Auf Telegram beitreten","Unisciti su Telegram","Entrar no Telegram","Word lid op Telegram","Telegram'a katıl"],
  "Pas de compte bookmaker ? Offre de bienvenue Winamax, code": ["No bookmaker account? Winamax welcome offer, code","¿Sin cuenta en una casa de apuestas? Oferta de bienvenida Winamax, código","Noch kein Wettanbieter-Konto? Winamax-Willkommensangebot, Code","Nessun conto bookmaker? Offerta di benvenuto Winamax, codice","Sem conta numa casa de apostas? Oferta de boas-vindas Winamax, código","Nog geen bookmakeraccount? Winamax-welkomstaanbod, code","Bahis hesabın yok mu? Winamax hoş geldin teklifi, kod"],
  "Voir l'offre": ["See the offer","Ver la oferta","Angebot ansehen","Vedi l'offerta","Ver a oferta","Bekijk het aanbod","Teklifi gör"],
  "Langue": ["Language","Idioma","Sprache","Lingua","Idioma","Taal","Dil"],
  "Pages": ["Pages","Páginas","Seiten","Pagine","Páginas","Pagina's","Sayfalar"],

  /* page du jour */
  "À venir et en direct": ["Upcoming and live","Próximos y en directo","Anstehend und live","In arrivo e in diretta","Próximos e ao vivo","Aankomend en live","Yaklaşan ve canlı"],
  "Tout": ["All","Todo","Alle","Tutto","Tudo","Alles","Tümü"],
  "Tous sports": ["All sports","Todos los deportes","Alle Sportarten","Tutti gli sport","Todos os desportos","Alle sporten","Tüm sporlar"],
  "Terminés": ["Finished","Terminados","Beendet","Terminati","Terminados","Afgelopen","Bitenler"],
  "Terminé": ["Finished","Terminado","Beendet","Terminato","Terminado","Afgelopen","Bitti"],
  "TERMINÉ": ["FINISHED","TERMINADO","BEENDET","TERMINATO","TERMINADO","AFGELOPEN","BİTTİ"],
  "En direct": ["Live","En directo","Live","In diretta","Ao vivo","Live","Canlı"],
  "En cours": ["In progress","En curso","Laufend","In corso","Em curso","Bezig","Devam ediyor"],
  "en cours": ["in progress","en curso","laufend","in corso","em curso","bezig","devam ediyor"],
  "En attente": ["Pending","Pendiente","Ausstehend","In attesa","Pendente","In afwachting","Beklemede"],
  "À venir": ["Upcoming","Próximamente","Demnächst","In arrivo","Em breve","Binnenkort","Yakında"],
  "A venir": ["Upcoming","Próximamente","Demnächst","In arrivo","Em breve","Binnenkort","Yakında"],
  "Gagné": ["Won","Ganado","Gewonnen","Vinta","Ganho","Gewonnen","Kazandı"],
  "GAGNÉ": ["WON","GANADO","GEWONNEN","VINTA","GANHO","GEWONNEN","KAZANDI"],
  "gagné": ["won","ganado","gewonnen","vinta","ganho","gewonnen","kazandı"],
  "Perdu": ["Lost","Perdido","Verloren","Persa","Perdido","Verloren","Kaybetti"],
  "perdu": ["lost","perdido","verloren","persa","perdido","verloren","kaybetti"],
  "Remboursé": ["Refunded","Reembolsado","Erstattet","Rimborsata","Reembolsado","Terugbetaald","İade"],
  "remboursé": ["refunded","reembolsado","erstattet","rimborsata","reembolsado","terugbetaald","iade"],
  "Chargement…": ["Loading…","Cargando…","Wird geladen…","Caricamento…","A carregar…","Laden…","Yükleniyor…"],
  "Le match vient de commencer": ["The match has just started","El partido acaba de empezar","Das Spiel hat gerade begonnen","La partita è appena iniziata","O jogo acabou de começar","De wedstrijd is net begonnen","Maç yeni başladı"],
  "Match terminé · retrouvez-le dans « Terminés »": ["Match finished · find it under “Finished”","Partido terminado · búscalo en «Terminados»","Spiel beendet · zu finden unter „Beendet“","Partita finita · la trovi in «Terminati»","Jogo terminado · encontre-o em «Terminados»","Wedstrijd afgelopen · te vinden onder ‘Afgelopen’","Maç bitti · «Bitenler» bölümünde bulabilirsiniz"],
  "Aucun pari ce jour-la": ["No bets that day","Ninguna apuesta ese día","Keine Tipps an diesem Tag","Nessuna scommessa quel giorno","Nenhuma aposta nesse dia","Geen weddenschappen die dag","O gün bahis yok"],
  "aucun pari": ["no bets","ninguna apuesta","keine Tipps","nessuna scommessa","nenhuma aposta","geen weddenschappen","bahis yok"],
  "Pas de compte": ["No account","Sin cuenta","Kein Konto","Nessun account","Sem conta","Geen account","Hesap yok"],
  "Série :": ["Streak:","Racha:","Serie:","Serie:","Série:","Reeks:","Seri:"],
  "Série en cours": ["Current streak","Racha actual","Aktuelle Serie","Serie in corso","Série atual","Huidige reeks","Süren seri"],
  "Meilleure série": ["Best streak","Mejor racha","Beste Serie","Miglior serie","Melhor série","Beste reeks","En iyi seri"],

  /* sports */
  "Football": ["Football","Fútbol","Fußball","Calcio","Futebol","Voetbal","Futbol"],
  "Tennis": ["Tennis","Tenis","Tennis","Tennis","Ténis","Tennis","Tenis"],
  "Hockey": ["Ice hockey","Hockey sobre hielo","Eishockey","Hockey su ghiaccio","Hóquei no gelo","IJshockey","Buz hokeyi"],
  "Basket": ["Basketball","Baloncesto","Basketball","Basket","Basquetebol","Basketbal","Basketbol"],
  "Baseball": ["Baseball","Béisbol","Baseball","Baseball","Basebol","Honkbal","Beyzbol"],
  "Handball": ["Handball","Balonmano","Handball","Pallamano","Andebol","Handbal","Hentbol"],
  "Football US": ["American football","Fútbol americano","American Football","Football americano","Futebol americano","American football","Amerikan futbolu"],
  "MMA / F1 / Golf": ["MMA / F1 / Golf","MMA / F1 / Golf","MMA / F1 / Golf","MMA / F1 / Golf","MMA / F1 / Golfe","MMA / F1 / Golf","MMA / F1 / Golf"],
  "Formule 1": ["Formula 1","Fórmula 1","Formel 1","Formula 1","Fórmula 1","Formule 1","Formül 1"],
  "Golf": ["Golf","Golf","Golf","Golf","Golfe","Golf","Golf"],
  "Basket (NBA)": ["Basketball (NBA)","Baloncesto (NBA)","Basketball (NBA)","Basket (NBA)","Basquetebol (NBA)","Basketbal (NBA)","Basketbol (NBA)"],
  "Football US (NFL)": ["American football (NFL)","Fútbol americano (NFL)","American Football (NFL)","Football americano (NFL)","Futebol americano (NFL)","American football (NFL)","Amerikan futbolu (NFL)"],
  "Corée du Sud": ["South Korea","Corea del Sur","Südkorea","Corea del Sud","Coreia do Sul","Zuid-Korea","Güney Kore"],
  "Suède": ["Sweden","Suecia","Schweden","Svezia","Suécia","Zweden","İsveç"],
  "Norvège": ["Norway","Noruega","Norwegen","Norvegia","Noruega","Noorwegen","Norveç"],
  "Tchéquie": ["Czechia","Chequia","Tschechien","Cechia","Chéquia","Tsjechië","Çekya"],
  "États-Unis": ["United States","Estados Unidos","USA","Stati Uniti","Estados Unidos","Verenigde Staten","Amerika Birleşik Devletleri"],
  "Pologne": ["Poland","Polonia","Polen","Polonia","Polónia","Polen","Polonya"],
  "Roumanie": ["Romania","Rumanía","Rumänien","Romania","Roménia","Roemenië","Romanya"],
  "Espagne": ["Spain","España","Spanien","Spagna","Espanha","Spanje","İspanya"],
  "France": ["France","Francia","Frankreich","Francia","França","Frankrijk","Fransa"],
  "Danemark": ["Denmark","Dinamarca","Dänemark","Danimarca","Dinamarca","Denemarken","Danimarka"],
  "Grèce": ["Greece","Grecia","Griechenland","Grecia","Grécia","Griekenland","Yunanistan"],

  /* cartes de paris */
  "Cote": ["Odds","Cuota","Quote","Quota","Cota","Odds","Oran"],
  "cote": ["odds","cuota","Quote","quota","cota","odds","oran"],
  "Mise": ["Stake","Apuesta","Einsatz","Puntata","Aposta","Inzet","Bahis tutarı"],
  "mise": ["stake","apuesta","Einsatz","puntata","aposta","inzet","bahis tutarı"],
  "Ma mise": ["My stake","Mi apuesta","Mein Einsatz","La mia puntata","A minha aposta","Mijn inzet","Bahsim"],
  "Mise conseillée": ["Suggested stake","Apuesta recomendada","Empfohlener Einsatz","Puntata consigliata","Aposta recomendada","Aanbevolen inzet","Önerilen bahis"],
  "Misé": ["Staked","Apostado","Eingesetzt","Puntato","Apostado","Ingezet","Yatırılan"],
  "Total misé": ["Total staked","Total apostado","Gesamteinsatz","Totale puntato","Total apostado","Totale inzet","Toplam bahis"],
  "total misé": ["total staked","total apostado","Gesamteinsatz","totale puntato","total apostado","totale inzet","toplam bahis"],
  "Gain net": ["Net gain","Ganancia neta","Nettogewinn","Guadagno netto","Ganho líquido","Nettowinst","Net kazanç"],
  "gain": ["gain","ganancia","Gewinn","guadagno","ganho","winst","kazanç"],
  "Plus gros gain": ["Biggest win","Mayor ganancia","Höchster Gewinn","Vincita maggiore","Maior ganho","Grootste winst","En büyük kazanç"],
  "Meilleur jour": ["Best day","Mejor día","Bester Tag","Giorno migliore","Melhor dia","Beste dag","En iyi gün"],
  "Jours dans le vert": ["Winning days","Días en positivo","Tage im Plus","Giorni in positivo","Dias no verde","Dagen in de plus","Kârda geçen günler"],
  "Publié": ["Published","Publicado","Veröffentlicht","Pubblicato","Publicado","Gepubliceerd","Yayınlandı"],
  "Publié avant le match": ["Published before the match","Publicado antes del partido","Vor dem Spiel veröffentlicht","Pubblicato prima della partita","Publicado antes do jogo","Voor de wedstrijd gepubliceerd","Maçtan önce yayınlandı"],
  "Résultat": ["Result","Resultado","Ergebnis","Risultato","Resultado","Resultaat","Sonuç"],
  "résultat": ["result","resultado","Ergebnis","risultato","resultado","resultaat","sonuç"],
  "Détail": ["Details","Detalle","Details","Dettaglio","Detalhe","Details","Ayrıntı"],
  "Début du match": ["Match start","Inicio del partido","Spielbeginn","Inizio della partita","Início do jogo","Start van de wedstrijd","Maç başlangıcı"],
  "Ligue": ["League","Liga","Liga","Campionato","Liga","Competitie","Lig"],
  "Match": ["Match","Partido","Spiel","Partita","Jogo","Wedstrijd","Maç"],
  "Sport": ["Sport","Deporte","Sportart","Sport","Desporto","Sport","Spor"],
  "Pari joueur": ["Player bet","Apuesta de jugador","Spielerwette","Scommessa sul giocatore","Aposta em jogador","Spelerweddenschap","Oyuncu bahsi"],
  "Paris joueurs": ["Player bets","Apuestas de jugadores","Spielerwetten","Scommesse sui giocatori","Apostas em jogadores","Spelerweddenschappen","Oyuncu bahisleri"],
  "Value bet": ["Value bet","Apuesta de valor","Value Bet","Value bet","Aposta de valor","Value bet","Değerli bahis"],
  "value bet": ["value bet","apuesta de valor","Value Bet","value bet","aposta de valor","value bet","değerli bahis"],
  "Handicap": ["Handicap","Hándicap","Handicap","Handicap","Handicap","Handicap","Handikap"],
  "Simulation": ["Simulation","Simulación","Simulation","Simulazione","Simulação","Simulatie","Simülasyon"],
  "simulation": ["simulation","simulación","Simulation","simulazione","simulação","simulatie","simülasyon"],
  "Plus de": ["Over","Más de","Über","Più di","Mais de","Meer dan","Üst"],
  "Moins de": ["Under","Menos de","Unter","Meno di","Menos de","Minder dan","Alt"],
  "Plus de / moins de": ["Over / under","Más de / menos de","Über / unter","Più di / meno di","Mais de / menos de","Meer dan / minder dan","Üst / alt"],
  "Points": ["Points","Puntos","Punkte","Punti","Pontos","Punten","Sayı"],
  "points": ["points","puntos","Punkte","punti","pontos","punten","sayı"],
  "rebonds": ["rebounds","rebotes","Rebounds","rimbalzi","ressaltos","rebounds","ribaund"],
  "passes": ["assists","asistencias","Assists","assist","assistências","assists","asist"],
  "paniers à 3 pts": ["3-pointers","triples","Dreier","triple","triplos","driepunters","3'lükler"],
  "Paniers à 3 pts": ["3-pointers","Triples","Dreier","Triple","Triplos","Driepunters","3'lükler"],
  "tirs cadrés": ["shots on target","tiros a puerta","Schüsse aufs Tor","tiri in porta","remates à baliza","schoten op doel","isabetli şut"],
  "Tirs cadrés": ["Shots on target","Tiros a puerta","Schüsse aufs Tor","Tiri in porta","Remates à baliza","Schoten op doel","İsabetli şut"],
  "réceptions": ["receptions","recepciones","Receptions","ricezioni","receções","ontvangsten","yakalayışlar"],
  "Réceptions": ["Receptions","Recepciones","Receptions","Ricezioni","Receções","Ontvangsten","Yakalayışlar"],
  "sets": ["sets","sets","Sätze","set","sets","sets","set"],
  "Total sets": ["Total sets","Total de sets","Sätze gesamt","Totale set","Total de sets","Totaal sets","Toplam set"],
  "Tennis Total sets": ["Tennis total sets","Tenis total de sets","Tennis Sätze gesamt","Tennis totale set","Ténis total de sets","Tennis totaal sets","Tenis toplam set"],
  "buts": ["goals","goles","Tore","gol","golos","doelpunten","gol"],
  "Handicap −1,5": ["Handicap −1.5","Hándicap −1,5","Handicap −1,5","Handicap −1,5","Handicap −1,5","Handicap −1,5","Handikap −1,5"],
  "Aces": ["Aces","Aces","Asse","Ace","Ases","Azen","Servis ası"],
  "Doubles fautes": ["Double faults","Dobles faltas","Doppelfehler","Doppi falli","Duplas faltas","Dubbele fouten","Çift hatalar"],
  "Au service": ["Serving","Al saque","Aufschlag","Al servizio","Ao serviço","Aan de opslag","Servis"],
  "1re balle": ["1st serve","1.er saque","1. Aufschlag","1ª di servizio","1.º serviço","1e service","1. servis"],
  "Balles de break sauvées": ["Break points saved","Bolas de break salvadas","Abgewehrte Breakbälle","Palle break salvate","Break points salvos","Gered breekpunten","Kurtarılan break topları"],
  "Pts gagnés 1re balle": ["Points won on 1st serve","Puntos ganados con 1.er saque","Gewonnene Punkte 1. Aufschlag","Punti vinti con la prima","Pontos ganhos no 1.º serviço","Gewonnen punten 1e service","1. servis kazanılan sayı"],
  "Pts gagnés 2e balle": ["Points won on 2nd serve","Puntos ganados con 2.º saque","Gewonnene Punkte 2. Aufschlag","Punti vinti con la seconda","Pontos ganhos no 2.º serviço","Gewonnen punten 2e service","2. servis kazanılan sayı"],
  "Retour sur 1re balle": ["Return on 1st serve","Resto sobre 1.er saque","Return auf 1. Aufschlag","Risposta sulla prima","Resposta ao 1.º serviço","Return op 1e service","1. servis karşılama"],
  "Retour sur 2e balle": ["Return on 2nd serve","Resto sobre 2.º saque","Return auf 2. Aufschlag","Risposta sulla seconda","Resposta ao 2.º serviço","Return op 2e service","2. servis karşılama"],
  "Totaux avec vent": ["Totals with wind","Totales con viento","Totals bei Wind","Totali con vento","Totais com vento","Totalen met wind","Rüzgarlı toplamlar"],
  "Points mérités": ["Earned points","Puntos merecidos","Verdiente Punkte","Punti meritati","Pontos merecidos","Verdiende punten","Hak edilen sayılar"],
  "Cote bookmaker": ["Bookmaker odds","Cuota de la casa","Buchmacher-Quote","Quota del bookmaker","Cota da casa","Bookmakerodds","Bahis şirketi oranı"],
  "cote relevée chez un bookmaker": ["odds taken from a bookmaker","cuota tomada de una casa de apuestas","bei einem Buchmacher abgelesene Quote","quota rilevata presso un bookmaker","cota recolhida numa casa de apostas","odds bij een bookmaker genoteerd","bir bahis şirketinden alınan oran"],
  "cote Pinnacle": ["Pinnacle odds","cuota Pinnacle","Pinnacle-Quote","quota Pinnacle","cota Pinnacle","Pinnacle-odds","Pinnacle oranı"],
  "cote de clôture": ["closing odds","cuota de cierre","Schlussquote","quota di chiusura","cota de fecho","slotodds","kapanış oranı"],
  "cote médiane": ["median odds","cuota mediana","Median-Quote","quota mediana","cota mediana","mediane odds","medyan oran"],
  "meilleure cote": ["best odds","mejor cuota","beste Quote","migliore quota","melhor cota","beste odds","en iyi oran"],
  "cote de consensus": ["consensus odds","cuota de consenso","Konsens-Quote","quota di consenso","cota de consenso","consensusodds","konsensüs oranı"],
  "Prolongation incluse": ["Overtime included","Prórroga incluida","Verlängerung inklusive","Supplementari inclusi","Prolongamento incluído","Verlenging inbegrepen","Uzatmalar dahil"],
  "Prolongation incluse.": ["Overtime included.","Prórroga incluida.","Verlängerung inklusive.","Supplementari inclusi.","Prolongamento incluído.","Verlenging inbegrepen.","Uzatmalar dahil."],
  "Prolongations incluses.": ["Overtime included.","Prórrogas incluidas.","Verlängerungen inklusive.","Supplementari inclusi.","Prolongamentos incluídos.","Verlengingen inbegrepen.","Uzatmalar dahil."],
  "Manches supplémentaires incluses.": ["Extra innings included.","Entradas extra incluidas.","Extra-Innings inklusive.","Inning supplementari inclusi.","Entradas extra incluídas.","Extra innings inbegrepen.","Ek devreler dahil."],
  "Match terminé ; abandon avant la fin = remboursé.": ["Match finished; retirement before the end = refunded.","Partido terminado; abandono antes del final = reembolsado.","Spiel beendet; Aufgabe vor dem Ende = erstattet.","Partita finita; ritiro prima della fine = rimborsata.","Jogo terminado; desistência antes do fim = reembolsado.","Wedstrijd afgelopen; opgave voor het einde = terugbetaald.","Maç bitti; bitmeden çekilme = iade."],
  "Résultat réglé depuis le score officiel.": ["Result settled from the official score.","Resultado liquidado según el marcador oficial.","Ergebnis nach offiziellem Spielstand abgerechnet.","Risultato regolato dal punteggio ufficiale.","Resultado liquidado pelo resultado oficial.","Resultaat verrekend op basis van de officiële uitslag.","Sonuç resmi skora göre belirlendi."],
  "Pari rejoué sur le passé avec les cotes de l'époque, jamais publié en direct.": ["Bet replayed on past matches with the odds of the time, never published live.","Apuesta reproducida sobre el pasado con las cuotas de la época, nunca publicada en directo.","Wette rückwirkend mit den damaligen Quoten simuliert, nie live veröffentlicht.","Scommessa rigiocata sul passato con le quote dell'epoca, mai pubblicata in diretta.","Aposta reproduzida no passado com as cotas da época, nunca publicada em direto.","Weddenschap herspeeld op het verleden met de odds van toen, nooit live gepubliceerd.","Geçmiş maçlarda o dönemin oranlarıyla yeniden oynanan bahis, canlı yayınlanmadı."],
  "Depuis le score officiel": ["From the official score","Según el marcador oficial","Nach offiziellem Spielstand","Dal punteggio ufficiale","Pelo resultado oficial","Op basis van de officiële uitslag","Resmi skordan"],

  /* page Resultats */
  "Tous les paris publiés · rien n'est supprimé · réglés depuis le score officiel": ["Every published bet · nothing is ever deleted · settled from the official score","Todas las apuestas publicadas · nada se borra · liquidadas según el marcador oficial","Alle veröffentlichten Tipps · nichts wird gelöscht · nach offiziellem Spielstand abgerechnet","Tutte le scommesse pubblicate · nulla viene cancellato · regolate dal punteggio ufficiale","Todas as apostas publicadas · nada é apagado · liquidadas pelo resultado oficial","Alle gepubliceerde weddenschappen · niets wordt verwijderd · verrekend op de officiële uitslag","Yayınlanan tüm bahisler · hiçbiri silinmez · resmi skora göre sonuçlandırılır"],
  "Tous les paris publiés · rien n'est supprimé": ["Every published bet · nothing is ever deleted","Todas las apuestas publicadas · nada se borra","Alle veröffentlichten Tipps · nichts wird gelöscht","Tutte le scommesse pubblicate · nulla viene cancellato","Todas as apostas publicadas · nada é apagado","Alle gepubliceerde weddenschappen · niets wordt verwijderd","Yayınlanan tüm bahisler · hiçbiri silinmez"],
  "Ma mise : 1 u =": ["My stake: 1 u =","Mi apuesta: 1 u =","Mein Einsatz: 1 u =","La mia puntata: 1 u =","A minha aposta: 1 u =","Mijn inzet: 1 u =","Bahsim: 1 u ="],
  "le bot mise de 0,75 u à 3 u selon sa confiance": ["the bot stakes from 0.75 u to 3 u depending on its confidence","el bot apuesta de 0,75 u a 3 u según su confianza","der Bot setzt je nach Zuversicht 0,75 bis 3 u","il bot punta da 0,75 u a 3 u in base alla sua fiducia","o bot aposta de 0,75 u a 3 u consoante a sua confiança","de bot zet 0,75 tot 3 u in, afhankelijk van zijn vertrouwen","bot, güvenine göre 0,75 ile 3 u arasında bahis yapar"],
  "Le bot mise de 0,75 u à 3 u selon sa confiance.": ["The bot stakes from 0.75 u to 3 u depending on its confidence.","El bot apuesta de 0,75 u a 3 u según su confianza.","Der Bot setzt je nach Zuversicht 0,75 bis 3 u.","Il bot punta da 0,75 u a 3 u in base alla sua fiducia.","O bot aposta de 0,75 u a 3 u consoante a sua confiança.","De bot zet 0,75 tot 3 u in, afhankelijk van zijn vertrouwen.","Bot, güvenine göre 0,75 ile 3 u arasında bahis yapar."],
  "Aujourd'hui": ["Today","Hoy","Heute","Oggi","Hoje","Vandaag","Bugün"],
  "aujourd'hui": ["today","hoy","heute","oggi","hoje","vandaag","bugün"],
  "Cette semaine": ["This week","Esta semana","Diese Woche","Questa settimana","Esta semana","Deze week","Bu hafta"],
  "cette semaine": ["this week","esta semana","diese Woche","questa settimana","esta semana","deze week","bu hafta"],
  "Ce mois": ["This month","Este mes","Dieser Monat","Questo mese","Este mês","Deze maand","Bu ay"],
  "ce mois": ["this month","este mes","dieser Monat","questo mese","este mês","deze maand","bu ay"],
  "Cette année": ["This year","Este año","Dieses Jahr","Quest'anno","Este ano","Dit jaar","Bu yıl"],
  "cette année": ["this year","este año","dieses Jahr","quest'anno","este ano","dit jaar","bu yıl"],
  "Depuis le début": ["Since the start","Desde el principio","Seit Beginn","Dall'inizio","Desde o início","Sinds het begin","Başlangıçtan beri"],
  "depuis le début": ["since the start","desde el principio","seit Beginn","dall'inizio","desde o início","sinds het begin","başlangıçtan beri"],
  "Bilan cumulé": ["Cumulative result","Balance acumulado","Gesamtbilanz","Bilancio cumulato","Balanço acumulado","Cumulatief saldo","Kümülatif sonuç"],
  "Bilan détaillé": ["Detailed breakdown","Balance detallado","Detaillierte Bilanz","Bilancio dettagliato","Balanço detalhado","Gedetailleerd saldo","Ayrıntılı sonuç"],
  "bilan": ["result","balance","Bilanz","bilancio","balanço","saldo","sonuç"],
  "Bénéfice": ["Profit","Beneficio","Gewinn","Profitto","Lucro","Winst","Kâr"],
  "bénéfice": ["profit","beneficio","Gewinn","profitto","lucro","winst","kâr"],
  "Bénéfice cumulé": ["Cumulative profit","Beneficio acumulado","Kumulierter Gewinn","Profitto cumulato","Lucro acumulado","Cumulatieve winst","Kümülatif kâr"],
  "Par sport": ["By sport","Por deporte","Nach Sportart","Per sport","Por desporto","Per sport","Spora göre"],
  "cliquer sur un sport pour filtrer toute la page": ["click a sport to filter the whole page","haz clic en un deporte para filtrar toda la página","Sportart anklicken, um die ganze Seite zu filtern","clicca su uno sport per filtrare tutta la pagina","clique num desporto para filtrar toda a página","klik op een sport om de hele pagina te filteren","tüm sayfayı filtrelemek için bir spora tıklayın"],
  "Détail des paris": ["Bet details","Detalle de las apuestas","Details der Tipps","Dettaglio delle scommesse","Detalhe das apostas","Details van de weddenschappen","Bahis ayrıntıları"],
  "cliquer sur un pari pour voir comment il a été réglé": ["click a bet to see how it was settled","haz clic en una apuesta para ver cómo se liquidó","Tipp anklicken, um die Abrechnung zu sehen","clicca su una scommessa per vedere come è stata regolata","clique numa aposta para ver como foi liquidada","klik op een weddenschap om te zien hoe die is verrekend","nasıl sonuçlandığını görmek için bir bahse tıklayın"],
  "Par jour": ["By day","Por día","Pro Tag","Per giorno","Por dia","Per dag","Güne göre"],
  "Par semaine": ["By week","Por semana","Pro Woche","Per settimana","Por semana","Per week","Haftaya göre"],
  "Par mois": ["By month","Por mes","Pro Monat","Per mese","Por mês","Per maand","Aya göre"],
  "Par année": ["By year","Por año","Pro Jahr","Per anno","Por ano","Per jaar","Yıla göre"],
  "← Plus récents": ["← Newer","← Más recientes","← Neuere","← Più recenti","← Mais recentes","← Nieuwer","← Daha yeni"],
  "Plus anciens →": ["Older →","Más antiguos →","Ältere →","Meno recenti →","Mais antigos →","Ouder →","Daha eski →"],
  "Nombre de paris par page": ["Bets per page","Apuestas por página","Tipps pro Seite","Scommesse per pagina","Apostas por página","Weddenschappen per pagina","Sayfa başına bahis"],
  "Page précédente": ["Previous page","Página anterior","Vorherige Seite","Pagina precedente","Página anterior","Vorige pagina","Önceki sayfa"],
  "Page suivante": ["Next page","Página siguiente","Nächste Seite","Pagina successiva","Página seguinte","Volgende pagina","Sonraki sayfa"],
  "Voir avant": ["See earlier","Ver anteriores","Früheres anzeigen","Vedi precedenti","Ver anteriores","Eerdere bekijken","Öncekini gör"],
  "Voir après": ["See later","Ver siguientes","Späteres anzeigen","Vedi successivi","Ver seguintes","Latere bekijken","Sonrakini gör"],
  "Paris réglés": ["Settled bets","Apuestas liquidadas","Abgerechnete Tipps","Scommesse regolate","Apostas liquidadas","Verrekende weddenschappen","Sonuçlanan bahisler"],
  "paris": ["bets","apuestas","Tipps","scommesse","apostas","weddenschappen","bahis"],
  "Paris": ["Bets","Apuestas","Tipps","Scommesse","Apostas","Weddenschappen","Bahisler"],
  "paris gagnés": ["bets won","apuestas ganadas","gewonnene Tipps","scommesse vinte","apostas ganhas","gewonnen weddenschappen","kazanılan bahisler"],
  "Paris à cote bookmaker": ["Bets with bookmaker odds","Apuestas con cuota de casa","Tipps mit Buchmacher-Quote","Scommesse con quota bookmaker","Apostas com cota da casa","Weddenschappen met bookmakerodds","Bahis şirketi oranlı bahisler"],
  "Retour · tous les paris": ["Return · all bets","Retorno · todas las apuestas","Rendite · alle Tipps","Ritorno · tutte le scommesse","Retorno · todas as apostas","Rendement · alle weddenschappen","Getiri · tüm bahisler"],
  "Retour · paris à cote bookmaker": ["Return · bets with bookmaker odds","Retorno · apuestas con cuota de casa","Rendite · Tipps mit Buchmacher-Quote","Ritorno · scommesse con quota bookmaker","Retorno · apostas com cota da casa","Rendement · weddenschappen met bookmakerodds","Getiri · bahis şirketi oranlı bahisler"],
  "retour (ROI)": ["return (ROI)","retorno (ROI)","Rendite (ROI)","ritorno (ROI)","retorno (ROI)","rendement (ROI)","getiri (ROI)"],
  "Réussite": ["Win rate","Acierto","Trefferquote","Percentuale vinta","Taxa de acerto","Slagingspercentage","Başarı"],
  "taux de réussite": ["win rate","tasa de acierto","Trefferquote","percentuale di successo","taxa de acerto","slagingspercentage","başarı oranı"],
  "ROI": ["ROI","ROI","ROI","ROI","ROI","ROI","ROI"],
  "Retour": ["Return","Retorno","Rendite","Ritorno","Retorno","Rendement","Getiri"],
  "Rendement du jour": ["Today's return","Rendimiento del día","Tagesrendite","Rendimento del giorno","Rendimento do dia","Rendement van vandaag","Günün getirisi"],
  "Départ · 0,00 €": ["Start · €0.00","Inicio · 0,00 €","Start · 0,00 €","Inizio · 0,00 €","Início · 0,00 €","Start · € 0,00","Başlangıç · 0,00 €"],
  "Ce qui compte": ["What matters","Lo que cuenta","Was zählt","Ciò che conta","O que conta","Wat telt","Önemli olan"],
  "Jamais après le coup d'envoi": ["Never after kick-off","Nunca después del inicio","Nie nach dem Anpfiff","Mai dopo il calcio d'inizio","Nunca depois do apito inicial","Nooit na het beginsignaal","Asla maç başladıktan sonra"],
  "Jamais supprimé": ["Never deleted","Nunca se borra","Nie gelöscht","Mai cancellato","Nunca apagado","Nooit verwijderd","Asla silinmez"],
  "Réglé automatiquement": ["Settled automatically","Liquidado automáticamente","Automatisch abgerechnet","Regolato automaticamente","Liquidado automaticamente","Automatisch verrekend","Otomatik sonuçlanır"],
  "Les paris perdus restent affichés": ["Lost bets stay visible","Las apuestas perdidas siguen visibles","Verlorene Tipps bleiben sichtbar","Le scommesse perse restano visibili","As apostas perdidas continuam visíveis","Verloren weddenschappen blijven zichtbaar","Kaybedilen bahisler görünür kalır"],
  "Le même bilan, converti dans votre mise": ["The same results, converted to your stake","El mismo balance, convertido a su apuesta","Dieselbe Bilanz, umgerechnet auf Ihren Einsatz","Lo stesso bilancio, convertito nella tua puntata","O mesmo balanço, convertido para a sua aposta","Hetzelfde saldo, omgerekend naar jouw inzet","Aynı sonuç, bahsinize çevrilmiş hali"],
  "Derniers paris": ["Latest bets","Últimas apuestas","Letzte Tipps","Ultime scommesse","Últimas apostas","Laatste weddenschappen","Son bahisler"],
  "Derniers paris avec votre mise": ["Latest bets with your stake","Últimas apuestas con su apuesta","Letzte Tipps mit Ihrem Einsatz","Ultime scommesse con la tua puntata","Últimas apostas com a sua aposta","Laatste weddenschappen met jouw inzet","Bahsinizle son bahisler"],
  "Valeur de 1 u": ["Value of 1 u","Valor de 1 u","Wert von 1 u","Valore di 1 u","Valor de 1 u","Waarde van 1 u","1 u değeri"],
  "Unité (u)": ["Unit (u)","Unidad (u)","Einheit (u)","Unità (u)","Unidade (u)","Eenheid (u)","Birim (u)"],
  "Unité, ROI, simulation": ["Unit, ROI, simulation","Unidad, ROI, simulación","Einheit, ROI, Simulation","Unità, ROI, simulazione","Unidade, ROI, simulação","Eenheid, ROI, simulatie","Birim, ROI, simülasyon"],
  "Total (buts, points, sets, jeux…) au-dessus ou en dessous de la ligne.": ["Total (goals, points, sets, games…) above or below the line.","Total (goles, puntos, sets, juegos…) por encima o por debajo de la línea.","Gesamtwert (Tore, Punkte, Sätze, Spiele …) über oder unter der Linie.","Totale (gol, punti, set, game…) sopra o sotto la linea.","Total (golos, pontos, sets, jogos…) acima ou abaixo da linha.","Totaal (doelpunten, punten, sets, games…) boven of onder de lijn.","Toplam (gol, sayı, set, oyun…) çizginin üstünde veya altında."],
  "Statistique d'un joueur comparée à une ligne (points, tirs cadrés, réceptions…).": ["A player's stat compared with a line (points, shots on target, receptions…).","Estadística de un jugador comparada con una línea (puntos, tiros a puerta, recepciones…).","Spielerstatistik im Vergleich zu einer Linie (Punkte, Schüsse aufs Tor, Receptions …).","Statistica di un giocatore confrontata con una linea (punti, tiri in porta, ricezioni…).","Estatística de um jogador comparada com uma linha (pontos, remates à baliza, receções…).","Statistiek van een speler vergeleken met een lijn (punten, schoten op doel, ontvangsten…).","Bir oyuncunun istatistiğinin bir çizgiyle karşılaştırılması (sayı, isabetli şut, yakalayış…)."],
  "Avance ou retard fictif donné à une équipe avant le match (−1,5 : gagner de 2 ou plus).": ["A head start or deficit given to a team before the match (−1.5: must win by 2 or more).","Ventaja o desventaja ficticia dada a un equipo antes del partido (−1,5: ganar por 2 o más).","Fiktiver Vorsprung oder Rückstand für ein Team vor dem Spiel (−1,5: Sieg mit 2 oder mehr Toren Unterschied).","Vantaggio o svantaggio fittizio dato a una squadra prima della partita (−1,5: vincere con 2 o più di scarto).","Vantagem ou desvantagem fictícia dada a uma equipa antes do jogo (−1,5: ganhar por 2 ou mais).","Fictieve voorsprong of achterstand voor een team voor de wedstrijd (−1,5: met 2 of meer verschil winnen).","Maçtan önce bir takıma verilen kurgusal avantaj veya dezavantaj (−1,5: 2 veya daha fazla farkla kazanmak)."],
  "Pari dont la cote est plus haute que la probabilité réelle estimée.": ["A bet whose odds are higher than the estimated real probability.","Apuesta cuya cuota es más alta que la probabilidad real estimada.","Wette, deren Quote höher ist als die geschätzte tatsächliche Wahrscheinlichkeit.","Scommessa la cui quota è più alta della probabilità reale stimata.","Aposta cuja cota é mais alta do que a probabilidade real estimada.","Weddenschap waarvan de odds hoger zijn dan de geschatte werkelijke kans.","Oranı, tahmin edilen gerçek olasılıktan yüksek olan bahis."],

  /* aide */
  "Centre d'aide": ["Help centre","Centro de ayuda","Hilfezentrum","Centro assistenza","Centro de ajuda","Helpcentrum","Yardım merkezi"],
  "Tout ce qu'il faut savoir pour lire nos paris, suivre les résultats et jouer sereinement.": ["Everything you need to read our bets, follow the results and play with peace of mind.","Todo lo que necesitas saber para leer nuestras apuestas, seguir los resultados y jugar con tranquilidad.","Alles, was Sie wissen müssen, um unsere Tipps zu lesen, die Ergebnisse zu verfolgen und gelassen zu spielen.","Tutto ciò che serve per leggere le nostre scommesse, seguire i risultati e giocare con serenità.","Tudo o que precisa de saber para ler as nossas apostas, acompanhar os resultados e jogar com tranquilidade.","Alles wat je moet weten om onze weddenschappen te lezen, de resultaten te volgen en rustig te spelen.","Bahislerimizi okumak, sonuçları takip etmek ve rahatça oynamak için bilmeniz gereken her şey."],
  "Rechercher dans l'aide": ["Search the help","Buscar en la ayuda","Hilfe durchsuchen","Cerca nell'aiuto","Pesquisar na ajuda","Zoeken in de help","Yardımda ara"],
  "Rechercher : cote, handicap, remboursé, unité…": ["Search: odds, handicap, refunded, unit…","Buscar: cuota, hándicap, reembolsado, unidad…","Suchen: Quote, Handicap, erstattet, Einheit …","Cerca: quota, handicap, rimborsata, unità…","Pesquisar: cota, handicap, reembolsado, unidade…","Zoeken: odds, handicap, terugbetaald, eenheid…","Ara: oran, handikap, iade, birim…"],
  "Rubriques de l'aide": ["Help topics","Temas de ayuda","Hilfethemen","Argomenti della guida","Tópicos de ajuda","Helponderwerpen","Yardım konuları"],
  "Aucune réponse ne correspond. Essayez un autre mot, ou écrivez-nous sur Telegram.": ["No answer matches. Try another word, or write to us on Telegram.","Ninguna respuesta coincide. Prueba otra palabra o escríbenos por Telegram.","Keine Antwort gefunden. Versuchen Sie ein anderes Wort oder schreiben Sie uns auf Telegram.","Nessuna risposta corrisponde. Prova un'altra parola o scrivici su Telegram.","Nenhuma resposta corresponde. Tente outra palavra ou escreva-nos no Telegram.","Geen antwoord gevonden. Probeer een ander woord of schrijf ons op Telegram.","Eşleşen yanıt yok. Başka bir kelime deneyin veya Telegram'dan bize yazın."],
  "Vous n'avez pas trouvé votre réponse ?": ["Didn't find your answer?","¿No has encontrado tu respuesta?","Keine Antwort gefunden?","Non hai trovato la tua risposta?","Não encontrou a sua resposta?","Je antwoord niet gevonden?","Yanıtınızı bulamadınız mı?"],
  "Écrivez-nous sur le canal Telegram, on répond à chaque question.": ["Write to us on the Telegram channel, we answer every question.","Escríbenos en el canal de Telegram, respondemos a cada pregunta.","Schreiben Sie uns im Telegram-Kanal, wir beantworten jede Frage.","Scrivici sul canale Telegram, rispondiamo a ogni domanda.","Escreva-nos no canal do Telegram, respondemos a todas as perguntas.","Schrijf ons in het Telegram-kanaal, we beantwoorden elke vraag.","Telegram kanalından bize yazın, her soruyu yanıtlıyoruz."],
  "Nous écrire sur Telegram": ["Write to us on Telegram","Escríbenos por Telegram","Schreiben Sie uns auf Telegram","Scrivici su Telegram","Escreva-nos no Telegram","Schrijf ons op Telegram","Bize Telegram'dan yazın"],
  "🚀 Bien démarrer": ["🚀 Getting started","🚀 Primeros pasos","🚀 Erste Schritte","🚀 Per iniziare","🚀 Primeiros passos","🚀 Aan de slag","🚀 Başlarken"],
  "🎫 Lire un pari": ["🎫 Reading a bet","🎫 Leer una apuesta","🎫 Einen Tipp lesen","🎫 Leggere una scommessa","🎫 Ler uma aposta","🎫 Een weddenschap lezen","🎫 Bir bahsi okumak"],
  "⚖️ Règlement": ["⚖️ Settlement","⚖️ Liquidación","⚖️ Abrechnung","⚖️ Regolamento","⚖️ Liquidação","⚖️ Afrekening","⚖️ Sonuçlandırma"],
  "⚖️ Règlement des paris": ["⚖️ Bet settlement","⚖️ Liquidación de apuestas","⚖️ Abrechnung der Tipps","⚖️ Regolamento delle scommesse","⚖️ Liquidação das apostas","⚖️ Afrekening van weddenschappen","⚖️ Bahislerin sonuçlandırılması"],
  "📊 Résultats et chiffres": ["📊 Results and figures","📊 Resultados y cifras","📊 Ergebnisse und Zahlen","📊 Risultati e numeri","📊 Resultados e números","📊 Resultaten en cijfers","📊 Sonuçlar ve rakamlar"],
  "👤 Compte et Telegram": ["👤 Account and Telegram","👤 Cuenta y Telegram","👤 Konto und Telegram","👤 Account e Telegram","👤 Conta e Telegram","👤 Account en Telegram","👤 Hesap ve Telegram"],
  "🛟 Jeu responsable": ["🛟 Responsible gambling","🛟 Juego responsable","🛟 Verantwortungsvolles Spielen","🛟 Gioco responsabile","🛟 Jogo responsável","🛟 Verantwoord gokken","🛟 Sorumlu oyun"],
  "📖 Lexique": ["📖 Glossary","📖 Glosario","📖 Glossar","📖 Glossario","📖 Glossário","📖 Woordenlijst","📖 Sözlük"],
  "Le principe, en 2 minutes": ["The idea, in 2 minutes","La idea, en 2 minutos","Das Prinzip in 2 Minuten","Il principio, in 2 minuti","O princípio, em 2 minutos","Het principe, in 2 minuten","Prensip, 2 dakikada"],
  "Cote, mise, marchés": ["Odds, stake, markets","Cuota, apuesta, mercados","Quote, Einsatz, Märkte","Quota, puntata, mercati","Cota, aposta, mercados","Odds, inzet, markten","Oran, bahis, pazarlar"],
  "Gagné, perdu, remboursé": ["Won, lost, refunded","Ganado, perdido, reembolsado","Gewonnen, verloren, erstattet","Vinta, persa, rimborsata","Ganho, perdido, reembolsado","Gewonnen, verloren, terugbetaald","Kazanıldı, kaybedildi, iade"],
  "Inscription, discussions": ["Sign-up, discussions","Registro, debates","Registrierung, Diskussionen","Registrazione, discussioni","Registo, discussões","Registratie, discussies","Kayıt, tartışmalar"],
  "Limites, aide, contacts": ["Limits, help, contacts","Límites, ayuda, contactos","Limits, Hilfe, Kontakte","Limiti, aiuto, contatti","Limites, ajuda, contactos","Limieten, hulp, contacten","Limitler, yardım, iletişim"],
  "G-BET, c'est quoi ?": ["What is G-BET?","¿Qué es G-BET?","Was ist G-BET?","Cos'è G-BET?","O que é o G-BET?","Wat is G-BET?","G-BET nedir?"],
  "Comment utiliser le site en 3 étapes ?": ["How to use the site in 3 steps?","¿Cómo usar el sitio en 3 pasos?","Wie nutzt man die Seite in 3 Schritten?","Come usare il sito in 3 passaggi?","Como usar o site em 3 passos?","Hoe gebruik je de site in 3 stappen?","Siteyi 3 adımda nasıl kullanırım?"],
  "Quels sports sont couverts ?": ["Which sports are covered?","¿Qué deportes se cubren?","Welche Sportarten werden abgedeckt?","Quali sport sono coperti?","Que desportos são cobertos?","Welke sporten worden gedekt?","Hangi sporlar kapsanıyor?"],
  "Combien de paris par jour ?": ["How many bets a day?","¿Cuántas apuestas al día?","Wie viele Tipps pro Tag?","Quante scommesse al giorno?","Quantas apostas por dia?","Hoeveel weddenschappen per dag?","Günde kaç bahis?"],
  "Combien miser ?": ["How much to stake?","¿Cuánto apostar?","Wie viel setzen?","Quanto puntare?","Quanto apostar?","Hoeveel inzetten?","Ne kadar bahis yapmalı?"],
  "Pourquoi les mises changent d'un pari à l'autre ?": ["Why do stakes change from one bet to another?","¿Por qué cambian las apuestas de una a otra?","Warum ändern sich die Einsätze von Tipp zu Tipp?","Perché le puntate cambiano da una scommessa all'altra?","Porque é que as apostas mudam de uma para outra?","Waarom verschillen de inzetten per weddenschap?","Bahis tutarları neden birbirinden farklı?"],
  "Et si la cote a bougé quand je veux parier ?": ["What if the odds have moved when I want to bet?","¿Y si la cuota ha cambiado cuando quiero apostar?","Und wenn sich die Quote bewegt hat, wenn ich wetten will?","E se la quota è cambiata quando voglio puntare?","E se a cota mudou quando quero apostar?","En als de odds zijn veranderd als ik wil wedden?","Bahis yapmak istediğimde oran değişmişse?"],
  "Plusieurs paris sur le même match ?": ["Several bets on the same match?","¿Varias apuestas en el mismo partido?","Mehrere Tipps auf dasselbe Spiel?","Più scommesse sulla stessa partita?","Várias apostas no mesmo jogo?","Meerdere weddenschappen op dezelfde wedstrijd?","Aynı maçta birden fazla bahis?"],
  "Que veut dire chaque ligne d'une carte ?": ["What does each line of a card mean?","¿Qué significa cada línea de una tarjeta?","Was bedeutet jede Zeile einer Karte?","Cosa significa ogni riga di una scheda?","O que significa cada linha de um cartão?","Wat betekent elke regel van een kaart?","Bir kartın her satırı ne anlama gelir?"],
  "Que veulent dire « handicap », « plus de / moins de », « paris joueurs » ?": ["What do “handicap”, “over / under” and “player bets” mean?","¿Qué significan «hándicap», «más de / menos de» y «apuestas de jugadores»?","Was bedeuten „Handicap“, „über / unter“ und „Spielerwetten“?","Cosa significano «handicap», «più di / meno di» e «scommesse sui giocatori»?","O que significam «handicap», «mais de / menos de» e «apostas em jogadores»?","Wat betekenen ‘handicap’, ‘meer dan / minder dan’ en ‘spelerweddenschappen’?","«Handikap», «üst / alt» ve «oyuncu bahisleri» ne demek?"],
  "Qui décide qu'un pari est gagné ou perdu ?": ["Who decides whether a bet is won or lost?","¿Quién decide si una apuesta se gana o se pierde?","Wer entscheidet, ob ein Tipp gewonnen oder verloren ist?","Chi decide se una scommessa è vinta o persa?","Quem decide se uma aposta é ganha ou perdida?","Wie beslist of een weddenschap gewonnen of verloren is?","Bir bahsin kazandığına veya kaybettiğine kim karar verir?"],
  "Quand un pari est-il remboursé ?": ["When is a bet refunded?","¿Cuándo se reembolsa una apuesta?","Wann wird ein Tipp erstattet?","Quando una scommessa viene rimborsata?","Quando é que uma aposta é reembolsada?","Wanneer wordt een weddenschap terugbetaald?","Bir bahis ne zaman iade edilir?"],
  "Un pari reste « en cours » alors que le match est fini ?": ["A bet is still “in progress” but the match is over?","¿Una apuesta sigue «en curso» aunque el partido ha terminado?","Ein Tipp ist noch „laufend“, obwohl das Spiel vorbei ist?","Una scommessa resta «in corso» anche se la partita è finita?","Uma aposta continua «em curso» embora o jogo tenha acabado?","Een weddenschap staat nog ‘bezig’ terwijl de wedstrijd voorbij is?","Maç bitti ama bahis hâlâ «devam ediyor» mu?"],
  "Bénéfice, ROI, taux de réussite : lequel regarder ?": ["Profit, ROI, win rate: which one to watch?","Beneficio, ROI, tasa de acierto: ¿cuál mirar?","Gewinn, ROI, Trefferquote: worauf achten?","Profitto, ROI, percentuale di successo: quale guardare?","Lucro, ROI, taxa de acerto: qual observar?","Winst, ROI, slagingspercentage: waar op letten?","Kâr, ROI, başarı oranı: hangisine bakmalı?"],
  "Pourquoi deux chiffres de retour ?": ["Why two return figures?","¿Por qué dos cifras de retorno?","Warum zwei Renditezahlen?","Perché due cifre di ritorno?","Porque há dois números de retorno?","Waarom twee rendementscijfers?","Neden iki getiri rakamı?"],
  "C'est quoi une unité (u) ?": ["What is a unit (u)?","¿Qué es una unidad (u)?","Was ist eine Einheit (u)?","Cos'è un'unità (u)?","O que é uma unidade (u)?","Wat is een eenheid (u)?","Birim (u) nedir?"],
  "C'est quoi les paris « simulation » ?": ["What are “simulation” bets?","¿Qué son las apuestas de «simulación»?","Was sind „Simulations“-Tipps?","Cosa sono le scommesse «simulazione»?","O que são as apostas de «simulação»?","Wat zijn ‘simulatie’-weddenschappen?","«Simülasyon» bahisleri nedir?"],
  "Pourquoi un sport affiche « 0 paris » ?": ["Why does a sport show “0 bets”?","¿Por qué un deporte muestra «0 apuestas»?","Warum zeigt eine Sportart „0 Tipps“?","Perché uno sport mostra «0 scommesse»?","Porque é que um desporto mostra «0 apostas»?","Waarom toont een sport ‘0 weddenschappen’?","Bir spor neden «0 bahis» gösteriyor?"],
  "Pourquoi créer un compte ?": ["Why create an account?","¿Por qué crear una cuenta?","Warum ein Konto erstellen?","Perché creare un account?","Porquê criar uma conta?","Waarom een account aanmaken?","Neden hesap oluşturmalı?"],
  "Telegram ou site, quelle différence ?": ["Telegram or website, what's the difference?","Telegram o sitio, ¿cuál es la diferencia?","Telegram oder Website, was ist der Unterschied?","Telegram o sito, qual è la differenza?","Telegram ou site, qual é a diferença?","Telegram of website, wat is het verschil?","Telegram mı site mi, fark nedir?"],
  "Le service est-il payant ?": ["Is the service paid?","¿El servicio es de pago?","Ist der Dienst kostenpflichtig?","Il servizio è a pagamento?","O serviço é pago?","Is de dienst betaald?","Hizmet ücretli mi?"],
  "Est-ce que les gains sont garantis ?": ["Are winnings guaranteed?","¿Están garantizadas las ganancias?","Sind Gewinne garantiert?","Le vincite sono garantite?","Os ganhos são garantidos?","Zijn winsten gegarandeerd?","Kazançlar garanti mi?"],
  "Je pense jouer trop, que faire ?": ["I think I'm gambling too much, what should I do?","Creo que juego demasiado, ¿qué hago?","Ich glaube, ich spiele zu viel – was tun?","Penso di giocare troppo, cosa faccio?","Acho que jogo demais, o que fazer?","Ik denk dat ik te veel speel, wat nu?","Çok oynadığımı düşünüyorum, ne yapmalıyım?"],
  "Les règles exactes, sport par sport": ["The exact rules, sport by sport","Las reglas exactas, deporte por deporte","Die genauen Regeln, Sportart für Sportart","Le regole esatte, sport per sport","As regras exatas, desporto a desporto","De exacte regels, sport voor sport","Kesin kurallar, spor spor"],

  /* connexion / discussion */
  "Connexion": ["Log in","Inicio de sesión","Anmeldung","Accesso","Início de sessão","Inloggen","Giriş"],
  "Connexion impossible": ["Unable to log in","No se pudo iniciar sesión","Anmeldung nicht möglich","Accesso impossibile","Não foi possível iniciar sessão","Inloggen niet mogelijk","Giriş yapılamadı"],
  "Connexion requise": ["Login required","Inicio de sesión necesario","Anmeldung erforderlich","Accesso richiesto","Início de sessão necessário","Inloggen vereist","Giriş gerekli"],
  "Créer un compte": ["Create an account","Crear una cuenta","Konto erstellen","Crea un account","Criar uma conta","Account aanmaken","Hesap oluştur"],
  "Créer mon compte": ["Create my account","Crear mi cuenta","Mein Konto erstellen","Crea il mio account","Criar a minha conta","Mijn account aanmaken","Hesabımı oluştur"],
  "Pseudo": ["Username","Apodo","Benutzername","Nome utente","Nome de utilizador","Gebruikersnaam","Kullanıcı adı"],
  "Mot de passe": ["Password","Contraseña","Passwort","Password","Palavra-passe","Wachtwoord","Şifre"],
  "Rester connecté sur cet appareil": ["Stay signed in on this device","Mantener la sesión en este dispositivo","Auf diesem Gerät angemeldet bleiben","Resta connesso su questo dispositivo","Manter sessão iniciada neste dispositivo","Ingelogd blijven op dit apparaat","Bu cihazda oturumu açık tut"],
  "Le compte sert uniquement à écrire dans les discussions.": ["The account is only used to write in the discussions.","La cuenta solo sirve para escribir en los debates.","Das Konto dient nur zum Schreiben in den Diskussionen.","L'account serve solo per scrivere nelle discussioni.","A conta serve apenas para escrever nas discussões.","Het account dient alleen om in de discussies te schrijven.","Hesap yalnızca tartışmalara yazmak için kullanılır."],
  "Le compte sert à participer aux discussions sous chaque match, avec votre pseudo. Les paris et résultats restent visibles sans compte.": ["The account lets you join the discussion under each match with your username. Bets and results remain visible without an account.","La cuenta sirve para participar en los debates de cada partido con tu apodo. Las apuestas y los resultados siguen siendo visibles sin cuenta.","Mit dem Konto können Sie unter jedem Spiel mit Ihrem Benutzernamen mitdiskutieren. Tipps und Ergebnisse bleiben auch ohne Konto sichtbar.","L'account serve per partecipare alle discussioni sotto ogni partita con il tuo nome utente. Scommesse e risultati restano visibili senza account.","A conta serve para participar nas discussões de cada jogo com o seu nome de utilizador. As apostas e os resultados continuam visíveis sem conta.","Met het account doe je mee aan de discussie bij elke wedstrijd met je gebruikersnaam. Weddenschappen en resultaten blijven zonder account zichtbaar.","Hesap, her maçın altındaki tartışmalara kullanıcı adınızla katılmanızı sağlar. Bahisler ve sonuçlar hesapsız da görünür."],
  "Votre pseudo est visible dans les discussions. 18+.": ["Your username is visible in the discussions. 18+.","Tu apodo es visible en los debates. +18.","Ihr Benutzername ist in den Diskussionen sichtbar. 18+.","Il tuo nome utente è visibile nelle discussioni. 18+.","O seu nome de utilizador é visível nas discussões. 18+.","Je gebruikersnaam is zichtbaar in de discussies. 18+.","Kullanıcı adınız tartışmalarda görünür. 18+."],
  "Message refusé": ["Message rejected","Mensaje rechazado","Nachricht abgelehnt","Messaggio rifiutato","Mensagem recusada","Bericht geweigerd","Mesaj reddedildi"],
  "Serveur injoignable, réessayez dans un instant.": ["Server unreachable, please try again in a moment.","Servidor inaccesible, inténtalo de nuevo en un momento.","Server nicht erreichbar, bitte gleich erneut versuchen.","Server non raggiungibile, riprova tra un attimo.","Servidor inacessível, tente novamente daqui a pouco.","Server onbereikbaar, probeer het zo opnieuw.","Sunucuya ulaşılamıyor, birazdan tekrar deneyin."],
  "Discussion": ["Discussion","Debate","Diskussion","Discussione","Discussão","Discussie","Tartışma"],
  "Discussion du match": ["Match discussion","Debate del partido","Spieldiskussion","Discussione della partita","Discussão do jogo","Wedstrijddiscussie","Maç tartışması"],
  "Ouvrir la discussion": ["Open the discussion","Abrir el debate","Diskussion öffnen","Apri la discussione","Abrir a discussão","Discussie openen","Tartışmayı aç"],
  "Écrire un message… (connexion requise)": ["Write a message… (login required)","Escribe un mensaje… (requiere iniciar sesión)","Nachricht schreiben … (Anmeldung erforderlich)","Scrivi un messaggio… (accesso richiesto)","Escreva uma mensagem… (início de sessão necessário)","Schrijf een bericht… (inloggen vereist)","Bir mesaj yazın… (giriş gerekli)"],
  "Envoyer": ["Send","Enviar","Senden","Invia","Enviar","Versturen","Gönder"],
  "Revenir": ["Go back","Volver","Zurück","Torna indietro","Voltar","Terug","Geri dön"],
  "Afficher": ["Show","Mostrar","Anzeigen","Mostra","Mostrar","Tonen","Göster"],
  "🔇 Son": ["🔇 Sound","🔇 Sonido","🔇 Ton","🔇 Suono","🔇 Som","🔇 Geluid","🔇 Ses"],
  "Petit son quand un pari est réglé": ["A short sound when a bet is settled","Un pequeño sonido cuando se liquida una apuesta","Kurzer Ton, wenn ein Tipp abgerechnet wird","Un breve suono quando una scommessa viene regolata","Um pequeno som quando uma aposta é liquidada","Een kort geluid wanneer een weddenschap is verrekend","Bir bahis sonuçlandığında kısa bir ses"],
  "Bienvenue": ["Welcome","Bienvenido","Willkommen","Benvenuto","Bem-vindo","Welkom","Hoş geldiniz"],
  "Envoyer le message": ["Send message","Enviar mensaje","Nachricht senden","Invia messaggio","Enviar mensagem","Bericht versturen","Mesajı gönder"],

  "d'affilée": ["in a row","seguidas","in Folge","di fila","seguidas","op rij","üst üste"],
  "terminé": ["finished","terminado","beendet","terminato","terminado","afgelopen","bitti"],
  "Tous les paris": ["All bets","Todas las apuestas","Alle Tipps","Tutte le scommesse","Todas as apostas","Alle weddenschappen","Tüm bahisler"],
  "bénéfice ÷ total misé": ["profit ÷ total staked","beneficio ÷ total apostado","Gewinn ÷ Gesamteinsatz","profitto ÷ totale puntato","lucro ÷ total apostado","winst ÷ totale inzet","kâr ÷ toplam bahis"],
  "Le pronostic est passé.": ["The pick came in.","La apuesta ha salido.","Der Tipp ist aufgegangen.","Il pronostico è andato a buon fine.","O palpite entrou.","De voorspelling is uitgekomen.","Tahmin tuttu."],
  "Le pronostic n'est pas passé.": ["The pick did not come in.","La apuesta no ha salido.","Der Tipp ist nicht aufgegangen.","Il pronostico non è andato a buon fine.","O palpite não entrou.","De voorspelling is niet uitgekomen.","Tahmin tutmadı."],
  "Pari remboursé : la mise est rendue (égalité pile sur la ligne, joueur absent, abandon ou match annulé).": ["Bet refunded: the stake is returned (exactly on the line, player absent, retirement or match cancelled).","Apuesta reembolsada: se devuelve la apuesta (justo en la línea, jugador ausente, abandono o partido anulado).","Tipp erstattet: Der Einsatz wird zurückgegeben (genau auf der Linie, Spieler fehlt, Aufgabe oder Spielabsage).","Scommessa rimborsata: la puntata viene restituita (esattamente sulla linea, giocatore assente, ritiro o partita annullata).","Aposta reembolsada: a aposta é devolvida (exatamente na linha, jogador ausente, desistência ou jogo anulado).","Weddenschap terugbetaald: de inzet wordt teruggegeven (precies op de lijn, speler afwezig, opgave of afgelaste wedstrijd).","Bahis iade edildi: bahis tutarı geri verilir (tam çizgide, oyuncu yok, çekilme veya iptal edilen maç)."],
  "G-BET Bot — Paris du jour, résultats, bilan": ["G-BET Bot — Today's bets, results, balance","G-BET Bot — Apuestas de hoy, resultados, balance","G-BET Bot — Tipps des Tages, Ergebnisse, Bilanz","G-BET Bot — Scommesse del giorno, risultati, bilancio","G-BET Bot — Apostas do dia, resultados, balanço","G-BET Bot — Weddenschappen van vandaag, resultaten, saldo","G-BET Bot — Günün bahisleri, sonuçlar, bilanço"],

  "Statistique officielle de la feuille de match ; joueur absent = remboursé.": ["Official match-sheet statistic; player absent = refunded.","Estadística oficial de la hoja del partido; jugador ausente = reembolsado.","Offizielle Statistik des Spielberichts; Spieler fehlt = erstattet.","Statistica ufficiale del referto; giocatore assente = rimborsata.","Estatística oficial da ficha de jogo; jogador ausente = reembolsado.","Officiële statistiek van het wedstrijdformulier; speler afwezig = terugbetaald.","Maç raporundaki resmi istatistik; oyuncu yoksa = iade."],
  "Résultat officiel ; combat annulé ou pilote non partant = remboursé ; golf : égalité = remboursé.": ["Official result; fight cancelled or driver not starting = refunded; golf: tie = refunded.","Resultado oficial; combate anulado o piloto que no sale = reembolsado; golf: empate = reembolsado.","Offizielles Ergebnis; Kampf abgesagt oder Fahrer startet nicht = erstattet; Golf: Gleichstand = erstattet.","Risultato ufficiale; incontro annullato o pilota non al via = rimborsata; golf: parità = rimborsata.","Resultado oficial; combate anulado ou piloto que não parte = reembolsado; golfe: empate = reembolsado.","Officiële uitslag; gevecht afgelast of coureur start niet = terugbetaald; golf: gelijkspel = terugbetaald.","Resmi sonuç; maç iptal veya pilot başlamazsa = iade; golf: beraberlik = iade."],

  /* jeu responsable : seul le titre et la ligne d'aide sont traduits, le texte legal reste en francais */
  "Pour en parler :": ["To talk about it:","Para hablar de ello:","Um darüber zu sprechen:","Per parlarne:","Para falar sobre isso:","Om erover te praten:","Konuşmak için:"],

  /* sondage pouce vert / rouge (22/10/2026) : nouvelles entrees TOUJOURS a la fin */
  "Votre avis sur ce pari ?": ["Your opinion on this bet?","¿Qué opinas de esta apuesta?","Ihre Meinung zu diesem Tipp?","Che ne pensi di questa scommessa?","O que acha desta aposta?","Wat vind je van deze weddenschap?","Bu bahis hakkında ne düşünüyorsunuz?"],
  "J'aime ce pari": ["I like this bet","Me gusta esta apuesta","Ich mag diesen Tipp","Mi piace questa scommessa","Gosto desta aposta","Ik vind deze weddenschap goed","Bu bahsi beğendim"],
  "Je n'aime pas ce pari": ["I don't like this bet","No me gusta esta apuesta","Ich mag diesen Tipp nicht","Non mi piace questa scommessa","Não gosto desta aposta","Ik vind deze weddenschap niet goed","Bu bahsi beğenmedim"],
  "Vote impossible pour le moment": ["Voting is not possible right now","No se puede votar ahora mismo","Abstimmen ist gerade nicht möglich","Al momento non è possibile votare","Não é possível votar neste momento","Stemmen is nu niet mogelijk","Şu anda oy verilemiyor"],
  "Trop de votes, ralentis un peu": ["Too many votes, slow down a little","Demasiados votos, ve más despacio","Zu viele Stimmen, bitte etwas langsamer","Troppi voti, rallenta un po'","Demasiados votos, abrande um pouco","Te veel stemmen, doe het even rustiger aan","Çok fazla oy, biraz yavaşlayın"],
  "Trop de votes depuis cette connexion": ["Too many votes from this connection","Demasiados votos desde esta conexión","Zu viele Stimmen von dieser Verbindung","Troppi voti da questa connessione","Demasiados votos desta ligação","Te veel stemmen vanaf deze verbinding","Bu bağlantıdan çok fazla oy"],
};

/* ---------- modeles de phrases (nombres, noms de joueurs, dates...) : gabarits {x} par langue ---------- */
const OVER  = ["Over","Más de","Über","Più di","Mais de","Meer dan","Üst"];
const UNDER = ["Under","Menos de","Unter","Meno di","Menos de","Minder dan","Alt"];
const OLD = {   // gabarits des 7 premieres langues, [en, es, de, it, pt, nl, tr]
  vict:  ["Win {x}","Victoria de {x}","Sieg {x}","Vittoria {x}","Vitória {x}","Winst {x}","Galibiyet: {x}"],
  duel:  ["Tournament duel — {a} ahead of {b}","Duelo de torneo — {a} por delante de {b}","Turnierduell — {a} vor {b}","Duello del torneo — {a} davanti a {b}","Duelo do torneio — {a} à frente de {b}","Toernooiduel — {a} voor {b}","Turnuva düellosu — {a} önünde: {b}"],
  maj:   ["Updated at {t}","Actualizado a las {t}","Aktualisiert um {t}","Aggiornato alle {t}","Atualizado às {t}","Bijgewerkt om {t}","Güncelleme: {t}"],
  dans:  ["in {x}","en {x}","in {x}","tra {x}","em {x}","over {x}","{x} sonra"],
  proch: ["Next bet around {t}.","Próxima apuesta hacia las {t}.","Nächster Tipp gegen {t}.","Prossima scommessa verso le {t}.","Próxima aposta por volta das {t}.","Volgende weddenschap rond {t}.","Sonraki bahis yaklaşık {t}."],
  comm:  ["In progress · started at {t}","En curso · empezó a las {t}","Läuft · begonnen um {t}","In corso · iniziata alle {t}","Em curso · começou às {t}","Bezig · begonnen om {t}","Devam ediyor · başlangıç {t}"],
  sem:   ["week of {d}","semana del {d}","Woche vom {d}","settimana del {d}","semana de {d}","week van {d}","hafta: {d}"],
  stats: ["Match stats","Estadísticas del partido","Spielstatistiken","Statistiche della partita","Estatísticas do jogo","Wedstrijdstatistieken","Maç istatistikleri"],
  bet1:  ["bet","apuesta","Tipp","scommessa","aposta","weddenschap","bahis"],
  sportn:["{n} sport(s)","{n} deporte(s)","{n} Sportart(en)","{n} sport","{n} desporto(s)","{n} sport(en)","{n} spor"],
  won:   ["{n} won","{n} ganadas","{n} gewonnen","{n} vinte","{n} ganhas","{n} gewonnen","{n} kazanıldı"],
  wonof: ["{n} won out of {m}","{n} ganadas de {m}","{n} gewonnen von {m}","{n} vinte su {m}","{n} ganhas em {m}","{n} gewonnen van {m}","{n} kazanıldı / {m}"],
  days:  ["{n} winning days in a row","{n} días positivos seguidos","{n} Gewinntage in Folge","{n} giorni positivi di fila","{n} dias positivos seguidos","{n} winstdagen op rij","{n} gün üst üste kâr"],
  rec:   ["{a} of {b} · record {c} in a row","{a} de {b} · récord {c} seguidos","{a} von {b} · Rekord {c} in Folge","{a} su {b} · record {c} di fila","{a} de {b} · recorde {c} seguidos","{a} van {b} · record {c} op rij","{a} / {b} · rekor {c} üst üste"],
  page:  ["{a}–{b} of {c} · page {d} / {e}","{a}–{b} de {c} · página {d} / {e}","{a}–{b} von {c} · Seite {d} / {e}","{a}–{b} su {c} · pagina {d} / {e}","{a}–{b} de {c} · página {d} / {e}","{a}–{b} van {c} · pagina {d} / {e}","{a}–{b} / {c} · sayfa {d} / {e}"],
  usur:  ["{a} u over {n} {bets}","{a} u en {n} {bets}","{a} u bei {n} {bets}","{a} u su {n} {bets}","{a} u em {n} {bets}","{a} u uit {n} {bets}","{a} u / {n} {bets}"],
  dont:  ["{n} {bets} · of which {m} simulated","{n} {bets} · de los cuales {m} simuladas","{n} {bets} · davon {m} simuliert","{n} {bets} · di cui {m} simulate","{n} {bets} · dos quais {m} simuladas","{n} {bets} · waarvan {m} gesimuleerd","{n} {bets} · bunun {m} simüle"],
  tfin:  ["Final total {t}, {rel} {l} → {ow} {res}.","Total final {t}, {rel} {l} → {ow} {res}.","Endstand gesamt {t}, {rel} {l} → {ow} {res}.","Totale finale {t}, {rel} {l} → {ow} {res}.","Total final {t}, {rel} {l} → {ow} {res}.","Eindtotaal {t}, {rel} {l} → {ow} {res}.","Final toplamı {t}, {rel} {l} → {ow} {res}."],
  above: ["above","por encima de","über","sopra","acima de","boven","üstünde:"],
  below: ["below","por debajo de","unter","sotto","abaixo de","onder","altında:"],
};
let W_CACHE = null;
function W() {      // gabarits de la langue courante (les langues chargees completent l'anglais pour toute cle manquante)
  if (W_CACHE) return W_CACHE;
  const de = i => { const o = {over: OVER[i], under: UNDER[i]}; Object.keys(OLD).forEach(k => { o[k] = OLD[k][i]; }); return o; };
  const f = lf();
  W_CACHE = I < 7 ? de(I) : Object.assign(de(0), (f && f.W) || {});
  return W_CACHE;
}
function fmt(t, v) { return t.replace(/\{(\w+)\}/g, (all, k) => (v[k] === undefined ? all : v[k])); }

function motifs(s) {
  const w = W(); let m;
  if ((m = s.match(/^Plus de \/ moins de ([\d.,]+)$/))) return tr("Plus de / moins de") + " " + m[1];
  if ((m = s.match(/^Total final (\S+), (au-dessus|en dessous) de (\S+) → (Plus|Moins) de (gagné|perdu)\.$/)))
    return fmt(w.tfin, {t: m[1], rel: m[2] === "au-dessus" ? w.above : w.below, l: m[3], ow: m[4] === "Plus" ? w.over : w.under, res: tr(m[5])});
  if ((m = s.match(/^(\d+) paris · dont (\d+) simulés$/))) return fmt(w.dont, {n: m[1], bets: tr("paris"), m: m[2]});
  if ((m = s.match(/^Victoire (.+)$/))) return fmt(w.vict, {x: m[1]});
  if ((m = s.match(/^(Plus|Moins) de ([\d.,]+)(?: (.+))?$/))) return (m[1] === "Plus" ? w.over : w.under) + " " + m[2] + (m[3] ? " " + tr(m[3]) : "");
  if ((m = s.match(/^(.+?)\s*:\s*(plus|moins) de ([\d.,]+) (.+)$/))) return m[1] + ": " + (m[2] === "plus" ? w.over : w.under).toLowerCase() + " " + m[3] + " " + tr(m[4]);
  if ((m = s.match(/^Duel tournoi — (.+) devant (.+)$/))) return fmt(w.duel, {a: m[1], b: m[2]});
  if ((m = s.match(/^Handicap (.+)$/))) return tr("Handicap") + " " + m[1];
  if ((m = s.match(/^Mis à jour à (.+)$/))) return fmt(w.maj, {t: m[1]});
  if ((m = s.match(/^Prochain pari vers (.+?)\.?$/))) return fmt(w.proch, {t: m[1]});
  if ((m = s.match(/^En cours · commencé à (.+)$/))) return fmt(w.comm, {t: m[1]});
  if ((m = s.match(/^semaine du (.+)$/))) return fmt(w.sem, {d: m[1]});
  if ((m = s.match(/^dans (.+)$/))) return fmt(w.dans, {x: m[1]});
  if ((m = s.match(/^📊 Stats du match · (.+)$/))) return "📊 " + w.stats + " · " + m[1];
  if ((m = s.match(/^(\d+) paris?$/))) return m[1] + " " + (m[1] === "1" ? w.bet1 : tr("paris"));
  if ((m = s.match(/^(\d+) paris ·$/))) return m[1] + " " + tr("paris") + " ·";
  if ((m = s.match(/^(\d+) sport\(s\)$/))) return fmt(w.sportn, {n: m[1]});
  if ((m = s.match(/^(\d+) gagnés$/))) return fmt(w.won, {n: m[1]});
  if ((m = s.match(/^(\d+) gagnés sur (\d+)$/))) return fmt(w.wonof, {n: m[1], m: m[2]});
  if ((m = s.match(/^(\d+) paris · (\d+) remboursés?$/))) return m[1] + " " + tr("paris") + " · " + m[2] + " " + tr("remboursé").toLowerCase();
  if ((m = s.match(/^(\d+) jours? positifs? de suite$/))) return fmt(w.days, {n: m[1]});
  if ((m = s.match(/^(\d+) sur (\d+) · record (\d+) de suite$/))) return fmt(w.rec, {a: m[1], b: m[2], c: m[3]});
  if ((m = s.match(/^(\d+)[–-](\d+) sur (\d+) · page (\d+) \/ (\d+)$/))) return fmt(w.page, {a: m[1], b: m[2], c: m[3], d: m[4], e: m[5]});
  if ((m = s.match(/^([\d\u00a0\u202f ,.]+) u sur (\d+) paris$/))) return fmt(w.usur, {a: m[1], n: m[2], bets: tr("paris")});
  if ((m = s.match(/^(\d+) paris · bénéfice ÷ total misé$/))) return m[1] + " " + tr("paris") + " · " + tr("bénéfice") + " ÷ " + tr("total misé");
  if ((m = s.match(/^(\d+) paris · (.+) u · (\d+) % de réussite$/))) return m[1] + " " + tr("paris") + " · " + m[2] + " u · " + m[3] + " % " + tr("taux de réussite");
  return null;
}

/* ---------- acces aux traductions (7 premieres langues : tableaux du dictionnaire ; autres : fichier de langue, meme ordre) ---------- */
const KEYS = Object.keys(D), KEYIDX = {};
KEYS.forEach((k, i) => { KEYIDX[k] = i; });
function dict(k) {
  if (I < 7) { const e = D[k]; return e ? e[I] : null; }
  const f = lf(), j = KEYIDX[k];
  const v = f && f.D && j !== undefined ? f.D[j] : null;
  return v || null;
}

/* ---------- traduction d'un texte ---------- */
function norm(s) { return s.replace(/[  ]/g, " ").replace(/\s+/g, " ").trim(); }

function tr(s) {
  if (I < 0 || !s) return s;
  const k = norm(s);
  if (!k) return s;
  let t = dict(k);
  if (t == null) t = motifs(k);
  if (t == null && k.indexOf(" · ") > 0) {
    const parts = k.split(" · "); let touche = false;
    const out = parts.map(p => { const q = tr(p); if (q !== p) touche = true; return q; });
    if (touche) t = out.join(" · ");
  }
  if (t == null && k.indexOf("(") > 0) {
    const q = k.replace(/\(([^)]+)\)/g, (all, x) => "(" + (dict(x) || x) + ")");
    if (q !== k) t = q;
  }
  if (t == null) return s;
  if (P.br) t = t.replace(/Ténis/g, "Tênis").replace(/Basquetebol/g, "Basquete").replace(/Equipa/g, "Time").replace(/equipa/g, "time").replace(/desporto/g, "esporte").replace(/Desporto/g, "Esporte").replace(/Palavra-passe/g, "Senha").replace(/utilizador/g, "usuário").replace(/ecrã/g, "tela").replace(/Golfe/g, "Golfe");
  return s.replace(s.trim(), () => t);
}

/* en anglais : 1,25 -> 1.25 et 18 732 -> 18,732 dans les nombres isoles */
function chiffres(s) {
  if (!EN_ANGLAIS) return s;
  return s.replace(/(\d)\s(\d{3})(?!\d)/g, "$1,$2").replace(/(\d),(\d)/g, "$1.$2");
}

/* ---------- blocs longs (aide, regles, bas de page) : traduits en entier, balises <b>/<a> comprises ---------- */
const H = {}, HK = Object.keys(window.GB_H || {});
HK.forEach((k, j) => { H[norm(k).slice(0, 30)] = j; });
function blocTexte(j) {
  if (I < 7) { const e = window.GB_H[HK[j]]; return e ? e[I] : null; }
  const f = lf(); return f && f.H ? f.H[j] || null : null;
}
const BLOCS = {P: 1, TD: 1, SPAN: 1, DIV: 1};
function bloc(el) {
  if (!BLOCS[el.nodeName]) return false;
  if (el.getAttribute("data-tr")) return true;
  const t = el.textContent;
  if (t.length < 20 || t.length > 1500) return false;
  const j = H[norm(t).slice(0, 30)];
  const h0 = j === undefined ? null : blocTexte(j);
  if (!h0 || !el.closest("#p-aide,#p-res,footer")) return false;
  el.setAttribute("data-tr", "1");
  let h = h0;
  if (P.br) h = h.replace(/Ténis/g, "Tênis").replace(/ténis/g, "tênis").replace(/desporto/g, "esporte").replace(/utilizador/g, "usuário").replace(/equipa/g, "time");
  el.innerHTML = EN_ANGLAIS ? chiffres(h) : h;
  return true;
}

/* ---------- application au DOM ---------- */
const ATTRS = ["aria-label", "placeholder", "title", "alt"];
const SKIP = {SCRIPT: 1, STYLE: 1, TEXTAREA: 1, NOSCRIPT: 1, CODE: 1};
function ignore(el) { return el && el.closest && el.closest(".notr,[data-notr]"); }

function texte(n) {
  const v = n.nodeValue;
  if (!v || !v.trim()) return;
  const p = n.parentNode;
  if (!p || SKIP[p.nodeName] || ignore(p)) return;
  let t = tr(v);
  if (EN_ANGLAIS) { const t2 = chiffres(t); if (t2 !== t) t = t2; }
  if (t !== v) n.nodeValue = t;
}
function attributs(el) {
  if (!el.getAttribute || ignore(el)) return;
  for (const a of ATTRS) {
    const v = el.getAttribute(a);
    if (v) { const t = tr(v); if (t !== v) el.setAttribute(a, t); }
  }
}
function parcourir(racine) {
  if (racine.nodeType === 3) { if (!racine.parentNode || !racine.parentNode.closest("[data-tr]")) texte(racine); return; }
  if (racine.nodeType !== 1 || SKIP[racine.nodeName] || ignore(racine) || racine.closest("[data-tr]")) return;
  if (bloc(racine)) return;
  attributs(racine);
  const filtre = {acceptNode(n) {
    if (n.nodeType === 3) return NodeFilter.FILTER_ACCEPT;
    if (SKIP[n.nodeName] || ignore(n)) return NodeFilter.FILTER_REJECT;
    if (bloc(n)) return NodeFilter.FILTER_REJECT;
    attributs(n);
    return NodeFilter.FILTER_SKIP;
  }};
  const w = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, filtre);
  let n;
  while ((n = w.nextNode())) texte(n);
}

/* ---------- selecteur de drapeaux ---------- */
function css() {
  const s = document.createElement("style");
  s.textContent =
    ".lang{position:relative}" +
    ".lang>button{display:flex;align-items:center;gap:6px;background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:6px 10px;cursor:pointer;color:var(--text)}" +
    ".lang>button:hover{border-color:var(--gold)}" +
    ".lang img{width:22px;height:16px;border-radius:3px;object-fit:cover;display:block;box-shadow:0 0 0 1px #0006}" +
    ".lang .car{font-size:10px;color:var(--muted)}" +
    ".lang ul{position:absolute;right:0;top:calc(100% + 6px);z-index:30;margin:0;padding:6px;list-style:none;background:var(--raise);border:1px solid var(--line);border-radius:12px;min-width:210px;box-shadow:0 10px 30px #000a;max-height:70vh;overflow:auto}" +
    ".lang li button{display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;border-radius:8px;padding:8px 10px;color:var(--text);cursor:pointer;text-align:left;font-weight:500}" +
    ".lang li button:hover,.lang li button[aria-selected=true]{background:var(--surface)}" +
    ".lang li button[aria-selected=true]{color:var(--gold)}" +
    "@media (max-width:560px){.lang ul{position:fixed;left:16px;right:16px;top:60px;min-width:0}}";
  document.head.appendChild(s);
}
function selecteur() {
  const barre = document.querySelector("header .bar");
  if (!barre || document.getElementById("lang")) return;
  const wrap = document.createElement("div");
  wrap.className = "lang notr"; wrap.id = "lang";
  const b = document.createElement("button");
  b.type = "button"; b.setAttribute("aria-haspopup", "listbox"); b.setAttribute("aria-expanded", "false");
  b.setAttribute("aria-label", "Langue / Language"); b.title = "Langue / Language";
  b.innerHTML = '<img src="assets/flags/' + (P.f || P.c) + '.svg" alt=""><span class="car">▾</span>';
  const ul = document.createElement("ul");
  ul.setAttribute("role", "listbox"); ul.hidden = true;
  PAYS.forEach(p => {
    const li = document.createElement("li");
    const x = document.createElement("button");
    x.type = "button"; x.setAttribute("role", "option"); x.setAttribute("aria-selected", p.c === P.c ? "true" : "false");
    x.innerHTML = '<img src="assets/flags/' + (p.f || p.c) + '.svg" alt="" loading="lazy"><span></span>';
    x.lastChild.textContent = p.nom;
    x.addEventListener("click", () => {
      try { localStorage.setItem(CLE, p.c); } catch (e) {}
      location.reload();
    });
    li.appendChild(x); ul.appendChild(li);
  });
  const fermer = () => { ul.hidden = true; b.setAttribute("aria-expanded", "false"); };
  b.addEventListener("click", e => { e.stopPropagation(); ul.hidden = !ul.hidden; b.setAttribute("aria-expanded", String(!ul.hidden)); });
  document.addEventListener("click", e => { if (!wrap.contains(e.target)) fermer(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") fermer(); });
  wrap.appendChild(b); wrap.appendChild(ul);
  const login = document.getElementById("btn-login");
  barre.insertBefore(wrap, login || null);
}

/* ---------- demarrage ---------- */
function demarrer() {
  css();
  selecteur();
  if (P.rtl) document.documentElement.dir = "rtl";
  if (I < 0) { document.documentElement.lang = "fr"; return; }
  document.documentElement.lang = P.loc.split("-")[0];
  if (document.title) document.title = tr(document.title);
  parcourir(document.body);
  new MutationObserver(muts => {
    for (const m of muts) {
      if (m.type === "characterData") { if (!m.target.parentNode || !m.target.parentNode.closest("[data-tr]")) texte(m.target); }
      else if (m.type === "attributes") attributs(m.target);
      else m.addedNodes.forEach(parcourir);
    }
  }).observe(document.body, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
else demarrer();

window.GB_I18N = {code: P.c, loc: P.loc, tz: P.tz, tr: tr, _D: D, _PAYS: PAYS, _LANGS: LANGS};
})();
