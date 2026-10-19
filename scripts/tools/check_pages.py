"""Review checks for finished Node pages (or writer JSON), against the Node files.

    python tools/check_pages.py <folder with .md pages or .json writer outputs> [--out review/page_checks.md]

Each page is matched to node_files/<node_uri>.json by file name. The checks mirror
what Joakim looks for in review: dashes, punctuation, banned wording, word counts,
methods the Node does not register, a method attached to a facility that does not
provide it, and junk in the generated tables and lists. Nothing is changed.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
NODE_FILES = HERE / "node_files"
SECTIONS = ["Overview", "Imaging technologies offered", "Specialties and research focus",
            "Services and user support", "Facilities"]
RANGE = {"Overview": (230, 290), "Imaging technologies offered": (180, 240),
         "Specialties and research focus": (150, 200), "Services and user support": (140, 190),
         "Facilities": (180, 240)}
BANNED = re.compile(r"\b(state-of-the-art|cutting-edge|world-class|unique|comprehensive|diverse|robust|seamless(ly)?|"
                    r"wide range|notably|importantly|it is worth noting|most users|listed as|is listed|are listed|strongest|best suited|well suited|suits|natural place|will find|most support|within one node|in one place|recorded|records|registered|according to|is described|are described)\b", re.I)
# (pattern in text, pattern in the Node's technology labels)
METHODS = [
    (r"\bSTED\b", r"STED"), (r"\b(STORM|dSTORM|PALM|DNA-PAINT|single[- ]molecule locali[sz]ation|SMLM)\b", r"SMLM|Single Molecule localization"),
    (r"\bMINFLUX\b", r"MINFLUX"), (r"light[- ]sheet", r"light[- ]?sheet|SPIM"), (r"two[- ]photon|multiphoton", r"Two-photon"),
    (r"\bFLIM\b|lifetime imaging", r"FLIM|Lifetime"), (r"\bFRET\b", r"FRET"), (r"\bFRAP\b", r"FRAP"),
    (r"\bFCS\b|correlation spectroscopy", r"FCS"), (r"\bTIRF\b|total internal reflection", r"TIRF"),
    (r"spinning[- ]dis[ck]", r"Spinning"), (r"structured illumination|\bSIM\b", r"\bSIM\b|Structured"),
    (r"expansion microscopy", r"Expansion"), (r"\bRaman\b", r"Raman"), (r"harmonic generation|\bSHG\b", r"Harmonic"),
    (r"cryo[- ]electron tomography|\bcryo-ET\b", r"Cryo Electron Tomography"), (r"\bFIB-SEM\b", r"FIB"),
    (r"serial block[- ]face", r"Serial Blockface"), (r"array tomography", r"Array tomography"),
    (r"\bCLEM\b|correlative light and electron", r"CLEM|Correlative"), (r"atomic force", r"Atomic Force"),
    (r"intravital", r"ntravital"), (r"\bSPECT\b", r"SPECT"), (r"\bPET\b", r"PET"), (r"\bMEG\b", r"MEG"),
    (r"optical coherence tomography|\bOCT\b", r"OCT"), (r"photoacoustic", r"hotoacoustic|PAI"),
    (r"mass spectrometry imaging|\bMALDI\b", r"Mass spectrometry"), (r"micro-?CT\b", r"CT"),
    (r"high[- ]content screening", r"high content|HTM"), (r"\bMRI\b|magnetic resonance", r"MRI|MRS"),
    (r"\bultrasound\b", r"\bUS\b|ultrasound"), (r"\bEEG\b", r"EEG"),
    (r"elemental analysis|\bEDX\b|\bEDS\b", r"EDX|Elemental"),
]
TABLE_JUNK = re.compile(r"(?i:documented|configuration|Named systems|inventory:|as detailed|Site scope|Partial list|"
                        r"historical|\(per )|TECHNICAL_CONTACT|INTERNAL|SQ\d")


def ai_sections(md: str) -> dict[str, str]:
    """The written text of each section, without the generated tables and lists."""
    out = {}
    for title in SECTIONS:
        m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", md, re.M | re.S)
        if not m:
            continue
        body = m.group(1)
        body = re.split(r"^### ", body, maxsplit=1, flags=re.M)[0]
        body = "\n".join(l for l in body.splitlines() if not l.startswith("|"))
        out[title] = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body).strip()  # links count as their text
    return out


def sentences(text: str) -> list[str]:
    return [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if x.strip()]


def check(name: str, secs: dict[str, str], md: str, doc: dict) -> list[str]:
    b = doc["node_briefing"]
    techs = [t for g in b["technologies_by_category"] for t in g["technologies"]]
    labels = [t["label"] for t in techs]
    facs = [f["short_name"] for f in b["facilities"]]
    flags = []
    for title in SECTIONS:
        if title not in secs:
            flags.append(f"{title}: missing")
    for title, text in secs.items():
        n = len(text.split())
        lo, hi = (80, 160) if title == "Facilities" and len(facs) == 1 else RANGE[title]
        if n < lo * 0.9 or n > hi * 1.1:
            flags.append(f"{title}: {n} words (aim {lo} to {hi})")
        for ch, what in ((";", "semicolons"), (":", "colons")):
            if text.count(ch) > 1:
                flags.append(f"{title}: {text.count(ch)} {what}")
        if re.search("[—–]", text):
            flags.append(f"{title}: dash used as punctuation")
        for w in sorted({m.group(0).lower() for m in BANNED.finditer(text)}):
            flags.append(f"{title}: wording '{w}'")
        for pat, lab in METHODS:
            m = re.search(pat, text, re.I if pat.islower() else 0)
            if m and not any(re.search(lab, l, re.I) for l in labels):
                flags.append(f"{title}: '{m.group(0)}' is not registered for this Node")
        # A sentence that names exactly one facility and a method that facility does not provide.
        for sent in sentences(text):
            named = [f for f in facs if re.search(rf"(?<![\w-]){re.escape(f)}(?![\w-])", sent)]
            if len(named) != 1:
                continue
            for pat, lab in METHODS:
                if not re.search(pat, sent, re.I if pat.islower() else 0):
                    continue
                rows = [t for t in techs if re.search(lab, t["label"], re.I)]
                if rows and not any(named[0] in (t.get("provided_by") or []) for t in rows):
                    flags.append(f"{title}: '{named[0]}' with '{re.search(pat, sent, re.I).group(0)}', "
                                 f"which it does not provide: \"{sent[:140]}\"")
    if md:
        for line in md.splitlines():
            if line.startswith("|") or line.startswith("- ") or line.startswith("Contact:") or line.startswith("**"):
                m = TABLE_JUNK.search(line)
                if m:
                    flags.append(f"generated part: '{m.group(0)}' in: {line[:120]}")
            if re.match(r"\s*Access:", line):
                flags.append("generated part: Access line")
            if line.strip() == "- Instruments":
                flags.append("generated part: bare 'Instruments' service")
        if re.search(r"\]\(https://www\.eurobioimaging-access\.eu/nodes/[^)]*\)\s*\|", md):
            flags.append("generated part: a facility links to the Access Portal page")
    return flags


def main() -> None:
    src = Path(sys.argv[1])
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    lines = [f"# Page checks ({src.name})", ""]
    total = 0
    for p in sorted(src.glob("*.md")) + sorted(src.glob("*.json")):
        key = re.sub(r"^[0-9a-f]{8}-", "", p.stem)
        key = re.sub(r"(_v1[01]|_v\d+|\d)$", "", key)
        nf = NODE_FILES / f"{key}.json"
        if not nf.exists():
            cands = [x for x in NODE_FILES.glob("*.json") if x.stem.startswith(key[:20])]
            if not cands:
                lines.append(f"## {p.name}\n\nNo Node file found for '{key}'.\n")
                continue
            nf = cands[0]
        doc = json.loads(nf.read_text(encoding="utf-8-sig"))
        if p.suffix == ".json":
            data = json.loads(p.read_text(encoding="utf-8-sig"))
            secs = {s["section_title"]: s["section_text"] for s in data["sections"]}
            md = ""
        else:
            md = p.read_text(encoding="utf-8-sig")
            secs = ai_sections(md)
        flags = check(p.name, secs, md, doc)
        total += len(flags)
        lines.append(f"## {p.name} ({len(flags)} flags)\n")
        lines += [f"- {f}" for f in flags] or ["- no flags"]
        lines.append("")
    text = "\n".join(lines)
    if out:
        out.parent.mkdir(exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nTotal flags: {total}")


if __name__ == "__main__":
    main()
