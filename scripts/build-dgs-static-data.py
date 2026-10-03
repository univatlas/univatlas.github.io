#!/usr/bin/env python3
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DGS_DIR = os.path.join(ROOT, "data", "dgs")
OUT = os.path.join(DGS_DIR, "static")

FIELDS = ["ua", "fa", "bi", "bga", "pt", "ut", "bo", "ia"]


def main():
    with open(os.path.join(DGS_DIR, "dgs-data.json"), encoding="utf-8") as f:
        source = json.load(f)
    with open(os.path.join(DGS_DIR, "dgs-onlisans.json"), encoding="utf-8") as f:
        assoc = json.load(f)
    with open(os.path.join(DGS_DIR, "dgs-meta.json"), encoding="utf-8") as f:
        meta = json.load(f)

    os.makedirs(OUT, exist_ok=True)
    for fn in os.listdir(OUT):
        if re.match(r"^(catalog|onlisans)-.*\.json$", fn):
            os.remove(os.path.join(OUT, fn))

    canon = json.dumps({"s": source, "o": assoc}, ensure_ascii=False, sort_keys=True)
    version = "%s-%s" % (meta["lastFetchYear"],
                         hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12])

    dictionary = [""]
    ids = {"": 0}

    def string_id(value):
        text = "" if value is None else str(value)
        if text not in ids:
            ids[text] = len(dictionary)
            dictionary.append(text)
        return ids[text]

    def compact_yearly(yearly):
        out = []
        for year in sorted((yearly or {}).keys()):
            s = yearly[year] or {}
            out.append([int(year), s.get("kn"), s.get("yl"), s.get("bos"),
                        s.get("min"), s.get("max")])
        return out

    rows = []
    for p in source:
        row = [p.get("k"), p.get("ui")]
        for field in FIELDS:
            row.append(string_id(p.get(field)))
        row.append(p.get("ik"))
        row.append(compact_yearly(p.get("y")))
        rows.append(row)

    catalog_name = "catalog-%s.json" % version
    with open(os.path.join(OUT, catalog_name), "w", encoding="utf-8") as f:
        json.dump({"v": version, "years": meta["displayYears"],
                   "d": dictionary, "r": rows}, f, ensure_ascii=False)

    names, name_ids = [], {}

    def name_id(name):
        if name not in name_ids:
            name_ids[name] = len(names)
            names.append(name)
        return name_ids[name]

    assoc_list = [[o["kod"], o["ad"]] for o in assoc.get("onlisans", [])]
    transfer_map = {}
    for code, lst in (assoc.get("mapping") or {}).items():
        transfer_map[code] = [[name_id(e["ad"]), e.get("kod", ""), e.get("pt", "")]
                              for e in (lst or [])]

    assoc_name = "onlisans-%s.json" % version
    with open(os.path.join(OUT, assoc_name), "w", encoding="utf-8") as f:
        json.dump({"v": version, "o": assoc_list, "d": names, "m": transfer_map},
                  f, ensure_ascii=False)

    with open(os.path.join(OUT, "config.js"), "w", encoding="utf-8") as f:
        f.write("window.DGS_DATA=%s;\n" % json.dumps({
            "version": version, "catalog": catalog_name,
            "onlisans": assoc_name,
            "totalPrograms": len(source),
            "lastFetchYear": meta["lastFetchYear"],
            "displayYears": meta["displayYears"],
        }, ensure_ascii=False))

    update_sitemap([p.get("k") for p in source if p.get("k")])

    for fn in (catalog_name, assoc_name, "config.js"):
        kb = os.path.getsize(os.path.join(OUT, fn)) / 1024
        print("  %s: %.0f KB" % (fn, kb))
    print("version: %s (%d programs)" % (version, len(source)))


def update_sitemap(codes):
    import os as _os
    from urllib.parse import quote
    all_programs = _os.environ.get("ALL_PROGRAMS", "1") != "0"
    site = "https://univatlas.github.io"
    p = os.path.join(ROOT, "sitemap.xml")
    try:
        with open(p, encoding="utf-8") as f:
            s = f.read()
    except OSError:
        s = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
             '</urlset>')
    lines = [l for l in s.split("\n") if "/dgs/?programkodu=" not in l]
    s = "\n".join(lines)
    if "/dgs/</loc>" not in s and "/dgs/" not in s:
        s = s.replace("</urlset>",
                      "<url><loc>%s/dgs/</loc><changefreq>weekly</changefreq>"
                      "<priority>0.9</priority></url>\n</urlset>" % site)
    if "privacy.html</loc>" not in s:
        s = s.replace("</urlset>",
                      "<url><loc>%s/privacy.html</loc><changefreq>yearly</changefreq>"
                      "<priority>0.3</priority></url>\n</urlset>" % site)
    if all_programs:
        tags = "".join(
            "<url><loc>%s/dgs/?programkodu=%s</loc><changefreq>monthly</changefreq>"
            "<priority>0.6</priority></url>\n" % (site, quote(str(k), safe=""))
            for k in sorted(set(codes)))
        s = s.replace("</urlset>", tags + "</urlset>")
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)
    print("  sitemap: %d DGS program links%s"
          % (len(set(codes)) if all_programs else 0,
             "" if all_programs else " (disabled: ALL_PROGRAMS=0)"))


if __name__ == "__main__":
    main()
