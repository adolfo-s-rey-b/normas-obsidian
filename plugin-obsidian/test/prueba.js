// Prueba de humo: instala una norma del catálogo local en un vault simulado.
const assert=require("assert"); const fs=require("fs"); const path=require("path");
const {App}=require("obsidian"); const Plugin=require("./.main-test.js").default;
(async()=>{
  const app=new App(); const p=new Plugin(app); await p.loadSettings();
  const cat=await p.leerCatalogo();
  const ley=cat.normas.find(n=>n.carpeta==="Ley 1996 de 2019");
  assert.ok(await p.instalar(ley));
  const notas=[...app.vault.files.values()].filter(f=>f.extension==="md");
  assert.strictEqual(notas.length, ley.notas, "nº de notas");
  assert.ok(app.vault.data.get("Normas/Ley 1996 de 2019/Ley 1996 de 2019.md").startsWith("---"));
  assert.strictEqual(p.settings.instaladas[ley.carpeta].hash, ley.hash);
  // nota obsoleta + reinstalación
  await app.vault.create("Normas/Ley 1996 de 2019/art. 999 Ley 1996 de 2019.md","vieja");
  assert.ok(await p.instalar(ley));
  assert.deepStrictEqual(app.trash, ["Normas/Ley 1996 de 2019/art. 999 Ley 1996 de 2019.md"]);
  // las notas de otras carpetas no se tocan
  await app.vault.createFolder("Normas/Mías"); await app.vault.create("Normas/Mías/nota.md","x");
  assert.ok(await p.instalar(ley)); assert.ok(app.vault.files.has("Normas/Mías/nota.md"));
  console.log("OK: plugin instala", notas.length, "notas, borra obsoletas y respeta otras carpetas");
})().catch(e=>{ console.error(e); process.exit(1); });
