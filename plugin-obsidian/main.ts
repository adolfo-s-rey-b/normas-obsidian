import {
  App,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  SuggestModal,
  TFile,
  TFolder,
  normalizePath,
  requestUrl,
} from "obsidian";

// ---------------------------------------------------------------------------
// Tipos del catálogo (generado por `normas-cli catalogo` en catalogo/)
// ---------------------------------------------------------------------------

interface EntradaCatalogo {
  carpeta: string; // carpeta de la norma dentro de la biblioteca ("CGP")
  sigla: string | null;
  norma: string; // "Ley 1564 de 2012"
  nombre: string; // "Código General del Proceso"
  epigrafe?: string | null;
  estado: string; // "vigente" | "derogada"
  articulos: number;
  actualizacion_fuente?: string | null;
  fecha_extraccion: string;
  hash: string;
  notas: number;
  bytes: number;
  paquete: string; // "CGP.json"
}

interface Catalogo {
  version: number;
  generado: string;
  normas: EntradaCatalogo[];
}

interface Paquete {
  version: number;
  carpeta: string;
  hash: string;
  archivos: Record<string, string>; // "CGP/…/art. 1 CGP.md" → contenido
}

interface Instalada {
  hash: string;
  fecha_extraccion: string;
  instalada: string; // fecha ISO de la descarga
}

interface NormasSettings {
  repo: string; // "usuario/repositorio"
  rama: string;
  carpetaCatalogo: string; // carpeta del catálogo dentro del repo
  destino: string; // carpeta destino dentro del vault
  instaladas: Record<string, Instalada>; // por carpeta de norma
}

const DEFAULTS: NormasSettings = {
  repo: "adolfo-s-rey-b/normas-obsidian",
  rama: "main",
  carpetaCatalogo: "catalogo",
  destino: "Normas",
  instaladas: {},
};

const CATALOGO_COMPATIBLE = 1;

function formatoTamano(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------

export default class NormasPlugin extends Plugin {
  settings: NormasSettings = { ...DEFAULTS, instaladas: {} };

  async onload() {
    await this.loadSettings();

    this.addCommand({
      id: "descargar-norma",
      name: "Descargar norma de la biblioteca",
      callback: () => this.descargarInteractivo(),
    });

    this.addCommand({
      id: "actualizar-normas",
      name: "Actualizar normas descargadas",
      callback: () => this.actualizarTodas(),
    });

    this.addSettingTab(new NormasSettingTab(this.app, this));
  }

  async loadSettings() {
    const datos = (await this.loadData()) ?? {};
    // Compatibilidad con la versión 0.1 (ajustes «branch» y «bibliotecaDir»).
    if (datos.branch && !datos.rama) datos.rama = datos.branch;
    delete datos.branch;
    delete datos.bibliotecaDir;
    this.settings = Object.assign({}, DEFAULTS, { instaladas: {} }, datos);
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  private urlCruda(ruta: string): string {
    const { repo, rama, carpetaCatalogo } = this.settings;
    const partes = [carpetaCatalogo.replace(/^\/+|\/+$/g, ""), ruta]
      .join("/")
      .split("/")
      .map(encodeURIComponent)
      .join("/");
    return `https://raw.githubusercontent.com/${repo}/${rama}/${partes}`;
  }

  async leerCatalogo(): Promise<Catalogo> {
    const res = await requestUrl({ url: this.urlCruda("index.json") });
    const cat = res.json as Catalogo;
    if (!cat || !Array.isArray(cat.normas)) {
      throw new Error("El catálogo no tiene el formato esperado.");
    }
    if (cat.version > CATALOGO_COMPATIBLE) {
      throw new Error("El catálogo es de una versión más nueva: actualiza el plugin.");
    }
    return cat;
  }

  async descargarInteractivo() {
    let cat: Catalogo;
    try {
      cat = await this.leerCatalogo();
    } catch (e) {
      console.error("[normas-colombianas]", e);
      new Notice(
        `No se pudo leer el catálogo de ${this.settings.repo}. Revisa la conexión y los ajustes del plugin.`
      );
      return;
    }
    if (!cat.normas.length) {
      new Notice("El catálogo no tiene normas.");
      return;
    }
    new NormaSuggestModal(this.app, this, cat.normas, (n) => {
      void this.instalarConConfirmacion(n);
    }).open();
  }

  /** Ruta de la norma dentro del vault. */
  carpetaVault(n: EntradaCatalogo): string {
    return normalizePath(`${this.settings.destino}/${n.carpeta}`);
  }

  private notasExistentes(carpeta: string): TFile[] {
    const raiz = this.app.vault.getAbstractFileByPath(carpeta);
    if (!(raiz instanceof TFolder)) return [];
    const out: TFile[] = [];
    const recorrer = (f: TFolder) => {
      for (const h of f.children) {
        if (h instanceof TFolder) recorrer(h);
        else if (h instanceof TFile && h.extension === "md") out.push(h);
      }
    };
    recorrer(raiz);
    return out;
  }

  async instalarConConfirmacion(n: EntradaCatalogo) {
    const existentes = this.notasExistentes(this.carpetaVault(n));
    if (existentes.length) {
      const ok = await confirmar(
        this.app,
        `Actualizar «${n.nombre}»`,
        `Ya hay ${existentes.length} notas en «${this.carpetaVault(n)}». Se reemplazarán con la versión de la biblioteca; ` +
          "las notas de esa carpeta que ya no existan en la biblioteca se enviarán a la papelera. " +
          "Los cambios que hayas hecho en esas notas se perderán.",
        "Reemplazar"
      );
      if (!ok) return;
    }
    await this.instalar(n);
  }

  /** Descarga el paquete de una norma y lo escribe en el vault. */
  async instalar(n: EntradaCatalogo): Promise<boolean> {
    const aviso = new Notice(`Descargando «${n.nombre}» (${formatoTamano(n.bytes)})…`, 0);
    let paquete: Paquete;
    try {
      const res = await requestUrl({ url: this.urlCruda(n.paquete) });
      paquete = res.json as Paquete;
    } catch (e) {
      aviso.hide();
      console.error("[normas-colombianas]", e);
      new Notice(`No se pudo descargar «${n.nombre}».`);
      return false;
    }

    const rutas = Object.keys(paquete.archivos ?? {});
    const destino = normalizePath(this.settings.destino);
    const nuevas = new Set(rutas.map((r) => normalizePath(`${destino}/${r}`)));
    let errores = 0;
    let hechas = 0;
    for (const ruta of rutas) {
      const destinoVault = normalizePath(`${destino}/${ruta}`);
      try {
        await this.escribir(destinoVault, paquete.archivos[ruta]);
      } catch (e) {
        errores++;
        console.error("[normas-colombianas] Error escribiendo", destinoVault, e);
      }
      hechas++;
      if (hechas % 200 === 0) {
        aviso.setMessage(`Escribiendo «${n.nombre}» (${hechas}/${rutas.length})…`);
      }
    }

    // Notas obsoletas: estaban en la carpeta de la norma y ya no existen.
    let borradas = 0;
    for (const f of this.notasExistentes(this.carpetaVault(n))) {
      if (!nuevas.has(f.path)) {
        try {
          await this.app.fileManager.trashFile(f);
          borradas++;
        } catch (e) {
          errores++;
          console.error("[normas-colombianas] Error borrando", f.path, e);
        }
      }
    }
    await this.borrarCarpetasVacias(this.carpetaVault(n));

    aviso.hide();
    if (errores === 0) {
      this.settings.instaladas[n.carpeta] = {
        hash: paquete.hash,
        fecha_extraccion: n.fecha_extraccion,
        instalada: new Date().toISOString(),
      };
      await this.saveSettings();
      new Notice(
        `✓ «${n.nombre}»: ${rutas.length} notas en ${this.carpetaVault(n)}` +
          (borradas ? ` (${borradas} obsoletas a la papelera)` : "")
      );
      return true;
    }
    new Notice(`«${n.nombre}» quedó incompleta: ${errores} errores. Revisa la consola y vuelve a intentarlo.`);
    return false;
  }

  async actualizarTodas() {
    const instaladas = Object.keys(this.settings.instaladas);
    if (!instaladas.length) {
      new Notice("Aún no has descargado normas con este plugin.");
      return;
    }
    let cat: Catalogo;
    try {
      cat = await this.leerCatalogo();
    } catch (e) {
      console.error("[normas-colombianas]", e);
      new Notice("No se pudo leer el catálogo.");
      return;
    }
    const pendientes = cat.normas.filter(
      (n) => this.settings.instaladas[n.carpeta] && this.settings.instaladas[n.carpeta].hash !== n.hash
    );
    if (!pendientes.length) {
      new Notice("Tus normas ya están al día.");
      return;
    }
    const ok = await confirmar(
      this.app,
      "Actualizar normas",
      `Hay versiones nuevas de: ${pendientes.map((n) => n.sigla ?? n.nombre).join(", ")}. ` +
        "Las notas de esas carpetas se reemplazarán y las obsoletas irán a la papelera; los cambios propios se perderán.",
      "Actualizar"
    );
    if (!ok) return;
    let bien = 0;
    for (const n of pendientes) if (await this.instalar(n)) bien++;
    new Notice(`Actualizadas ${bien} de ${pendientes.length} normas.`);
  }

  private async asegurarCarpeta(ruta: string) {
    if (!ruta) return;
    const partes = ruta.split("/");
    let actual = "";
    for (const p of partes) {
      actual = actual ? `${actual}/${p}` : p;
      const f = this.app.vault.getAbstractFileByPath(actual);
      if (!f) {
        try {
          await this.app.vault.createFolder(actual);
        } catch (e) {
          // Otra escritura pudo crearla entre la consulta y la creación.
          if (!(this.app.vault.getAbstractFileByPath(actual) instanceof TFolder)) throw e;
        }
      } else if (!(f instanceof TFolder)) {
        throw new Error(`«${actual}» existe y no es una carpeta`);
      }
    }
  }

  /** Crea o reemplaza un archivo del vault, creando las carpetas que falten. */
  private async escribir(ruta: string, contenido: string) {
    await this.asegurarCarpeta(ruta.split("/").slice(0, -1).join("/"));
    const existente = this.app.vault.getAbstractFileByPath(ruta);
    if (existente instanceof TFile) {
      await this.app.vault.process(existente, () => contenido);
    } else if (!existente) {
      await this.app.vault.create(ruta, contenido);
    } else {
      throw new Error(`«${ruta}» existe y no es un archivo`);
    }
  }

  private async borrarCarpetasVacias(ruta: string) {
    const f = this.app.vault.getAbstractFileByPath(ruta);
    if (!(f instanceof TFolder)) return;
    for (const h of [...f.children]) {
      if (h instanceof TFolder) await this.borrarCarpetasVacias(h.path);
    }
    if (f.children.length === 0 && f.path !== normalizePath(this.settings.destino)) {
      await this.app.fileManager.trashFile(f);
    }
  }
}

// ---------------------------------------------------------------------------
// Interfaz
// ---------------------------------------------------------------------------

class NormaSuggestModal extends SuggestModal<EntradaCatalogo> {
  constructor(
    app: App,
    private plugin: NormasPlugin,
    private normas: EntradaCatalogo[],
    private onElegir: (n: EntradaCatalogo) => void
  ) {
    super(app);
    this.setPlaceholder("Busca una norma por sigla, nombre o número…");
  }

  getSuggestions(consulta: string): EntradaCatalogo[] {
    const q = consulta
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
    return this.normas.filter((n) =>
      [n.sigla ?? "", n.nombre, n.norma]
        .join(" ")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .includes(q)
    );
  }

  renderSuggestion(n: EntradaCatalogo, el: HTMLElement) {
    const titulo = el.createDiv();
    titulo.createSpan({ text: n.sigla ? `${n.sigla} · ` : "", cls: "normas-sigla" });
    titulo.createSpan({ text: n.nombre });
    const inst = this.plugin.settings.instaladas[n.carpeta];
    let estado = "";
    if (inst) estado = inst.hash === n.hash ? " · descargada" : " · hay actualización";
    if (n.estado === "derogada") estado += " · derogada";
    el.createEl("small", {
      text: `${n.norma} · ${n.articulos} artículos · ${formatoTamano(n.bytes)}${estado}`,
      cls: "normas-detalle",
    });
  }

  onChooseSuggestion(n: EntradaCatalogo) {
    this.onElegir(n);
  }
}

class ConfirmarModal extends Modal {
  private resuelto = false;
  constructor(
    app: App,
    private titulo: string,
    private mensaje: string,
    private boton: string,
    private resolver: (ok: boolean) => void
  ) {
    super(app);
  }

  onOpen() {
    this.titleEl.setText(this.titulo);
    this.contentEl.createEl("p", { text: this.mensaje });
    new Setting(this.contentEl)
      .addButton((b) =>
        b.setButtonText("Cancelar").onClick(() => {
          this.cerrar(false);
        })
      )
      .addButton((b) =>
        b
          .setButtonText(this.boton)
          .setWarning()
          .onClick(() => {
            this.cerrar(true);
          })
      );
  }

  private cerrar(ok: boolean) {
    this.resuelto = true;
    this.resolver(ok);
    this.close();
  }

  onClose() {
    if (!this.resuelto) this.resolver(false);
    this.contentEl.empty();
  }
}

function confirmar(app: App, titulo: string, mensaje: string, boton: string): Promise<boolean> {
  return new Promise((resolve) => new ConfirmarModal(app, titulo, mensaje, boton, resolve).open());
}

class NormasSettingTab extends PluginSettingTab {
  constructor(app: App, private plugin: NormasPlugin) {
    super(app, plugin);
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName("Carpeta destino")
      .setDesc("Carpeta del vault donde se guardan las normas descargadas.")
      .addText((t) =>
        t.setValue(this.plugin.settings.destino).onChange(async (v) => {
          this.plugin.settings.destino = normalizePath(v.trim() || "Normas");
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl).setName("Fuente de la biblioteca").setHeading();

    new Setting(containerEl)
      .setName("Repositorio")
      .setDesc("usuario/repositorio en GitHub que publica el catálogo de normas.")
      .addText((t) =>
        t.setValue(this.plugin.settings.repo).onChange(async (v) => {
          this.plugin.settings.repo = v.trim() || DEFAULTS.repo;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl).setName("Rama").addText((t) =>
      t.setValue(this.plugin.settings.rama).onChange(async (v) => {
        this.plugin.settings.rama = v.trim() || DEFAULTS.rama;
        await this.plugin.saveSettings();
      })
    );

    new Setting(containerEl)
      .setName("Carpeta del catálogo")
      .setDesc("Ruta del catálogo dentro del repositorio.")
      .addText((t) =>
        t.setValue(this.plugin.settings.carpetaCatalogo).onChange(async (v) => {
          this.plugin.settings.carpetaCatalogo = v.trim() || DEFAULTS.carpetaCatalogo;
          await this.plugin.saveSettings();
        })
      );
  }
}
