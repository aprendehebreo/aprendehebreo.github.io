# pyright: reportMissingImports=false
"""Audio del curso: letras, vocales y las 100 palabras más frecuentes.

Genera MP3 con edge-tts (voces he-IL de Microsoft Edge, sin clave de API) y escribe
v1/audio/index.json con el texto de cada clip.

Uso:
    python3 build/audio.py                 # genera lo que falte
    python3 build/audio.py --force         # regenera todo
    python3 build/audio.py --voz he-IL-AvriNeural
"""

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = os.path.join(os.path.dirname(RAIZ), ".venv", "bin", "edge-tts")
VOZ = "he-IL-HilaNeural"
VELOCIDAD = "-10%"          # un poco más lento: es material de aprendizaje


def cargar(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def lista_trabajo(out="v1"):
    trabajos = []
    alef = cargar(os.path.join(out, "alefbet.json"))
    for l in alef["items"]:
        trabajos.append({"id": l["audio"], "texto": l["nombre_he"],
                         "grupo": "letra", "ref_id": l["id"]})
    nq = cargar(os.path.join(out, "niqqud.json"))
    for s in nq["items"]:
        if s.get("audio") and s.get("ejemplo_he"):
            trabajos.append({"id": s["audio"], "texto": s["ejemplo_he"],
                             "grupo": "niqqud", "ref_id": s["id"]})
    vc = cargar(os.path.join(out, "vocab", "top100.json"))
    for i, it in enumerate(vc["items"], 1):
        trabajos.append({"id": "audio/palabra-%03d.mp3" % i, "texto": it["forma_he"],
                         "grupo": "palabra", "ref_id": it["strong"]})
    idx_pas = os.path.join(out, "reading", "index.json")
    if os.path.exists(idx_pas):
        for p in cargar(idx_pas)["pasajes"]:
            d = cargar(os.path.join(out, p["archivo"]))
            for v in d["versiculos"]:
                trabajos.append({"id": v["audio"], "texto": v["he"], "grupo": "verso",
                                 "ref_id": "%s/%d/%d" % (p["slug"], p["capitulo"], v["n"])})
    return trabajos


def generar(trabajo, destino, voz, forzar=False):
    ruta = os.path.join(destino, trabajo["id"].replace("audio/", ""))
    if os.path.exists(ruta) and not forzar and os.path.getsize(ruta) > 512:
        return trabajo, os.path.getsize(ruta), "ya existe"
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    # ojo: "--rate=-10%" con "=" porque el valor empieza por guion
    cmd = [EDGE, "--voice", voz, "--rate=" + VELOCIDAD,
           "--text", trabajo["texto"], "--write-media", ruta]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=90)
    except Exception as exc:                                    # noqa: BLE001
        return trabajo, 0, "error: %s" % exc
    return trabajo, os.path.getsize(ruta) if os.path.exists(ruta) else 0, "ok"


def construir(out="v1", voz=VOZ, forzar=False, hilos=4):
    destino = os.path.join(RAIZ, out, "audio")
    trabajos = lista_trabajo(out)
    hechos = {}
    fallos = []
    with cf.ThreadPoolExecutor(max_workers=hilos) as pool:
        for trabajo, size, estado in pool.map(lambda t: generar(t, destino, voz, forzar), trabajos):
            if size > 512:
                hechos[trabajo["id"]] = {"texto": trabajo["texto"], "grupo": trabajo["grupo"],
                                         "ref_id": trabajo["ref_id"], "bytes": size}
            else:
                fallos.append((trabajo["id"], estado))
    with open(os.path.join(destino, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"voz": voz, "velocidad": VELOCIDAD, "total": len(hechos),
                   "nota": "Audio generado con edge-tts (voces he-IL de Microsoft Edge).",
                   "clips": hechos}, fh, ensure_ascii=False, indent=1)
    return hechos, fallos


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="v1")
    ap.add_argument("--voz", default=VOZ)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--hilos", type=int, default=4)
    a = ap.parse_args()
    if not os.path.exists(EDGE):
        raise SystemExit("falta edge-tts: python3 -m venv .venv && .venv/bin/pip install edge-tts")
    hechos, fallos = construir(a.out, a.voz, a.force, a.hilos)
    kb = sum(v["bytes"] for v in hechos.values()) / 1024
    print("clips=%d (%.0f KB) voz=%s" % (len(hechos), kb, a.voz))
    if fallos:
        print("fallos (%d): %s" % (len(fallos), fallos[:5]))
        sys.exit(1)
