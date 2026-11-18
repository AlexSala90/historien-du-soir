# L'Historien du Soir — producció diària

Canal YouTube en francès d'« histoire pour dormir ». Un vídeo cada dia a les 19:00 (Europe/Andorra), publicat automàticament.

## Com funciona
1. **Cada dia, una sessió de Claude** escriu el guió i el desa com a `episodes/AAAA-MM-DD-slug/episode.json`, i en fa commit a `main`.
2. **GitHub Actions** (`.github/workflows/produce.yml`) detecta el nou `episode.json`, genera veu, imatges, muntatge, miniatura i fitxa, i el puja a YouTube programat a `publish_at`.

## Regles del guió (no canviar sense l'Àlex)
- Abans de triar tema: llegeix `temes.md` i, si hi ha credencials, `python3 run.py titles`. No repeteixis cap tema publicat, programat ni privat.
- 10 seccions amb títol. Intro (època, lloc, personatge, la pregunta) → 8 temàtiques → conclusió que respon i relaxa.
- To lent i calmat, frases curtes, «vous», sense ensurts. Només fets acceptats pels historiadors; si és dubtós, dir-ho.
- 35–45 mil caràcters (≈40–50 min). Tancament fix: « Merci d'avoir passé… avec L'Historien du Soir. Si ce voyage vous a aidé à trouver le repos, abonnez-vous pour nous retrouver d'autres nuits, en d'autres siècles. Dormez bien. »
- Títol: acaba en « | Histoire pour dormir » + 2 emojis temàtics. Format preferit: « Pourquoi vous ne survivriez pas… ».
- Descripció: comença « Installez-vous confortablement. Ce soir, nous… ». 3 hashtags (#histoirepourdormir #moyenage + temàtic).
- 6 prompts d'imatge per secció, en anglès, escena concreta. Sense «Paris» ni «winter» en interiors; evita objectes moderns (fanals, teteres, vidres).
- Miniatura: 2 línies en crema + 1 en daurat, majúscules.
- `publish_at`: l'endemà del darrer vídeo programat, 19:00 Andorra (18:00Z a l'hivern, 17:00Z a l'estiu).
- Actualitza `temes.md` (mou el tema a «Publicats o ja fets») al mateix commit.

## Format d'episode.json
Vegeu `episodes/2026-11-18-voyage/episode.json` com a exemple.

## Secrets de GitHub necessaris
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (es generen amb `authorize.py`).

## Castellà i anglès (des del 18/11)
Cada vídeo es puja amb el títol i la descripció també en castellà i anglès (localitzacions de YouTube) i amb subtítols en francès, castellà i anglès, sincronitzats amb la veu. L'àudio continua sent només en francès (el canal encara no té pistes d'àudio en altres idiomes).
- Afegeix a `episode.json` el bloc `localizations` (el títol i la descripció pesen per a la cerca; la traducció automàtica del workflow és només la reserva):
```json
"localizations": {
  "es": {"title": "Una noche en una posada en 1396: no sobrevivirías | Historia para dormir 🍷",
         "description_intro": "Ponte cómodo. Esta noche llegamos…",
         "section_titles": ["Introducción: el camino al anochecer", "… 10 en total"]},
  "en": {"title": "A Night at a Medieval Inn in 1396: You Wouldn't Survive | History for Sleep 🍷",
         "description_intro": "Get comfortable. Tonight, we arrive…",
         "section_titles": ["Introduction: the road at dusk", "… 10 en total"]}
}
```
- Títols: mateixes regles que en francès (ganxo al davant, ≤ 100 caràcters, 1 emoji), acabats en « | Historia para dormir » i « | History for Sleep ». Escriu-los com un natiu, no calcats («tú» en castellà, «you» en anglès).
- `description_intro`: comença « Ponte cómodo. Esta noche… » / « Get comfortable. Tonight, we… ». El codi hi afegeix capítols, tancament i hashtags.
- `section_titles`: exactament 10, en el mateix ordre.
- Els subtítols es tradueixen sols al workflow (Helsinki-NLP opus-mt, fr→en i fr→en→es) a partir dels temps reals de cada frase. Queden també als artefactes «control» (`subs_*.srt`, `localizations.json`).
- Pujar subtítols requereix el permís `youtube.force-ssl`: si el registre diu que falta, torna a executar `authorize.py` (amb el compte del canal) i actualitza `YT_REFRESH_TOKEN`. Després, `python3 run.py languages WORKDIR` els torna a pujar.
