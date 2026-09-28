/* Pruebas de la app del curso sin navegador (jsdom) contra la API real del repo.
 *
 *   NODE_PATH=/tmp/jtest/node_modules node tests/app-test.js
 */
const fs = require("fs");
const path = require("path");

let JSDOM;
try { ({ JSDOM } = require("jsdom")); }
catch (e) { ({ JSDOM } = require("/tmp/jtest/node_modules/jsdom")); }

const ROOT = path.resolve(__dirname, "..");
// jsdom no carga <script src> sin servidor: se inyecta app.js en línea (mismo código).
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8")
  // ojo: el reemplazo va en función para que "$$" y "$&" del código no se interpreten
  .replace('<script src="app.js"></script>',
           () => "<script>" + fs.readFileSync(path.join(ROOT, "app.js"), "utf8") + "</script>");
const leer = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));

let ok = 0, fail = 0;
const chk = (c, label, d) => { if (c) { ok++; console.log("OK   " + label + (d ? " | " + d : "")); }
                               else { fail++; console.log("FALLA " + label + (d ? " | " + d : "")); } };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const letters = (s) => (s || "").replace(/[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]/g, "");

const falta = [];

async function arrancar() {
  const dom = new JSDOM(html, {
    url: "http://localhost/", runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(win) {
      win.fetch = async (url) => {
        const p = path.join(ROOT, String(url).replace(/^\//, "").split("?")[0]);
        if (!fs.existsSync(p)) return { ok: false, status: 404, json: async () => ({}) };
        return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, "utf8")) };
      };
      win.Element.prototype.scrollIntoView = () => {};
      win.scrollTo = () => {};
      win.Audio = class { constructor() {} play() { return Promise.resolve(); } pause() {} };
      win.navigator.clipboard = { writeText: async () => {} };
      win.confirm = () => true;
    },
  });
  await wait(500);
  return dom.window;
}

(async () => {
  const w = await arrancar();
  const $ = (s) => w.document.querySelector(s);
  const $$ = (s) => Array.from(w.document.querySelectorAll(s));

  // 0) sin recursos externos
  const ext = $$("script[src], link[href]").map((e) => e.getAttribute("src") || e.getAttribute("href"))
    .filter((u) => u && /^https?:/i.test(u));
  chk(ext.length === 0, "sin recursos externos", ext.join(","));
  chk($$("header nav a").length === 7, "menú con 7 secciones", $$("header nav a").length);

  // 1) portada con las 12 lecciones
  chk(/Curso de hebreo bíblico/.test($("#vista").textContent), "portada cargada");
  chk($$("#vista .leccion-card").length === 12, "portada lista 12 lecciones", $$("#vista .leccion-card").length);

  // 2) alef-bet: 27 formas con audio
  w.location.hash = "#/alefbet";
  await wait(300);
  chk($$("#vista .letra").length === 27, "alef-bet: 27 formas", $$("#vista .letra").length);
  w.location.hash = "#/alefbet/" + encodeURIComponent("א");
  await wait(300);
  chk(/Gematria/.test($("#vista").textContent) && /1/.test($("#vista table").textContent),
      "detalle de letra con gematria");
  chk($$("#vista [data-audio]").length > 0, "detalle de letra con botón de audio");
  const audioLetra = $("#vista [data-audio]").getAttribute("data-audio");
  chk(fs.existsSync(path.join(ROOT, audioLetra)), "el audio de la letra existe en disco", audioLetra);

  // 3) niqqud
  w.location.hash = "#/niqqud";
  await wait(300);
  chk($$("#vista h2").length >= 5, "niqqud agrupado por tipo", $$("#vista h2").length);
  chk(/kamats/.test($("#vista").textContent), "niqqud incluye kamats");

  // 4) vocabulario
  w.location.hash = "#/vocab";
  await wait(400);
  chk($$("#vista tbody tr").length === 100, "vocabulario: 100 filas", $$("#vista tbody tr").length);
  const mCob = $("#vista").textContent.match(/cubren el ([\d.]+)%/);
  chk(mCob && Math.abs(parseFloat(mCob[1]) - 50.5) < 0.2, "vocabulario muestra la cobertura (~50,5%)",
      mCob ? mCob[1] + "%" : "no encontrado");

  // 5) lección 2: ítems con audio y ejercicio que se responde
  w.location.hash = "#/leccion/2";
  await wait(400);
  const items = $$("#vista .tarjeta .he.grande").length;
  chk(items >= 6, "lección 2 con ítems (≥6)", items);
  const opciones = $$("#vista .opcion");
  chk(opciones.length >= 4, "lección 2 con opciones de ejercicio", opciones.length);
  const carta = opciones[0].closest(".tarjeta");
  const ejId = carta.dataset.ejercicio;
  const lec = +carta.dataset.leccion;
  const correcta = leer(`v1/lessons/${String(lec).padStart(2, "0")}.json`).ejercicios.find((e) => e.id === ejId).correcta;
  $$(".opcion", carta)[correcta].click();
  await wait(50);
  const retro = carta.querySelector(".retro");
  chk(!retro.hidden && /Correcto/.test(retro.textContent), "respuesta correcta marcada", retro.textContent.slice(0, 24));
  chk(JSON.parse(w.localStorage.getItem("aprendehebreo.v1")).lecciones[lec].ok.includes(ejId),
      "el acierto se guarda en localStorage");

  // 6) ejercicio de escritura (lección 1 o 2, tipo escribir)
  const lec1 = leer("v1/lessons/01.json");
  const escribir = lec1.ejercicios.find((e) => e.tipo === "escribir");
  if (escribir) {
    w.location.hash = "#/leccion/1";
    await wait(300);
    const carta2 = $$("#vista .tarjeta").find((c) => c.dataset.ejercicio === escribir.id);
    const input = carta2.querySelector("input");
    input.value = escribir.respuesta;
    carta2.querySelector("[data-accion=revisar]").click();
    await wait(50);
    chk(/Correcto/.test(carta2.querySelector(".retro").textContent),
        "ejercicio de escritura acepta la respuesta exacta");
    input.value = escribir.respuesta.replace(/[\u0591-\u05bd]/g, "");
    carta2.querySelector("[data-accion=revisar]").click();
    chk(/Correcto/.test(carta2.querySelector(".retro").textContent),
        "y también sin niqqud (comparación normalizada)");
  } else {
    falta.push("lección 1 sin ejercicio de escritura (opcional)");
  }

  // 7) repaso espaciado
  w.location.hash = "#/repaso";
  await wait(400);
  chk(/Repaso/.test($("#vista").textContent), "vista de repaso");
  const antes = Object.keys(JSON.parse(w.localStorage.getItem("aprendehebreo.v1") || "{}").srs || {}).length;
  $("#ver").click();
  await wait(50);
  chk(!$("#respuesta").hidden, "la tarjeta revela la respuesta");
  const bien = $$("#cualidades button").find((b) => b.dataset.q === "4");
  bien.click();
  await wait(200);
  const despues = Object.keys(JSON.parse(w.localStorage.getItem("aprendehebreo.v1")).srs).length;
  chk(despues === antes + 1, "SM-2 registra la tarjeta respondida", `${antes} → ${despues}`);

  // 8) lectura interlineal con análisis por palabra
  w.location.hash = "#/leer";
  await wait(400);
  chk($$("#vista .tarjeta").length >= 5, "lectura: 5 pasajes", $$("#vista .tarjeta").length);
  w.location.hash = "#/leer/bereshit/1";
  await wait(500);
  const palabras = $$("#vista .palabra-click");
  chk(palabras.length > 400, "Bereshit 1 con palabras analizables", palabras.length);
  palabras[0].click();
  await wait(50);
  chk(!$("#analisis").hidden && /H\d+/.test($("#analisis").textContent), "el clic muestra el análisis (Strong)",
      $("#analisis").textContent.slice(0, 40));
  chk(/EN el principio|en el principio/i.test($("#vista").textContent), "el español del versículo está presente");

  // 9) progreso
  w.location.hash = "#/progreso";
  await wait(300);
  chk(/Progreso/.test($("#vista").textContent) && /respuestas/.test($("#vista").textContent), "vista de progreso con estadísticas");

  // 10) la API declara 12 lecciones y 253 clips
  const idx = leer("v1/index.json");
  chk(idx.conteos.lecciones === 12 && idx.conteos.clips_audio >= 250, "portada de la API coherente",
      JSON.stringify(idx.conteos));

  if (falta.length) console.log("NOTA: " + falta.join("; "));
  console.log("\n== RESUMEN: " + ok + " OK / " + fail + " FALLA ==");
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
