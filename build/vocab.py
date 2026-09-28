# pyright: reportMissingImports=false
"""Vocabulario por frecuencia real del Tanaj.

Genera:
  v1/vocab/top100.json, top300.json, top1000.json   (material del curso)
  content/vocab/top1000.tsv                          (lista de trabajo para las glosas en español)
  v1/vocab/index.json                                (rangos, cobertura)
"""

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import corpus                                          # noqa: E402

TOPS = (100, 300, 1000)


def leer_glosas(ruta):
    """TSV: strong<TAB>glosa_es[<TAB>nota]  (las líneas con # se ignoran)."""
    glosas = {}
    if not os.path.exists(ruta):
        return glosas
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.rstrip("\n")
            if not linea or linea.startswith("#"):
                continue
            partes = linea.split("\t")
            if len(partes) >= 2 and partes[0].strip():
                glosas[partes[0].strip().upper()] = partes[1].strip()
    return glosas


def construir(out="v1", glosas_tsv=None, lexicon_idx=None):
    d = corpus.cargar()
    glosas_tsv = glosas_tsv or os.path.join(RAIZ, "content", "vocab", "glosas_es.tsv")
    glosas = leer_glosas(glosas_tsv)
    lex = {}
    if lexicon_idx and os.path.exists(lexicon_idx):
        with open(lexicon_idx, encoding="utf-8") as fh:
            lex = json.load(fh)

    total = d["total_palabras"]
    freq = d["freq_strong"]
    orden = sorted(freq.items(), key=lambda kv: (-kv[1], int("".join(c for c in kv[0] if c.isdigit()))))

    acum = 0
    items = []
    for i, (strong, n) in enumerate(orden, 1):
        acum += n
        formas = d["formas_strong"].get(strong, {})
        forma = max(formas.items(), key=lambda kv: kv[1])[0] if formas else ""
        ref = d["forma_ref"].get(forma, "")
        entrada = lex.get(strong, {})
        items.append({
            "rango": i,
            "strong": "H" + strong,
            "forma": forma,
            "forma_he": d["forma_he"].get(forma, ""),
            "forma_n": formas.get(forma, 0),
            "ocurrencias": n,
            "cobertura": round(100.0 * acum / total, 2),
            "he": entrada.get("he", ""),
            "xlit": entrada.get("xlit", ""),
            "glosa_es": glosas.get("H" + strong, ""),
            "glosa_en": (entrada.get("def_en") or [""])[0] if entrada else "",
            "ref": ref,
            "morph": max(d["morph_strong"].get(strong, {"": 0}).items(),
                         key=lambda kv: kv[1])[0] if d["morph_strong"].get(strong) else "",
        })

    resumen = {"total_palabras": total, "lemas": len(freq), "generado_por": "build/vocab.py", "rangos": {}}
    for top in TOPS:
        sub = items[:top]
        ruta = os.path.join(out, "vocab", "top%d.json" % top)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump({"rango": top, "cobertura": sub[-1]["cobertura"] if sub else 0,
                       "items": sub}, fh, ensure_ascii=False, separators=(",", ":"))
        resumen["rangos"]["top%d" % top] = {
            "cobertura": sub[-1]["cobertura"] if sub else 0,
            "con_glosa_es": sum(1 for it in sub if it["glosa_es"]),
            "archivo": "vocab/top%d.json" % top,
        }

    # lista de trabajo para curar glosas a mano (TSV legible)
    os.makedirs(os.path.join(RAIZ, "content", "vocab"), exist_ok=True)
    tsv = os.path.join(RAIZ, "content", "vocab", "top1000.tsv")
    with open(tsv, "w", encoding="utf-8") as fh:
        fh.write("# rango\tstrong\tforma_he\tforma\tocurrencias\tcobertura\tglosa_actual\n")
        for it in items[:1000]:
            fh.write("%d\t%s\t%s\t%s\t%d\t%.2f\t%s\n" % (it["rango"], it["strong"], it["forma_he"],
                                                         it["forma"], it["ocurrencias"],
                                                         it["cobertura"], it["glosa_es"]))

    with open(os.path.join(out, "vocab", "index.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=1)
    return items, resumen


if __name__ == "__main__":
    items, res = construir()
    print("lemas=%d palabras=%d" % (res["lemas"], res["total_palabras"]))
    for k, v in res["rangos"].items():
        print("  %-7s cobertura=%.1f%% con_glosa_es=%d" % (k, v["cobertura"], v["con_glosa_es"]))
    print("lista de trabajo: content/vocab/top1000.tsv")
