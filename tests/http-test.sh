#!/bin/bash
# Pruebas del sitio servido por HTTP (como quedará en GitHub Pages).
# Uso: bash tests/http-test.sh [puerto]
set -uo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8093}"
OK=0; FAIL=0
chk() { if [ "$2" = "1" ]; then echo "OK   $1${3:+ | $3}"; OK=$((OK+1)); else echo "FALLA $1${3:+ | $3}"; FAIL=$((FAIL+1)); fi; }

python3 -m http.server "$PORT" >/tmp/aprendehebreo-http.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.25; done

code() { curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT$1"; }
ct()   { curl -s -o /dev/null -w "%{content_type}" "http://127.0.0.1:$PORT$1"; }
sz()   { curl -s -o /dev/null -w "%{size_download}" "http://127.0.0.1:$PORT$1"; }

chk "portada 200" "$([ "$(code /)" = 200 ] && echo 1 || echo 0)"
for r in /styles.css /app.js /sw.js /manifest.webmanifest /icon.svg /api.html \
         /v1/index.json /v1/alefbet.json /v1/niqqud.json /v1/vocab/top100.json /v1/vocab/top300.json \
         /v1/lexicon/index.json /v1/lexicon/H7225.json /v1/lessons/index.json /v1/lessons/01.json \
         /v1/reading/index.json /v1/reading/bereshit/1.json /v1/audio/index.json \
         /v1/audio/letra-01.mp3 /v1/manifest.json; do
  chk "$r 200" "$([ "$(code $r)" = 200 ] && echo 1 || echo 0)"
done

chk "JSON con content-type correcto" "$([ "$(ct /v1/index.json)" = "application/json" ] && echo 1 || echo 0)" "$(ct /v1/index.json)"
chk "MP3 con content-type de audio" "$(echo "$(ct /v1/audio/letra-01.mp3)" | grep -qc audio && echo 1 || echo 0)" "$(ct /v1/audio/letra-01.mp3)"
chk "audio pesa lo suficiente (>5 KB)" "$([ "$(sz /v1/audio/letra-01.mp3)" -gt 5000 ] && echo 1 || echo 0)" "$(sz /v1/audio/letra-01.mp3) B"
chk "portada ligera (< 40 KB)" "$([ "$(sz /index.html)" -lt 40000 ] && echo 1 || echo 0)" "$(sz /index.html) B"
chk "app.js ligero (< 40 KB)" "$([ "$(sz /app.js)" -lt 40000 ] && echo 1 || echo 0)" "$(sz /app.js) B"
chk "404 real" "$([ "$(code /v1/lessons/99.json)" = 404 ] && echo 1 || echo 0)"

# contenido servido correcto (una letra, una palabra y un pasaje)
PORT_N="$PORT" python3 - <<'PY' > /tmp/aprendehebreo-check.txt
import json, os, urllib.request
b = "http://127.0.0.1:" + os.environ["PORT_N"]
alef = json.load(urllib.request.urlopen(b + "/v1/alefbet.json"))
pal = json.load(urllib.request.urlopen(b + "/v1/vocab/top100.json"))
pas = json.load(urllib.request.urlopen(b + "/v1/reading/bereshit/1.json"))
print("letras:", alef["total_formas"], alef["total_finales"])
print("palabra1:", pal["items"][0]["forma"], pal["items"][0]["glosa_es"][:20])
print("versiculo1:", pas["versiculos"][0]["he_plain"][:22])
print("cobertura:", pal["cobertura"])
PY
chk "alef-bet servido (27 formas, 5 finales)" "$(grep -c '^letras: 27 5' /tmp/aprendehebreo-check.txt)"
chk "vocabulario servido con glosa en español" "$(grep -c '^palabra1: את' /tmp/aprendehebreo-check.txt)"
chk "pasaje servido (Bereshit 1:1)" "$(grep -c '^versiculo1: בראשית ברא אלהים' /tmp/aprendehebreo-check.txt)"

echo
echo "== RESUMEN: $OK OK / $FAIL FALLA =="
[ "$FAIL" = 0 ] || exit 1
