import {
  App,
  FuzzySuggestModal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  normalizePath,
  requestUrl,
} from "obsidian";

interface NormasSettings {
  repo: string; // "usuario/repositorio"
  branch: string; // "main"
  bibliotecaDir: string; // carpeta dentro del repo
  destino: string; // carpeta destino dentro del vault
}

const DEFAULTS: NormasSettings = {
  repo: "argonautarey/normas-obsidian",
  branch: "main",
  bibliotecaDir: "biblioteca",
  destino: "Normas",
};

/** Un archivo del árbol de git (path completo + sha). */
interface TreeFile {
  path: string;
  type: string;
}

export default class NormasPlugin extends Plugin {
  settings: NormasSettings = DEFAULTS;

  async onload() {
    await this.loadSettings();

    this.addCommand({
      id: "descargar-norma",
      name: "Descargar norma de la biblioteca",
      callback: () => this.descargarNormaInteractivo(),
    });

    this.addSettingTab(new NormasSettingTab(this.app, this));
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  /** Lista los archivos del repo (árbol recursivo) bajo la carpeta biblioteca. */
  async listarArbol(): Promise<TreeFile[]> {
    const { repo, branch, bibliotecaDir } = this.settings;
    const url = `https://api.github.com/repos/${repo}/git/trees/${branch}?recursive=1`;
    const res = await requestUrl({ url, headers: { Accept: "application/vnd.github+json" } });
    const tree: TreeFile[] = (res.json.tree ?? []) as TreeFile[];
    const prefijo = bibliotecaDir.replace(/\/$/, "") + "/";
    return tree.filter((f) => f.path.startsWith(prefijo));
  }

  /** Nombres de las normas disponibles (carpetas de primer nivel en biblioteca/). */
  normasDisponibles(arbol: TreeFile[]): string[] {
    const prefijo = this.settings.bibliotecaDir.replace(/\/$/, "") + "/";
    const set = new Set<string>();
    for (const f of arbol) {
      const resto = f.path.slice(prefijo.length);
      const top = resto.split("/")[0];
      if (top) set.add(top);
    }
    return [...set].sort();
  }

  async descargarNormaInteractivo() {
    let arbol: TreeFile[];
    try {
      arbol = await this.listarArbol();
    } catch (e) {
      new Notice(`No se pudo leer el repositorio (${this.settings.repo}). Revisa los ajustes.`);
      console.error(e);
      return;
    }
    const normas = this.normasDisponibles(arbol);
    if (!normas.length) {
      new Notice("No se encontraron normas en la biblioteca del repositorio.");
      return;
    }
    new NormaSuggestModal(this.app, normas, (norma) =>
      this.descargarNorma(norma, arbol)
    ).open();
  }

  /** Descarga todas las notas .md de una norma y las crea en el vault. */
  async descargarNorma(norma: string, arbol: TreeFile[]) {
    const { repo, branch, bibliotecaDir, destino } = this.settings;
    const prefijo = bibliotecaDir.replace(/\/$/, "") + "/" + norma + "/";
    const archivos = arbol.filter(
      (f) => f.type === "blob" && f.path.startsWith(prefijo) && f.path.endsWith(".md")
    );
    if (!archivos.length) {
      new Notice(`La norma "${norma}" no tiene notas.`);
      return;
    }

    const aviso = new Notice(`Descargando "${norma}" (0/${archivos.length})…`, 0);
    let n = 0;
    for (const f of archivos) {
      const rutaRel = f.path.slice((bibliotecaDir.replace(/\/$/, "") + "/").length);
      const destinoVault = normalizePath(`${destino}/${rutaRel}`);
      const rawUrl =
        `https://raw.githubusercontent.com/${repo}/${branch}/` +
        f.path.split("/").map(encodeURIComponent).join("/");
      try {
        const res = await requestUrl({ url: rawUrl });
        await this.escribirArchivo(destinoVault, res.text);
      } catch (e) {
        console.error("Error descargando", f.path, e);
      }
      n++;
      aviso.setMessage(`Descargando "${norma}" (${n}/${archivos.length})…`);
    }
    aviso.hide();
    new Notice(`✓ "${norma}" descargada (${n} notas) en ${destino}/`);
  }

  /** Crea (o sobrescribe) un archivo en el vault, creando carpetas si faltan. */
  async escribirArchivo(ruta: string, contenido: string) {
    const carpeta = ruta.split("/").slice(0, -1).join("/");
    if (carpeta && !this.app.vault.getAbstractFileByPath(carpeta)) {
      await this.app.vault.createFolder(carpeta).catch(() => {});
    }
    const existente = this.app.vault.getAbstractFileByPath(ruta);
    if (existente && "stat" in existente) {
      await this.app.vault.modify(existente as any, contenido);
    } else {
      await this.app.vault.create(ruta, contenido).catch(async () => {
        const f = this.app.vault.getAbstractFileByPath(ruta);
        if (f) await this.app.vault.modify(f as any, contenido);
      });
    }
  }
}

class NormaSuggestModal extends FuzzySuggestModal<string> {
  constructor(
    app: App,
    private normas: string[],
    private onElegir: (norma: string) => void
  ) {
    super(app);
    this.setPlaceholder("Elige una norma para descargar…");
  }
  getItems(): string[] {
    return this.normas;
  }
  getItemText(item: string): string {
    return item;
  }
  onChooseItem(item: string): void {
    this.onElegir(item);
  }
}

class NormasSettingTab extends PluginSettingTab {
  constructor(app: App, private plugin: NormasPlugin) {
    super(app, plugin);
  }
  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName("Repositorio")
      .setDesc("usuario/repositorio en GitHub con la biblioteca de normas.")
      .addText((t) =>
        t.setValue(this.plugin.settings.repo).onChange(async (v) => {
          this.plugin.settings.repo = v.trim();
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Rama")
      .addText((t) =>
        t.setValue(this.plugin.settings.branch).onChange(async (v) => {
          this.plugin.settings.branch = v.trim() || "main";
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Carpeta de biblioteca")
      .setDesc("Ruta de la biblioteca dentro del repositorio.")
      .addText((t) =>
        t.setValue(this.plugin.settings.bibliotecaDir).onChange(async (v) => {
          this.plugin.settings.bibliotecaDir = v.trim() || "biblioteca";
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Carpeta destino")
      .setDesc("Carpeta dentro de tu vault donde se guardarán las normas.")
      .addText((t) =>
        t.setValue(this.plugin.settings.destino).onChange(async (v) => {
          this.plugin.settings.destino = v.trim() || "Normas";
          await this.plugin.saveSettings();
        })
      );
  }
}
