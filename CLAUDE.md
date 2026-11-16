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
