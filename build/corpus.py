# pyright: reportMissingImports=false
"""Extrae el corpus del Tanaj (WLC) a un caché reutilizable: data/corpus.json.

Por cada palabra del Tanaj guarda:
  lemas Strong (con prefijos separados), forma sin niqqud y con niqqud, código morfológico
  y la referencia (slug/capítulo/versículo) de su primera aparición.

También arma:
  - frecuencias por Strong, formas por Strong
  - frecuencias por forma (para el vocabulario y los ejercicios)
  - índice de la primera aparición de cada forma, para los ejemplos verificables
"""

import collections
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import slugs                                          # noqa: E402

NIQ = re.compile(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]")
TAG = re.compile(r"<[^>]+>")
W = re.compile(r'<w\b([^>]*)>(.*?)</w>', re.S)
ATTR = re.compile(r'(\w+)="([^"]*)"')
VERSE = re.compile(r'<verse osisID="([^.]+)\.(\d+)\.(\d+)">(.*?)</verse>', re.S)


def strongs(lemma):
    """'b/7225' -> ['7225'];  '1254 a' -> ['1254a'];  'm/3293 a' -> ['3293a']."""
    out = []
    for parte in re.split(r"[/\s]+", lemma.strip()):
        if not parte:
            continue
        m = re.match(r"^(\d+)([a-z]?)$", parte)
        if m:
            out.append(m.group(1) + m.group(2))
    return out


def limpiar(txt):
    return re.sub(r"\s+", " ", TAG.sub("", txt or "")).strip()


def construir(wlc_dir, salida):
    # estructura de libros -> capítulos y versículos por capítulo (para validar refs)
    libros = {}
    freq = collections.Counter()          # strong -> ocurrencias
    formas = collections.defaultdict(collections.Counter)   # strong -> forma sin niqqud
    forma_ref = {}                        # forma -> [slug, cap, verso, strong]
    forma_he = {}                         # forma -> forma con niqqud
    forma_n = collections.Counter()       # forma -> ocurrencias
    morphs = collections.defaultdict(collections.Counter)   # strong -> códigos morph
    total = 0

    for libro in slugs.BOOKS:
        ruta = os.path.join(wlc_dir, libro["osis"] + ".xml")
        if not os.path.exists(ruta):
            raise SystemExit("falta %s" % ruta)
        x = open(ruta, encoding="utf-8").read()
        info = libros.setdefault(libro["slug"], {"chapters": 0, "verses": [], "verses_total": 0})
        for m in VERSE.finditer(x):
            capitulo, verso = int(m.group(2)), int(m.group(3))
            while len(info["verses"]) < capitulo:
                info["verses"].append(0)
            info["verses"][capitulo - 1] = max(info["verses"][capitulo - 1], verso)
            info["chapters"] = max(info["chapters"], capitulo)
            info["verses_total"] += 1
            for w in W.finditer(m.group(4)):
                attrs = dict(ATTR.findall(w.group(1)))
                con_niqqud = limpiar(w.group(2)).replace("/", "")
                plano = NIQ.sub("", con_niqqud).replace("\u05be", "")
                if not plano:
                    continue
                total += 1
                forma_n[plano] += 1
                forma_he.setdefault(plano, con_niqqud)
                ref = "%s/%d/%d" % (libro["slug"], capitulo, verso)
                forma_ref.setdefault(plano, [ref, None])
                for s in strongs(attrs.get("lemma", "")):
                    freq[s] += 1
                    formas[s][plano] += 1
                    morphs[s][attrs.get("morph", "")] += 1
                    if forma_ref[plano][1] is None:
                        forma_ref[plano] = [ref, s]

    datos = {
        "total_palabras": total,
        "libros": libros,
        "lemas": len(freq),
        "freq_strong": dict(freq),
        "formas_strong": {s: dict(c) for s, c in formas.items()},
        "morph_strong": {s: dict(c) for s, c in morphs.items()},
        "freq_forma": dict(forma_n),
        "forma_he": forma_he,
        "forma_ref": {k: v[0] for k, v in forma_ref.items()},
        "forma_strong": {k: (v[1] or "") for k, v in forma_ref.items()},
    }
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"))
    return datos


def cargar(salida=None):
    salida = salida or os.path.join(RAIZ, "data", "corpus.json")
    if not os.path.exists(salida):
        raise SystemExit("falta %s: corre build/build_all.py primero" % salida)
    with open(salida, encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    wlc = os.path.join(RAIZ, "data", "morphhb", "wlc")
    d = construir(wlc, os.path.join(RAIZ, "data", "corpus.json"))
    caps = sum(v["chapters"] for v in d["libros"].values())
    vers = sum(v["verses_total"] for v in d["libros"].values())
    print("palabras=%d lemas=%d formas=%d | libros=%d capitulos=%d versiculos=%d" %
          (d["total_palabras"], d["lemas"], len(d["freq_forma"]), len(d["libros"]), caps, vers))
