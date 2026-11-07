// Sincroniza la versión de package.json con ../manifest.json y ../versions.json
// (se ejecuta con `npm version <nueva>` desde plugin-obsidian/).
import { readFileSync, writeFileSync } from "fs";

const version = process.env.npm_package_version;
const manifest = JSON.parse(readFileSync("../manifest.json", "utf8"));
const { minAppVersion } = manifest;
manifest.version = version;
writeFileSync("../manifest.json", JSON.stringify(manifest, null, 2) + "\n");

const versions = JSON.parse(readFileSync("../versions.json", "utf8"));
versions[version] = minAppVersion;
writeFileSync("../versions.json", JSON.stringify(versions, null, 2) + "\n");
