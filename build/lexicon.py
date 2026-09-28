# pyright: reportMissingImports=false
"""Léxico Strong en JSON: v1/lexicon/<H####>.json + v1/lexicon/index.json

Fuente: data/StrongHebrewG.xml (openscriptures/strongs, dominio público).
Se enriquece con las ocurrencias reales del Tanaj (data/corpus.json) y con las glosas
en español curadas en content/vocab/glosas_es.tsv.
"""

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import corpus                                          # noqa: E402
import pasajes                                         # noqa: E402
import vocab as vocab_mod                              # noqa: E402

ENTRY = re.compile(r'<div\b[^>]*type="entry"[^>]*n="(\d+)"[^>]*>(.*?)</div>', re.S)
W = re.compile(r"<w\b([^>]*)>(.*?)</w>", re.S)
ATTR = re.compile(r'(\w+)="([^"]*)"')
ITEM = re.compile(r"<item>(.*?)</item>", re.S)
NOTE = re.compile(r'<note\b[^>]*type="([^"]+)"[^>]*>(.*?)</note>', re.S)
TAG = re.compile(r"<[^>]+>")
ESPACIOS = re.compile(r"\s+")


def limpiar(t):
    return ESPACIOS.sub(" ", TAG.sub("", t or "")).strip()


def parsear(ruta):
    """H#### -> entrada del diccionario."""
    x = open(ruta, encoding="utf-8").read()
    salida = {}
    for m in ENTRY.finditer(x):
        num, cuerpo = m.group(1), m.group(2)
        e = {"strong": "H" + num, "he": "", "xlit": "", "pron": ""}
        w = W.search(cuerpo)
        if w:
            a = dict(ATTR.findall(w.group(1)))
            e["he"] = limpiar(w.group(2))
            e["xlit"] = a.get("xlit", "")
            e["pron"] = a.get("POS", "")
        items = [limpiar(i) for i in ITEM.findall(cuerpo)]
        notas = {}
        for tipo, texto in NOTE.findall(cuerpo):
            notas.setdefault(tipo, []).append(limpiar(texto))
        e["def_en"] = items
        e["kjv"] = " / ".join(notas.get("translation", [])[:1])
        e["expl"] = notas.get("explanation", [""])[0] if notas.get("explanation") else ""
        e["etim"] = notas.get("exegesis", [""])[0] if notas.get("exegesis") else ""
        e["raices"] = ["H" + s for s in re.findall(r'<w\b[^>]*src="(\d+)"', cuerpo)]
        salida[e["strong"]] = e
    return salida


def construir(out="v1", minimo=2, tope_extra=1000):
    lex = parsear(os.path.join(RAIZ, "data", "StrongHebrewG.xml"))
    datos = corpus.cargar()
    glosas = vocab_mod.leer_glosas(os.path.join(RAIZ, "content", "vocab", "glosas_es.tsv"))
    freq = datos["freq_strong"]
    top = [it["strong"] for it in vocab_mod.construir(out)[0][:tope_extra]]

    usados = {s for s, n in freq.items() if n >= minimo}
    usados |= {"H" + s[1:] for s in top}
    # más todos los lemas que aparecen en los pasajes del curso (análisis palabra por palabra)
    usados |= pasajes.strongs_de_pasajes()
    os.makedirs(os.path.join(out, "lexicon"), exist_ok=True)

    indice = {}
    escritos = 0
    for strong, n in sorted(freq.items(), key=lambda kv: -kv[1]):
        clave = "H" + strong
        if clave not in usados:
            continue
        e = dict(lex.get(clave, {"strong": clave, "he": "", "xlit": "", "pron": "",
                                 "def_en": [], "kjv": "", "expl": "", "etim": "", "raices": []}))
        formas = datos["formas_strong"].get(strong, {})
        e["ocurrencias"] = n
        e["formas"] = [{"forma": f, "forma_he": datos["forma_he"].get(f, ""), "n": c,
                        "ref": datos["forma_ref"].get(f, "")}
                       for f, c in sorted(formas.items(), key=lambda kv: -kv[1])[:5]]
        e["morph"] = [m for m, _ in sorted(datos["morph_strong"].get(strong, {}).items(),
                                           key=lambda kv: -kv[1])[:5] if m]
        e["glosa_es"] = glosas.get(clave, "")
        ruta = os.path.join(out, "lexicon", clave + ".json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(e, fh, ensure_ascii=False, indent=1)
        escritos += 1
        indice[clave] = {"ocurrencias": n, "he": e["he"], "xlit": e["xlit"],
                         "glosa_es": e["glosa_es"], "archivo": "lexicon/%s.json" % clave}

    with open(os.path.join(out, "lexicon", "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"total": escritos, "criterio_frecuencia": minimo,
                   "nota": ("lemas con ≥%d ocurrencias, del top %d, o presentes en los pasajes del curso"
                            % (minimo, tope_extra)),
                   "entradas": indice}, fh, ensure_ascii=False, separators=(",", ":"))
    return escritos, len(lex)


if __name__ == "__main__":
    n, total_dict = construir()
    print("entradas publicadas=%d (diccionario completo=%d)" % (n, total_dict))
    print("índice: v1/lexicon/index.json")
