const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');

const root = path.join(__dirname, '..');
const urapDir = path.join(root, 'data', 'urap');
const outFile = path.join(root, 'data', 'urap', 'urap.json');

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
  const yearData = {};
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!row || !row[1]) continue;
    const name = String(row[1]).trim().toUpperCase();
    const rank = row[0] != null ? Number(row[0]) : i;
    const total = row[row.length - 1] != null ? Number(row[row.length - 1]) : null;
    yearData[name] = { rank, total };
  }
  result[year] = yearData;
  console.log(`URAP ${year}: ${Object.keys(yearData).length} universities`);
}

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(result));
console.log(`Written: ${outFile}`);
