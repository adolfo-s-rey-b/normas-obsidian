// Simulación mínima en memoria de la API de Obsidian para `npm test` (no es la API real).
const fs = require("fs"), path = require("path");
const RAIZ = process.env.REPO_LOCAL || path.resolve(__dirname, "../../../..");
class TAbstractFile { constructor(p){ this.path=p; this.name=p.split("/").pop(); this.parent=null; } }
class TFile extends TAbstractFile { constructor(p){ super(p); this.extension=p.split(".").pop(); } }
class TFolder extends TAbstractFile { constructor(p){ super(p); this.children=[]; } }
class Vault {
  constructor(){ this.files=new Map(); this.data=new Map(); }
  getAbstractFileByPath(p){ return this.files.get(p) || null; }
  _add(f){ const dir=f.path.split("/").slice(0,-1).join("/"); this.files.set(f.path,f);
    if(dir){ const padre=this.files.get(dir); if(!padre) throw new Error("sin carpeta padre "+dir); padre.children.push(f); f.parent=padre; } }
  async createFolder(p){ if(this.files.has(p)) throw new Error("existe"); this._add(new TFolder(p)); }
  async create(p,c){ if(this.files.has(p)) throw new Error("existe"); this._add(new TFile(p)); this.data.set(p,c); }
  async process(f,fn){ this.data.set(f.path, fn(this.data.get(f.path))); }
}
class App { constructor(){ this.vault=new Vault(); this.trash=[]; const app=this;
  this.fileManager={ async trashFile(f){ app.trash.push(f.path); app.vault.files.delete(f.path);
    if(f.parent) f.parent.children=f.parent.children.filter(x=>x!==f); } }; } }
class Notice { constructor(m){ if(process.env.VERBOSO) console.log("Notice:",m); } setMessage(m){} hide(){} }
class Plugin { constructor(app){ this.app=app; } async loadData(){ return null; } async saveData(d){ this._data=d; } addCommand(){} addSettingTab(){} }
class Modal { constructor(app){ this.app=app; } open(){} close(){} }
class SuggestModal extends Modal { setPlaceholder(){} }
class PluginSettingTab {} class Setting {}
function normalizePath(p){ return p.replace(/\/+/g,"/").replace(/^\/|\/$/g,""); }
async function requestUrl({url}){
  const m=url.match(/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/[^/]+\/(.*)$/);
  const local=path.join(RAIZ, decodeURIComponent(m[1]).split("/").map(decodeURIComponent).join("/"));
  const text=fs.readFileSync(local,"utf8"); return { text, json: JSON.parse(text) };
}
module.exports={App,TFile,TFolder,Notice,Plugin,Modal,SuggestModal,PluginSettingTab,Setting,normalizePath,requestUrl};
