# pyright: reportMissingImports=false
"""Cadena completa del curso: fuentes -> datos -> audio -> lecciones -> manifiesto.

    python3 build/build_all.py                 # todo menos audio si ya existe
    python3 build/build_all.py --sin-audio     # sin audio (rápido)
    python3 build/build_all.py --force-audio   # regenera los MP3
    python3 build/build_all.py --fuentes       # además baja las fuentes

Termina ejecutando build/verify.py: si algo no cuadra, sale con error.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def correr(cmd, **kw):
    print("  $ %s" % " ".join(cmd))
    r = subprocess.run(cmd, cwd=RAIZ, **kw)
    if r.returncode != 0:
        raise SystemExit("falló: %s" % " ".join(cmd))


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def manifiesto(out="v1"):
    archivos = {}
    for base, _, nombres in os.walk(os.path.join(RAIZ, out)):
        for n in sorted(nombres):
            if n in ("manifest.json",):
                continue
            p = os.path.join(base, n)
            rel = os.path.relpath(p, os.path.join(RAIZ, out)).replace(os.sep, "/")
            archivos[rel] = {"bytes": os.path.getsize(p), "sha256": sha256(p)}
    datos = {"generado_por": "build/build_all.py", "fecha": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "total_archivos": len(archivos), "archivos": archivos}
    with open(os.path.join(RAIZ, out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)
    return datos


def portada(out="v1"):
    def cargar(nombre):
        with open(os.path.join(RAIZ, out, nombre), encoding="utf-8") as fh:
            return json.load(fh)

    alef, nq = cargar("alefbet.json"), cargar("niqqud.json")
    voc = cargar("vocab/index.json")
    lex = cargar("lexicon/index.json")
    les = cargar("lessons/index.json")
    aud = cargar("audio/index.json")
    datos = {
        "nombre": "aprendehebreo.io",
        "descripcion": "Curso de hebreo bíblico para principiantes, con API JSON abierta.",
        "version": "1.0.0",
        "tanaj_api": "https://avisonofgod.github.io/v1/",
        "generado_por": "build/build_all.py",
        "conteos": {
            "letras_y_finales": alef["total_formas"],
            "signos_niqqud": nq["total"],
            "lemas_con_lexico": lex["total"],
            "palabras_con_audio": sum(1 for v in aud["clips"].values() if v["grupo"] == "palabra"),
            "clips_audio": aud["total"],
            "lecciones": les["total"],
            "items_de_lecciones": sum(l["items"] for l in les["lecciones"]),
            "ejercicios": sum(l["ejercicios"] for l in les["lecciones"]),
        },
        "cobertura_vocabulario": voc["rangos"],
        "fuentes": {
            "hebreo": {"obra": "Westminster Leningrad Codex (morphhb)", "licencia": "CC BY 4.0",
                       "url": "https://github.com/openscriptures/morphhb"},
            "lexico": {"obra": "Strong's Hebrew Dictionary", "licencia": "dominio público",
                       "url": "https://github.com/openscriptures/strongs"},
            "espanol": {"obra": "Reina-Valera 1909", "licencia": "dominio público",
                        "url": "https://api.getbible.net/"},
            "letras": {"obra": "Unicode Character Database", "licencia": "Unicode License",
                       "url": "https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt"},
            "audio": {"obra": "edge-tts (voces he-IL de Microsoft Edge)", "licencia": "términos de Microsoft",
                      "nota": "voz sintética; se puede sustituir por grabaciones"},
        },
        "endpoints": {
            "alefbet": "alefbet.json",
            "niqqud": "niqqud.json",
            "vocabulario": "vocab/top100.json | top300.json | top1000.json",
            "lexico": "lexicon/<H####>.json (índice en lexicon/index.json)",
            "lecciones": "lessons/index.json y lessons/<NN>.json",
            "audio": "audio/index.json y audio/<id>.mp3",
            "integridad": "manifest.json",
        },
    }
    with open(os.path.join(RAIZ, out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)
    return datos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="v1")
    ap.add_argument("--sin-audio", action="store_true")
    ap.add_argument("--force-audio", action="store_true")
    ap.add_argument("--fuentes", action="store_true")
    ap.add_argument("--sin-pasajes", action="store_true")
    a = ap.parse_args()
    py = sys.executable

    if a.fuentes:
        print("· fuentes"); correr(["bash", "build/fetch_sources.sh"])
    print("· corpus"); correr([py, "build/corpus.py"])
    print("· alef-bet y niqqud"); correr([py, "build/alefbet.py"])
    print("· vocabulario"); correr([py, "build/vocab.py"])
    print("· léxico"); correr([py, "build/lexicon.py"])
    if not a.sin_audio:
        print("· audio")
        cmd = [py, "build/audio.py", "--out", a.out]
        if a.force_audio:
            cmd.append("--force")
        correr(cmd)
    print("· pasajes de lectura"); correr([py, "build/pasajes.py", "--out", a.out])
    print("· lecciones"); correr([py, "build/lessons.py", "--out", a.out])
    print("· portada e integridad")
    idx = portada(a.out)
    man = manifiesto(a.out)
    print("  conteos: %s" % json.dumps(idx["conteos"], ensure_ascii=False))
    print("  archivos con sha256: %d" % man["total_archivos"])
    print("· verificación")
    correr([py, "build/verify.py", "--out", a.out])


if __name__ == "__main__":
    main()
