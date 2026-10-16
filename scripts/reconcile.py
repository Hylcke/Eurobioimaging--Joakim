"""Check the older August Node profile against the Knowledge Base Master.

The August master (EuBI_Master_Nodes_and_Facilities_v1.xlsx) has Node-level text
the Knowledge Base does not: a short description, specialties, featured
technologies, services and instrument highlights. It is older. The Knowledge
Base is current, so where the two disagree the Knowledge Base wins:

- a sentence that gives a facility, institution or city count the master does
  not support, names a city where the Node has no facility, or names a
  technology the Node does not offer is left out;
- a featured technology or technology area the Node does not offer is left out;
- an instrument whose model names are not found in the master's facility
  records is left out;
- services are passed on as they are (the master never says a service is not
  offered, so they cannot contradict it);
- August's structure, imaging domain and counts are not passed on at all; they
  are derived from the master.

Everything left out is returned as a review line for the "Missing information"
block, so nothing disappears silently.
"""
from __future__ import annotations

import re

NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
       "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
       "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
COUNT_RE = re.compile(r"\b(\d{1,3}|" + "|".join(NUM) + r")\s+(?:[A-Za-z-]+\s+){0,2}?"
                      r"(facilities|facility|units|platforms|centres|centers|core facilities|labs|laboratories|"
                      r"institutions|host institutions|partners|partner institutions|universities|"
                      r"cities|locations|sites|hubs)\b", re.I)
FAMILY_WORDS = {
    "light microscopy": r"light microscop|optical microscop|fluorescen|confocal|super-?resolution|nanoscop|"
                        r"light-?sheet|intravital|multiphoton|two-photon",
    "electron microscopy": r"electron microscop|\bcryo-?EM\b|\bTEM\b|\bSEM\b|\bFIB|volume EM",
    "correlative light and electron microscopy": r"correlative|\bCLEM\b",
    "preclinical imaging": r"preclinical|pre-clinical|small[- ]animal|micro-?(?:CT|PET|MRI|SPECT|US)\b",
    "clinical and human imaging": r"clinical imaging|human imaging|medical imaging|\bclinical\b",
}
IGNORE_CATEGORIES = {"Biological Image Data Services", "Medical Image Data services"}
STOP = set("""and the for with from into onto that this these those their its are was were has have had can may
also such other more most well very within across including include includes based using use used offer offers
offered provide provides provided provision available availability support supports supporting service services
access user users node nodes facility facilities platform platforms core unit units project projects range wide
dedicated specific specialised specialized advanced high state art level expert expertise""".split())
VENDORS = {"zeiss", "leica", "nikon", "olympus", "evident", "andor", "oxford", "abberior", "bruker", "jeol", "fei",
           "thermo", "fisher", "scientific", "hitachi", "tescan", "gatan", "siemens", "philips", "ge", "mediso",
           "perkinelmer", "perkin", "elmer", "visualsonics", "fujifilm", "miltenyi", "lavision", "yokogawa",
           "hamamatsu", "picoquant", "becker", "hickl", "agilent", "canon", "toshiba", "keyence", "healthcare"}


def s(v) -> str:
    return "" if v is None else str(v).strip()


def split_items(text: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in s(text):
        depth += ch in "(["
        depth -= ch in ")]" and depth > 0
        if ch in ";\n" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip(" .,-•\t") for p in parts if p.strip(" .,-•\t")]


def sentences(text: str) -> list[str]:
    return [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", s(text)) if x.strip()]


class Catalogue:
    """Technology names and abbreviations from the Technologies sheet."""

    def __init__(self, techs: dict[str, dict]):
        self.terms: list[tuple[re.Pattern, str]] = []
        for uri, t in techs.items():
            if s(t.get("category_name")) in IGNORE_CATEGORIES:
                continue
            label = s(t.get("technology_name")).replace("*", "").strip()
            base = re.sub(r"\s*\([^)]*\)", "", label).strip()
            if len(base) >= 8:
                self.terms.append((re.compile(r"\b" + re.escape(base) + r"\b", re.I), uri))
            abbrs = re.findall(r"\(([^)]*)\)", label) + [s(t.get("abbreviation"))]
            for a in abbrs:
                for part in re.split(r"[/,]| - ", a):
                    part = part.strip()
                    if len(part) >= 3 and re.search(r"[A-Z]{2}", part) and " " not in part:
                        self.terms.append((re.compile(r"(?<![\w-])" + re.escape(part) + r"(?![\w-])"), uri))

    def mentions(self, text: str) -> dict[str, set[str]]:
        """{matched text: technology URIs it can mean}."""
        out: dict[str, set[str]] = {}
        for pat, uri in self.terms:
            for m in pat.finditer(text):
                out.setdefault(m.group(0), set()).add(uri)
        return out

    def missing(self, text: str, node_techs: set[str]) -> list[str]:
        """Technology names in text that the Node does not offer."""
        return sorted(k for k, uris in self.mentions(text).items() if not uris & node_techs)


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9+-]*", text.lower()) if len(w) >= 4 and w not in STOP}


def model_tokens(text: str) -> set[str]:
    """Words that identify an instrument model rather than a modality or maker."""
    toks = set()
    for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9.+-]*", text):
        lw = w.lower().strip(".-")
        if lw in VENDORS or lw in STOP or len(lw) < 2:
            continue
        if UNIT.fullmatch(lw):
            continue
        if (re.search(r"\d", w) and re.search(r"[A-Za-z]", w)) or re.fullmatch(r"[A-Z][a-z]+[A-Z][A-Za-z]*", w):
            toks.add(lw)
    return toks


UNIT = re.compile(r"\d+(?:[.,]\d+)?(?:t|tesla|kv|nm|mm|um|\u00b5m|cm|x|d|k|mhz|ghz|hz|w|mw|ms|fps|st|nd|rd|th|"
                 r"gb|tb|h|min|s|l|ml)(?:-\w+)?")
NOT_CITIES = re.compile(r"multi|site|various|several|online|virtual|remote|distributed|national|region", re.I)
COMMON_CAPS = {"clinical", "preclinical", "imaging", "microscopy", "microscope", "microscopes", "confocal",
               "electron", "light", "super", "resolution", "spinning", "scanner", "scanners", "system", "systems",
               "multiphoton", "widefield", "lightsheet", "light-sheet", "cryo", "transmission", "scanning",
               "optical", "ultrasound", "magnetic", "resonance", "tomography", "human", "animal", "small",
               "high-field", "field", "research", "dedicated", "platform", "facility", "facilities", "several",
               "multiple", "various", "advanced", "intravital", "correlative", "focused", "beam", "access"}


def reconcile(aug: dict, ctx: dict, cat: Catalogue) -> tuple[dict, list[str]]:
    """Return (clean August profile, review lines).

    ctx: node_techs (set of technology URIs), families (list), n_facilities, n_institutions,
         n_cities, cities (list), other_cities (set of every master city), instrument_corpus,
         service_corpus (lower-case text).
    """
    review: list[str] = []
    node_techs = ctx["node_techs"]

    def bad_sentence(sent: str) -> str:
        for m in COUNT_RE.finditer(sent):
            raw, what = m.group(1).lower(), m.group(2).lower()
            n = int(raw) if raw.isdigit() else NUM[raw]
            if re.match(r"(institution|host|partner|universit)", what):
                ok = {ctx["n_institutions"]}
            elif re.match(r"(cities|locations|sites|hubs)", what):
                ok = {ctx["n_cities"], ctx["n_institutions"], ctx["n_facilities"]}
            else:
                ok = {ctx["n_facilities"]}
            if n not in ok:
                return f"says {m.group(0)}; the master has {ctx['n_facilities']} facilities, " \
                       f"{ctx['n_institutions']} institutions, {ctx['n_cities']} cities"
        here = " ".join(ctx["cities"]).lower()
        for c in ctx["other_cities"]:
            if NOT_CITIES.search(c) or len(c) < 4:
                continue
            if c.lower() not in here and re.search(rf"\b{re.escape(c)}\b", sent):
                return f"names {c}, where the Node has no facility in the master"
        gone = cat.missing(sent, node_techs)
        if gone:
            return f"names {', '.join(gone)}, not offered by the Node in the master"
        return ""

    def clean_text(field: str, label: str) -> str:
        keep = []
        for sent in sentences(aug.get(field)):
            why = bad_sentence(sent)
            if why:
                review.append(f"Older August {label}, left out: \"{sent[:160]}\" ({why})")
            else:
                keep.append(sent)
        return " ".join(keep)

    out = {"short_description": clean_text("Short public description", "description"),
           "node_specialties": clean_text("Specialties / expertise", "specialties")}

    feat = []
    for item in split_items(aug.get("Featured technologies / capabilities")):
        gone = cat.missing(item, node_techs)
        if gone and len(gone) == len(cat.mentions(item)):
            review.append(f"Older August featured technology, left out: \"{item[:120]}\" (not offered by the Node in the master)")
        else:
            feat.append(item)
    areas = []
    for item in split_items(aug.get("Main technology areas")):
        named = {fm for fm, rx in FAMILY_WORDS.items() if re.search(rx, item, re.I)}
        if named and not named & set(ctx["families"]):
            review.append(f"Older August technology area, left out: \"{item[:120]}\" (no such technologies in the master)")
        else:
            areas.append(item)
    inst = []
    corpus = ctx["instrument_corpus"]
    for item in split_items(aug.get("Instrument / platform highlights")):
        toks = model_tokens(item)
        gone = cat.missing(item, node_techs)
        if toks and not any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", corpus) for t in toks):
            review.append(f"Older August instrument, left out: \"{item[:140]}\" (model not found in the master's facility records)")
        elif gone and len(gone) == len(cat.mentions(item)):
            review.append(f"Older August instrument, left out: \"{item[:140]}\" (technology not offered by the Node in the master)")
        else:
            inst.append(item)
    # Services: the master does not record what a Node does NOT offer, so an older
    # service cannot contradict it. They are passed on as background.
    serv = split_items(aug.get("Services / support"))
    out["profile"] = {k: v for k, v in (("main_technology_areas", "; ".join(areas)),
                                        ("featured_technologies", "; ".join(feat)),
                                        ("services_support", "; ".join(serv)),
                                        ("instrument_highlights", "; ".join(inst))) if v}
    return out, review
