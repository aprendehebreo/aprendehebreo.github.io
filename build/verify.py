# pyright: reportMissingImports=false
"""Verificación del curso publicado en v1/. Sin red: todo se comprueba contra los archivos.

Comprueba: conteos canónicos del alef-bet, signos, cobertura del vocabulario, integridad del
léxico, audio realmente presente en disco, referencias al Tanaj que existen, esquema de las
lecciones, sha256 del manifiesto y la portada.

    python3 build/verify.py [--out v1]
"""

import argparse
import hashlib
import unicodedata
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import corpus                                          # noqa: E402
import lessons as lessons_mod                          # noqa: E402
import slugs                                           # noqa: E402

OK, FALLAS = 0, []


def chk(cond, etiqueta, detalle=None):
    global OK
    detalle = "" if detalle is None else str(detalle)
    if cond:
        OK += 1
        print("OK   %s%s" % (etiqueta, (" | " + str(detalle)) if detalle else ""))
    else:
        FALLAS.append(etiqueta)
        print("FALLA %s%s" % (etiqueta, (" | " + str(detalle)) if detalle else ""))


def cargar(out, nombre):
    with open(os.path.join(RAIZ, out, nombre), encoding="utf-8") as fh:
        return json.load(fh)


def ref_existe(ref, datos):
    """Acepta 'libro', 'libro/capitulo' y 'libro/capitulo/versiculo'."""
    partes = str(ref or "").split("/")
    libro = datos["libros"].get(partes[0])
    if not libro:
        return False
    if len(partes) == 1:
        return True
    cap = int(partes[1])
    if not 1 <= cap <= libro["chapters"]:
        return False
    if len(partes) == 2:
        return True
    ver = int(partes[2])
    return 1 <= ver <= libro["verses"][cap - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="v1")
    a = ap.parse_args()
    out = a.out
    datos = corpus.cargar()
    idx = cargar(out, "index.json")
    slugs_by_slug = {b["slug"]: b for b in slugs.BOOKS}

    # ── alef-bet ─────────────────────────────────────────────────────────────
    alef = cargar(out, "alefbet.json")
    chk(alef["total_formas"] == 27, "alef-bet: 27 formas", alef["total_formas"])
    chk(alef["total_letras_base"] == 22, "alef-bet: 22 letras base", alef["total_letras_base"])
    chk(alef["total_finales"] == 5, "alef-bet: 5 formas finales", alef["total_finales"])
    gem = {l["he"]: l["gematria"] for l in alef["items"]}
    esperado = {"א": 1, "י": 10, "כ": 20, "ק": 100, "ת": 400, "ך": 500, "ץ": 900}
    chk(all(gem[k] == v for k, v in esperado.items()), "alef-bet: gematria correcta",
        {k: gem[k] for k in esperado})
    chk(all(l["final"] == (l["he"] in "ךםןףץ") for l in alef["items"]), "alef-bet: finales marcadas")
    chk(all(l["ejemplo"] and ref_existe(l["ejemplo"]["ref"], datos) for l in alef["items"]),
        "alef-bet: 27 ejemplos con referencia real")
    chk(all(l["unicode"].startswith("U+") for l in alef["items"]), "alef-bet: código Unicode en cada forma")

    # ── niqqud ───────────────────────────────────────────────────────────────
    nq = cargar(out, "niqqud.json")
    chk(nq["total"] >= 50, "niqqud: ≥50 signos", nq["total"])
    chk(set(nq["por_tipo"]) <= {"vocal", "jatuf", "sheva", "dagesh", "puntuacion", "te'am", "marca"},
        "niqqud: tipos permitidos", nq["por_tipo"])
    chk(sum(nq["por_tipo"].values()) == nq["total"], "niqqud: el desglose cuadra")
    vocales = [s for s in nq["items"] if s["tipo"] == "vocal"]
    chk(len(vocales) >= 11, "niqqud: vocales completas (kamats..shuruk)", len(vocales))

    # ── vocabulario ──────────────────────────────────────────────────────────
    voc = cargar(out, "vocab/index.json")
    esperado_cob = {"top100": 50.5, "top300": 67.8, "top1000": 83.5}
    for rango, cob in esperado_cob.items():
        chk(abs(voc["rangos"][rango]["cobertura"] - cob) < 0.2,
            "vocabulario %s: cobertura %.1f%%" % (rango, cob), voc["rangos"][rango]["cobertura"])
    top100 = cargar(out, "vocab/top100.json")["items"]
    top300 = cargar(out, "vocab/top300.json")["items"]
    chk(len(top100) == 100 and len(top300) == 300, "vocabulario: 100 y 300 entradas",
        "%d/%d" % (len(top100), len(top300)))
    chk(all(it["glosa_es"] for it in top300), "vocabulario: los 300 con glosa en español",
        sum(1 for it in top300 if it["glosa_es"]))
    chk(all(ref_existe(it["ref"], datos) for it in top100 if it["ref"]),
        "vocabulario: referencias del top100 existen")
    chk(len({it["strong"] for it in top300}) == 300, "vocabulario: sin lemas repetidos")

    # ── léxico ───────────────────────────────────────────────────────────────
    lex = cargar(out, "lexicon/index.json")
    chk(lex["total"] == len(lex["entradas"]), "léxico: índice cuadra con las entradas", lex["total"])
    faltan = [k for k, v in lex["entradas"].items()
              if not os.path.exists(os.path.join(RAIZ, out, v["archivo"]))]
    chk(not faltan, "léxico: todos los archivos existen", faltan[:3])
    muestra = [k for k in ("H7225", "H430", "H3068") if k in lex["entradas"]]
    chk(len(muestra) == 3, "léxico: incluye lemas clave", muestra)
    e = cargar(out, lex["entradas"]["H7225"]["archivo"])
    chk(e["he"] and e["xlit"] and e["def_en"] and e["ocurrencias"] > 0,
        "léxico: H7225 con hebreo, transliteración, definición y ocurrencias",
        "%s / %s / %d" % (e["he"], e["xlit"], e["ocurrencias"]))
    chk(all(cargar(out, v["archivo"])["ocurrencias"] > 0 for v in list(lex["entradas"].values())[:25]),
        "léxico: ocurrencias > 0 en la muestra")

    # ── audio ────────────────────────────────────────────────────────────────
    aud = cargar(out, "audio/index.json")
    faltan_audio = [k for k in aud["clips"]
                    if not os.path.exists(os.path.join(RAIZ, out, k.replace("audio/", "audio/")))
                    or os.path.getsize(os.path.join(RAIZ, out, k.replace("audio/", "audio/"))) < 512]
    chk(not faltan_audio, "audio: todos los clips existen en disco", len(aud["clips"]))
    chk(aud["total"] == len(aud["clips"]), "audio: índice cuadra", aud["total"])
    letras_audio = [l for l in alef["items"] if l["audio"] in aud["clips"]]
    chk(len(letras_audio) == 27, "audio: las 27 letras tienen clip", len(letras_audio))
    palabras_audio = [c for c in aud["clips"].values() if c["grupo"] == "palabra"]
    chk(len(palabras_audio) == 100, "audio: las 100 palabras tienen clip", len(palabras_audio))
    voces = {v["grupo"] for v in aud["clips"].values()}
    chk({"letra", "niqqud", "palabra", "verso"} <= voces, "audio: cubre letras, niqqud, palabras y versículos",
        sorted(voces))

    # ── lecciones ────────────────────────────────────────────────────────────
    les = cargar(out, "lessons/index.json")
    chk(les["total"] == 12, "lecciones: 12 publicadas", les["total"])
    problemas = []
    for l in les["lecciones"]:
        d = cargar(out, "lessons/" + l["archivo"])
        problemas += ["%s: %s" % (l["archivo"], e) for e in lessons_mod.validar(d, l["archivo"], datos)]
    chk(not problemas, "lecciones: validación (ids, opciones, refs)", problemas[:3])
    ids = [l["id"] for l in les["lecciones"]]
    chk(sorted(ids) == list(range(1, 13)), "lecciones: ids 1..12", ids)
    chk(all(l["items"] >= 6 and l["ejercicios"] >= 3 for l in les["lecciones"]),
        "lecciones: al menos 6 items y 3 ejercicios cada una")
    chk(all("html" in cargar(out, "lessons/" + l["archivo"]) for l in les["lecciones"]),
        "lecciones: prosa convertida a HTML")

    # cotejo independiente: cada palabra/ejemplo citado debe existir en el versículo citado
    NIQ = re.compile(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]")

    def norm_he(t):
        t = NIQ.sub("", unicodedata.normalize("NFC", t or ""))
        # el XML del WLC trae "/" entre prefijo y raíz: no cuenta en el cotejo
        return (t.replace("\u05be", "").replace("\u05c0", "").replace("\u05c3", "")
                 .replace("/", "").replace(" ", ""))

    def versiculo_wlc(ref):
        partes = str(ref).split("/")
        if len(partes) < 2 or partes[0] not in slugs_by_slug:
            return ""
        ruta = os.path.join(RAIZ, "data", "morphhb", "wlc", slugs_by_slug[partes[0]]["osis"] + ".xml")
        if not os.path.exists(ruta):
            return ""
        x = open(ruta, encoding="utf-8").read()
        cap = int(partes[1])
        ver = int(partes[2]) if len(partes) > 2 else None
        textos = []
        for m in re.finditer(r'<verse osisID="[^.]+\.(\d+)\.(\d+)">(.*?)</verse>', x, re.S):
            if int(m.group(1)) != cap:
                continue
            if ver is not None and int(m.group(2)) != ver:
                continue
            textos.append(re.sub(r"<[^>]+>", " ", m.group(3)))
        return " ".join(textos)

    fallos_ej = []
    for l in les["lecciones"]:
        d = cargar(out, "lessons/" + l["archivo"])
        for it in d.get("items", []):
            pares = [(it.get("he"), it.get("ref"))]
            ej = it.get("ejemplo") or {}
            pares.append((ej.get("he"), ej.get("ref")))
            for he, ref in pares:
                if not he or not ref or "/" not in str(ref):
                    continue
                texto = versiculo_wlc(ref)
                if not texto or norm_he(he) not in norm_he(texto):
                    fallos_ej.append("%s: %s no aparece en %s" % (l["archivo"], he, ref))
    if fallos_ej:
        print("     " + "\n     ".join(fallos_ej[:5]))
    chk(not fallos_ej, "lecciones: cada palabra citada aparece en su versículo",
        "%d citas comprobadas" % sum(1 for l in les["lecciones"] for it in cargar(out, "lessons/" + l["archivo"]).get("items", [])
                                     for par in [(it.get("he"), it.get("ref")), ((it.get("ejemplo") or {}).get("he"), (it.get("ejemplo") or {}).get("ref"))]
                                     if par[0] and par[1] and "/" in str(par[1])))

    # ── pasajes de lectura ───────────────────────────────────────────────────
    rd = cargar(out, "reading/index.json")
    chk(rd["total"] >= 5, "lectura: ≥5 pasajes analizados", rd["total"])
    total_versos = 0
    problemas_rd = []
    for p in rd["pasajes"]:
        d = cargar(out, p["archivo"])
        libro = datos["libros"][p["slug"]]
        if d["total_versiculos"] != libro["verses"][p["capitulo"] - 1]:
            problemas_rd.append("%s: versículos %d != %d" % (p["archivo"], d["total_versiculos"],
                                                             libro["verses"][p["capitulo"] - 1]))
        for v in d["versiculos"]:
            total_versos += 1
            if not v["palabras"] or not v["he_plain"] or not v["es"]:
                problemas_rd.append("%s v%d incompleto" % (p["archivo"], v["n"]))
            if not ref_existe("%s/%d/%d" % (p["slug"], p["capitulo"], v["n"]), datos):
                problemas_rd.append("%s v%d no existe" % (p["archivo"], v["n"]))
    chk(not problemas_rd, "lectura: versículos completos, con español y referencia válida",
        problemas_rd[:3])
    palabras = [w for p in rd["pasajes"] for v in cargar(out, p["archivo"])["versiculos"]
                for w in v["palabras"]]
    con_strong = [w for w in palabras if w["strong"]]
    en_lex = [w for w in con_strong if w["strong"] in lex["entradas"]]
    chk(len(con_strong) / max(1, len(palabras)) > 0.9,
        "lectura: ≥90%% de las palabras con número Strong",
        "%.1f%%" % (100.0 * len(con_strong) / max(1, len(palabras))))
    chk(len(en_lex) / max(1, len(con_strong)) > 0.95,
        "lectura: ≥95%% de esas palabras tienen entrada de léxico",
        "%.1f%%" % (100.0 * len(en_lex) / max(1, len(con_strong))))
    aud_versos = [c for c in aud["clips"].values() if c["grupo"] == "verso"]
    chk(len(aud_versos) == total_versos, "audio: un clip por versículo de los pasajes",
        "%d/%d" % (len(aud_versos), total_versos))

    # ── portada y manifiesto ─────────────────────────────────────────────────
    chk("tanaj_api" in idx and idx["conteos"]["lecciones"] == 12, "portada: conteos y enlace al Tanaj")
    chk(all(v.get("licencia") for v in idx["fuentes"].values()), "portada: cada fuente con licencia")
    man = cargar(out, "manifest.json")
    chk(man["total_archivos"] == len(man["archivos"]), "manifiesto: cuadra el total", man["total_archivos"])

    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    malos = [r for r, v in man["archivos"].items()
             if not os.path.exists(os.path.join(RAIZ, out, r))
             or sha(os.path.join(RAIZ, out, r)) != v["sha256"]]
    chk(not malos, "manifiesto: sha256 correcto en todos los archivos", len(man["archivos"]))

    # ── referencias contra el Tanaj (offline, contra el corpus) ──────────────
    refs = {l["ejemplo"]["ref"] for l in alef["items"] if l["ejemplo"]}
    refs |= {it["ref"] for it in top100 if it["ref"]}
    refs |= {l["pasaje"] for l in les["lecciones"] if l["pasaje"]}
    malas = [r for r in refs if not ref_existe(r, datos)]
    chk(not malas, "referencias al Tanaj válidas", "%d refs" % len(refs))

    print()
    if FALLAS:
        print("== %d OK / %d FALLA ==" % (OK, len(FALLAS)))
        for f in FALLAS:
            print("  - %s" % f)
        sys.exit(1)
    print("== %d OK / 0 FALLA ==" % OK)


if __name__ == "__main__":
    main()
