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
- Títol (actualitzat 18/11, objectiu CTR ≥ 4 %): **el ganxo va al davant** (lloc/època/situació concreta i després la promesa), perquè al mòbil només es veuen els primers ~45 caràcters. **Sense punt final** i **com a màxim 1 emoji**, al final. Acaba en « | Histoire pour dormir » + 1 emoji temàtic. Exemples:
  « Un hiver au Moyen Âge : vous n'y survivriez pas | Histoire pour dormir 🕯️ »
  « Une nuit à l'auberge en 1396 : vous n'y survivriez pas | Histoire pour dormir 🍷 »
  (El codi treu sol els emojis de més i el punt final, però escriu-lo ja bé.)
- Descripció: comença « Installez-vous confortablement. Ce soir, nous… ». 3 hashtags (#histoirepourdormir #moyenage + temàtic).
- 6 prompts d'imatge per secció, en anglès, escena concreta. Sense «Paris» ni «winter» en interiors; evita objectes moderns (fanals, teteres, vidres).
- Miniatura (actualitzada 18/11): una cara en primer pla il·luminada per una espelma (càlid) sobre un fons de nit blau (fred); text de **2 o 3 paraules** com a màxim, molt gran, que **completi el títol sense repetir-lo** (« −20 °C AU LIT », « 1347 », « AUCUN BRUIT », « SANS FEU ? »). El codi hi posa l'espelma petita de marca i deixa buida la cantonada de baix a la dreta (durada). Si l'episodi és una continuació, `label: "PARTIE 2"`.
- `publish_at`: l'endemà del darrer vídeo programat, 19:00 Andorra (18:00Z a l'hivern, 17:00Z a l'estiu).
- Actualitza `temes.md` (mou el tema a «Publicats o ja fets») al mateix commit.

## Format d'episode.json
Vegeu `episodes/2026-11-18-voyage/episode.json` com a exemple (ja té el títol i el bloc `thumbnail` en el format nou; el vídeo es va publicar amb l'antic). El bloc `thumbnail` és així:
```json
"thumbnail": {
  "text": "−20 °C AU LIT",
  "alt_text": "SANS FEU ?",
  "face": "exhausted medieval peasant man with a frost-covered beard, wrapped in a wool blanket, shivering",
  "background": "medieval village of thatched cottages buried in snow at night",
  "label": ""
}
```
- `text`: 2–3 paraules en majúscules (francès). `alt_text`: una alternativa amb una idea diferent (per a la variant C).
- `face`: en anglès, UNA persona de l'època amb una expressió clara però tranquil·la (fred, cansament, calma); descriu edat, barba, barret o caputxa. Evita «eyes closed/half closed», «wide eyes» o «staring»: amb SD-Turbo fan ulls estranys i la miniatura fa por (no és contingut de terror). Sense mans, objectes moderns ni text. El codi ja afegeix «primer pla, llum d'espelma, mirada suau a càmera».
- `background`: en anglès, escena exterior o de nit de l'episodi, sense gent (el codi la torna blava i freda).
- `label`: buit, o « PARTIE 2 » si toca.
El workflow genera 8 cares, tria la més neta (detector de cares YuNet: una sola cara, ulls i nas ben posats, nítida) i deixa `thumbnail.jpg` (la que es puja), `thumbnail_b.jpg` (2a cara), `thumbnail_c.jpg` (text alternatiu) i `thumbnail_faces.jpg` als artefactes «control». YouTube «Tester et comparer» no es pot fer per API: si es vol, es pugen a mà les variants a YouTube Studio.

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
