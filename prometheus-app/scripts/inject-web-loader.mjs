import { promises as fs } from 'node:fs';
import path from 'node:path';

const DIST_DIR = path.join(process.cwd(), 'dist');

const STYLE_TAG = `<style id="app-shell-loader-style">
#app-shell-loader{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#F5F8F7;z-index:2147483647}
#app-shell-loader .card{width:min(360px,92vw);padding:22px 20px;border-radius:16px;background:rgba(255,255,255,0.86);box-shadow:0 12px 36px rgba(19,32,24,0.10);border:1px solid rgba(19,32,24,0.06)}
#app-shell-loader .brand{font:800 18px/1.2 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;letter-spacing:0.18em;text-align:center;color:#132018}
#app-shell-loader .spinner{width:44px;height:44px;margin:18px auto 10px;border-radius:50%;border:4px solid rgba(19,32,24,0.14);border-top-color:#00D084;animation:appShellSpin .9s linear infinite}
#app-shell-loader .sub{font:500 13px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;text-align:center;color:#2A3C33;opacity:.92}
@keyframes appShellSpin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion: reduce){#app-shell-loader .spinner{animation:none}}
</style>`;

const LOADER_DIV = `<div id="app-shell-loader" role="status" aria-live="polite" aria-label="Loading">
  <div class="card">
    <div class="brand">PROMETHEUS</div>
    <div class="spinner" aria-hidden="true"></div>
    <div class="sub">불러오는 중...</div>
  </div>
</div>`;

async function* walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      yield* walk(fullPath);
      continue;
    }
    yield fullPath;
  }
}

function skipWhitespaceAndComments(html, startIndex) {
  let i = startIndex;
  while (i < html.length) {
    while (i < html.length && /\s/.test(html[i])) i += 1;

    if (html.startsWith('<!--', i)) {
      const end = html.indexOf('-->', i + 4);
      if (end === -1) return i;
      i = end + 3;
      continue;
    }

    break;
  }
  return i;
}

function detectRootHasVisibleContent(html) {
  const rootOpenRegex = /<div[^>]*id=(\"|')root\1[^>]*>/i;
  const match = html.match(rootOpenRegex);
  if (!match || typeof match.index !== 'number') return false;

  const afterRootOpen = match.index + match[0].length;
  const cursor = skipWhitespaceAndComments(html, afterRootOpen);
  return !html.startsWith('</div>', cursor);
}

function stripShellLoader(html) {
  let next = html;

  // Remove style tag (simple, no nesting).
  next = next.replace(
    /<style[^>]*id=(\"|')app-shell-loader-style\1[^>]*>[\s\S]*?<\/style>/i,
    ''
  );

  const loaderOpenIndex = next.indexOf('<div id="app-shell-loader"');
  if (loaderOpenIndex === -1) return next;

  const rootIndex = next.indexOf('<div id="root"', loaderOpenIndex);
  if (rootIndex !== -1) {
    return next.slice(0, loaderOpenIndex) + next.slice(rootIndex);
  }

  // Fallback: remove loader by scanning nested <div> depth.
  let depth = 0;
  let i = loaderOpenIndex;
  while (i < next.length) {
    const open = next.indexOf('<div', i);
    const close = next.indexOf('</div>', i);

    if (open !== -1 && open < close) {
      depth += 1;
      i = open + 4;
      continue;
    }

    if (close !== -1) {
      depth -= 1;
      i = close + 6;
      if (depth <= 0) {
        return next.slice(0, loaderOpenIndex) + next.slice(i);
      }
      continue;
    }

    break;
  }

  return next;
}

function injectShellLoader(html) {
  const rootHasContent = detectRootHasVisibleContent(html);
  const hasLoader = html.includes('app-shell-loader-style') || html.includes('app-shell-loader');

  // Side-effect guard: if Expo static rendering already produced real HTML in #root,
  // do NOT overlay a loader that would hide it. If a loader exists (from a previous run),
  // strip it back out.
  if (rootHasContent) {
    if (!hasLoader) return { updated: false, html };
    const stripped = stripShellLoader(html);
    return { updated: stripped !== html, html: stripped };
  }

  if (hasLoader) {
    return { updated: false, html };
  }

  let next = html;

  if (next.includes('</head>')) {
    next = next.replace('</head>', `${STYLE_TAG}</head>`);
  } else if (next.includes('<head>')) {
    next = next.replace('<head>', `<head>${STYLE_TAG}`);
  } else {
    next = `${STYLE_TAG}${next}`;
  }

  const rootTagRegex = /<div[^>]*id=(\"|')root\1[^>]*>/i;
  if (rootTagRegex.test(next)) {
    next = next.replace(rootTagRegex, `${LOADER_DIV}$&`);
    return { updated: true, html: next };
  }

  const bodyTagRegex = /<body[^>]*>/i;
  const match = next.match(bodyTagRegex);
  if (match) {
    next = next.replace(bodyTagRegex, `${match[0]}${LOADER_DIV}`);
    return { updated: true, html: next };
  }

  // Fallback: prepend to document.
  return { updated: true, html: `${LOADER_DIV}${next}` };
}

async function main() {
  const distExists = await fs
    .stat(DIST_DIR)
    .then(stat => stat.isDirectory())
    .catch(() => false);

  if (!distExists) {
    console.error(`[inject-web-loader] dist directory not found at: ${DIST_DIR}`);
    process.exitCode = 1;
    return;
  }

  let updatedCount = 0;
  let htmlCount = 0;

  for await (const filePath of walk(DIST_DIR)) {
    if (!filePath.toLowerCase().endsWith('.html')) continue;
    htmlCount += 1;

    const raw = await fs.readFile(filePath, 'utf8');
    const { updated, html } = injectShellLoader(raw);
    if (!updated) continue;

    await fs.writeFile(filePath, html, 'utf8');
    updatedCount += 1;
  }

  console.info(`[inject-web-loader] scanned=${htmlCount} updated=${updatedCount}`);
}

main().catch(err => {
  console.error('[inject-web-loader] failed', err);
  process.exitCode = 1;
});
