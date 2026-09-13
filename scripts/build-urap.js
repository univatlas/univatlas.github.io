const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');

const root = path.join(__dirname, '..');
const urapDir = path.join(root, 'data', 'urap');
const outFile = path.join(root, 'data', 'urap', 'urap.json');

function stripCity(name) {
  return name.replace(/\s*\([^)]*\)\s*$/, '').trim();
}

const catalogPath = path.join(root, 'data', 'static');
const catalogFile = fs.readdirSync(catalogPath).find(f => /^catalog-/.test(f));
let nameToId = {};
if (catalogFile) {
  const catalog = JSON.parse(fs.readFileSync(path.join(catalogPath, catalogFile), 'utf8'));
  const d = catalog.d;
  for (const row of catalog.r) {
    const ua = d[row[2]];
    if (ua) nameToId[stripCity(ua.toUpperCase())] = row[1];
  }
  console.log(`Catalog: ${Object.keys(nameToId).length} universities mapped`);
}

const result = {};
const files = fs.readdirSync(urapDir).filter(f => /^urap_\d{4}\.xlsx$/i.test(f));
if (!files.length) { console.log('No urap_YYYY.xlsx files found in data/urap/'); process.exit(0); }

for (const file of files) {
  const yearMatch = file.match(/urap_(\d{4})\.xlsx/i);
  if (!yearMatch) continue;
  const year = yearMatch[1];
  const wb = XLSX.readFile(path.join(urapDir, file));
  const ws = wb.Sheets[wb.SheetNames[0]];
  const data = XLSX.utils.sheet_to_json(ws, { header: 1 });
  const yearArr = [];
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!row || !row[1]) continue;
    const name = stripCity(String(row[1]).trim().toUpperCase());
    const rank = row[0] != null ? Number(row[0]) : i;
    const id = nameToId[name];
    if (id) yearArr.push([id, rank]);
    else console.log(`  No match: ${row[1]} -> ${name}`);
  }
  yearArr.sort((a, b) => a[1] - b[1]);
  result[year] = { total: yearArr.length, r: yearArr };
  console.log(`URAP ${year}: ${yearArr.length} matched universities`);
}

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(result));
console.log(`Written: ${outFile}`);
