import { cp, mkdir, rm } from "node:fs/promises";

const outputDirectory = new URL("../dist/", import.meta.url);
await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });

for (const file of ["index.html", "admin.html", "config.js"]) {
  await cp(new URL(`../${file}`, import.meta.url), new URL(file, outputDirectory));
}

console.log("Static site built in dist/.");
