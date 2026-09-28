# pyright: reportMissingImports=false
"""Pasajes de lectura: palabras analizadas por versículo (interlineal).

Genera v1/reading/<slug>/<cap>.json para los pasajes del curso, con:
  he / he_plain del versículo, texto español (RV1909), y por palabra: forma con niqqud,
  forma sin niqqud, Strong, transliteración y glosa en español (si existe).

Fuente: data/morphhb (texto + morfología) y data/valera.json (RV1909).
"""

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import corpus                                          # noqa: E402
import lexicon as lexicon_mod                          # noqa: E402
import slugs                                           # noqa: E402

# pasajes del curso (se pueden ampliar)
PASAJES = [("bereshit", 1), ("bereshit", 12), ("shemot", 20), ("devarim", 6), ("tehilim", 23)]

W = re.compile(r'<w\b([^>]*)>(.*?)</w>', re.S)
ATTR = re.compile(r'(\w+)="([^"]*)"')
TAG = re.compile(r"<[^>]+>")
NIQ = re.compile(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]")
VERSE = re.compile(r'<verse osisID="[^.]+\.(\d+)\.(\d+)">(.*?)</verse>', re.S)
RV_NOMBRE = {b["rv1909"]: b for b in slugs.BOOKS}


def strongs_de_pasajes(pasajes=None):
    """{'H7225', ...}: todos los lemas Strong que aparecen en los pasajes del curso."""
    salida = set()
    for slug, cap in (pasajes or PASAJES):
        libro = slugs.BY_SLUG[slug]
        ruta = os.path.join(RAIZ, "data", "morphhb", "wlc", libro["osis"] + ".xml")
        x = open(ruta, encoding="utf-8").read()
        for m in VERSE.finditer(x):
            if int(m.group(1)) != cap:
                continue
            for w in W.finditer(m.group(3)):
                attrs = dict(ATTR.findall(w.group(1)))
                for s in re.split(r"[/\s]+", attrs.get("lemma", "")):
                    if re.fullmatch(r"\d+[a-z]?", s or ""):
                        salida.add("H" + re.match(r"(\d+)", s).group(1))
    return salida


def texto_es():
    d = json.load(open(os.path.join(RAIZ, "data", "valera.json"), encoding="utf-8"))
    libros = d["books"] if isinstance(d, dict) else d
    salida = {}
    for libro in libros:
        info = RV_NOMBRE.get(libro["name"])
        if not info:
            continue
        for cap in libro["chapters"]:
            salida[(info["slug"], int(cap["chapter"]))] = {
                int(v["verse"]): v["text"] for v in cap["verses"]}
    return salida


def construir(out="v1", pasajes=None):
    pasajes = pasajes or PASAJES
    ruta_lex = os.path.join(RAIZ, out, "lexicon", "index.json")
    if not os.path.exists(ruta_lex):
        raise SystemExit("falta %s: corre build/lexicon.py antes" % ruta_lex)
    with open(ruta_lex, encoding="utf-8") as fh:
        lex_idx = json.load(fh)["entradas"]
    es = texto_es()
    hechos = []
    for slug, cap in pasajes:
        libro = slugs.BY_SLUG[slug]
        ruta = os.path.join(RAIZ, "data", "morphhb", "wlc", libro["osis"] + ".xml")
        x = open(ruta, encoding="utf-8").read()
        versiculos = []
        for m in VERSE.finditer(x):
            if int(m.group(1)) != cap:
                continue
            palabras = []
            for w in W.finditer(m.group(3)):
                attrs = dict(ATTR.findall(w.group(1)))
                con = re.sub(r"\s+", " ", TAG.sub("", w.group(2))).strip().replace("/", "")
                plano = NIQ.sub("", con).replace("\u05be", "")
                if not plano:
                    continue
                strongs = [s for s in re.split(r"[/\s]+", attrs.get("lemma", ""))
                           if re.fullmatch(r"\d+[a-z]?", s or "")]
                clave = "H" + strongs[0] if strongs else ""
                entrada = lex_idx.get(clave, {})
                palabras.append({"he": con, "plano": plano, "strong": clave,
                                 "morph": attrs.get("morph", ""),
                                 "xlit": entrada.get("xlit", ""),
                                 "glosa_es": entrada.get("glosa_es", "")})
            texto = " ".join(p["he"] for p in palabras)
            versiculos.append({"n": int(m.group(2)), "he": texto,
                               "audio": "audio/verso-%s-%d-%d.mp3" % (slug, cap, int(m.group(2))),
                               "he_plain": NIQ.sub("", texto).replace("\u05be", ""),
                               "es": (es.get((slug, cap)) or {}).get(int(m.group(2)), ""),
                               "palabras": palabras})
        salida = {"libro": {"slug": slug, "he": libro["he"], "es": libro["es"],
                            "en": libro["en"], "section": libro["section"]},
                  "capitulo": cap, "versiculos": versiculos,
                  "total_versiculos": len(versiculos)}
        destino = os.path.join(RAIZ, out, "reading", slug)
        os.makedirs(destino, exist_ok=True)
        with open(os.path.join(destino, "%d.json" % cap), "w", encoding="utf-8") as fh:
            json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
        hechos.append({"slug": slug, "capitulo": cap, "versiculos": len(versiculos),
                       "palabras": sum(len(v["palabras"]) for v in versiculos),
                       "archivo": "reading/%s/%d.json" % (slug, cap),
                       "con_es": sum(1 for v in versiculos if v["es"])})
    with open(os.path.join(RAIZ, out, "reading", "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"total": len(hechos), "pasajes": hechos}, fh, ensure_ascii=False, indent=1)
    return hechos


if __name__ == "__main__":
    for p in construir():
        print("  %-9s %-3d versiculos=%3d palabras=%4d con_es=%d" %
              (p["slug"], p["capitulo"], p["versiculos"], p["palabras"], p["con_es"]))
