import argparse
import glob
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THE_DIR = os.path.join(ROOT, "data", "the")
OUT_FILE = os.path.join(THE_DIR, "the.json")
THRESH = 0.30
API = "https://www.timeshighereducation.com/json/ranking_tables/world_university_rankings/{}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

SYN = [
    ("technical", "teknik"),
    ("technology", "teknoloji"),
    ("technologies", "teknoloji"),
    ("sciences", "bilimleri"),
    (r"\bscience\b", "bilim"),
    (r"\bhealth\b", "saglik"),
    (r"\beconomics\b", "ekonomi"),
    (r"\binstitute\b", "enstitu"),
    (r"\binstitutes\b", "enstitu"),
]

MANUAL = {
    "middle east teknik": 122571,
    "izmir enstitu teknoloji": 116207,
    "tobb ekonomi teknoloji": 125552,
    "saglik bilimleri turkey": 270121,
    "turkish aeronautical association": 203267,
    "social bilimleri ankara": 232846,
    "t c demiroglu bilim": 384591,
    "sakarya applied bilimleri": 339988,
    "mus alparslan": 121164,
    "bilkent": 105118,
    "acibadem": 326654,
    "beykent": 448766,
    "bezmialem vakif": 163894,
    "karamanoglu mehmet bey": 117553,
}


def strip_city(name):
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(name)).strip()


def norm(s):
    s = str(s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("â", "a").replace("î", "i").replace("û", "u").replace("ı", "i")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core(s):
    t = " " + norm(s) + " "
    for pat, rep in SYN:
        t = re.sub(pat, rep, t)
    t = re.sub(r"\benstutus[ue]\b", "enstitu", t)
    t = re.sub(r"\benstitus[ue]\b", "enstitu", t)
    for w in ("university", "universitesi", "universite", "of", "the", "ve", "and"):
        t = re.sub(r"\b" + w + r"\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def load_catalog():
    files = glob.glob(os.path.join(ROOT, "data", "static", "catalog-*.json"))
    if not files:
        raise SystemExit("Catalog not found, run build-static-data.js first.")
    cat = json.load(open(files[0], encoding="utf-8"))
    d = cat["d"]
    seen, out = {}, []
    for row in cat["r"]:
        uid, ua = row[1], d[row[2]]
        if uid in seen or not ua:
            continue
        seen[uid] = True
        name = strip_city(ua)
        out.append({"id": uid, "name": name, "core": core(name)})
    return out


def build_matcher(yok):
    exact = {y["core"]: y for y in yok}
    spaceless = {y["core"].replace(" ", ""): y for y in yok}
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    mat = vec.fit_transform([y["core"] for y in yok])
    by_id = {y["id"]: y for y in yok}
    return {"exact": exact, "spaceless": spaceless, "vec": vec, "mat": mat, "by_id": by_id}


def match_one(name, yok, m, thresh=THRESH):
    key = core(name)
    if not key:
        return None
    uid = MANUAL.get(key) or MANUAL.get(norm(name))
    if uid:
        return {"id": uid, "method": "manual", "score": 1.0}
    if key in m["exact"]:
        return {"id": m["exact"][key]["id"], "method": "exact", "score": 1.0}
    ns = key.replace(" ", "")
    if ns in m["spaceless"]:
        return {"id": m["spaceless"][ns]["id"], "method": "spaceless", "score": 1.0}
    kt = key.split()
    cands = [y for y in yok if all(t in set(y["core"].split()) for t in kt)]
    if cands:
        cands.sort(key=lambda y: len(y["core"].split()))
        lens = [len(y["core"].split()) for y in cands]
        if not (len(cands) > 1 and lens[0] == lens[1]):
            return {"id": cands[0]["id"], "method": "subset", "score": 1.0}
    sims = cosine_similarity(m["vec"].transform([key]), m["mat"])[0]
    j = int(sims.argmax())
    score = float(sims[j])
    if score >= thresh:
        return {"id": yok[j]["id"], "method": "tfidf", "score": round(score, 3)}
    return None


def fetch_year(year):
    url = API.format(year)
    print(f"Trying THE {year}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  404 -> {year} not published yet.")
            return None
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None)
    a = ap.parse_args()

    import datetime
    yok = load_catalog()
    print(f"Catalog: {len(yok)} universities")
    m = build_matcher(yok)

    year = a.year or datetime.date.today().year
    raw = fetch_year(year)
    if raw is None and a.year is None:
        year -= 1
        raw = fetch_year(year)
    if raw is None:
        raise SystemExit("Could not fetch THE data.")

    os.makedirs(THE_DIR, exist_ok=True)
    with open(os.path.join(THE_DIR, f"the_{year}.json"), "w", encoding="utf-8") as f:
        json.dump(raw, f)
    for fn in os.listdir(THE_DIR):
        mm = re.fullmatch(r"the_(\d{4})\.json", fn)
        if mm and mm.group(1) != str(year):
            os.remove(os.path.join(THE_DIR, fn))
            print(f"Deleted old dump: {fn}")
    print(f"Raw dump written: data/the/the_{year}.json")

    rows = [r for r in raw.get("data", [])
            if str(r.get("location", "")).strip().lower() in ("turkey", "türkiye")]
    print(f"Turkey records: {len(rows)}")

    arr, methods = [], {}
    tr_rank = 0
    for r in rows:
        world = str(r.get("rank", "")).strip()
        name = str(r.get("name", "")).strip()
        hit = match_one(name, yok, m)
        if hit is None:
            print(f'  No match: "{name}" -> "{core(name)}" (World:{world})')
            continue
        uid = hit["id"]
        k = hit["method"]
        methods[k] = methods.get(k, 0) + 1
        if "reporter" in world.lower():
            arr.append([uid, None, "Reporter"])
        else:
            tr_rank += 1
            arr.append([uid, tr_rank, world])
    ranked = sum(1 for x in arr if x[1] is not None)
    arr.sort(key=lambda x: (x[1] is None, x[1] or 0))
    print(f"THE {year}: {ranked} ranked + {len(arr) - ranked} reporters = {len(arr)} matched {methods}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({str(year): {"total": ranked, "r": arr}}, f)
    print(f"Written: {OUT_FILE} (only {year})")


if __name__ == "__main__":
    main()
