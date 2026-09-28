#!/bin/bash
# Baja (o reutiliza) las fuentes del curso a data/ — data/ NO se versiona.
#
#   morphhb          texto hebreo + morfología (CC BY 4.0)
#   StrongHebrewG    léxico Strong hebreo (dominio público)
#   valera.json      RV1909 español (dominio público)
#   UnicodeData.txt  nombres oficiales de letras y signos hebreos (Unicode License)
#
# Uso: bash build/fetch_sources.sh [--force]
set -euo pipefail
cd "$(dirname "$0")/.."
FORCE="${1:-}"
mkdir -p data

# 1) morphhb: se reutiliza /tmp/tanakh-src si ya está clonado (113 MB)
if [ ! -d data/morphhb/wlc ] || [ "$FORCE" = "--force" ]; then
  if [ -d /tmp/tanakh-src/wlc ]; then
    echo "· copiando morphhb desde /tmp/tanakh-src"
    rm -rf data/morphhb && mkdir -p data/morphhb && cp -a /tmp/tanakh-src/wlc data/morphhb/
  else
    echo "· clonando morphhb"
    rm -rf data/morphhb && git clone --depth 1 -q https://github.com/openscriptures/morphhb data/morphhb
  fi
fi

# 2) licencia del corpus
[ -f data/morphhb/LICENSE.md ] || curl -sSfL -o data/morphhb/LICENSE.md \
  https://raw.githubusercontent.com/openscriptures/morphhb/master/LICENSE.md || true

# 3) léxico Strong (6,4 MB)
if [ ! -s data/StrongHebrewG.xml ] || [ "$FORCE" = "--force" ]; then
  echo "· bajando StrongHebrewG.xml"
  curl -sSfL -o data/StrongHebrewG.xml \
    https://raw.githubusercontent.com/openscriptures/strongs/master/hebrew/StrongHebrewG.xml
fi

# 4) RV1909
if [ ! -s data/valera.json ] || [ "$FORCE" = "--force" ]; then
  echo "· bajando valera.json"
  curl -sSfL -o data/valera.json https://api.getbible.net/v2/valera.json
fi

# 5) Unicode Character Database
if [ ! -s data/UnicodeData.txt ] || [ "$FORCE" = "--force" ]; then
  echo "· bajando UnicodeData.txt"
  curl -sSfL -o data/UnicodeData.txt https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt
fi

echo
echo "· fuentes en data/:"
for f in data/morphhb/wlc data/StrongHebrewG.xml data/valera.json data/UnicodeData.txt; do
  if [ -e "$f" ]; then
    printf '  %-28s %s  %s\n' "$f" "$(du -sh "$f" | cut -f1)" \
      "$( [ -f "$f" ] && sha256sum "$f" | cut -c1-16 || echo '(dir)' )"
  else
    echo "  FALTA $f"
  fi
done
