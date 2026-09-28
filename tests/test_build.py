"""Pruebas del generador del curso (sin red).

    python3 -m unittest discover -s tests -p 'test_*.py' -v
"""

# pyright: reportMissingImports=false
import json
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "build"))

import alefbet as alefbet_mod                          # noqa: E402
import lessons as lessons_mod                          # noqa: E402
import corpus                                          # noqa: E402
import vocab as vocab_mod                              # noqa: E402

V1 = os.path.join(RAIZ, "v1")
HAY_DATOS = os.path.exists(os.path.join(RAIZ, "data", "corpus.json"))
HAY_V1 = os.path.exists(os.path.join(V1, "index.json"))


def cargar(rel):
    with open(os.path.join(V1, rel), encoding="utf-8") as fh:
        return json.load(fh)


class TestMarkdown(unittest.TestCase):
    def test_titulos_listas_tablas(self):
        html = lessons_mod.md_a_html("## T\n\nParrafo **b** y `c`.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n- x\n- y\n\n1. u\n2. d\n\n> cita\n")
        for pieza in ("<h2>T</h2>", "<strong>b</strong>", "<code>c</code>", "<th>a</th>", "<td>1</td>",
                      "<ul>", "<ol>", "<blockquote>cita</blockquote>"):
            self.assertIn(pieza, html)

    def test_escapa_html(self):
        self.assertNotIn("<script>", lessons_mod.md_a_html("<script>alert(1)</script>"))


@unittest.skipUnless(HAY_DATOS, "faltan datos: corre build/build_all.py")
class TestCorpus(unittest.TestCase):
    def test_conteos(self):
        d = corpus.cargar()
        self.assertEqual(d["total_palabras"], 306785)
        self.assertEqual(d["lemas"], 8640)
        self.assertEqual(len(d["libros"]), 39)
        self.assertEqual(sum(v["chapters"] for v in d["libros"].values()), 929)
        self.assertEqual(sum(v["verses_total"] for v in d["libros"].values()), 23213)


@unittest.skipUnless(HAY_V1, "falta v1/: corre build/build_all.py")
class TestAlefbet(unittest.TestCase):
    def test_formas_y_gematria(self):
        a = cargar("alefbet.json")
        self.assertEqual(a["total_formas"], 27)
        self.assertEqual(a["total_letras_base"], 22)
        self.assertEqual(a["total_finales"], 5)
        gem = {l["he"]: l["gematria"] for l in a["items"]}
        self.assertEqual([gem[x] for x in "אבגדהוזחטיכלמנסעפצקרשת"],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400])
        self.assertEqual([gem[x] for x in "ךםןףץ"], [500, 600, 700, 800, 900])

    def test_finales_apuntan_a_su_base(self):
        a = cargar("alefbet.json")
        pares = {l["he"]: l["base"] for l in a["items"] if l["final"]}
        self.assertEqual(pares, {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})

    def test_ejemplos_reales(self):
        a = cargar("alefbet.json")
        for l in a["items"]:
            self.assertTrue(l["ejemplo"] and l["ejemplo"]["ref"], l["id"])
            self.assertIn("/", l["ejemplo"]["ref"])

    def test_niqqud(self):
        n = cargar("niqqud.json")
        self.assertGreaterEqual(n["total"], 50)
        self.assertEqual(sum(n["por_tipo"].values()), n["total"])
        self.assertIn("vocal", n["por_tipo"])
        sin_nombre = [s for s in n["items"] if not s["nombre_es"] or not s["codigo"].startswith("U+")]
        self.assertEqual(sin_nombre, [])


@unittest.skipUnless(HAY_V1, "falta v1/: corre build/build_all.py")
class TestVocabYLecciones(unittest.TestCase):
    def test_cobertura(self):
        v = cargar("vocab/index.json")
        self.assertAlmostEqual(v["rangos"]["top100"]["cobertura"], 50.5, delta=0.2)
        self.assertAlmostEqual(v["rangos"]["top300"]["cobertura"], 67.8, delta=0.2)
        self.assertAlmostEqual(v["rangos"]["top1000"]["cobertura"], 83.5, delta=0.2)
        top300 = cargar("vocab/top300.json")["items"]
        self.assertEqual(len(top300), 300)
        self.assertTrue(all(it["glosa_es"] for it in top300))
        self.assertEqual(len({it["strong"] for it in top300}), 300)

    def test_glosas_sin_repetir(self):
        ruta = os.path.join(RAIZ, "content", "vocab", "glosas_es.tsv")
        glosas = vocab_mod.leer_glosas(ruta)
        self.assertGreaterEqual(len(glosas), 300)
        self.assertTrue(all(v.strip() for v in glosas.values()))

    def test_lecciones_validan(self):
        datos = corpus.cargar()
        idx = cargar("lessons/index.json")
        self.assertEqual(idx["total"], 12)
        for l in idx["lecciones"]:
            d = cargar("lessons/" + l["archivo"])
            self.assertEqual(lessons_mod.validar(d, l["archivo"], datos), [], l["archivo"])
            self.assertTrue(d["html"].strip())

    def test_lexico_h7225(self):
        e = cargar("lexicon/H7225.json")
        self.assertEqual(e["he"], "ראשית")
        self.assertTrue(e["xlit"] and e["def_en"] and e["ocurrencias"] > 0)
        self.assertIn("H7218", e["raices"])

    def test_lectura_bereshit_1(self):
        d = cargar("reading/bereshit/1.json")
        self.assertEqual(d["total_versiculos"], 31)
        v1 = d["versiculos"][0]
        self.assertTrue(v1["he_plain"].startswith("בראשית ברא אלהים"))
        self.assertTrue(v1["es"].startswith("EN el principio"))
        self.assertTrue(all(w["plano"] for w in v1["palabras"]))
        con_strong = [w for w in v1["palabras"] if w["strong"]]
        self.assertGreaterEqual(len(con_strong), 5)

    def test_verify_completo(self):
        """verify.py debe terminar sin fallas (cotejo de citas, audio en disco, sha256...)."""
        import subprocess
        r = subprocess.run([sys.executable, "build/verify.py"], cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-800:])
        self.assertIn("0 FALLA", r.stdout)
        self.assertIn("cada palabra citada aparece en su versículo", r.stdout)

    def test_audio_presente(self):
        a = cargar("audio/index.json")
        self.assertGreaterEqual(a["total"], 250)
        muestra = ["letra-01.mp3", "palabra-001.mp3", "verso-bereshit-1-1.mp3"]
        for m in muestra:
            p = os.path.join(V1, "audio", m)
            self.assertTrue(os.path.exists(p), m)
            self.assertGreater(os.path.getsize(p), 512, m)


if __name__ == "__main__":
    unittest.main(verbosity=2)
