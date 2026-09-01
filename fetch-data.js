
const fs = require('fs');
const path = require('path');
const https = require('https');

const DATA_DIR = path.join(__dirname, 'data');
const API = 'https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search';
const NETLER_API = 'https://yokatlas.yok.gov.tr/api/netler/search';
const PAGE_SIZE = 500;
const MAX_RETRIES = 3;

const HEADERS = {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'User-Agent': 'yokatlas-py/0.6',
};

let totalDownloaded = 0;

function post(url, body, retry = 0) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const u = new URL(url);
    const req = https.request({
      hostname: u.hostname,
      path: u.pathname,
      method: 'POST',
      headers: { ...HEADERS, 'Content-Length': Buffer.byteLength(data) },
      timeout: 30000,
    }, res => {
      let buf = [];
      res.on('data', c => { buf.push(c); totalDownloaded += c.length; });
      res.on('end', () => {
        const raw = Buffer.concat(buf).toString();
        if (res.statusCode === 418 || res.statusCode === 429) {
          if (retry < MAX_RETRIES) {
            const wait = Math.pow(2, retry + 1) * 1000;
            console.log(`  Ã¢ÂÂ³ Rate limit (${res.statusCode}), ${wait / 1000}s bekleniyor... (deneme ${retry + 1}/${MAX_RETRIES})`);
            return setTimeout(() => post(url, body, retry + 1).then(resolve, reject), wait);
          }
          return reject(new Error(`Rate limit aÃ…Å¸Ã„Â±ldÃ„Â± (${res.statusCode})`));
        }
        if (res.statusCode !== 200) {
          if (retry < MAX_RETRIES) {
            const wait = Math.pow(2, retry + 1) * 1000;
            console.log(`  Ã¢ÂÂ³ HTTP ${res.statusCode}, ${wait / 1000}s bekleniyor... (deneme ${retry + 1}/${MAX_RETRIES})`);
            return setTimeout(() => post(url, body, retry + 1).then(resolve, reject), wait);
          }
          return reject(new Error(`HTTP ${res.statusCode}: ${raw.substring(0, 200)}`));
        }
        try { resolve(JSON.parse(raw)); }
        catch (e) { reject(new Error('JSON parse: ' + e.message)); }
      });
    });
    req.on('error', err => {
      if (retry < MAX_RETRIES) {
        const wait = Math.pow(2, retry + 1) * 1000;
        console.log(`  Ã¢ÂÂ³ BaÃ„Å¸lantÃ„Â± hatasÃ„Â±, ${wait / 1000}s bekleniyor... (deneme ${retry + 1}/${MAX_RETRIES})`);
        return setTimeout(() => post(url, body, retry + 1).then(resolve, reject), wait);
      }
      reject(err);
    });
    req.on('timeout', () => {
      req.destroy();
      if (retry < MAX_RETRIES) {
        const wait = Math.pow(2, retry + 1) * 1000;
        console.log(`  Ã¢ÂÂ³ Zaman aÃ…Å¸Ã„Â±mÃ„Â±, ${wait / 1000}s bekleniyor... (deneme ${retry + 1}/${MAX_RETRIES})`);
        return setTimeout(() => post(url, body, retry + 1).then(resolve, reject), wait);
      }
      reject(new Error('Zaman aÃ…Å¸Ã„Â±mÃ„Â±'));
    });
    req.write(data);
    req.end();
  });
}

function fmt(n) {
  if (n >= 1073741824) return (n / 1073741824).toFixed(2) + ' GB';
  if (n >= 1048576) return (n / 1048576).toFixed(2) + ' MB';
  if (n >= 1024) return (n / 1024).toFixed(1) + ' KB';
  return n + ' B';
}

async function fetchAll() {
  console.log('Ã¢â€¢â€Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢â€”');
  console.log('Ã¢â€¢â€˜   YÃƒâ€“K Atlas Veri Ãƒâ€¡ekme BaÃ…Å¸latÃ„Â±ldÃ„Â±   Ã¢â€¢â€˜');
  console.log('Ã¢â€¢Å¡Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â');
  console.log('');

  let all = [];
  let page = 0;
  let total = Infinity;
  const totalPages = () => Math.ceil(total / PAGE_SIZE);
  const pct = () => total > 0 ? ((all.length / total) * 100).toFixed(1) : '0.0';
  const startTime = Date.now();

  while (all.length < total) {
    const res = await post(API, {
      filters: {},
      page,
      size: PAGE_SIZE,
      sortBy: 'basariSirasi',
      direction: 'ASC',
    });
    total = res.totalElements || 0;
    const content = res.content || [];
    all.push(...content);

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(0);
    const kalan = totalPages() - page - 1;
    console.log(
      `  ÄŸÅ¸â€œÂ¥ Sayfa ${page + 1}/${totalPages()} | ` +
      `${all.length.toLocaleString('tr-TR')}/${total.toLocaleString('tr-TR')} (%${pct()}) | ` +
      `Ã„Â°ndirilen: ${fmt(totalDownloaded)} | ` +
      `Kalan: ${kalan} sayfa | ` +
      `${elapsed}s`
    );

    if (content.length < PAGE_SIZE) break;
    page++;
    await new Promise(r => setTimeout(r, 50));
  }

  console.log('');
  console.log(`  Ã¢Å“â€¦ ${all.length.toLocaleString('tr-TR')} program ÃƒÂ§ekildi (${fmt(totalDownloaded)})`);
  console.log(`  Ã¢ÂÂ±  SÃƒÂ¼re: ${((Date.now() - startTime) / 1000).toFixed(0)}s`);
  console.log('');

  console.log('  ÄŸÅ¸â€œÂ¦ Veri iÃ…Å¸leniyor...');
  const offline = {};
  const yilCounts = {};
  for (const p of all) {
    const y = String(p.yil || '');
    if (y) yilCounts[y] = (yilCounts[y] || 0) + 1;
  }
  const defaultYil = Object.entries(yilCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || String(new Date().getFullYear());
  for (const p of all) {
    const kod = String(p.kilavuzKodu || '');
    if (!kod) continue;
    const yil = String(p.yil || String(new Date().getFullYear()));
    const yearly = {};
    yearly[yil] = {
      kn: p.kontenjan,
      yl: p.gkY,
      mp: p.minPuan || null,
      bs: p.basariSirasi || null,
    };
    for (let i = 1; i <= 3; i++) {
      const yr = String(Number(yil) - i);
      const gk = p['gk' + i];
      const mp = p['minPuan' + i];
      const bs = p['basariSirasi' + i];
      if (mp != null || bs != null) {
        yearly[yr] = { kn: gk || null, yl: gk || null, mp: mp || null, bs: bs || null };
      }
    }
    offline[kod] = {
      kilavuzKodu: kod,
      universiteId: p.universiteId,
      universiteAdi: p.universiteAdi,
      uniIlAdi: p.uniIlAdi,
      fymkAdi: p.fymkAdi,
      birimAdi: p.birimAdi,
      birimGrupId: p.birimGrupId,
      birimGrupAdi: p.birimGrupAdi,
      puanTuru: p.puanTuru,
      universiteTuru: p.universiteTuru,
      bursOraniAdi: p.bursOraniAdi,
      ogrenimSuresi: p.ogrenimSuresi,
      ogrenimDiliAdi: p.ogrenimDiliAdi,
      ilKodu: p.ilKodu,
      ilAdi: p.ilAdi,
      kosul: p.kosul,
      kosulList: p.kosulList || [],
      akreditasyon: p.akreditasyon || '',
      tyc: p.tyc || false,
      yearly,
    };
  }

  fs.writeFileSync(path.join(DATA_DIR, 'offline-data.json'), JSON.stringify(offline));
  console.log(`  ÄŸÅ¸â€œâ€ offline-data.json: ${fmt(fs.statSync(path.join(DATA_DIR, 'offline-data.json')).size)}`);

  console.log('');
  console.log('  ÄŸÅ¸â€œÂ¥ Net verileri ÃƒÂ§ekiliyor...');
  let allNets = [];
  let netPage = 0;
  let netTotal = Infinity;
  let netDownloaded = 0;
  const netStart = Date.now();

  while (allNets.length < netTotal) {
    const res = await post(NETLER_API, { page: netPage, size: PAGE_SIZE });
    netTotal = res.totalElements || 0;
    const content = res.content || [];
    allNets.push(...content);
    const netTotalPages = Math.ceil(netTotal / PAGE_SIZE);
    const pct = netTotal > 0 ? ((allNets.length / netTotal) * 100).toFixed(1) : '0.0';
    const kalan = netTotalPages - netPage - 1;
    console.log(
      `    ÄŸÅ¸â€œÂ¥ Sayfa ${netPage + 1}/${netTotalPages} | ` +
      `${allNets.length.toLocaleString('tr-TR')}/${netTotal.toLocaleString('tr-TR')} (%${pct}) | ` +
      `Kalan: ${kalan} sayfa`
    );
    if (content.length < PAGE_SIZE) break;
    netPage++;
    await new Promise(r => setTimeout(r, 50));
  }

  for (const n of allNets) {
    const kod = String(n.kilavuzKodu || '');
    if (!kod || !offline[kod]) continue;
    const yil = String(n.yil || '');
    if (!yil) continue;
    if (!offline[kod].yearly[yil]) offline[kod].yearly[yil] = {};
    Object.assign(offline[kod].yearly[yil], {
      tytTrkNet: n.tytTrkNet, tytSosNet: n.tytSosNet,
      tytMatNet: n.tytMatNet, tytFenNet: n.tytFenNet,
      aytMatNet: n.aytMatNet, aytFizNet: n.aytFizNet,
      aytKimNet: n.aytKimNet, aytBioNet: n.aytBioNet,
      aytTdeNet: n.aytTdeNet, aytTrh1Net: n.aytTrh1Net,
      aytCog1Net: n.aytCog1Net, aytTrh2Net: n.aytTrh2Net,
      aytCog2Net: n.aytCog2Net, aytFelNet: n.aytFelNet,
      aytDinNet: n.aytDinNet, ydtYdilNet: n.ydtYdilNet,
      obp: n.obp, katsayi: n.katsayi,
    });
  }
  console.log(`  Ã¢Å“â€¦ ${allNets.length.toLocaleString('tr-TR')} net kaydÃ„Â± birleÃ…Å¸tirildi (${((Date.now() - netStart) / 1000).toFixed(0)}s)`);

  fs.writeFileSync(path.join(DATA_DIR, 'offline-data.json'), JSON.stringify(offline));

  const table = [];
  const yearlyOut = {};
  for (const [kod, p] of Object.entries(offline)) {
    const sy = {};
    for (const [y, s] of Object.entries(p.yearly || {})) {
      const c = {};
      for (const [k, v] of Object.entries(s)) {
        if (v != null && v !== '' && k !== 'year') c[k] = v;
      }
      sy[y] = c;
    }
    table.push({
      k: kod, ui: p.universiteId, ua: p.universiteAdi || '', uai: p.uniIlAdi || '',
      fa: p.fymkAdi || '', bi: p.birimAdi || '', bg: p.birimGrupId, bga: p.birimGrupAdi || '',
      bt: p.birimTuruAdi || '', pt: p.puanTuru || '', ut: p.universiteTuru || '', bo: p.bursOraniAdi || '',
      os: p.ogrenimSuresi, od: p.ogrenimDiliAdi || '', ik: p.ilKodu, ia: p.ilAdi || '',
      ila: p.ilceAdi || '', ks: p.kosul || '', kl: p.kosulList || [], akr: p.akreditasyon || '',
      tyc: p.tyc || false, y: sy,
    });
    yearlyOut[kod] = sy;
  }

  fs.writeFileSync(path.join(DATA_DIR, 'table-data.json'), JSON.stringify(table));
  fs.writeFileSync(path.join(DATA_DIR, 'yearly-data.json'), JSON.stringify(yearlyOut));
  console.log(`  ÄŸÅ¸â€œâ€ table-data.json: ${fmt(fs.statSync(path.join(DATA_DIR, 'table-data.json')).size)}`);
  console.log(`  ÄŸÅ¸â€œâ€ yearly-data.json: ${fmt(fs.statSync(path.join(DATA_DIR, 'yearly-data.json')).size)}`);

  const meta = { lastFetchYear: Number(defaultYil), totalPrograms: all.length };
  fs.writeFileSync(path.join(DATA_DIR, 'metadata.json'), JSON.stringify(meta));

  console.log('');
  console.log('Ã¢â€¢â€Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢â€”');
  console.log('Ã¢â€¢â€˜        Ã¢Å“â€¦ Ãƒâ€¡ekme TamamlandÃ„Â±!          Ã¢â€¢â€˜');
  console.log('Ã¢â€¢Å¡Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â');
}

fetchAll().catch(e => { console.error('Ã¢ÂÅ’ Hata:', e.message); process.exit(1); });
