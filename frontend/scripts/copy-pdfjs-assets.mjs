import { cp, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = path.resolve(
  fileURLToPath(new URL('..', import.meta.url)),
);
const packageRoot = path.join(frontendRoot, 'node_modules', 'pdfjs-dist');
const publicRoot = path.join(frontendRoot, 'public');
const targetRoot = path.join(publicRoot, 'pdfjs');

if (!targetRoot.startsWith(`${publicRoot}${path.sep}`)) {
  throw new Error(
    'Refusing to prepare PDF.js assets outside the public directory.',
  );
}

await rm(targetRoot, { recursive: true, force: true });
await mkdir(targetRoot, { recursive: true });
await cp(
  path.join(packageRoot, 'build', 'pdf.worker.min.mjs'),
  path.join(targetRoot, 'pdf.worker.min.mjs'),
);

for (const directory of [
  'cmaps',
  'standard_fonts',
  'wasm',
  'iccs',
  'image_decoders',
]) {
  await cp(
    path.join(packageRoot, directory),
    path.join(targetRoot, directory),
    {
      recursive: true,
    },
  );
}

console.log('PDF.js browser assets are ready.');
