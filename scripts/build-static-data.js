const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');

const root = path.join(__dirname, '..');
const source = JSON.parse(fs.readFileSync(path.join(root, 'data', 'table-data.json'), 'utf8'));
const meta = JSON.parse(fs.readFileSync(path.join(root, 'data', 'metadata.json'), 'utf8'));
const out = path.join(root, 'data', 'static');
const detailDir = path.join(out, 'details');
fs.mkdirSync(detailDir, { recursive: true });
for (const oldFile of fs.readdirSync(out)) {
  if (/^catalog-[\w-]+\.json$/.test(oldFile)) fs.unlinkSync(path.join(out, oldFile));
}
for (const oldFile of fs.readdirSync(detailDir)) {
  if (/^\d+\.json(?:\.gz)?$/.test(oldFile)) fs.unlinkSync(path.join(detailDir, oldFile));
}

const version = `${meta.lastFetchYear || 'data'}-${crypto.createHash('sha256').update(JSON.stringify(source)).digest('hex').slice(0, 12)}`;
const fields = ['ua', 'uai', 'fa', 'bi', 'bga', 'bt', 'pt', 'ut', 'bo', 'od', 'ia', 'ila', 'ks', 'akr'];
const dictionary = [''];
const ids = new Map([['', 0]]);
function id(value) {
  const text = value == null ? '' : String(value);
  if (!ids.has(text)) { ids.set(text, dictionary.length); dictionary.push(text); }
  return ids.get(text);
}
function compactYearly(yearly) {
  return Object.entries(yearly || {}).map(([year, s]) => [Number(year), s.kn ?? null, s.yl ?? null, s.mp ?? null, s.bs ?? null]);
}
const details = Array.from({ length: 64 }, () => ({}));
const rows = source.map(p => {
  const row = [p.k, p.ui ?? null];
  fields.forEach(field => row.push(id(p[field])));
  row.push(p.bg ?? null, p.os ?? null, p.ik ?? null, p.tyc ? 1 : 0, compactYearly(p.y));
  const detailYearly = {};
  for (const [year, value] of Object.entries(p.y || {})) {
    const copy = { ...value };
    delete copy.kn; delete copy.yl; delete copy.mp; delete copy.bs;
    if (Object.keys(copy).length) detailYearly[year] = copy;
  }
  const detail = {};
  if (p.kl?.length) detail.kl = p.kl;
  if (Object.keys(detailYearly).length) detail.y = detailYearly;
  if (Object.keys(detail).length) details[Number(p.k) % details.length][p.k] = detail;
  return row;
});

function writeJson(file, value) {
  const content = JSON.stringify(value);
  fs.writeFileSync(file, content);
  return { raw: Buffer.byteLength(content), gzip: zlib.gzipSync(content, { level: 9 }).length };
}
function writeGzipJson(file, value) {
  const raw = Buffer.from(JSON.stringify(value));
  const gzip = zlib.gzipSync(raw, { level: 9 });
  fs.writeFileSync(file, gzip);
  return { raw: raw.length, gzip: gzip.length };
}
const catalog = `catalog-${version}.json`;
const catalogSize = writeJson(path.join(out, catalog), { v: version, years: [meta.lastFetchYear, meta.lastFetchYear - 1, meta.lastFetchYear - 2], d: dictionary, r: rows });
let detailSize = { raw: 0, gzip: 0 };
for (let i = 0; i < details.length; i++) {
  const size = writeGzipJson(path.join(detailDir, `${i}.json.gz`), details[i]);
  detailSize.raw += size.raw; detailSize.gzip += size.gzip;
}
fs.writeFileSync(path.join(out, 'config.js'), `window.YOK_ATLAS_DATA=${JSON.stringify({ version, catalog, totalPrograms: source.length, lastFetchYear: meta.lastFetchYear })};\n`);

const siteUrl = 'https://yokatlas.com';
const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>${siteUrl}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
${source.map(p => `<url><loc>${siteUrl}/?programkodu=${encodeURIComponent(p.k)}</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>`).join('\n')}
</urlset>`;
fs.writeFileSync(path.join(root, 'sitemap.xml'), sitemapXml);

console.log(`Static catalogue: ${(catalogSize.raw / 1024 / 1024).toFixed(2)} MB raw, ${(catalogSize.gzip / 1024 / 1024).toFixed(2)} MB gzip`);
console.log(`Details: ${(detailSize.raw / 1024 / 1024).toFixed(2)} MB raw, ${(detailSize.gzip / 1024 / 1024).toFixed(2)} MB gzip in ${details.length} lazy-loaded shards`);
console.log(`Sitemap: ${source.length + 1} URL`);
