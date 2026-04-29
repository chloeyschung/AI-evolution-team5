import { mkdir, cp, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const distRoot = path.resolve(projectRoot, 'dist');

async function ensureDir(dirPath) {
  await mkdir(dirPath, { recursive: true });
}

async function copyTextFile(sourcePath, destPath, replacements = []) {
  let content = await readFile(sourcePath, 'utf-8');
  for (const [from, to] of replacements) {
    content = content.replace(from, to);
  }
  await ensureDir(path.dirname(destPath));
  await writeFile(destPath, content, 'utf-8');
}

async function buildManifest() {
  const sourceManifestPath = path.resolve(projectRoot, 'manifest.json');
  const manifest = JSON.parse(await readFile(sourceManifestPath, 'utf-8'));

  manifest.background = {
    service_worker: 'background/service-worker.js',
    type: 'module',
  };
  manifest.content_scripts = [
    {
      matches: ['<all_urls>'],
      js: ['content/content-script.js'],
      css: ['content/content-script.css'],
      run_at: 'document_end',
    },
  ];
  manifest.action = {
    ...manifest.action,
    default_popup: 'popup/popup.html',
  };
  manifest.web_accessible_resources = [
    {
      resources: ['login/login.html'],
      matches: ['<all_urls>'],
    },
  ];

  await writeFile(
    path.resolve(distRoot, 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
    'utf-8',
  );
}

async function main() {
  await ensureDir(distRoot);
  await buildManifest();

  await copyTextFile(
    path.resolve(projectRoot, 'src/popup/popup.html'),
    path.resolve(distRoot, 'popup/popup.html'),
    [['popup.ts', 'popup.js']],
  );
  await copyTextFile(
    path.resolve(projectRoot, 'src/login/login.html'),
    path.resolve(distRoot, 'login/login.html'),
    [['login.ts', 'login.js']],
  );

  await ensureDir(path.resolve(distRoot, 'popup'));
  await ensureDir(path.resolve(distRoot, 'login'));
  await ensureDir(path.resolve(distRoot, 'content'));

  await cp(
    path.resolve(projectRoot, 'src/popup/popup.css'),
    path.resolve(distRoot, 'popup/popup.css'),
    { force: true },
  );
  await cp(
    path.resolve(projectRoot, 'src/login/login.css'),
    path.resolve(distRoot, 'login/login.css'),
    { force: true },
  );
  await cp(
    path.resolve(projectRoot, 'src/content/content-script.css'),
    path.resolve(distRoot, 'content/content-script.css'),
    { force: true },
  );
  await cp(
    path.resolve(projectRoot, 'icons'),
    path.resolve(distRoot, 'icons'),
    { recursive: true, force: true },
  );
}

await main();
