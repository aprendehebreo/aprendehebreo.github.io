# pyright: reportMissingImports=false
"""Lecciones: content/lessons/NN.md -> v1/lessons/NN.json

Cada .md trae un bloque ```json con los datos estructurados (items, ejercicios, pasaje) y,
debajo, la prosa en markdown que se convierte a HTML (subconjunto: títulos, listas,
párrafos, negrita/cursiva, código, citas, tablas simples y reglas).

Valida: ids únicos, rangos de respuestas, tipos permitidos y que las referencias al Tanaj
existan de verdad (contra data/corpus.json).
"""

import html
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
import corpus                                          # noqa: E402

BLOQUE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
TIPOS_ITEM = {"letra", "niqqud", "palabra", "gramatica", "frase"}
TIPOS_EJ = {"opcion", "escribir", "leer", "audio", "ordenar"}


# ── markdown mínimo ─────────────────────────────────────────────────────────
def inline(t):
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def md_a_html(md):
    salida, parrafo, lista, tabla = [], [], None, False

    def cerrar():
        nonlocal parrafo, lista, tabla
        if parrafo:
            salida.append("<p>%s</p>" % " ".join(parrafo)); parrafo = []
        if lista:
            salida.append("</%s>" % lista); lista = None
        if tabla:
            salida.append("</tbody></table>"); tabla = False

    for cruda in md.split("\n"):
        linea = cruda.rstrip()
        if not linea.strip():
            cerrar()
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", linea)
        if m:
            cerrar()
            n = len(m.group(1))
            salida.append("<h%d>%s</h%d>" % (n, inline(m.group(2)), n))
            continue
        if re.match(r"^(-{3,}|\*{3,})$", linea.strip()):
            cerrar(); salida.append("<hr>"); continue
        if linea.strip().startswith("|") and linea.count("|") >= 2:
            if parrafo or lista:
                cerrar()
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in celdas):
                continue                                   # fila separadora
            if not tabla:
                salida.append("<table><tbody>"); tabla = True
                salida.append("<tr>%s</tr>" % "".join("<th>%s</th>" % inline(c) for c in celdas))
            else:
                salida.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in celdas))
            continue
        if tabla:
            cerrar()
        m = re.match(r"^\s*[-*]\s+(.*)$", linea)
        if m:
            if parrafo:
                salida.append("<p>%s</p>" % " ".join(parrafo)); parrafo = []
            if lista != "ul":
                if lista:
                    salida.append("</%s>" % lista)
                salida.append("<ul>"); lista = "ul"
            salida.append("<li>%s</li>" % inline(m.group(1)))
            continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)$", linea)
        if m:
            if parrafo:
                salida.append("<p>%s</p>" % " ".join(parrafo)); parrafo = []
            if lista != "ol":
                if lista:
                    salida.append("</%s>" % lista)
                salida.append("<ol>"); lista = "ol"
            salida.append("<li>%s</li>" % inline(m.group(1)))
            continue
        if linea.strip().startswith(">"):
            if parrafo:
                salida.append("<p>%s</p>" % " ".join(parrafo)); parrafo = []
            salida.append("<blockquote>%s</blockquote>" % inline(linea.strip()[1:].strip()))
            continue
        parrafo.append(inline(linea.strip()))
    cerrar()
    return "\n".join(salida)


# ── validación ─────────────────────────────────────────────────────────────
def revisar_pasaje(ref, datos):
    if not ref:
        return ""
    partes = ref.split("/")
    slug = partes[0]
    libro = datos["libros"].get(slug)
    if not libro:
        return "pasaje: libro desconocido %r" % slug
    if len(partes) >= 2:
        cap = int(partes[1])
        if not 1 <= cap <= libro["chapters"]:
            return "pasaje: capítulo %d fuera de rango (1..%d)" % (cap, libro["chapters"])
        if len(partes) >= 3:
            v = int(partes[2])
            if not 1 <= v <= libro["verses"][cap - 1]:
                return "pasaje: versículo %d fuera de rango (1..%d)" % (v, libro["verses"][cap - 1])
    return ""


def validar(d, ruta, datos):
    errores = []
    if not isinstance(d.get("id"), int) or not 1 <= d["id"] <= 12:
        errores.append("id debe ser 1..12")
    for campo in ("titulo", "objetivos", "items", "ejercicios"):
        if campo not in d:
            errores.append("falta %s" % campo)
    vistos = set()
    for it in d.get("items", []):
        if not it.get("id") or it["id"] in vistos:
            errores.append("item sin id o repetido: %r" % it.get("id"))
        vistos.add(it.get("id"))
        if it.get("tipo") not in TIPOS_ITEM:
            errores.append("item %s: tipo inválido %r" % (it.get("id"), it.get("tipo")))
        if not it.get("he"):
            errores.append("item %s: sin hebreo" % it.get("id"))
        for campo in ("ejemplo",):
            if isinstance(it.get(campo), dict) and it[campo].get("ref"):
                e = revisar_pasaje(it[campo]["ref"], datos)
                if e:
                    errores.append("item %s: %s" % (it.get("id"), e))
        if it.get("ref"):
            e = revisar_pasaje(it["ref"], datos)
            if e:
                errores.append("item %s: %s" % (it.get("id"), e))
    vistos_ej = set()
    for ej in d.get("ejercicios", []):
        if not ej.get("id") or ej["id"] in vistos_ej:
            errores.append("ejercicio sin id o repetido: %r" % ej.get("id"))
        vistos_ej.add(ej.get("id"))
        if ej.get("tipo") not in TIPOS_EJ:
            errores.append("ejercicio %s: tipo inválido %r" % (ej.get("id"), ej.get("tipo")))
        if ej.get("tipo") in ("opcion", "leer", "audio"):
            ops = ej.get("opciones") or []
            if not 2 <= len(ops) <= 4:
                errores.append("ejercicio %s: %d opciones" % (ej.get("id"), len(ops)))
            if not isinstance(ej.get("correcta"), int) or not 0 <= ej["correcta"] < len(ops):
                errores.append("ejercicio %s: correcta fuera de rango" % ej.get("id"))
        if ej.get("tipo") == "escribir" and not ej.get("respuesta"):
            errores.append("ejercicio %s: sin respuesta" % ej.get("id"))
    errores += [e for e in [revisar_pasaje(d.get("pasaje"), datos)] if e]
    return errores


def construir(out="v1", contenido=None, estricto=True):
    contenido = contenido or os.path.join(RAIZ, "content", "lessons")
    datos = corpus.cargar()
    archivos = sorted(f for f in os.listdir(contenido) if re.fullmatch(r"\d+\.md", f))
    if not archivos:
        raise SystemExit("no hay lecciones en %s" % contenido)

    indice, problemas = [], []
    os.makedirs(os.path.join(out, "lessons"), exist_ok=True)
    for nombre in archivos:
        texto = open(os.path.join(contenido, nombre), encoding="utf-8").read()
        m = BLOQUE.search(texto)
        if not m:
            raise SystemExit("%s: falta el bloque ```json" % nombre)
        d = json.loads(m.group(1))
        prosa = texto[m.end():]
        errs = validar(d, nombre, datos)
        if errs:
            problemas.append((nombre, errs))
        d["html"] = md_a_html(prosa)
        d["archivo"] = nombre
        d["items_total"] = len(d.get("items", []))
        d["ejercicios_total"] = len(d.get("ejercicios", []))
        with open(os.path.join(out, "lessons", "%02d.json" % d["id"]), "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        indice.append({"id": d["id"], "titulo": d["titulo"], "objetivos": d.get("objetivos", []),
                       "items": d["items_total"], "ejercicios": d["ejercicios_total"],
                       "pasaje": d.get("pasaje", ""), "archivo": "%02d.json" % d["id"]})

    with open(os.path.join(out, "lessons", "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"total": len(indice), "lecciones": sorted(indice, key=lambda x: x["id"])},
                  fh, ensure_ascii=False, indent=1)
    if problemas and estricto:
        for nombre, errs in problemas:
            print("  %s: %s" % (nombre, "; ".join(errs[:4])))
        raise SystemExit("lecciones con errores (usa --no-estricto para publicar igual)")
    return indice, problemas


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="v1")
    ap.add_argument("--no-estricto", action="store_true")
    a = ap.parse_args()
    idx, probs = construir(a.out, estricto=not a.no_estricto)
    print("lecciones=%d items=%d ejercicios=%d problemas=%d" %
          (len(idx), sum(l["items"] for l in idx), sum(l["ejercicios"] for l in idx), len(probs)))
    for l in idx:
        print("  %02d %-38s %2d items %d ejercicios %s" %
              (l["id"], l["titulo"][:38], l["items"], l["ejercicios"], l["pasaje"]))
