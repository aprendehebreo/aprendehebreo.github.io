"use strict";
/* Aprende hebreo bíblico — app de una sola página, sin dependencias.
   Todo el material viene de la API estática v1/ del propio repo. */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const NIQ = /[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]/g;
const normHe = (t) => String(t || "").replace(NIQ, "").replace(/[\u05be\u05c0\u05c3]/g, "").replace(/\s+/g, "");
const normEs = (t) => String(t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const hoy = () => new Date().toISOString().slice(0, 10);
const TANJ = "https://avisonofgod.github.io";

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(url + " → HTTP " + r.status);
  return r.json();
}

/* ── estado y progreso ─────────────────────────────────────────────── */
const S = {
  idx: null, alefbet: null, niqqud: null, voc: {}, read: [], lex: {},
  lecciones: {},            // id -> datos de la lección (perezoso)
  progreso: { lecciones: {}, srs: {}, racha: { dias: [], ultimo: "" }, hechos: 0, aciertos: 0 },
  audioEl: null, cola: [], enCurso: null,
};

function cargarProgreso() {
  try {
    const g = JSON.parse(localStorage.getItem("aprendehebreo.v1") || "null");
    if (g) S.progreso = Object.assign(S.progreso, g);
  } catch (e) { /* progreso corrupto: se empieza de cero */ }
}
function guardarProgreso() {
  localStorage.setItem("aprendehebreo.v1", JSON.stringify(S.progreso));
  pintarProgresoMini();
}

/* ── audio ─────────────────────────────────────────────────────────── */
function tocar(ruta, boton) {
  if (!ruta) return;
  if (!S.audioEl) S.audioEl = new Audio();
  S.audioEl.pause();
  S.audioEl.src = ruta;
  S.audioEl.play().catch(() => { if (boton) boton.title = "No se pudo reproducir"; });
}
const rutaAudio = (r) => (!r ? "" : /^(v1\/|https?:)/.test(r) ? r : "v1/" + r);
const botonAudio = (ruta, etiqueta = "🔊") =>
  ruta ? `<button class="audio" data-audio="${esc(rutaAudio(ruta))}" title="Escuchar">${etiqueta}</button>` : "";

/* ── repaso espaciado (SM-2) ───────────────────────────────────────── */
const SRS = {
  tarjeta(key) {
    return S.progreso.srs[key] || { ef: 2.5, ivl: 0, reps: 0, due: hoy(), lapses: 0 };
  },
  responder(key, q) {
    const c = this.tarjeta(key);
    c.ef = Math.max(1.3, c.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
    if (q < 3) { c.reps = 0; c.ivl = 1; c.lapses++; }
    else { c.reps++; c.ivl = c.reps === 1 ? 1 : c.reps === 2 ? 6 : Math.round(c.ivl * c.ef); }
    const d = new Date(); d.setDate(d.getDate() + c.ivl);
    c.due = d.toISOString().slice(0, 10);
    S.progreso.srs[key] = c;
    if (!S.progreso.racha.dias.includes(hoy())) S.progreso.racha.dias.push(hoy());
    S.progreso.racha.ultimo = hoy();
    guardarProgreso();
  },
  vencidas() {
    const h = hoy();
    return Object.entries(S.progreso.srs).filter(([, c]) => c.due <= h).map(([k]) => k);
  },
};

function tarjetas() {
  const out = [];
  for (const l of Object.values(S.lecciones)) {
    for (const it of l.items || []) {
      out.push({ key: `${l.id}:${it.id}`, he: it.he, es: it.es || it.nota || "", xlit: it.xlit || "",
               audio: audioDe(it), ref: it.ref || (it.ejemplo && it.ejemplo.ref) || "",
                 leccion: l.id });
    }
  }
  for (const it of vocItems()) {
    out.push({ key: "voc:" + it.strong, he: it.forma_he, es: it.glosa_es, xlit: it.xlit || "",
               audio: `audio/palabra-${String(it.rango).padStart(3, "0")}.mp3`, ref: it.ref,
               strong: it.strong, leccion: 8 });
  }
  return out;
}
const vocItems = () => (S.voc.top100 && S.voc.top100.items) || [];
const porClave = () => {
  const m = {};
  for (const t of tarjetas()) m[t.key] = t;
  return m;
};

/* ── ejercicios ────────────────────────────────────────────────────── */
function pintarEjercicio(ej, leccion) {
  const id = `ej-${leccion}-${ej.id}`;
  let cuerpo = "";
  if (ej.tipo === "escribir") {
    cuerpo = `<input type="text" class="he-input" id="${id}-in" aria-label="Escribe en hebreo"
                autocomplete="off" spellcheck="false">
              <button class="primario" data-accion="revisar" data-ej="${ej.id}">Revisar</button>`;
  } else {
    const ops = (ej.opciones || []).map((o, i) =>
      `<button class="opcion" data-accion="opcion" data-ej="${ej.id}" data-i="${i}" data-leccion="${leccion}">
         <span class="muted">${i + 1}.</span> ${esc(o)}</button>`).join("");
    cuerpo = ops + (ej.tipo === "audio" && ej.audio ? botonAudio(ej.audio, "🔊 Escuchar") : "");
  }
  return `<div class="tarjeta" id="carta-${id}" data-ejercicio="${ej.id}" data-leccion="${leccion}">
    <p><strong>${esc(ej.pregunta)}</strong></p>
    ${cuerpo}
    <div class="retro" id="retro-${id}" hidden></div>
  </div>`;
}

function responderOpcion(leccion, ejId, i, boton) {
  const l = S.lecciones[leccion];
  const ej = l.ejercicios.find((e) => e.id === ejId);
  const bien = i === ej.correcta;
  const carta = boton.closest(".tarjeta");
  $$(".opcion", carta).forEach((b, j) => {
    b.disabled = true;
    if (j === ej.correcta) b.classList.add("correcta");
    else if (j === i) b.classList.add("incorrecta");
  });
  const retro = $("#retro-" + carta.id.replace("carta-", ""));
  retro.hidden = false;
  retro.className = "retro " + (bien ? "ok" : "mal");
  retro.innerHTML = (bien ? "<strong>Correcto.</strong> " : "<strong>Casi.</strong> ") + esc(ej.explica || "");
  registrar(leccion, ejId, bien);
}

function responderEscribir(leccion, ejId) {
  const l = S.lecciones[leccion];
  const ej = l.ejercicios.find((e) => e.id === ejId);
  const entrada = $(`#ej-${leccion}-${ejId}-in`);
  const bien = normHe(entrada.value) === normHe(ej.respuesta);
  const retro = $(`#retro-ej-${leccion}-${ejId}`);
  retro.hidden = false;
  retro.className = "retro " + (bien ? "ok" : "mal");
  retro.innerHTML = (bien ? "<strong>Correcto.</strong> " : `<strong>Esperado:</strong> <span class="he">${esc(ej.respuesta)}</span> `) +
    esc(ej.explica || "");
  registrar(leccion, ejId, bien);
}

function registrar(leccion, ejId, bien) {
  const p = S.progreso.lecciones[leccion] || (S.progreso.lecciones[leccion] = { ok: [], mal: [] });
  p.ok = p.ok.filter((x) => x !== ejId);
  p.mal = p.mal.filter((x) => x !== ejId);
  (bien ? p.ok : p.mal).push(ejId);
  S.progreso.hechos++;
  if (bien) S.progreso.aciertos++;
  const l = S.lecciones[leccion];
  if (p.ok.length === l.ejercicios.length) p.completo = true;
  guardarProgreso(); pintarProgresoMini();
}

/* ── vistas ────────────────────────────────────────────────────────── */
async function vistaCurso() {
  const idx = S.idx;
  const hechas = Object.values(S.progreso.lecciones).filter((p) => p.completo).length;
  const lecciones = await getJSON("v1/lessons/index.json");
  const html = `
    <h1>Curso de hebreo bíblico</h1>
    <p class="muted">Doce lecciones para leer el Tanaj desde el alef-bet. Hebreo con niqqud y te'amim,
       las 100 palabras más frecuentes (la mitad del texto), audio en cada ítem y lectura guiada.
       Sin registro: tu progreso se guarda en este navegador.</p>
    <div class="tarjeta">
      <strong>Tu avance</strong>
      <div class="barra"><i style="width:${(100 * hechas / lecciones.total).toFixed(0)}%"></i></div>
      <p class="muted">${hechas} de ${lecciones.total} lecciones completadas ·
         ${S.progreso.racha.dias.length} día(s) de estudio · ${S.progreso.aciertos}/${S.progreso.hechos} respuestas correctas</p>
      <p><a class="btn" href="#/leccion/${Math.min(hechas + 1, 12)}">${hechas ? "Continuar" : "Empezar"} lección ${Math.min(hechas + 1, 12)}</a>
         <a class="btn" href="#/repaso">Repasar (${SRS.vencidas().length})</a></p>
    </div>
    <h2>Lecciones</h2>
    <div class="grid">
      ${lecciones.lecciones.map((l) => `
        <a class="tarjeta leccion-card" href="#/leccion/${l.id}" style="text-decoration:none">
          <div class="n">${l.id}</div>
          <div>
            <strong class="${S.progreso.lecciones[l.id]?.completo ? "hecho" : ""}">${esc(l.titulo)}</strong>
            <div class="muted">${l.items} ítems · ${l.ejercicios} ejercicios${l.pasaje ? " · " + esc(l.pasaje) : ""}</div>
          </div>
        </a>`).join("")}
    </div>
    <h2>Material de consulta</h2>
    <div class="grid">
      <a class="tarjeta" href="#/alefbet"><strong>Alef-bet</strong><div class="muted">${idx.conteos.letras_y_finales} formas con audio y ejemplo real</div></a>
      <a class="tarjeta" href="#/niqqud"><strong>Niqqud</strong><div class="muted">${idx.conteos.signos_niqqud} vocales y signos del códice</div></a>
      <a class="tarjeta" href="#/vocab"><strong>Vocabulario</strong><div class="muted">100 palabras = ${idx.cobertura_vocabulario.top100.cobertura}% del Tanaj</div></a>
      <a class="tarjeta" href="#/leer"><strong>Leer</strong><div class="muted">Pasajes interlineales con análisis por palabra</div></a>
    </div>`;
  $("#vista").innerHTML = html;
}

async function vistaLeccion(id) {
  const l = S.lecciones[id] || (S.lecciones[id] = await getJSON(`v1/lessons/${String(id).padStart(2, "0")}.json`));
  const p = S.progreso.lecciones[id] || {};
  const prev = id > 1 ? `<a class="btn" href="#/leccion/${id - 1}">← Anterior</a>` : "";
  const next = id < 12 ? `<a class="btn primario" href="#/leccion/${id + 1}">Siguiente →</a>` : "";
  $("#vista").innerHTML = `
    <h1>${id}. ${esc(l.titulo)}</h1>
    <ul class="muted">${(l.objetivos || []).map((o) => `<li>${esc(o)}</li>`).join("")}</ul>
    ${p.completo ? "<p class='muted'>Lección completada ✓</p>" : ""}
    <h2>Material</h2>
    <div class="grid">
      ${(l.items || []).map((it) => tarjetaItem(it)).join("")}
    </div>
    <h2>Ejercicios</h2>
    ${(l.ejercicios || []).map((e) => pintarEjercicio(e, id)).join("")}
    <h2>Explicación</h2>
    <div class="tarjeta lectura">${l.html || ""}</div>
    ${l.pasaje ? `<p><a class="btn" href="#/leer/${l.pasaje}">Leer ${esc(l.pasaje)} con análisis →</a></p>` : ""}
    <div style="display:flex;gap:10px;margin-top:18px">${prev}<span style="flex:1"></span>${next}</div>`;
}

/* el audio de un ítem se resuelve por su letra/signo/palabra en la API */
function audioDe(it) {
  if (it.audio) return it.audio;
  if (S.alefbet) {
    const l = S.alefbet.items.find((x) => x.he === it.he);
    if (l && l.audio) return l.audio;
  }
  if (S.niqqud) {
    const s = S.niqqud.items.find((x) => x.he === it.he);
    if (s && s.audio) return s.audio;
  }
  const v = vocItems().find((x) => x.forma_he === it.he || x.forma === it.he);
  if (v) return `audio/palabra-${String(v.rango).padStart(3, "0")}.mp3`;
  const ej = it.ejemplo && it.ejemplo.he;
  if (ej && S.alefbet) {
    const l2 = S.alefbet.items.find((x) => x.he === ej);
    if (l2) return l2.audio;
  }
  return "";
}

function tarjetaItem(it) {
  const ejemplo = it.ejemplo && it.ejemplo.he
    ? `<div class="muted">Ejemplo: <span class="he">${esc(it.ejemplo.he)}</span>
       ${it.ejemplo.ref ? `<a href="${TANJ}/#/${esc(it.ejemplo.ref)}" target="_blank" rel="noopener">${esc(it.ejemplo.ref)}</a>` : ""}</div>`
    : (it.ref ? `<div class="muted">Referencia: <a href="${TANJ}/#/${esc(it.ref)}" target="_blank" rel="noopener">${esc(it.ref)}</a></div>` : "");
  return `<div class="tarjeta">
    <div class="he grande">${esc(it.he)}</div>
    <div><strong>${esc(it.es || "")}</strong>${it.xlit ? ` <span class="xlit">${esc(it.xlit)}</span>` : ""}</div>
    ${it.sonido ? `<div class="muted">Sonido: ${esc(it.sonido)}</div>` : ""}
    ${it.nota ? `<div class="muted">${esc(it.nota)}</div>` : ""}
    ${ejemplo}
    ${botonAudio(audioDe(it))}
  </div>`;
}

async function vistaAlefbet(letra) {
  const a = S.alefbet;
  const sel = letra ? a.items.find((l) => l.he === letra || l.id === letra) : null;
  $("#vista").innerHTML = `
    <h1>Alef-bet</h1>
    <p class="muted">${a.total_letras_base} letras y ${a.total_finales} formas finales.
       Se lee de derecha a izquierda. Cada letra con su sonido, su valor numérico (gematria) y una palabra real del Tanaj.</p>
    <div class="grid letras">
      ${a.items.map((l) => `
        <a class="tarjeta letra ${sel && sel.he === l.he ? "activa" : ""}" href="#/alefbet/${encodeURIComponent(l.he)}" style="text-decoration:none">
          <div class="he">${esc(l.he)}</div>
          <small>${esc(l.nombre_es)}</small>
          <small class="muted">${l.gematria}</small>
        </a>`).join("")}
    </div>
    ${sel ? detalleLetra(sel) : ""}`;
}

function detalleLetra(l) {
  return `<h2>${esc(l.nombre_es)} — <span class="he">${esc(l.he)}</span></h2>
    <div class="tarjeta">
      <div class="he grande">${esc(l.he)} ${botonAudio(l.audio)}</div>
      <table>
        <tr><th>Nombre</th><td>${esc(l.nombre_es)} · <span class="he">${esc(l.nombre_he)}</span></td></tr>
        <tr><th>Sonido</th><td>${esc(l.sonido)}</td></tr>
        <tr><th>Transliteración</th><td>${esc(l.translit_es)} <span class="muted">(académica: ${esc(l.translit_acad)})</span></td></tr>
        <tr><th>Gematria</th><td>${l.gematria}${l.final ? " · forma final de " + esc(l.base) : ""}</td></tr>
        <tr><th>Unicode</th><td>${esc(l.unicode)} · ${esc(l.nombre_unicode)}</td></tr>
        <tr><th>Ejemplo</th><td><span class="he">${esc(l.ejemplo ? l.ejemplo.forma_he : "")}</span>
            ${l.ejemplo ? `· <a href="${TANJ}/#/${esc(l.ejemplo.ref)}" target="_blank" rel="noopener">${esc(l.ejemplo.ref)}</a>
            <span class="muted">(${l.ejemplo.ocurrencias} veces en el Tanaj)</span>` : ""}</td></tr>
      </table>
      <p class="muted">${esc(l.nota)}</p>
    </div>`;
}

async function vistaNiqqud() {
  const n = S.niqqud;
  const grupos = {};
  n.items.forEach((s) => (grupos[s.tipo] = grupos[s.tipo] || []).push(s));
  const nombre = { vocal: "Vocales", jatuf: "Jatuf (vocales brevísimas)", sheva: "Sheva", dagesh: "Dagesh",
                   puntuacion: "Puntuación", "te'am": "Te'amim (acentos)", marca: "Marcas" };
  $("#vista").innerHTML = `
    <h1>Niqqud y signos</h1>
    <p class="muted">${n.total} signos. El niqqud son los puntos y rayas que indican las vocales; los te'amim marcan
       el canto y la pausa del versículo.</p>
    ${Object.entries(grupos).map(([tipo, items]) => `
      <h2>${nombre[tipo] || tipo} <span class="muted">(${items.length})</span></h2>
      <table>
        <tr><th>Signo</th><th>Nombre</th><th>Sonido</th><th>Nota</th><th>Ejemplo</th></tr>
        ${items.map((s) => `<tr>
          <td class="he" style="font-size:1.6rem">${esc(s.he)}${s.ejemplo_he ? "" : "&nbsp;"}</td>
          <td>${esc(s.nombre_es)}<div class="muted">${esc(s.codigo)}</div></td>
          <td>${esc(s.sonido)}</td>
          <td>${esc(s.nota)}</td>
          <td>${s.ejemplo_he ? `<span class="he">${esc(s.ejemplo_he)}</span> ${botonAudio(s.audio)}` : "—"}</td>
        </tr>`).join("")}
      </table>`).join("")}`;
}

async function vistaVocab(rango) {
  rango = rango || "top100";
  const d = S.voc[rango] || (S.voc[rango] = await getJSON(`v1/vocab/${rango}.json`));
  const busq = $("#q-vocab") ? $("#q-vocab").value : "";
  const filas = d.items.filter((it) => !busq || normEs(it.glosa_es).includes(normEs(busq)) ||
    it.forma.includes(busq) || it.strong.toLowerCase().includes(busq.toLowerCase()));
  $("#vista").innerHTML = `
    <h1>Vocabulario por frecuencia</h1>
    <p class="muted">Los ${d.items.length} lemas más frecuentes cubren el ${d.cobertura}% del Tanaj.</p>
    <p>
      ${["top100", "top300", "top1000"].map((r) =>
        `<a class="btn ${r === rango ? "primario" : ""}" href="#/vocab/${r}">${r.replace("top", "top ")}</a>`).join(" ")}
      <input type="search" id="q-vocab" placeholder="Filtrar (español, hebreo o H####)" value="${esc(busq)}">
    </p>
    <table>
      <thead><tr><th>#</th><th>Hebreo</th><th>Glosa</th><th>Strong</th><th>Veces</th><th>Cobertura</th><th></th></tr></thead>
      <tbody>${filas.map((it) => `<tr>
        <td class="muted">${it.rango}</td>
        <td class="he" style="font-size:1.4rem">${esc(it.forma_he || it.forma)}</td>
        <td>${esc(it.glosa_es || it.glosa_en || "")}${it.xlit ? ` <span class="xlit">${esc(it.xlit)}</span>` : ""}</td>
        <td><a href="v1/lexicon/${esc(it.strong)}.json" target="_blank" rel="noopener">${esc(it.strong)}</a></td>
        <td>${it.ocurrencias}</td>
        <td class="muted">${it.cobertura}%</td>
        <td>${botonAudio(`audio/palabra-${String(it.rango).padStart(3, "0")}.mp3`)}</td>
      </tr>`).join("")}</tbody>
    </table>`;
  const q = $("#q-vocab");
  if (q) {
    let t = null;
    q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => vistaVocab(rango), 250); });
  }
}

async function vistaRepaso() {
  const mapa = porClave();
  const vencidas = SRS.vencidas().filter((k) => mapa[k]);
  if (!S.cola.length || !S.cola.some((k) => mapa[k])) {
    const nuevas = tarjetas().filter((t) => !S.progreso.srs[t.key]).slice(0, 12).map((t) => t.key);
    S.cola = [...vencidas, ...nuevas];
  }
  const key = S.cola[0];
  const t = key ? mapa[key] : null;
  if (!t) {
    $("#vista").innerHTML = `<h1>Repaso</h1><div class="tarjeta">No hay tarjetas pendientes.
      <p class="muted">Vuelve mañana o estudia una lección nueva. El repaso espaciado (SM-2) te mostrará cada
      ítem justo antes de que lo olvides.</p></div>`;
    return;
  }
  $("#vista").innerHTML = `
    <h1>Repaso <span class="muted">(${S.cola.length} pendientes)</span></h1>
    <div class="tarjeta" style="text-align:center">
      <div class="he grande" style="font-size:3rem">${esc(t.he)}</div>
      ${botonAudio(t.audio)}
      <div id="respuesta" hidden style="margin-top:10px">
        <div><strong>${esc(t.es)}</strong>${t.xlit ? ` <span class="xlit">${esc(t.xlit)}</span>` : ""}</div>
        ${t.strong ? `<div class="muted">Léxico: <a href="v1/lexicon/${esc(t.strong)}.json" target="_blank" rel="noopener">${esc(t.strong)}</a></div>` : ""}
        ${t.ref ? `<div class="muted">Ejemplo: <a href="${TANJ}/#/${esc(t.ref)}" target="_blank" rel="noopener">${esc(t.ref)}</a></div>` : ""}
      </div>
      <p>
        <button id="ver" class="primario">Ver respuesta</button>
      </p>
      <p id="cualidades" hidden>
        <button data-q="0">Otra vez</button>
        <button data-q="3">Difícil</button>
        <button data-q="4">Bien</button>
        <button data-q="5">Fácil</button>
      </p>
      <p class="muted">${S.progreso.racha.dias.length} día(s) de estudio · ${Object.keys(S.progreso.srs).length} ítems en repaso</p>
    </div>`;
  $("#ver").onclick = () => { $("#respuesta").hidden = false; $("#cualidades").hidden = false; $("#ver").hidden = true; };
  $$("#cualidades button").forEach((b) => b.onclick = () => {
    SRS.responder(key, +b.dataset.q);
    S.cola.shift();
    vistaRepaso();
  });
}

async function vistaLeer(pasaje) {
  if (!S.read.length) S.read = (await getJSON("v1/reading/index.json")).pasajes;
  if (!pasaje) {
    $("#vista").innerHTML = `<h1>Leer el Tanaj</h1>
      <p class="muted">Pasajes con hebreo, transliteración del léxico y español, palabra por palabra.
         Haz clic en cualquier palabra para ver su forma, su número Strong y su glosa.</p>
      <div class="grid">${S.read.map((p) => `
        <a class="tarjeta" href="#/leer/${p.slug}/${p.capitulo}">
          <strong>${esc(p.slug)} ${p.capitulo}</strong>
          <div class="muted">${p.versiculos} versículos · ${p.palabras} palabras</div>
        </a>`).join("")}</div>
      <p class="muted">¿Quieres leer cualquier capítulo del Tanaj? Usa
        <a href="${TANJ}/" target="_blank" rel="noopener">el lector completo</a>
        (misma fuente de texto).</p>`;
    return;
  }
  const [slug, cap] = pasaje.split("/");
  const d = await getJSON(`v1/reading/${slug}/${cap}.json`);
  $("#vista").innerHTML = `
    <h1><span class="he">${esc(d.libro.he)}</span> ${cap} <span class="muted">· ${esc(d.libro.es)}</span></h1>
    <p class="muted">${d.total_versiculos} versículos. Pulsa una palabra para analizarla.
       <a href="${TANJ}/#/${esc(slug)}/${cap}" target="_blank" rel="noopener">Ver en el lector del Tanaj</a></p>
    <div id="analisis" class="tarjeta" hidden></div>
    ${d.versiculos.map((v) => `
      <div class="verso" id="v${v.n}">
        <div class="num">${v.n} ${botonAudio(v.audio)}</div>
        <div class="he">${v.palabras.map((w) =>
          `<span class="palabra-click" data-he="${esc(w.he)}" data-plano="${esc(w.plano)}"
                 data-strong="${esc(w.strong)}" data-xlit="${esc(w.xlit)}"
                 data-glosa="${esc(w.glosa_es)}">${esc(w.he)}</span>`).join(" ")}</div>
        <div class="es muted">${esc(v.es)}</div>
      </div>`).join("")}`;
  $$(".palabra-click").forEach((el) => el.onclick = () => {
    const w = el.dataset;
    const panel = $("#analisis");
    panel.hidden = false;
    panel.innerHTML = `<div class="he grande">${esc(w.he)}</div>
      <p><strong>${esc(w.glosa || "—")}</strong> ${w.xlit ? `<span class="xlit">${esc(w.xlit)}</span>` : ""}</p>
      <p class="muted">Forma sin signos: <span class="he">${esc(w.plano)}</span> ·
        Léxico: ${w.strong ? `<a href="v1/lexicon/${esc(w.strong)}.json" target="_blank" rel="noopener">${esc(w.strong)}</a>` : "sin número"}
        · <a href="${TANJ}/#/${esc(slug)}/${cap}" target="_blank" rel="noopener">contexto</a></p>`;
    panel.scrollIntoView({ block: "nearest" });
  });
}

function vistaProgreso() {
  const lecciones = Object.entries(S.progreso.lecciones);
  const srs = S.progreso.srs;
  const maduras = Object.values(srs).filter((c) => c.ivl >= 21).length;
  $("#vista").innerHTML = `
    <h1>Progreso</h1>
    <div class="tarjeta">
      <p><strong>${lecciones.filter(([, p]) => p.completo).length} de 12</strong> lecciones completadas ·
         <strong>${S.progreso.hechos}</strong> respuestas · ${S.progreso.aciertos} correctas
         (${S.progreso.hechos ? Math.round(100 * S.progreso.aciertos / S.progreso.hechos) : 0}%)</p>
      <p><strong>${Object.keys(srs).length}</strong> ítems en repaso espaciado (${maduras} maduros) ·
         <strong>${S.progreso.racha.dias.length}</strong> días de estudio</p>
      <p class="muted">Todo se guarda en este navegador (localStorage). Nada se envía a ningún servidor.</p>
      <p><button id="exp">Exportar progreso</button> <button id="imp">Importar</button>
         <button id="reset">Borrar</button></p>
      <textarea id="json" rows="6" style="width:100%;display:none"></textarea>
    </div>
    <h2>Lecciones</h2>
    <table>
      <tr><th>#</th><th>Estado</th><th>Aciertos</th><th>Fallos</th></tr>
      ${Array.from({ length: 12 }, (_, i) => i + 1).map((n) => {
        const p = S.progreso.lecciones[n] || { ok: [], mal: [] };
        return `<tr><td>${n}</td><td>${p.completo ? "completada ✓" : p.ok.length || p.mal.length ? "en curso" : "sin empezar"}</td>
                <td>${p.ok.length}</td><td>${p.mal.length}</td></tr>`;
      }).join("")}
    </table>`;
  $("#exp").onclick = () => {
    const t = $("#json"); t.style.display = "block";
    t.value = JSON.stringify(S.progreso);
    t.select(); document.execCommand && document.execCommand("copy");
    $("#estado").textContent = "Progreso copiado al portapapeles (JSON).";
  };
  $("#imp").onclick = () => {
    const t = $("#json");
    if (t.style.display === "none") { t.style.display = "block"; t.placeholder = "Pega aquí el JSON exportado"; return; }
    try { S.progreso = Object.assign(S.progreso, JSON.parse(t.value)); guardarProgreso(); vistaProgreso(); }
    catch (e) { $("#estado").textContent = "JSON inválido"; }
  };
  $("#reset").onclick = () => {
    if (confirm("¿Borrar todo el progreso de este navegador?")) {
      S.progreso = { lecciones: {}, srs: {}, racha: { dias: [], ultimo: "" }, hechos: 0, aciertos: 0 };
      guardarProgreso(); vistaProgreso();
    }
  };
}

function pintarProgresoMini() {
  const hechas = Object.values(S.progreso.lecciones).filter((p) => p.completo).length;
  const mini = $("#progreso-mini");
  if (mini) mini.textContent = `${hechas}/12 lecciones`;
  const pend = $("#pendientes");
  if (pend) pend.textContent = String(SRS.vencidas().length);
}

/* ── router ────────────────────────────────────────────────────────── */
async function pintar() {
  const hash = location.hash.replace(/^#\/?/, "");
  const [ruta, a, b] = hash.split("/");
  $$("header nav a").forEach((x) => {
    const dest = x.getAttribute("href").replace(/^#\/?/, "").split("/")[0];
    if (dest === (ruta || "")) x.setAttribute("aria-current", "page");
    else x.removeAttribute("aria-current");
  });
  try {
    if (!ruta) await vistaCurso();
    else if (ruta === "leccion") await vistaLeccion(Math.min(12, Math.max(1, +a || 1)));
    else if (ruta === "alefbet") await vistaAlefbet(a ? decodeURIComponent(a) : null);
    else if (ruta === "niqqud") await vistaNiqqud();
    else if (ruta === "vocab") await vistaVocab(a);
    else if (ruta === "repaso") await vistaRepaso();
    else if (ruta === "leer") await vistaLeer(a ? `${a}/${b || 1}` : null);
    else if (ruta === "progreso") vistaProgreso();
    else await vistaCurso();
    window.scrollTo({ top: 0 });
  } catch (e) {
    $("#vista").innerHTML = `<div class="tarjeta"><strong>No se pudo cargar.</strong>
      <p class="muted">${esc(e.message)}</p>
      <p class="muted">Si abriste el archivo directamente, sirve el sitio por HTTP
      (<code>python3 -m http.server</code>).</p></div>`;
  }
  pintarProgresoMini();
}

document.addEventListener("click", (e) => {
  const aud = e.target.closest("[data-audio]");
  if (aud) { tocar(aud.dataset.audio, aud); return; }
  const op = e.target.closest("[data-accion=opcion]");
  if (op) { responderOpcion(+op.dataset.leccion, op.dataset.ej, +op.dataset.i, op); return; }
  const rev = e.target.closest("[data-accion=revisar]");
  if (rev) {
    const carta = rev.closest(".tarjeta");
    responderEscribir(+carta.dataset.leccion, rev.dataset.ej);
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.classList.contains("he-input")) {
    const carta = e.target.closest(".tarjeta");
    responderEscribir(+carta.dataset.leccion, carta.dataset.ejercicio);
    return;
  }
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  const carta = $(".tarjeta:has(.opcion:not([disabled]))");
  if (!carta || !/^[1-4]$/.test(e.key)) return;
  const boton = $$(".opcion", carta)[+e.key - 1];
  if (boton && !boton.disabled) responderOpcion(+carta.dataset.leccion, carta.dataset.ejercicio, +e.key - 1, boton);
});
window.addEventListener("hashchange", pintar);

async function arrancar() {
  cargarProgreso();
  try {
    S.idx = await getJSON("v1/index.json");
    const [alef, nq] = await Promise.all([getJSON("v1/alefbet.json"), getJSON("v1/niqqud.json")]);
    S.alefbet = alef; S.niqqud = nq;
    const li = await getJSON("v1/lessons/index.json");
    for (const l of li.lecciones) S.lecciones[l.id] = await getJSON(`v1/lessons/${l.archivo}`);
    S.voc.top100 = await getJSON("v1/vocab/top100.json");   // objeto {rango, cobertura, items}
  } catch (e) {
    $("#vista").innerHTML = `<div class="tarjeta"><strong>Error al cargar la API.</strong>
      <p class="muted">${esc(e.message)}</p></div>`;
  }
  await pintar();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}
window.Hebreo = { S, SRS, tarjetas, pintar, normHe };   // usado por las pruebas
arrancar();
