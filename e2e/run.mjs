#!/usr/bin/env node
// Pruebas de punta a punta del plugin en Obsidian real, vía el CLI de Obsidian.
//
// Requisitos: entorno creado con e2e/preparar.sh, catálogo servido con
// e2e/servir.sh (o URL_CATALOGO apuntando a GitHub) y Obsidian abierto con
// e2e/obsidian.sh. Uso:  node e2e/run.mjs [escenario …]
//
// Escribe $E2E_DIR/informe.md y las capturas en $E2E_DIR/capturas/.
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const E2E = process.env.E2E_DIR || "/tmp/normas-e2e";
const VAULT = join(E2E, "vault");
const CAPTURAS = join(E2E, "capturas");
const OBS = join(AQUI, "obsidian.sh");
const PLUGIN = 'app.plugins.plugins["normas-colombianas"]';
mkdirSync(CAPTURAS, { recursive: true });

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

/** Ejecuta un comando del CLI de Obsidian y devuelve su salida. */
function ob(...args) {
  const r = spawnSync(OBS, args, {
    encoding: "utf8",
    timeout: 600_000,
    env: { ...process.env, E2E_DIR: E2E },
  });
  if (r.error) throw r.error;
  return (r.stdout || "").trim();
}

/** Evalúa JavaScript dentro de Obsidian (espera promesas) y devuelve el valor como texto. */
function js(codigo) {
  const out = ob("eval", `code=${codigo}`);
  if (out === "=>") return ""; // resultado vacío
  return out.startsWith("=> ") ? out.slice(3) : out;
}
const jsJSON = (codigo) => {
  // Con Obsidian ocupado (indexando, buscando) el CLI a veces devuelve vacío: reintentar.
  let t = "";
  // Tras descargar miles de notas el índice puede tardar más de un minuto en liberarse.
  for (let k = 0; k < 20 && !t; k++) {
    t = js(`(async()=>JSON.stringify(await (async()=>(${codigo}))()))()`);
    if (!t) spawnSync("sleep", ["3"]);
  }
  try {
    return JSON.parse(t);
  } catch {
    throw new Error(`eval no devolvió JSON: ${t.slice(0, 300)}`);
  }
};

function captura(nombre) {
  const ruta = join(CAPTURAS, `${nombre}.png`);
  ob("dev:screenshot", `path=${ruta}`);
  return ruta;
}

async function abrir(ruta, { lectura = false } = {}) {
  ob("open", `path=${ruta}`);
  await dormir(700);
  // Dar el foco a la pestaña de la nota (no al panel de búsqueda u otro lateral).
  js(`(()=>{const l=app.workspace.getLeavesOfType("markdown").find(x=>x.view.file&&x.view.file.path===${JSON.stringify(ruta)});if(l)app.workspace.setActiveLeaf(l,{focus:true});return 1})()`);
  await dormir(300);
  const modo = js("app.workspace.activeLeaf.view.getMode && app.workspace.activeLeaf.view.getMode()");
  if ((lectura && modo !== "preview") || (!lectura && modo === "preview")) {
    ob("command", "id=markdown:toggle-preview");
    await dormir(700);
  }
}

const resultados = [];
function registrar(escenario, ok, detalle, capturas = []) {
  resultados.push({ escenario, ok, detalle, capturas });
  console.log(`${ok ? "✓" : "✗"} ${escenario}: ${detalle}`);
}
async function escenario(nombre, fn) {
  fijarVentana();
  try {
    await fn();
  } catch (e) {
    registrar(nombre, false, `excepción: ${e.message}`);
  }
}

/**
 * El `eval` del CLI no espera promesas largas: se lanza la tarea en segundo
 * plano dentro de Obsidian y se sondea su resultado.
 */
async function tarea(clave, codigoAsync, maxSeg = 900) {
  js(`(()=>{window.__e2e=window.__e2e||{};delete window.__e2e[${JSON.stringify(clave)}];(async()=>{try{window.__e2e[${JSON.stringify(clave)}]={ok:true,v:await (${codigoAsync})}}catch(e){window.__e2e[${JSON.stringify(clave)}]={ok:false,v:String(e)}}})();return 1})()`);
  const t0 = Date.now();
  while ((Date.now() - t0) / 1000 < maxSeg) {
    await dormir(1000);
    const r = js(`JSON.stringify((window.__e2e||{})[${JSON.stringify(clave)}]||null)`);
    if (r && r !== "null") return { ...JSON.parse(r), seg: (Date.now() - t0) / 1000 };
  }
  throw new Error(`la tarea «${clave}» no terminó en ${maxSeg} s`);
}

/** Cuenta elementos del DOM («No elements found.» = 0). */
/** Notas de una carpeta según Obsidian. Mientras indexa, el CLI puede responder vacío
 *  (= 0): se reintenta hasta obtener `esperado` o agotar los intentos. */
async function contarNotas(carpeta, esperado = null) {
  let n = 0;
  for (let k = 0; k < 10; k++) {
    if (k) await dormir(2000);
    n = Number(ob("files", `folder=${carpeta}`, "total")) || 0;
    if (esperado === null ? n > 0 : n === esperado) break;
  }
  return n;
}
const cuenta = (selector) => Number(ob("dev:dom", `selector=${selector}`, "total")) || 0;

/** Espera a que exista un elemento del DOM; devuelve su texto (o "" si no aparece). */
async function esperarDom(selector, maxMs = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    const n = cuenta(selector);
    if (n > 0) return ob("dev:dom", `selector=${selector}`, "text", "all");
    await dormir(400);
  }
  return "";
}
const existe = (ruta) => !/not found|no existe/i.test(ob("file", `path=${ruta}`)) && ob("file", `path=${ruta}`) !== "";

/**
 * Hace scroll hasta el final de la vista de lectura (el renderizado es diferido)
 * y espera a que exista el pie de navegación («↑ …»).
 */
async function alFinal() {
  for (let k = 0; k < 20; k++) {
    const r = js(`(()=>{const v=document.querySelector(".workspace-leaf.mod-active .markdown-preview-view");if(!v)return "sin-vista";v.scrollTop=v.scrollHeight-v.clientHeight;return [...v.querySelectorAll("a.internal-link")].some(a=>/^Capítulo|^Título|^Libro|^Sección|^Parte/.test(a.textContent)&&v.scrollTop>0)?"pie":"no"})()`);
    if (r === "pie" && k >= 1) return;
    await dormir(600);
  }
}
const SEL_ENLACES = ".workspace-leaf.mod-active .markdown-preview-view a.internal-link";

/** Busca la ruta de una nota de la biblioteca por nombre. */
const rutaDe = (nombre) =>
  jsJSON(`(app.metadataCache.getFirstLinkpathDest(${JSON.stringify(nombre)}, "")||{}).path||""`);

// ---------------------------------------------------------------------------

const elegidos = new Set(process.argv.slice(2));
const corre = (id) => elegidos.size === 0 || elegidos.has(id);

// Ventana de tamaño fijo para capturas comparables (se pierde al abrir/cerrar otras
// ventanas o la emulación móvil, por eso se reaplica en cada escenario).
function fijarVentana() {
  ob("dev:cdp", "method=Emulation.setDeviceMetricsOverride",
    'params={"width":1400,"height":900,"deviceScaleFactor":1,"mobile":false}');
}
fijarVentana();

// Con una configuración nueva Obsidian abre Preferencias unos segundos después de
// arrancar; mientras esté abierta, los modales y avisos se dibujan en esa ventana.
async function cerrarPreferencias() {
  for (let k = 0; k < 20; k++) {
    js(`(()=>{try{app.setting.close()}catch(e){}return 1})()`);
    await dormir(700);
    const abierta = spawnSync(join(AQUI, "ventana.sh"), ["Preferencias"], { encoding: "utf8" }).stdout.trim();
    if (!abierta && k >= 2) return;
  }
}
await cerrarPreferencias();

// Bóveda nueva: Obsidian pregunta «¿Confía en el autor de esta bóveda?» y deja los
// complementos sin cargar (modo restringido) hasta que se acepta.
async function activarComplementos() {
  for (let k = 0; k < 30; k++) {
    if (js(`String(!!app.plugins.plugins["normas-colombianas"])`) === "true") return true;
    js(`(()=>{const b=[...document.querySelectorAll(".modal button")].find(x=>/Confiar|Trust/.test(x.textContent));if(b)b.click();return 1})()`);
    if (k === 3) {
      ob("plugins:restrict", "off");
      ob("plugin:enable", "id=dataview");
      ob("plugin:enable", "id=normas-colombianas");
    }
    await dormir(1000);
  }
  return false;
}
const pluginActivo = await activarComplementos();
await cerrarPreferencias();

if (corre("arranque")) await escenario("1. Arranque", async () => {
  const habilitados = ob("plugins:enabled", "filter=community");
  const errores = ob("dev:errors");
  const ok = pluginActivo && habilitados.includes("normas-colombianas") && /No errors/i.test(errores);
  registrar("1. Arranque", ok, `plugins: ${habilitados.replace(/\n/g, ", ")}; errores: ${errores.slice(0, 120)}`,
    [captura("01-arranque")]);
});

let base = null;
if (corre("linea-base")) await escenario("2. Línea base de enlaces", async () => {
  base = Number(ob("unresolved", "total"));
  const lista = jsJSON(`Object.entries(app.metadataCache.unresolvedLinks).filter(([f])=>!f.startsWith("Normas/")).reduce((t,[,o])=>t+Object.entries(o).filter(([l])=>/^art\\. /.test(l)).reduce((a,[,n])=>a+n,0),0)`);
  writeFileSync(join(E2E, "linea-base.json"), JSON.stringify({ unresolved: base, articulos: lista }));
  registrar("2. Línea base de enlaces", true, `${base} enlaces sin resolver (${lista} a artículos)`);
});

if (corre("descarga-ui")) await escenario("3. Descarga por la interfaz (Ley 1996)", async () => {
  // Punto de partida limpio: sin normas descargadas.
  js(`(async()=>{for(const c of ["Normas","Biblioteca jurídica","Pruebas"]){const f=app.vault.getAbstractFileByPath(c);if(f)await app.vault.delete(f,true)}${PLUGIN}.settings.instaladas={};await ${PLUGIN}.saveSettings();return 1})()`);
  await dormir(1000);
  await cerrarPreferencias();
  ob("command", "id=normas-colombianas:descargar-norma");
  let sugerencias = 0;
  for (let k = 0; k < 30 && !(sugerencias > 0); k++) {
    await dormir(500);
    sugerencias = cuenta(".suggestion-item");
  }
  const c1 = captura("03a-selector");
  js(`(()=>{const i=document.querySelector(".prompt-input");i.value="1996";i.dispatchEvent(new Event("input"));return 1})()`);
  await dormir(600);
  const filtradas = ob("dev:dom", "selector=.suggestion-item", "text", "all");
  const c2 = captura("03b-selector-filtrado");
  ob("dev:cdp", "method=Input.dispatchKeyEvent", 'params={"type":"keyDown","key":"Enter","code":"Enter","windowsVirtualKeyCode":13}');
  // Espera a que termine la escritura (el aviso de éxito y el registro en ajustes).
  let instalada = false;
  for (let k = 0; k < 40 && !instalada; k++) {
    await dormir(500);
    instalada = js(`!!${PLUGIN}.settings.instaladas["Ley 1996 de 2019"]`) === "true";
  }
  const avisos = ob("dev:dom", "selector=.notice", "text", "all");
  const c3 = captura("03c-aviso");
  const notas = Number(ob("files", "folder=Normas/Ley 1996 de 2019", "total"));
  const esperado = jsJSON(`(await ${PLUGIN}.leerCatalogo()).normas.find(n=>n.carpeta==="Ley 1996 de 2019").notas`);
  const ok = sugerencias >= 19 && /1996/.test(filtradas) && instalada && notas === esperado;
  registrar("3. Descarga por la interfaz (Ley 1996)", ok,
    `${sugerencias} normas en el selector; filtro «1996» → ${filtradas.split("\n")[0]}; ${notas}/${esperado} notas; aviso: ${avisos.split("\n")[0]}`,
    [c1, c2, c3]);
});

if (corre("descarga-todas")) await escenario("4. Descarga de todas las normas", async () => {
  ob("dev:errors", "clear"); // solo cuentan los errores de este escenario
  const cat = jsJSON(`(await ${PLUGIN}.leerCatalogo()).normas.map(n=>({c:n.carpeta,notas:n.notas,mb:+(n.bytes/1048576).toFixed(1)}))`);
  const filas = [];
  let todoOk = true;
  for (const n of cat) {
    const r = await tarea(`instalar-${n.c}`,
      `(async()=>{const n=(await ${PLUGIN}.leerCatalogo()).normas.find(x=>x.carpeta===${JSON.stringify(n.c)});return await ${PLUGIN}.instalar(n)})()`);
    const ok = r.ok && r.v === true;
    const seg = r.seg.toFixed(1);
    const notas = await contarNotas(`Normas/${n.c}`, n.notas);
    const bien = ok && notas === n.notas;
    todoOk &&= bien;
    filas.push(`${bien ? "✓" : "✗"} ${n.c}: ${notas}/${n.notas} notas, ${n.mb} MB, ${seg} s`);
    console.log("   ", filas.at(-1));
  }
  const memoria = js("(performance.memory.usedJSHeapSize/1048576).toFixed(0)+' MB'");
  const errores = ob("dev:errors");
  registrar("4. Descarga de todas las normas", todoOk && /No errors/i.test(errores),
    `${filas.join("; ")}. Memoria JS: ${memoria}. Errores: ${errores.slice(0, 100)}`, [captura("04-explorador")]);
});

if (corre("enlaces")) await escenario("5. Resolución de los enlaces de tus notas", async () => {
  await dormir(3000); // que termine de indexar
  // Solo enlaces que salen de tus notas (no de la biblioteca), contados por aparición.
  const r = jsJSON(`(()=>{const res={total:0,porNorma:{},ej:[]};for(const [f,o] of Object.entries(app.metadataCache.unresolvedLinks)){if(f.startsWith("Normas/")||f.startsWith("Biblioteca")||f.startsWith("Pruebas/"))continue;for(const [l,n] of Object.entries(o)){if(!/^art\\. /.test(l))continue;res.total+=n;const k=l.replace(/^art\\. \\S+ /,"");res.porNorma[k]=(res.porNorma[k]||0)+n;if(res.ej.length<15)res.ej.push(l)}}return res})()`);
  writeFileSync(join(E2E, "enlaces-sin-resolver.json"), JSON.stringify(r, null, 1));
  const lb = existsSync(join(E2E, "linea-base.json")) ? JSON.parse(readFileSync(join(E2E, "linea-base.json"))) : null;
  const top = Object.entries(r.porNorma).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([k, v]) => `${k} (${v})`).join(", ");
  const back = ob("backlinks", "file=art. 621 CCo");
  const okBack = /Cheque|Clase|Títulos/i.test(back) || !existsSync(join(VAULT, "Derecho"));
  registrar("5. Resolución de los enlaces de tus notas", okBack && (!lb || r.total < lb.articulos * 0.2),
    `enlaces a artículos sin resolver en tus notas: ${lb ? lb.articulos + " → " : ""}${r.total}. Restantes por norma: ${top}. Backlinks de art. 621 CCo: ${back.split("\n").filter(Boolean).length} (${back.split("\n")[0]})`);
});

if (corre("vistas")) await escenario("6. Visualización de notas", async () => {
  const casos = [
    ["06a-cgp22-lectura", "art. 22 CGP", true],
    ["06b-cgp22-codigo", "art. 22 CGP", false],
    ["06c-cpol1", "art. 1 CPol", true],
    ["06d-transitorio", "art. transitorio 5 (AL 1 de 2017) CPol", true],
    ["06e-et-tabla", "art. 241 ET", true],
    ["06f-indice", "CGP - Libro Primero - Sección Primera - Título I - Capítulo I", true],
    ["06g-raiz", "CGP", true],
    ["06h-cc33-tachados", "art. 33 CC", true],
    ["06i-clase-cheque", "Clase 08 - Cheque", true],
  ];
  const caps = [];
  const fallos = [];
  for (const [nombre, nota, lectura] of casos) {
    const ruta = rutaDe(nota);
    if (!ruta) { fallos.push(`no existe «${nota}»`); continue; }
    await abrir(ruta, { lectura });
    caps.push(captura(nombre));
  }
  // Señales en el DOM de la vista de lectura del art. 22 CGP.
  await abrir(rutaDe("art. 22 CGP"), { lectura: true });
  const tachados = cuenta(".markdown-preview-view del");
  const callouts = cuenta(".markdown-preview-view .callout");
  const rotos = cuenta(".markdown-preview-view a.internal-link.is-unresolved");
  const props = cuenta(".metadata-property");
  // Lo derogado aparece tachado (DAFP) o suprimido como «(texto no vigente)» (Senado).
  const noVigente = js(`String(document.querySelector(".workspace-leaf.mod-active .markdown-preview-view")?.textContent.includes("texto no vigente"))`) === "true";
  const ok = !fallos.length && (tachados > 0 || noVigente) && callouts >= 2 && props > 5;
  registrar("6. Visualización de notas", ok,
    `art. 22 CGP: ${tachados} tachados, «texto no vigente»: ${noVigente}, ${callouts} callouts, ${props} propiedades, ${rotos} enlaces sin resolver. ${fallos.join("; ")}`, caps);
});

if (corre("vista-previa")) await escenario("7. Vista previa al pasar el ratón", async () => {
  await abrir(rutaDe("art. 22 CGP"), { lectura: true });
  let r = null;
  let visibles = "";
  for (let k = 0; k < 8 && !r; k++) {
    await alFinal();
    r = jsJSON(`(()=>{const a=[...document.querySelectorAll(${JSON.stringify(SEL_ENLACES)})].find(x=>x.textContent==="art. 23 CGP");if(!a)return null;const b=a.getBoundingClientRect();return {x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)}})()`);
    if (!r) visibles = js(`[...document.querySelectorAll(${JSON.stringify(SEL_ENLACES)})].map(a=>a.textContent).join(", ")`);
  }
  if (!r) return registrar("7. Vista previa al pasar el ratón", false, `no se encontró el enlace «art. 23 CGP» del pie (visibles: ${visibles})`);
  ob("dev:cdp", "method=Input.dispatchMouseEvent", `params={"type":"mouseMoved","x":${r.x - 40},"y":${r.y}}`);
  ob("dev:cdp", "method=Input.dispatchMouseEvent", `params={"type":"mouseMoved","x":${r.x},"y":${r.y}}`);
  let popover = 0;
  for (let k = 0; k < 12 && !popover; k++) {
    await dormir(500);
    popover = cuenta(".hover-popover");
  }
  const texto = popover ? await esperarDom(".hover-popover h2", 8000) : "";
  const cap = captura("07-vista-previa");
  ob("dev:cdp", "method=Input.dispatchMouseEvent", 'params={"type":"mouseMoved","x":5,"y":450}');
  registrar("7. Vista previa al pasar el ratón", popover > 0 && /Artículo 23/.test(texto),
    `popover del pie «art. 23 CGP»: ${popover ? texto : "no apareció"}`, [cap]);
});

if (corre("navegacion")) await escenario("8. Navegación", async () => {
  await abrir(rutaDe("art. 22 CGP"), { lectura: true });
  await alFinal();
  const pasos = [];
  const clic = (sel, patron) => js(`(()=>{const a=[...document.querySelectorAll(${JSON.stringify(sel)})].filter(x=>${patron}.test(x.textContent));const e=a.at(-1);if(!e)return "";e.click();return e.textContent})()`);
  pasos.push(["siguiente", clic(SEL_ENLACES, "/^art\\. 23 CGP$/")]);
  await dormir(1200);
  const tras1 = js("app.workspace.getActiveFile().basename");
  await alFinal();
  pasos.push(["↑ capítulo", clic(SEL_ENLACES, "/^Capítulo I$/")]);
  await dormir(1200);
  const tras2 = js("app.workspace.getActiveFile().basename");
  const cap = captura("08-indice-desde-migas");
  const ok = tras1 === "art. 23 CGP" && /Capítulo I$/.test(tras2);
  registrar("8. Navegación", ok, `siguiente → ${tras1}; miga → ${tras2}`, [cap]);
});

if (corre("propiedades")) await escenario("9. Propiedades y Dataview", async () => {
  const vig = ob("property:read", "name=vigencia", "file=art. 22 CGP");
  const epi = ob("property:read", "name=epigrafe", "file=art. 1494 CC");
  // Dataview indexa las notas nuevas por su cuenta y tarda minutos con miles de notas.
  for (let k = 0; k < 120; k++) {
    const r = js(`"dv="+(app.plugins.plugins.dataview.index.pages.size>=app.vault.getMarkdownFiles().length-5)`);
    if (r.includes("dv=true")) break;
    await dormir(5000);
  }
  const ruta = "Pruebas/Derogados CGP.md";
  ob("create", `path=${ruta}`, "overwrite",
    'content=```dataview\\nTABLE epigrafe, vigencia FROM #normas/cgp\\nWHERE tipo = "articulo" AND vigencia = "derogado"\\nSORT file.name ASC\\n```');
  await abrir(ruta, { lectura: true });
  let filas = 0;
  for (let k = 0; k < 20 && filas === 0; k++) {
    await dormir(1000);
    filas = cuenta(".dataview.table-view-table tbody tr");
  }
  const cap = captura("09-dataview");
  registrar("9. Propiedades y Dataview", vig === "parcialmente derogado" && !!epi && filas > 0,
    `vigencia(art. 22 CGP)=${vig}; epígrafe(art. 1494 CC)=${epi}; Dataview: ${filas} artículos derogados del CGP`, [cap]);
});

if (corre("busqueda")) await escenario("10. Búsqueda", async () => {
  // El `search` del CLI no responde a tiempo con >10.000 notas: se prueba la búsqueda de la interfaz.
  const consultas = [
    ["10a-busqueda-texto", '"responsabilidad extracontractual" path:Normas'],
    ["10b-busqueda-propiedad", '[epigrafe:"Competencia de los jueces de familia"]'],
  ];
  const detalle = [];
  const caps = [];
  let ok = true;
  for (const [nombre, q] of consultas) {
    ob("search:open", `query=${q}`);
    let n = 0;
    for (let k = 0; k < 30 && n === 0; k++) {
      await dormir(1000);
      n = cuenta(".search-result-file-title");
    }
    const primero = n ? ob("dev:dom", "selector=.search-result-file-title", "text", "all").replace(/\n/g, ", ") : "";
    caps.push(captura(nombre));
    detalle.push(`${q} → ${n} archivos (${primero})`);
    ok &&= n > 0;
  }
  // Dejar la búsqueda limpia: una consulta abierta sobre 12.000 notas consume CPU.
  js(`(()=>{for(const l of app.workspace.getLeavesOfType("search"))l.view.setQuery("");return 1})()`);
  registrar("10. Búsqueda", ok && /art\. 22 CGP/.test(detalle[1]), detalle.join("; "), caps);
});

if (corre("actualizacion")) await escenario("11. Actualización con confirmación", async () => {
  const carpeta = "Normas/Ley 1996 de 2019";
  js(`(async()=>{${PLUGIN}.settings.destino="Normas";await ${PLUGIN}.saveSettings();return 1})()`);
  // Una nota obsoleta en la carpeta de la norma y una nota propia fuera de ella.
  ob("create", `path=${carpeta}/art. 999 Ley 1996 de 2019.md`, "content=obsoleta", "overwrite");
  ob("create", "path=Normas/Mis apuntes.md", "content=mías", "overwrite");
  js(`(()=>{${PLUGIN}.settings.instaladas["Ley 1996 de 2019"].hash="viejo";return 1})()`);
  // Cancelar
  js(`(()=>{${PLUGIN}.actualizarTodas();return 1})()`);
  const titulo = await esperarDom(".modal .modal-title");
  const cap1 = captura("11a-confirmacion");
  js(`(()=>{[...document.querySelectorAll(".modal button")].find(b=>b.textContent==="Cancelar").click();return 1})()`);
  await dormir(1000);
  const sigue = existe(`${carpeta}/art. 999 Ley 1996 de 2019.md`);
  // Aceptar
  js(`(()=>{${PLUGIN}.actualizarTodas();return 1})()`);
  await esperarDom(".modal .modal-title");
  js(`(()=>{[...document.querySelectorAll(".modal button")].find(b=>b.textContent==="Actualizar").click();return 1})()`);
  let listo = false;
  for (let k = 0; k < 40 && !listo; k++) {
    await dormir(500);
    listo = js(`${PLUGIN}.settings.instaladas["Ley 1996 de 2019"].hash!=="viejo"`) === "true";
  }
  let borrada = false;
  for (let k = 0; k < 10 && !borrada; k++) {
    await dormir(1500); // con miles de notas indexándose, el CLI va rezagado
    borrada = !existe(`${carpeta}/art. 999 Ley 1996 de 2019.md`);
  }
  const propia = existe("Normas/Mis apuntes.md");
  const cap2 = captura("11b-actualizada");
  registrar("11. Actualización con confirmación", /Actualizar/.test(titulo) && sigue && listo && borrada && propia,
    `modal «${titulo}»; cancelar conserva la obsoleta: ${sigue}; aceptar actualiza: ${listo}, borra la obsoleta: ${borrada}, respeta «Mis apuntes»: ${propia}`,
    [cap1, cap2]);
});

if (corre("errores")) await escenario("12. Errores y ajustes", async () => {
  // jsJSON: con urlBase vacía (GitHub, el valor por defecto) el CLI imprime «=>» a secas.
  const original = jsJSON(`${PLUGIN}.settings.urlBase`);
  const estado = js(`JSON.stringify(${PLUGIN}.settings)`);
  // Catálogo inaccesible
  js(`(()=>{${PLUGIN}.settings.urlBase="http://127.0.0.1:9/no-existe";return 1})()`);
  js(`(()=>{${PLUGIN}.descargarInteractivo();return 1})()`);
  const aviso = await esperarDom(".notice");
  const cap = captura("12a-sin-conexion");
  const modal = cuenta(".modal");
  // Catálogo de versión futura (servido por el servidor local desde e2e/.tmp-catalogo)
  const dirFuturo = join(AQUI, ".tmp-catalogo");
  mkdirSync(dirFuturo, { recursive: true });
  writeFileSync(join(dirFuturo, "index.json"), JSON.stringify({ version: 99, normas: [] }));
  const futuro = (await tarea("futuro", `(async()=>{${PLUGIN}.settings.urlBase="http://127.0.0.1:8765/e2e/.tmp-catalogo";try{await ${PLUGIN}.leerCatalogo();return "sin error"}catch(e){return e.message}})()`)).v;
  rmSync(dirFuturo, { recursive: true, force: true });
  js(`(()=>{${PLUGIN}.settings.urlBase=${JSON.stringify(original)};return 1})()`);
  // Carpeta destino personalizada (para una norma aún no instalada)
  js(`(()=>{${PLUGIN}.settings.destino="Biblioteca jurídica";delete ${PLUGIN}.settings.instaladas["Ley 1258 de 2008"];return 1})()`);
  const r2 = await tarea("destino", `(async()=>{const n=(await ${PLUGIN}.leerCatalogo()).normas.find(x=>x.carpeta==="Ley 1258 de 2008");return await ${PLUGIN}.instalar(n)})()`);
  const ok2 = r2.ok && r2.v === true;
  const enOtra = await contarNotas("Biblioteca jurídica/Ley 1258 de 2008");
  // Restaurar el estado anterior y quitar la copia de prueba.
  js(`(async()=>{Object.assign(${PLUGIN}.settings, JSON.parse(${JSON.stringify(estado)}));await ${PLUGIN}.saveSettings();const f=app.vault.getAbstractFileByPath("Biblioteca jurídica");if(f)await app.vault.delete(f,true);return 1})()`);
  registrar("12. Errores y ajustes", /No se pudo leer/.test(aviso) && modal === 0 && /versión más nueva/.test(futuro) && ok2 && enOtra > 0,
    `sin conexión → «${aviso.split("\n")[0]}», sin modal; versión futura → «${futuro}»; destino personalizado: ${enOtra} notas`, [cap]);
});

if (corre("ajustes")) await escenario("13. Pestaña de ajustes", async () => {
  // Obsidian 1.15 abre Preferencias en otra ventana: el DOM se lee desde la pestaña
  // del plugin y la captura se toma con grim usando la geometría de hyprctl.
  js(`(()=>{app.setting.open();app.setting.openTabById("normas-colombianas");return 1})()`);
  await dormir(1500);
  const nombres = js(`app.setting.pluginTabs.find(t=>t.id==="normas-colombianas").containerEl.querySelectorAll(".setting-item-name").length+": "+[...app.setting.pluginTabs.find(t=>t.id==="normas-colombianas").containerEl.querySelectorAll(".setting-item-name")].map(e=>e.textContent).join(" · ")`);
  const caps = [];
  const geo = spawnSync(join(AQUI, "ventana.sh"), ["Preferencias"], { encoding: "utf8" }).stdout.trim();
  if (geo) {
    const ruta = join(CAPTURAS, "13-ajustes.png");
    spawnSync("grim", ["-g", geo, ruta]);
    caps.push(ruta);
  }
  js(`(()=>{app.setting.close();return 1})()`);
  registrar("13. Pestaña de ajustes", /Carpeta destino/.test(nombres) && /URL base/.test(nombres), nombres, caps);
});

if (corre("movil")) await escenario("14. Emulación móvil", async () => {
  ob("dev:mobile", "on");
  await dormir(2500);
  await abrir(rutaDe("art. 22 CGP"), { lectura: true });
  const cap = captura("14-movil");
  ob("dev:mobile", "off");
  await dormir(4000);
  let errores = "";
  for (let k = 0; k < 10 && !errores; k++) { errores = ob("dev:errors"); if (!errores) await dormir(1000); }
  registrar("14. Emulación móvil", /No errors/i.test(errores), `errores: ${errores.slice(0, 100)}`, [cap]);
});

// ---------------------------------------------------------------------------
const ok = resultados.filter((r) => r.ok).length;
const md = [
  `# Informe E2E — Normas Colombianas`,
  "",
  `${new Date().toISOString()} · Obsidian ${ob("version")} · ${ok}/${resultados.length} escenarios en verde`,
  "",
  ...resultados.flatMap((r) => [
    `## ${r.ok ? "✓" : "✗"} ${r.escenario}`,
    "",
    r.detalle,
    "",
    ...r.capturas.map((c) => `![${c.split("/").pop()}](capturas/${c.split("/").pop()})`),
    "",
  ]),
].join("\n");
writeFileSync(join(E2E, "informe.md"), md);
console.log(`\n${ok}/${resultados.length} escenarios en verde · informe: ${join(E2E, "informe.md")}`);
process.exit(ok === resultados.length ? 0 : 1);
