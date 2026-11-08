import esbuild from "esbuild";
import { builtinModules } from "node:module";

const production = process.argv[2] === "production";

const ctx = await esbuild.context({
  entryPoints: ["main.ts"],
  bundle: true,
  external: ["obsidian", "electron", ...builtinModules],
  format: "cjs",
  target: "es2018",
  logLevel: "info",
  sourcemap: production ? false : "inline",
  treeShaking: true,
  outfile: "main.js",
});

if (production) {
  await ctx.rebuild();
  process.exit(0);
} else {
  await ctx.watch();
}
