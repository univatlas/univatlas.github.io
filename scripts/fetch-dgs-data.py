#!/usr/bin/env python3
import html
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required: pip install requests", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DGS_DIR = os.path.join(ROOT, "data", "dgs")
STATIC_DIR = os.path.join(ROOT, "data", "static")

MENU_URLS = [
    "https://www.osym.gov.tr/SinavGrubu/Menu/767",
    "https://www.osym.gov.tr/SinavGrubu/Index/8",
]
GUIDE_PAGE_PATTERNS = [
    "https://www.osym.gov.tr/{y}-dgs-tercih-bilgileri-ve-tablolar",
    "https://www.osym.gov.tr/{y}-dgs-tercih-islemleri",
]
DETAIL_PAGE_PATTERNS = [
    "https://www.osym.gov.tr/{y}dgs-yerlestirme-sonuclarina-iliskin-sayisal-bilgiler",
    "https://www.osym.gov.tr/{y}-dgs-yerlestirme-sonuclarina-iliskin-sayisal-bilgiler",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) univatlas-dgs-bot/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara",
    "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman",
    "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne",
    "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun",
    "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir",
    "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri",
    "Kırıkkale", "Kırklareli", "Kırşehir", "Kilis", "Kocaeli", "Konya", "Kütahya",
    "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde",
    "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas",
    "Şanlıurfa", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak",
    "Van", "Yalova", "Yozgat", "Zonguldak", "Karabük",
]

FACULTY_KEYWORDS = re.compile(
    r"(FAK[\w]*LTES[\w]*|Y[\w]*KSEKOKULU|KONSERVATUVAR[\w]*|ENST[\w]*T[\w]*S[\w]*|"
    r"MESLEK Y[\w]*KSEKOKULU|UYGULAMALI B[\w]*L[\w]*MLER Y[\w]*KSEKOKULU)",
    re.IGNORECASE,
)


def tr_titlecase(s):
    if not s or not isinstance(s, str):
        return s
    letters = [c for c in s if c.isalpha()]
    if not letters or any(c.islower() for c in letters):
        return s

    def lower_tr(t):
        return t.replace("İ", "i").replace("I", "ı").lower()

    def upper_first(ch):
        if ch == "i":
            return "İ"
        if ch == "ı":
            return "I"
        return ch.upper()

    def fix_word(m):
        w = m.group(0)
        return upper_first(lower_tr(w)[0]) + lower_tr(w)[1:] if w else w

    titled = re.sub(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", fix_word, s)
    small = {"ve", "ile", "ya", "veya", "yahut", "ki", "de", "da",
             "mi", "mı", "mu", "mü"}

    def fix_small(m):
        w = m.group(0)
        return lower_tr(w) if lower_tr(w) in small else w

    titled = re.sub(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", fix_small, titled, count=0)
    m0 = re.match(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", titled)
    if m0:
        w = m0.group(0)
        titled = upper_first(lower_tr(w)[0]) + lower_tr(w)[1:] + titled[len(w):]
    return titled


def normalize(s):
    if s is None:
        return ""
    s = str(s)
    tr = str.maketrans({"ı": "i", "I": "i", "İ": "i", "ş": "s", "Ş": "s",
                        "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o",
                        "Ö": "o", "ç": "c", "Ç": "c"})
    s = s.translate(tr).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_text(url, timeout=40):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def extract_links(page_text, base):
    out = []
    pat = re.compile(r'<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                     re.IGNORECASE | re.DOTALL)
    for m in pat.finditer(page_text):
        href = html.unescape(m.group(1)).strip()
        text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        text = re.sub(r"\s+", " ", text).strip()
        if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
            out.append((urljoin(base, href), text))
    return out


def contains_all(haystack, *needles):
    h = normalize(haystack)
    return all(normalize(n) in h for n in needles)


def find_placement_years(now_year):
    found = {}
    for menu in MENU_URLS:
        try:
            page = fetch_text(menu)
        except Exception as e:
            print(f"  ! menu unreachable ({menu}): {e}")
            continue
        for href, text in extract_links(page, menu):
            blob = f"{text} {href}"
            if not (contains_all(blob, "dgs") and contains_all(blob, "yerlestirme")):
                continue
            if not contains_all(blob, "sayisal"):
                if not contains_all(blob, "sonuc"):
                    continue
            m = re.search(r"(20\d{2})", blob)
            if not m:
                continue
            year = int(m.group(1))
            if not (now_year - 30 <= year <= now_year):
                continue
            is_extra = "ek" in normalize(blob).split() or "ek-yerlestirme" in normalize(href) \
                or "ek yerlestirme" in normalize(text)
            prev = found.get(year)
            if prev is None or (prev[1] and not is_extra):
                found[year] = (href, is_extra)
                print(f"  menu found: {year}{' (extra)' if is_extra else ''} -> {href}")
    for y in range(now_year, now_year - 7, -1):
        prev = found.get(y)
        if prev is not None and not prev[1]:
            continue
        for pat in DETAIL_PAGE_PATTERNS:
            url = pat.format(y=y)
            try:
                page = fetch_text(url)
            except Exception:
                continue
            if contains_all(page, "dgs") and (
                    contains_all(page, "en kucuk") or contains_all(page, "yerlestirme")):
                found[y] = (url, False)
                print(f"  direct hit: {y} -> {url}")
                break
    return found


def find_minmax_pdf(detail_url):
    page = fetch_text(detail_url)
    cands = []
    for href, text in extract_links(page, detail_url):
        if not href.lower().endswith(".pdf"):
            continue
        score = 0
        ntext, nhref = normalize(text), normalize(href.lower())
        if "en kucuk" in ntext and "en buyuk" in ntext:
            score += 10
        elif "en kucuk" in ntext or "en buyuk" in ntext:
            score += 6
        if "minmax" in nhref or "min-max" in nhref:
            score += 6
        if "kucuk" in nhref and "buyuk" in nhref:
            score += 6
        if "puan" in ntext:
            score += 2
        if "sayisal" in ntext and "bilgiler" in ntext:
            score -= 4
        if score > 0:
            cands.append((score, href, text))
    if not cands:
        pdfs = [h for h, _ in extract_links(page, detail_url)
                if h.lower().endswith(".pdf")]
        if pdfs:
            dok = [h for h in pdfs if "dokuman.osym.gov.tr" in h]
            pick = (dok or pdfs)[0]
            print(f"  ! no scored match, trying first PDF: {pick}")
            return pick
        raise RuntimeError(f"PDF not found: {detail_url}")
    cands.sort(reverse=True)
    print(f"  pdf: [{cands[0][0]} pts] {cands[0][2]} -> {cands[0][1]}")
    return cands[0][1]


def download(url, dest, timeout=120):
    with requests.get(url, headers=HEADERS, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    print(f"  downloaded ({os.path.getsize(dest)/1e6:.1f} MB): {os.path.basename(dest)}")


def parse_placement_pdf(path, year):
    import fitz
    doc = fitz.open(path)
    lines = []
    for page in doc:
        lines.extend(page.get_text().split("\n"))
    doc.close()

    score_types = {"SAY", "EA", "SOZ", "SÖZ"}
    records = []
    i, n = 0, len(lines)
    code_re = re.compile(r"^\d{9}$")

    def token_or_none(t):
        t = t.strip()
        if t in ("--", "-", "", "—"):
            return None
        return t

    while i < n:
        if not code_re.match(lines[i].strip()):
            i += 1
            continue
        code = lines[i].strip()
        i += 1
        name_parts = []
        while i < n and lines[i].strip().upper().replace("Ö", "O") not in score_types \
                and normalize(lines[i]) not in ("say", "ea", "soz"):
            t = lines[i].strip()
            if t:
                name_parts.append(t)
            i += 1
            if len(name_parts) > 4:
                break
        if i >= n:
            break
        raw_type = lines[i].strip().upper()
        score_type = "SÖZ" if raw_type.startswith("S") and "Z" in raw_type else raw_type
        if score_type not in ("SAY", "EA", "SÖZ"):
            score_type = {"SOZ": "SÖZ"}.get(score_type, raw_type)
        i += 1
        toks = []
        while i < n and len(toks) < 5:
            t = lines[i].strip()
            i += 1
            if not t:
                continue
            if code_re.match(t):
                i -= 1
                break
            for part in t.split():
                if re.match(r"^(--|-|\d+|\d{1,3}(,\d+)+)$", part):
                    toks.append(part)
                elif toks and len(toks) < 5 and part in ("--",):
                    toks.append(part)
                else:
                    if len(toks) == 0 and name_parts is not None and \
                            not re.match(r"^\d", part):
                        name_parts.append(part)
                    else:
                        break
            if toks and len(toks) < 5 and code_re.match(lines[i - 1].strip()):
                break
        while len(toks) < 5:
            toks.append(None)

        def to_int(t):
            t = token_or_none(t) if t else None
            if t is None:
                return None
            try:
                return int(t)
            except ValueError:
                return None

        def to_float(t):
            t = token_or_none(t) if t else None
            if t is None:
                return None
            try:
                return round(float(t.replace(".", "").replace(",", ".")
                                   if "," in t else float(t)), 5)
            except ValueError:
                return None

        records.append({
            "code": code,
            "program_name": re.sub(r"\s+", " ", " ".join(name_parts)).strip(),
            "score_type": score_type if score_type in ("SAY", "EA", "SÖZ") else "SAY",
            "quota": to_int(toks[0]),
            "placed": to_int(toks[1]),
            "empty": to_int(toks[2]),
            "min_score": to_float(toks[3]),
            "max_score": to_float(toks[4]),
            "year": year,
        })
    print(f"  parsed: {len(records)} records (year {year})")
    return records


def parse_table2_pdf(path):
    import pdfplumber
    associate = {}
    transfers = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if not table or len(table[0]) < 4:
                    continue
                head = normalize(" ".join(c or "" for c in table[0]))
                start = 0
                if "alan" in head and "lisans" in head:
                    start = 1
                for row in table[start:]:
                    if len(row) < 5:
                        continue
                    c0, c1, c2, c3, c4 = [(r or "") for r in row[:5]]
                    if "TABLO" in c0.upper() and not re.search(r"\d", c0):
                        continue
                    assoc_codes = [t.strip() for t in c0.split("\n") if t.strip()]
                    assoc_names = [t.strip() for t in c1.split("\n") if t.strip()]
                    prog_names = [t.strip() for t in c2.split("\n") if t.strip()]
                    prog_codes = [t.strip() for t in c3.split("\n") if t.strip()]
                    prog_types = [t.strip().upper() for t in c4.split("\n") if t.strip()]
                    if not assoc_codes or not re.match(r"^\d+$", assoc_codes[0]):
                        continue
                    programs = []
                    for j, pname in enumerate(prog_names):
                        pcode = prog_codes[j] if j < len(prog_codes) else ""
                        ptype = prog_types[j] if j < len(prog_types) else ""
                        ptype = "SÖZ" if ptype.startswith("S") and "Z" in ptype else ptype
                        programs.append({"ad": pname, "kod": pcode, "pt": ptype})
                    for j, code in enumerate(assoc_codes):
                        if not re.match(r"^\d+$", code):
                            continue
                        aname = assoc_names[j] if j < len(assoc_names) else (assoc_names[0] if assoc_names else code)
                        associate[code] = tr_titlecase(clean_text(aname))
                        transfers.setdefault(code, [])
                        for k, entry in enumerate(programs):
                            entry = dict(entry, ad=tr_titlecase(clean_text(entry["ad"])))
                            programs[k] = entry
                            if entry not in transfers[code]:
                                transfers[code].append(entry)
    print(f"  table-2: {len(associate)} associate fields, {sum(len(v) for v in transfers.values())} links")
    return associate, transfers


def load_yok_universities():
    universities = []
    try:
        files = [f for f in os.listdir(STATIC_DIR) if re.match(r"catalog-.*\.json$", f)]
    except OSError:
        files = []
    if not files:
        return universities
    files.sort()
    with open(os.path.join(STATIC_DIR, files[-1]), encoding="utf-8") as f:
        cat = json.load(f)
    d = cat.get("d", [])
    seen = {}
    for row in cat.get("r", []):
        try:
            name = d[row[2]] if isinstance(row[2], int) and row[2] < len(d) else ""
            city = d[row[12]] if isinstance(row[12], int) and row[12] < len(d) else ""
        except (IndexError, TypeError):
            continue
        if not name or name in seen:
            continue
        seen[name] = True
        try:
            utype = d[row[9]] if isinstance(row[9], int) and row[9] < len(d) else ""
        except (IndexError, TypeError):
            utype = ""
        universities.append({
            "name": name,
            "full_key": normalize(name),
            "short_key": normalize(re.sub(r"\s*\([^()]*\)\s*$", "", name)),
            "id": row[1],
            "type": utype or "",
            "city": city or "",
            "city_id": row[18] if len(row) > 18 else None,
        })
    universities.sort(key=lambda u: -max(len(u["full_key"]), len(u["short_key"])))
    print(f"  YOK catalog: {len(universities)} universities loaded")
    return universities


CITY_INDEX = {normalize(c): c for c in CITIES}


def guess_city(text):
    for m in re.finditer(r"\(([^()]*)\)", text or ""):
        cand = CITY_INDEX.get(normalize(m.group(1)))
        if cand:
            return cand
    nt = normalize(text)
    for cn, proper in sorted(CITY_INDEX.items(), key=lambda x: -len(x[0])):
        if cn and cn in nt:
            return proper
    return ""


def split_faculty_program(tail):
    tail = clean_text(tail)
    ms = list(FACULTY_KEYWORDS.finditer(tail or ""))
    if not ms:
        return "", (tail or "").strip()
    last = ms[-1]
    return (clean_text(tail[:last.end()]),
            clean_text(tail[last.end():].strip()))


def clean_text(s):
    if not s:
        return ""
    s = re.sub(r"^[/|\-–—\s]+", "", str(s))
    s = re.sub(r"[/|\-–—\s]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def detect_tuition(text):
    t = normalize(text or "")
    if "burslu" in t:
        return "Burslu"
    if "%50" in (text or ""):
        return "%50 İndirimli"
    if "%25" in (text or ""):
        return "%25 İndirimli"
    if "%75" in (text or ""):
        return "%75 İndirimli"
    if "ucretli" in t or "ucreti" in t:
        return "Ücretli"
    return ""


def base_name(program):
    b = re.sub(r"\([^()]*\)", " ", program or "")
    b = re.sub(r"\s+", " ", b).strip()
    return b


def merge_records(records_by_year, yok_universities):
    merged = {}
    for year, recs in records_by_year.items():
        for r in recs:
            code = r["code"]
            m = merged.setdefault(code, {
                "k": code, "pt": r["score_type"], "y": {},
            })
            m["y"][str(year)] = {
                "kn": r["quota"], "yl": r["placed"], "bos": r["empty"],
                "min": r["min_score"], "max": r["max_score"],
            }
            if "program_adi" not in m:
                m["program_adi"] = r["program_name"]
    for code, m in merged.items():
        full_name = m.get("program_adi", "")
        key = normalize(full_name)
        hit = None
        cut = 0
        for u in yok_universities:
            if u["full_key"] and key.startswith(u["full_key"]):
                hit, cut = u, len(u["name"])
                break
            if u["short_key"] and key.startswith(u["short_key"]):
                hit, cut = u, len(re.sub(r"\s*\([^()]*\)\s*$", "", u["name"]))
                break
        if hit:
            m["ua"] = hit["name"]
            m["ui"] = hit["id"]
            m["ut"] = hit["type"] or "DEVLET"
            m["ia"] = hit["city"]
            m["ik"] = hit["city_id"]
            tail = full_name[cut:].strip()
            tail = re.sub(r"^\([^()]*\)\s*", "", tail)
        else:
            pm = re.match(r"^(.*?ÜNİVERSİTESİ|.*?UNIVERSITESI|.*?ÜNİVERSİTE|.*?ENSTİTÜSÜ)\s*(\([^()]*\))?\s*(.*)$",
                          full_name, re.IGNORECASE | re.DOTALL)
            if pm:
                m["ua"] = pm.group(1).strip()
                tail = (pm.group(3) or "").strip()
            else:
                m["ua"] = full_name.split("  ")[0].strip()[:80]
                tail = full_name[len(m["ua"]):].strip()
            city = guess_city(full_name)
            m["ui"] = None
            m["ia"] = city
            m["ik"] = None
            m["ut"] = ""
        faculty, program = split_faculty_program(tail)
        tuition = detect_tuition(full_name)
        if not m.get("ut"):
            m["ut"] = "VAKIF" if (tuition or "VAKIF" in normalize(full_name)) else "DEVLET"
        m["fa"] = tr_titlecase(faculty)
        m["bi"] = tr_titlecase(program or tail or full_name)
        m["bga"] = tr_titlecase(base_name(program or tail))
        m["bo"] = tuition
        if not m.get("ia"):
            m["ia"] = guess_city(full_name + " " + m.get("ua", ""))
    return merged


def main():
    args = sys.argv[1:]
    local_pdf = None
    local_year = None
    years_override = None
    for i, a in enumerate(args):
        if a == "--local-pdf" and i + 1 < len(args):
            local_pdf = args[i + 1]
        if a == "--year" and i + 1 < len(args):
            local_year = int(args[i + 1])
        if a == "--years" and i + 1 < len(args):
            years_override = [int(y) for y in args[i + 1].split(",") if y.strip().isdigit()]

    now_year = datetime.now(timezone.utc).year
    tmp = tempfile.mkdtemp(prefix="dgs-")
    try:
        records_by_year = {}
        target_years = []

        if local_pdf:
            y = local_year or now_year
            print(f"Using local PDF: {local_pdf} (year {y})")
            recs = parse_placement_pdf(local_pdf, y)
            records_by_year[y] = recs
            target_years = [y]
        else:
            year_pages = find_placement_years(now_year)
            if years_override:
                wanted = sorted(years_override, reverse=True)
            else:
                mains = sorted([y for y, (u, extra) in year_pages.items() if not extra],
                               reverse=True)[:3]
                wanted = mains if mains else [now_year, now_year - 1, now_year - 2]
            print(f"Target years: {wanted}")
            for y in wanted:
                if y in year_pages:
                    detail_url, is_extra = year_pages[y]
                    if is_extra:
                        print(f"  ! {y} has only a supplementary round page, skipping")
                        continue
                    try:
                        pdf_url = find_minmax_pdf(detail_url)
                    except Exception as e:
                        print(f"  ! {y} PDF link not found: {e}")
                        continue
                else:
                    print(f"  ! no menu entry for {y}, skipping")
                    continue
                dest = os.path.join(tmp, f"dgs-minmax-{y}.pdf")
                try:
                    download(pdf_url, dest)
                    records_by_year[y] = parse_placement_pdf(dest, y)
                    target_years.append(y)
                except Exception as e:
                    print(f"  ! {y} download/parse error: {e}")
                finally:
                    if os.path.exists(dest):
                        os.remove(dest)
                if len(target_years) >= 3:
                    break

        if not records_by_year:
            print("ERROR: no yearly data downloaded.", file=sys.stderr)
            sys.exit(1)

        target_years = sorted(records_by_year.keys(), reverse=True)[:3]
        print(f"Processing years: {target_years}")

        associate, transfers = {}, {}
        latest = target_years[0]
        for y in range(latest, latest - 6, -1):
            ok = False
            for pat in GUIDE_PAGE_PATTERNS:
                url = pat.format(y=y)
                try:
                    page = fetch_text(url)
                except Exception:
                    continue
                for href, text in extract_links(page, url):
                    if not href.lower().endswith(".pdf"):
                        continue
                    if "tablo-2" in normalize(f"{text} {href}").replace(" ", "") or \
                            ("tablo" in normalize(text) and "2" in text):
                        dest = os.path.join(tmp, f"dgs-tablo2-{y}.pdf")
                        try:
                            download(href, dest)
                            associate, transfers = parse_table2_pdf(dest)
                            ok = True
                            print(f"  table-2 source: {url}")
                            break
                        except Exception as e:
                            print(f"  ! table-2 parse error: {e}")
                        finally:
                            if os.path.exists(dest):
                                os.remove(dest)
                    if ok:
                        break
                if ok:
                    break
            if ok:
                break
        if not associate:
            try:
                sdir = os.path.join(DGS_DIR, "static")
                sfiles = sorted(f for f in os.listdir(sdir)
                                if re.match(r"^onlisans-.*\.json$", f))
            except OSError:
                sfiles = []
            if sfiles:
                with open(os.path.join(sdir, sfiles[-1]), encoding="utf-8") as f:
                    old = json.load(f)
                associate = {code: name for code, name in old.get("o", [])}
                name_dict = old.get("d", [])
                transfers = {code: [{"ad": name_dict[i] if i < len(name_dict) else "",
                                     "kod": lk, "pt": pt} for i, lk, pt in lst]
                             for code, lst in (old.get("m") or {}).items()}
                print("  ! table-2 download failed, keeping committed map")
                keep = None
            else:
                keep = os.path.join(DGS_DIR, "dgs-onlisans.json")
            if keep and os.path.exists(keep):
                with open(keep, encoding="utf-8") as f:
                    old = json.load(f)
                associate = {o["kod"]: o["ad"] for o in old.get("onlisans", [])}
                transfers = old.get("mapping", {})
                print("  ! table-2 download failed, keeping existing map")
            else:
                print("  ! table-2 download failed and no existing map", file=sys.stderr)

        yok_universities = load_yok_universities()
        merged = merge_records(records_by_year, yok_universities)

        os.makedirs(DGS_DIR, exist_ok=True)
        table = []
        for code in sorted(merged.keys()):
            m = merged[code]
            table.append({
                "k": code, "ua": m.get("ua", ""), "ui": m.get("ui"),
                "fa": m.get("fa", ""), "bi": m.get("bi", ""),
                "bga": m.get("bga", ""), "pt": m.get("pt", ""),
                "ut": m.get("ut", ""), "bo": m.get("bo", ""),
                "ik": m.get("ik"), "ia": m.get("ia", ""),
                "y": m.get("y", {}),
            })
        with open(os.path.join(DGS_DIR, "dgs-data.json"), "w", encoding="utf-8") as f:
            json.dump(table, f, ensure_ascii=False)
        with open(os.path.join(DGS_DIR, "dgs-onlisans.json"), "w", encoding="utf-8") as f:
            json.dump({
                "onlisans": [{"kod": k, "ad": v}
                             for k, v in sorted(associate.items(),
                                                key=lambda x: x[1].lower())],
                "mapping": transfers,
            }, f, ensure_ascii=False)
        meta = {
            "lastFetchYear": target_years[0],
            "displayYears": target_years,
            "totalPrograms": len(table),
            "onlisansCount": len(associate),
            "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "version": f"{target_years[0]}-{os.urandom(6).hex()}",
        }
        with open(os.path.join(DGS_DIR, "dgs-meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        print(f"DONE: {len(table)} programs, years {target_years}, "
              f"{len(associate)} associate fields -> {DGS_DIR}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("  temp files removed")


if __name__ == "__main__":
    main()
