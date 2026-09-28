# pyright: reportMissingImports=false
"""Alef-bet y niqqud: material generado desde la UCD + las notas curadas en español.

Fuentes:
  data/UnicodeData.txt        nombres oficiales de cada letra y signo (Unicode License)
  content/alefbet_es.tsv      nombre, transliteración, sonido y nota en español (curado)
  content/niqqud_es.tsv       ídem para vocales, dagesh, sheva, te'amim y puntuación
  data/corpus.json            para el ejemplo real de cada letra (palabra + referencia)

Salida: v1/alefbet.json, v1/niqqud.json
"""

import json
import os
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import corpus                                           # noqa: E402

GEMATRIA = {}


def leer_ucd(ruta):
    """codepoint -> (nombre oficial, categoría)."""
    salida = {}
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            partes = linea.rstrip("\n").split(";")
            if len(partes) < 3:
                continue
            cp = int(partes[0], 16)
            if 0x0590 <= cp <= 0x05FF:
                salida[cp] = (partes[1], partes[2])
    return salida


def leer_tsv(ruta, minimo):
    filas = []
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.rstrip("\n")
            if not linea or linea.startswith("#"):
                continue
            partes = linea.split("\t")
            if len(partes) < minimo:
                raise SystemExit("fila corta en %s: %r" % (ruta, linea[:40]))
            filas.append([p.strip() for p in partes])
    return filas


def ejemplo_de(corpus_datos, letra):
    """La forma más frecuente que contiene la letra, con su referencia del Tanaj."""
    candidatos = [(f, n) for f, n in corpus_datos["freq_forma"].items()
                  if letra in f and len(f) > 1]
    if not candidatos:
        return None
    forma = max(candidatos, key=lambda kv: kv[1])[0]
    return {"forma": forma, "forma_he": corpus_datos["forma_he"].get(forma, ""),
            "ref": corpus_datos["forma_ref"].get(forma, ""), "ocurrencias": dict(candidatos)[forma]}


def construir(out="v1"):
    ucd = leer_ucd(os.path.join(RAIZ, "data", "UnicodeData.txt"))
    datos = corpus.cargar()

    # ── letras ────────────────────────────────────────────────────────────────
    letras_es = leer_tsv(os.path.join(RAIZ, "content", "alefbet_es.tsv"), 7)
    letras = []
    for i, (he, nombre_es, t_es, t_ac, sonido, nota, nombre_he) in enumerate(letras_es):
        cp = ord(he)
        if cp not in ucd or "HEBREW LETTER" not in ucd[cp][0]:
            raise SystemExit("no es letra hebrea según la UCD: %r (U+%04X)" % (he, cp))
        final = "FINAL" in ucd[cp][0]
        letras.append({
            "id": unicodedata.name(he).split()[-1].lower(),
            "he": he,
            "nombre_es": nombre_es,
            "nombre_he": nombre_he,
            "unicode": "U+%04X" % cp,
            "nombre_unicode": ucd[cp][0].title().replace("Hebrew Letter ", ""),
            "translit_es": t_es,
            "translit_acad": t_ac,
            "sonido": sonido,
            "nota": nota,
            "final": final,
            "ejemplo": ejemplo_de(datos, he),
            "audio": "audio/letra-%02d.mp3" % (len(letras) + 1),
        })

    # gematria: 1..400 para las 22 letras base y 500..900 para las 5 finales
    gem = 0
    for l in letras:
        if not l["final"]:
            gem = gem + 1 if gem < 10 else (gem + 10 if gem < 100 else gem + 100)
            l["gematria"] = gem
            l["base"] = l["he"]
        else:
            l["gematria"] = 0
    fin = {"ך": 500, "ם": 600, "ן": 700, "ף": 800, "ץ": 900}
    parejas = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
    for l in letras:
        if l["final"]:
            l["base"] = parejas[l["he"]]
            l["gematria"] = fin[l["he"]]

    # ── niqqud y signos ──────────────────────────────────────────────────────
    signos = []
    for i, (codigo, nombre_es, tipo, sonido, nota, ejemplo) in enumerate(
            leer_tsv(os.path.join(RAIZ, "content", "niqqud_es.tsv"), 6)):
        cp = int(codigo, 16)
        if cp not in ucd:
            raise SystemExit("U+%04X no está en la UCD" % cp)
        signos.append({
            "id": "%s-%02d" % (tipo, i + 1),
            "he": chr(cp),
            "codigo": "U+%04X" % cp,
            "nombre_es": nombre_es,
            "nombre_unicode": ucd[cp][0].title(),
            "tipo": tipo,
            "sonido": sonido,
            "nota": nota,
            "ejemplo_he": ejemplo if ejemplo != "—" else "",
            "audio": ("audio/niqqud-%02d.mp3" % (i + 1)) if ejemplo != "—" else "",
        })

    alefbet = {
        "titulo": "Alef-bet: 22 letras y 5 formas finales",
        "total_formas": len(letras),
        "total_letras_base": sum(1 for l in letras if not l["final"]),
        "total_finales": sum(1 for l in letras if l["final"]),
        "fuente_unicode": "Unicode Character Database (Unicode License)",
        "items": letras,
        "por_letra": {l["he"]: l["id"] for l in letras},
        "gematria": {l["id"]: l["gematria"] for l in letras},
    }
    niqqud = {
        "titulo": "Niqqud, dagesh, sheva y signos del códice",
        "total": len(signos),
        "por_tipo": {t: sum(1 for s in signos if s["tipo"] == t)
                     for t in sorted({s["tipo"] for s in signos})},
        "fuente_unicode": "Unicode Character Database (Unicode License)",
        "items": signos,
    }

    os.makedirs(out, exist_ok=True)
    for nombre, obj in (("alefbet.json", alefbet), ("niqqud.json", niqqud)):
        with open(os.path.join(out, nombre), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
    return alefbet, niqqud


if __name__ == "__main__":
    a, n = construir()
    print("letras=%d (base=%d finales=%d) signos=%d %s" %
          (a["total_formas"], a["total_letras_base"], a["total_finales"], n["total"], n["por_tipo"]))
    ej = [l for l in a["items"] if l["ejemplo"]]
    print("letras con ejemplo del Tanaj: %d/%d" % (len(ej), a["total_formas"]))
    print("gematria:", {l["he"]: l["gematria"] for l in a["items"]})
