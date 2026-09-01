(() => {
  const realFetch = window.fetch.bind(window);
  let programs = [], byCode = new Map(), ready;
  const jsonResponse = body => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
  const url = file => new URL(file, document.baseURI).toString();
  function decode(catalog) {
    const d = catalog.d, F = ['ua','uai','fa','bi','bga','bt','pt','ut','bo','od','ia','ila','ks','akr'];
    programs = catalog.r.map(row => {
      const p = { k: row[0], ui: row[1] }; let n = 2;
      F.forEach(f => p[f] = d[row[n++]]);
      p.bg = row[n++]; p.os = row[n++]; p.ik = row[n++]; p.tyc = !!row[n++];
      p.y = Object.fromEntries(row[n++].map(y => [String(y[0]), { kn:y[1], yl:y[2], mp:y[3], bs:y[4] }]));
      return p;
    });
    byCode = new Map(programs.map(p => [String(p.k), p]));
    return catalog;
  }
  function load() {
    if (!ready) ready = realFetch(url(`data/static/${window.YOK_ATLAS_DATA.catalog}?v=${encodeURIComponent(window.YOK_ATLAS_DATA.version)}`)).then(r => r.json()).then(decode);
    return ready;
  }
  async function loadGzipJson(file) {
    const response = await realFetch(url(file));
    if (!response.ok) throw new Error(`Could not load ${file}`);
    if (!('DecompressionStream' in window)) throw new Error('Bu tarayıcı sıkıştırılmış ayrıntı verisini desteklemiyor.');
    return new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
  }
  function years() { return [window.YOK_ATLAS_DATA.lastFetchYear, window.YOK_ATLAS_DATA.lastFetchYear-1, window.YOK_ATLAS_DATA.lastFetchYear-2]; }
  function indexes() {
    const cities = new Map(), unis = new Map(), groups = new Map(), cityUnis = {};
    for (const p of programs) {
      if (p.ik && !cities.has(p.ik)) cities.set(p.ik, { il_kodu:p.ik, il_adi:p.ia });
      if (p.ui && !unis.has(p.ui)) unis.set(p.ui, { universite_id:p.ui, universite_adi:p.ua, universite_turu:p.ut });
      if (p.ui && p.ik) (cityUnis[p.ik] ||= []).includes(p.ui) || cityUnis[p.ik].push(p.ui);
      if (p.bga) {
        const gk=p.bga+'|'+p.pt;
        const g = groups.get(gk) || { birim_grup_id:p.bg, birim_grup_adi:p.bga, puan_turu:p.pt, kontenjan_yillar:{} };
        for (const [y, s] of Object.entries(p.y)) if (s.kn != null) g.kontenjan_yillar[y] = (g.kontenjan_yillar[y] || 0) + s.kn;
        groups.set(gk, g);
      }
    }
    return { cities:[...cities.values()], unis:[...unis.values()], groups:[...groups.values()], cityUnis };
  }
  let index;
  const shardCache = new Map();
  function filter(f) {
    const ly = String(years()[0]); let r = programs;
    if (f.puanTuru && f.puanTuru !== 'ALL') r = r.filter(p => p.pt === f.puanTuru);
    const types = []; if (f.devlet !== false) types.push('DEVLET'); if (f.vakif !== false) types.push('VAKIF');
    r = types.length === 2 ? r : r.filter(p => types.includes(p.ut));
    const burs = []; if (f.bursUcretsiz !== false) burs.push('u'); if (f.bursBurslu !== false) burs.push('b'); if (f.burs50 !== false) burs.push('50'); if (f.burs25 !== false) burs.push('25'); if (f.bursUcretli !== false) burs.push('x');
    if (burs.length < 5) r = r.filter(p => { if ((p.bo||'').includes('%75')) return true; return burs.some(b => b === 'u' ? p.ut === 'DEVLET' : b === 'b' ? p.bo === 'Burslu' : b === 'x' ? p.bo.includes('Ücretli') : p.bo.includes('%'+b)); });
    if (f.iller?.length) { const s = new Set(f.iller.map(String)); r = r.filter(p => s.has(String(p.ik))); }
    if (f.universiteler?.length) { const s = new Set(f.universiteler.map(Number)); r = r.filter(p => s.has(p.ui)); }
    if (f.bolumler?.length) { const s = new Set(f.bolumler.map(Number)); r = r.filter(p => s.has(p.bg)); }
    if (f.minSir || f.maxSir) { const a = f.minSir || 0, b = f.maxSir || Infinity; r = r.filter(p => p.y[ly].bs == null || (p.y[ly].bs >= a && p.y[ly].bs <= b)); }
    if (f.yeni === false) r = r.filter(p => !(p.y[ly] && p.y[ly].mp == null && p.y[ly].bs == null));
    if (f.dolmamis !== true) r = r.filter(p => !(p.y[ly] && p.y[ly].yl != null && p.y[ly].kn != null && p.y[ly].yl < p.y[ly].kn));
    if (f.kktc !== true) r = r.filter(p => !p.bi.includes('KKTC'));
    if (f.mtok !== true) r = r.filter(p => !p.bi.includes('M.T.O.K'));
    const field = f.sortBy === 'mp' ? 'mp' : 'bs', direction = f.sortDir === 'desc' ? -1 : 1;
    const value = p => { const v = p.y[ly]?.[field]; return v == null || v === '' || Number(v) === 0 ? null : Number(v); };
    return r.slice().sort((a,b) => { const av=value(a),bv=value(b); if(av==null)return bv==null?0:1;if(bv==null)return -1;return(av-bv)*direction; });
  }
  async function program(kod) {
    const p = byCode.get(String(kod)); if (!p) return { error:'Bulunamadı' };
    const shard = Number(kod) % 64;
    const shardUrl = `data/static/details/${shard}.json.gz?v=${encodeURIComponent(window.YOK_ATLAS_DATA.version)}`;
    if (!shardCache.has(shardUrl)) shardCache.set(shardUrl, loadGzipJson(shardUrl));
    const detail = await shardCache.get(shardUrl).then(x => x[String(kod)] || {});
    const yearly = structuredClone(p.y);
    for (const [year, values] of Object.entries(detail.y || {})) Object.assign(yearly[year] ||= {}, values);
    return { kilavuzKodu:p.k, universiteAdi:p.ua, ui:p.ui, uniIlAdi:p.uai, fymkAdi:p.fa, birimAdi:p.bi, birimGrupAdi:p.bga, birimTuruAdi:p.bt, puanTuru:p.pt, universiteTuru:p.ut, bursOraniAdi:p.bo, ogrenimSuresi:p.os, ogrenimDiliAdi:p.od, ilAdi:p.ia, ilceAdi:p.ila, kosul:p.ks, kosulList:detail.kl || [], akreditasyon:p.akr, tyc:p.tyc, yearly };
  }
  window.fetch = async (input, init = {}) => {
    const request = typeof input === 'string' ? input : input.url;
    const path = new URL(request, location.href).pathname;
    if (!path.includes('/api/')) return realFetch(input, init);
    await load(); index ||= indexes();
    if (path.endsWith('/metadata')) return jsonResponse({ lastFetchYear:window.YOK_ATLAS_DATA.lastFetchYear, totalPrograms:window.YOK_ATLAS_DATA.totalPrograms, displayYears:years() });
    if (path.endsWith('/cities')) return jsonResponse(index.cities);
    if (path.endsWith('/universities')) return jsonResponse(index.unis);
    if (path.endsWith('/program-groups')) return jsonResponse(index.groups);
    if (path.endsWith('/city-unis')) return jsonResponse(index.cityUnis);
    if (path.endsWith('/search')) { const f = JSON.parse(init.body || '{}'), r = filter(f), size = f.size || 100, page = f.page || 0; return jsonResponse({ content:r.slice(page*size, page*size+size), totalElements:r.length, totalPages:Math.ceil(r.length/size), years:years() }); }
    const match = path.match(/\/api\/program\/([^/]+)/); if (match) return jsonResponse(await program(decodeURIComponent(match[1])));
    return jsonResponse({ error:'Unsupported static API' });
  };
})();
