# aprendehebreo — curso de hebreo bíblico + API JSON

Curso web **para principiantes hispanohablantes** que quieren leer el Tanaj: del alef-bet a los
tres pasajes clásicos (Bereshit 1, Devarim 6, Tehilim 23), con **audio en cada ítem**,
vocabulario por frecuencia real y API JSON abierta. Sin registro, sin backend: la página y la
API viven en este repositorio (GitHub Pages).

Sitio: <https://aprendehebreo.github.io/> · API: [`api.html`](api.html)

(Es el sitio raíz de la organización, como <https://avisonofgod.github.io/>. Todas las rutas son
relativas, así que también funcionaría igual con un dominio propio: bastaría añadir un `CNAME`.)

## Qué incluye

- **Alef-bet**: 27 formas (22 letras + 5 finales) con nombre, sonido, transliteración, gematria,
  código Unicode, palabra real del Tanaj y audio.
- **Niqqud**: 55 signos (vocales, jatuf, sheva, dagesh, te'amim y puntuación del códice).
- **12 lecciones** con 150 ítems y 64 ejercicios corregidos al momento, y explicación en HTML.
- **Vocabulario por frecuencia**: los 100 lemas más frecuentes cubren el **50,5 %** del Tanaj;
  los 300, el **67,8 %**; los 1.000, el **83,5 %** (medido sobre 306.785 palabras).
- **Léxico Strong** (1.072 entradas publicadas): lema, transliteración, pronunciación,
  definición, etimología y formas del Tanaj.
- **Lectura interlineal**: 5 pasajes con análisis palabra por palabra (forma, Strong, glosa, audio).
- **Repaso espaciado SM-2** en el navegador + progreso exportable.
- **Audio**: 253 clips MP3 (letras, niqqud, 100 palabras, 108 versículos).

## Estructura

```
index.html · app.js · styles.css   curso (una página, sin frameworks ni CDN)
api.html                           documentación de la API
sw.js · manifest.webmanifest · icon.svg
v1/                                la API (generada, se versiona)
  index.json                       portada: conteos, cobertura, fuentes y licencias
  alefbet.json · niqqud.json       letras y signos
  vocab/top100|300|1000.json       vocabulario por frecuencia con glosa en español
  lexicon/<H####>.json             léxico Strong (índice en lexicon/index.json)
  lessons/index.json · NN.json     las 12 lecciones
  reading/<slug>/<cap>.json        pasajes con análisis por palabra
  audio/index.json · *.mp3         audio
  manifest.json                    ruta → bytes y sha256
build/                             generador (Python 3, solo biblioteca estándar + edge-tts)
  fetch_sources.sh                 morphhb + Strong + RV1909 + UnicodeData a data/ (no versionada)
  corpus.py                        corpus del Tanaj en caché (palabras, lemas, formas, referencias)
  alefbet.py                       letras y signos desde la UCD + notas curadas
  vocab.py                         frecuencia real y cobertura acumulada
  lexicon.py                       Strong OSIS → JSON, con ocurrencias reales
  pasajes.py                       pasajes con análisis palabra por palabra
  lessons.py                       content/lessons/*.md → JSON + validación
  audio.py                         MP3 con edge-tts (voces he-IL)
  build_all.py                     orquesta todo y genera portada + manifiesto
  verify.py                        43 comprobaciones; si algo no cuadra, falla
content/
  alefbet_es.tsv · niqqud_es.tsv   material curado en español (letras y signos)
  vocab/glosas_es.tsv              glosas en español de los 300 lemas más frecuentes
  vocab/top1000.tsv                lista de trabajo generada (para curar más glosas)
  lessons/01..12.md                texto de las lecciones (datos + prosa)
tests/
  test_build.py                    unittest del generador
  app-test.js                      pruebas de la app con jsdom
  http-test.sh                     el sitio servido por HTTP, como en Pages
```

## Generar y verificar

```bash
bash build/fetch_sources.sh                    # fuentes a data/ (no se versionan)
python3 build/build_all.py                     # corpus → datos → audio → lecciones → manifiesto → verify
python3 build/verify.py                        # 43 comprobaciones (se ejecuta solo en el paso anterior)
python3 -m unittest discover -s tests -p 'test_*.py'
NODE_PATH=/ruta/node_modules node tests/app-test.js
bash tests/http-test.sh

python3 -m http.server 8080                    # y abrir http://localhost:8080/
```

El audio necesita `edge-tts` (`python3 -m venv .venv && .venv/bin/pip install edge-tts`).
Si no hay red, `python3 build/build_all.py --sin-audio` genera todo lo demás.

## API (resumen)

| Ruta | Contenido |
|---|---|
| `v1/index.json` | conteos, cobertura del vocabulario, fuentes y licencias |
| `v1/alefbet.json` | 27 formas: nombre, sonido, transliteración, gematria, Unicode, ejemplo y audio |
| `v1/niqqud.json` | 55 signos agrupados por tipo |
| `v1/vocab/top100.json` | frecuencia, forma más común, glosa en español, ocurrencias, cobertura, referencia |
| `v1/lexicon/H7225.json` | Strong: hebreo, xlit, pronunciación, definición, etimología, formas |
| `v1/lessons/NN.json` | objetivos, ítems, ejercicios y explicación de la lección |
| `v1/reading/bereshit/1.json` | versículos + análisis palabra por palabra |
| `v1/audio/index.json` | los 253 clips con su texto |
| `v1/manifest.json` | `sha256` de cada archivo |

GitHub Pages responde `access-control-allow-origin: *`, así que la API se puede consumir desde
cualquier web. Para caché inmutable por versión:
`https://cdn.jsdelivr.net/gh/aprendehebreo/aprendehebreo.github.io@v1.0.0/v1/alefbet.json`.

## Fuentes y licencias

- Hebreo y morfología: [Westminster Leningrad Codex (morphhb)](https://github.com/openscriptures/morphhb) — **CC BY 4.0**.
- Léxico: [Strong's Hebrew Dictionary](https://github.com/openscriptures/strongs) — **dominio público**.
- Español: Reina-Valera 1909 — **dominio público** ([getbible v2](https://api.getbible.net/)).
- Letras y signos: [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt) — Unicode License.
- Audio: `edge-tts` con voz `he-IL-HilaNeural` (voces he-IL de Microsoft Edge), ritmo −10 %.
  Es voz sintética: si necesitas una licencia plenamente propia, sustituye los MP3 por grabaciones
  con el mismo nombre (el build no cambia).
- Código: MIT (ver [`LICENSE`](LICENSE)). El texto y el léxico conservan sus atribuciones.

## Estado y hoja de ruta

Verificado por el propio build: 27 formas, 929 capítulos / 23.213 versículos de referencia,
cobertura del vocabulario, 108/108 versículos con audio, 12/12 lecciones válidas y `sha256`
de los 1.353 archivos. Hoja de ruta: más pasajes de lectura, ejercicios de ordenar palabras,
transliteración automática por reglas, tarjetas de verbos por binyan y modo “escribir sin mirar”.
