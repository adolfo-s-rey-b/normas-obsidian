// Misma base que el escáner de la tienda de Obsidian (eslint-plugin-obsidianmd, config recomendada).
import { defineConfig, globalIgnores } from "eslint/config";
import obsidianmd from "eslint-plugin-obsidianmd";

export default defineConfig([
  globalIgnores(["node_modules", "main.js", "esbuild.config.mjs", "version-bump.mjs", "test"]),
  ...obsidianmd.configs.recommended,
  {
    languageOptions: {
      parserOptions: {
        projectService: { allowDefaultProject: ["eslint.config.*"] },
      },
    },
  },
]);
