"""Link a facility's named instruments to the technologies it provides.

Two routes, both conservative:
  1. Direct: Evidence rows that already name the technology (technique_uri) and
     the instrument set-up for that facility.
  2. By name: an instrument from the facility's own records is linked to one of
     that facility's technologies only if the instrument text contains a
     recognised name for it (the technology's abbreviation, or a keyword below,
     such as "spinning disk", "Dragonfly" or "SoRa" for spinning disk confocal).

An instrument is never linked to a technology the facility does not provide in
the master, and nothing is inferred beyond the words in the record.
"""
from __future__ import annotations

import re

# Keywords that identify instruments of a technology (case-insensitive, whole words
# unless the keyword contains a space or hyphen). Abbreviations come from the master.
KEYWORDS: dict[str, list[str]] = {
    "laser-scanning-confocal-microscopy-lscm-clsm": ["confocal", "LSM", "SP5", "SP8", "Stellaris", "FV1000", "FV3000",
                                                     "FluoView", "Airyscan", "A1R", "AX R", "Nikon A1", "TCS", "Zeiss LSM",
                                                     "Leica SP", "Olympus FV", "NSPARC", "AX R"],
    "spinning-disk-confocal-microscopy-sdcm": ["spinning disk", "spinning disc", "spinning-disk", "spinning-disc", "CSU",
                                               "Dragonfly", "SoRa", "SpinSR", "X-Light", "Yokogawa", "CV1000", "CQ1",
                                               "UltraVIEW"],
    "deconvolution-widefield-microscopy-dwm": ["widefield", "wide-field", "deconvolution", "DeltaVision", "THUNDER",
                                               "Thunder", "Axio Observer", "Ti2", "Ti-E", "IX83", "IX81", "DMi8"],
    "total-internal-reflection-fluorescence-microscopy-tirf": ["TIRF", "total internal reflection"],
    "two-photon-microscopy-2p": ["two-photon", "2-photon", "multiphoton", "multi-photon", "2P", "Ultima", "TriM",
                                 "Femto2D", "FEMTO3D", "Femtonics", "SP8 MP", "LSM 7 MP", "Bergamo", "Trimscope"],
    "structured-illumination-microscopy-sim": ["SIM", "structured illumination", "Elyra", "N-SIM", "OMX", "DeepSIM",
                                               "Lattice SIM"],
    "stimulated-emission-depletion-microscopy-sted": ["STED", "TauSTED", "STEDYCON", "Facility Line"],
    "single-molecule-localization-microscopy-smlm": ["SMLM", "STORM", "dSTORM", "PALM", "N-STORM", "PAINT", "ONI",
                                                     "Nanoimager", "SAFe", "Vutara", "Elyra 7"],
    "minimal-photon-fluxes-microscopy-minflux": ["MINFLUX"],
    "expansion-microscopy-exm": ["expansion"],
    "image-scanning-microscopy-ism": ["ISM", "Airyscan", "NSPARC", "image scanning", "Re-scan", "RCM"],
    "random-illumination-microscopy-rim": ["RIM", "random illumination"],
    "super-resolution-radial-fluctuations-srrf": ["SRRF"],
    "lattice-light-sheet-lls": ["lattice light-sheet", "lattice lightsheet", "LLS7", "Lattice Lightsheet"],
    "light-sheet-mesoscopic-imaging-spim-dslsm": ["light-sheet", "lightsheet", "light sheet", "SPIM", "mesoSPIM",
                                                  "UltraMicroscope", "Lightsheet 7", "Z.1", "LaVision", "Blaze",
                                                  "Alpha3", "SmartSPIM", "Viventis", "MuVi", "Luxendo"],
    "optical-projection-tomography-opt": ["OPT", "optical projection"],
    "fluorescence-lifetime-imaging-flim": ["FLIM", "lifetime", "FALCON", "PicoQuant", "TCSPC", "Becker"],
    "phosphorescence-lifetime-imaging-plim": ["PLIM"],
    "fluorescence-cross-correlation-spectroscopy-fcs-fccs": ["FCS", "FCCS", "correlation spectroscopy"],
    "fluorescence-resonance-energy-transfer-fret": ["FRET"],
    "fluorescence-recovery-after-photobleaching-frap": ["FRAP"],
    "high-throughput-microscopy-high-content-screening-htm-hcs": ["high-content", "high content", "high-throughput",
                                                                  "Opera", "Operetta", "ImageXpress", "CellInsight",
                                                                  "ScanR", "CellVoyager", "Incucyte", "Cytation",
                                                                  "Celldiscoverer", "CellDiscoverer"],
    "imaging-flow-cytometry-ifc": ["ImageStream", "imaging flow", "FlowSight"],
    "second-third-harmonic-generation-shg-thg": ["SHG", "THG", "harmonic"],
    "coherent-anti-stokes-raman-scattering-microscopy-cars": ["CARS"],
    "stimulated-raman-scattering-srs": ["SRS", "stimulated Raman"],
    "raman-spectroscopy-rs": ["Raman", "WITec", "inVia", "alpha300"],
    "fourier-transform-infrared-imaging-ftir": ["FTIR", "infrared"],
    "brillouin-scattering-microscopy-bsm": ["Brillouin"],
    "quantitative-phase-imaging-qpi": ["phase imaging", "holotomograph", "Nanolive", "Tomocube", "holographic", "QPI"],
    "polarization-microscopy-pm": ["polarization", "polarisation", "polarized", "polarised"],
    "intravital-microscopy-ivm": ["intravital", "IVM"],
    "intravital-microscopy-ivm-med": ["intravital", "IVM"],
    "photomanipulation-pmanip": ["photomanipulation", "photoactivation", "ablation", "uncaging", "FRAPPA", "Mosaic"],
    "microdissection-mdis": ["microdissection", "LMD", "PALM MicroBeam", "MMI CellCut"],
    "multiplexing-imaging-mxi": ["CODEX", "PhenoCycler", "multiplex", "COMET", "MACSima", "CellDIVE", "Akoya"],
    "spatial-transcriptomics-st": ["Visium", "Xenium", "MERSCOPE", "CosMx", "spatial transcriptomics"],
    "atomic-force-microscopy-afm": ["AFM", "atomic force", "NanoWizard", "JPK", "Cypher"],
    "traction-force-microscopy-tfm": ["traction force"],
    "mass-spectrometry-based-imaging-msi-bio": ["MALDI", "mass spectrometry", "DESI", "timsTOF", "imaging MS"],
    "mass-spectrometry-based-imaging-msi-med": ["MALDI", "mass spectrometry", "DESI", "timsTOF", "imaging MS"],
    "secondary-ion-mass-spectrometry-with-mev-ions-mev-sims": ["SIMS"],
    "micro-x-ray-fluorescence-spectrometry-xrf": ["XRF", "X-ray fluorescence"],
    "tem-of-chemical-fixed-samples-tem": ["TEM", "transmission electron", "Tecnai", "Talos", "JEM", "JEOL", "Morgagni",
                                          "Libra", "Hitachi HT", "Spirit", "Tecnai"],
    "tem-of-cryo-immobilized-samples-tem-cryo-samples": ["high-pressure freez", "HPF", "freeze substitution", "AFS",
                                                         "EM ICE", "HPM", "Leica EM ICE", "EM PACT"],
    "tem-of-immobilized-particles-tem-neg-stain": ["negative stain", "TEM", "Talos L120C", "Tecnai Spirit"],
    "cryo-transmission-electron-microscopy-cryo-tem": ["cryo-TEM", "cryo-EM", "Krios", "Glacios", "Talos Arctica",
                                                       "Arctica", "Titan", "CRYO ARM", "K3", "Tundra"],
    "cryo-electron-tomography-cryo-et": ["cryo-ET", "cryo-electron tomography", "Krios", "Titan"],
    "cryo-focussed-ion-beam-cryo-fib": ["cryo-FIB", "Aquilos", "Arctis", "Amber Cryo", "Hydra", "cryo FIB"],
    "cryo-scanning-electron-microscop-cryo-sem": ["cryo-SEM", "cryo SEM", "PP3010", "ACE600"],
    "cryo-fluorescence-microscopy-cryofm": ["cryo-fluorescence", "CryoFM", "cryo-CLEM", "THUNDER Imager EM Cryo",
                                            "Linkam", "iFLM", "METEOR"],
    "scanning-electron-microscopy-sem": ["SEM", "scanning electron", "Gemini", "Sigma", "Merlin", "Apreo", "Quanta",
                                         "Quattro", "Phenom", "Verios", "Teneo"],
    "focussed-ion-beam-sem-fib-sem": ["FIB", "FIB-SEM", "Crossbeam", "Helios", "Scios", "Auriga", "Amber"],
    "serial-blockface-sem-sbf-sem": ["3View", "serial block", "SBF", "VolumeScope", "SBEM", "block-face", "blockface"],
    "array-tomography-at": ["array tomography", "ATUMtome", "ATUM"],
    "serial-section-tem-sstem": ["serial section", "ssTEM"],
    "em-tomography-et": ["tomography", "electron tomography", "ET"],
    "stem-tomography-stem": ["STEM"],
    "large-scale-em-lstem": ["large-scale", "large scale", "montage", "lsTEM"],
    "elemental-analysis-edx": ["EDX", "EDS", "energy-dispersive", "energy dispersive"],
    "immuno-gold-em-on-thawed-cryo-sections-tokuyasu-em": ["Tokuyasu", "cryo-ultramicrotome", "cryo ultramicrotome",
                                                           "UC7 FC7", "EM FC7"],
    "immuno-gold-em-on-resin-sections-resin-em": ["immunogold", "immuno-gold", "ultramicrotome", "UC7"],
    "correlative-array-tomography-cat": ["array tomography", "ATUM"],
    "micro-ct": ["micro-CT", "microCT", "µCT", "SkyScan", "Quantum GX", "Quantum FX", "U-CT", "Albira CT", "CT"],
    "ex-vivo-micro-ct": ["micro-CT", "microCT", "µCT", "SkyScan", "Zeiss Xradia", "Xradia", "CT"],
    "micro-mri-mrs-gte-7t": ["BioSpec", "PharmaScan", "9.4 T", "9.4T", "7 T", "7T", "11.7", "14.1", "Bruker MRI"],
    "micro-mri-mrs-lt-7t": ["ICON", "1 T", "1T", "3 T", "3T", "4.7 T", "4.7T", "MRS 3000"],
    "micro-mri-mrs-gte-7t-ex-vivo": ["BioSpec", "9.4 T", "9.4T", "11.7", "14.1", "NMR"],
    "micro-mri-mrs-lt-7t-ex-vivo": ["ICON", "1 T", "3 T", "4.7 T"],
    "micro-pet": ["PET", "β-CUBE", "beta-CUBE"],
    "micro-pet-ct": ["PET/CT", "PET-CT"],
    "micro-pet-mri": ["PET/MR", "PET-MR", "PET insert", "PET-Insert", "nanoScan PET/MR"],
    "micro-spect": ["SPECT", "U-SPECT", "VECTor", "Inveon SPECT"],
    "micro-spect-ct": ["SPECT/CT", "SPECT-CT", "U-SPECT", "VECTor", "Inveon SPECT/CT"],
    "micro-us": ["ultrasound", "Vevo", "US system"],
    "in-vivo-optical-imaging-oi": ["IVIS", "Lago", "BLI", "bioluminescence", "fluorescence imaging system", "FMT",
                                   "Pearl", "Spectrum"],
    "photoacoustic-imaging-pai-med": ["photoacoustic", "optoacoustic", "MSOT", "Vevo LAZR", "LAZR"],
    "photoacoustic-imaging-pai-bio": ["photoacoustic", "optoacoustic", "MSOT"],
    "magnetic-particle-imaging-mpi-1": ["MPI", "magnetic particle"],
    "magnetic-particle-imaging-mpi-ex-vivo": ["MPI", "magnetic particle"],
    "mri-mrs-gte-7t": ["7T", "7 T", "7-Tesla", "Terra", "Magnetom Terra", "Philips 7T"],
    "mri-mrs-lt-7t": ["1.5T", "1.5 T", "3T", "3 T", "Prisma", "Skyra", "Ingenia", "Achieva", "Signa", "Vida"],
    "pet": ["PET", "Biograph", "Discovery MI"],
    "pet-ct": ["PET/CT", "PET-CT", "Biograph", "Discovery MI"],
    "pet-mri-1": ["PET/MR", "PET-MR", "PET/MRI", "Biograph mMR", "Signa PET"],
    "magnetoencephalography-meg-1": ["MEG", "magnetoencephalograph"],
    "laser-speckle-imaging": ["laser speckle", "speckle", "moorFLPI", "PeriCam"],
    "correlated-optical-coherence-tomography-photoacoustic-tomography-oct-pat": ["OCT", "PAT", "optical coherence"],
    "terahertz-plant-imaging-thzi": ["terahertz", "THz"],
    "imaging-for-plant-phenotyping-pheno": ["phenotyping", "PlantScreen", "Scanalyzer", "phenomics"],
    "plant-phenotyping-phenoplant": ["phenotyping", "PlantScreen", "Scanalyzer", "phenomics"],
    "long-term-vertical-stage-confocal-airyscan-microscopy": ["vertical", "root tracker", "vertical stage"],
    "high-speed-imaging-hsi": ["high-speed", "high speed", "Kinetix", "Prime 95B", "ORCA-Lightning"],
    "voltage-ph-ion-imaging": ["voltage", "calcium imaging", "ratiometric"],
    "tissue-clearing-tc": ["clearing", "SmartClear", "X-CLARITY", "CLARITY"],
}
# Instrument text that rules a technology out even when a keyword matches.
EXCLUDE = {
    "laser-scanning-confocal-microscopy-lscm-clsm": re.compile(r"spinning|SoRa|Dragonfly|CSU|Yokogawa|Raman|inVia", re.I),
    "tem-of-chemical-fixed-samples-tem": re.compile(r"cryo|Krios|Glacios|Arctica|Aquilos", re.I),
    "micro-pet": re.compile(r"^(?!.*PET).*$", re.I),
    "em-tomography-et": re.compile(r"PET|SPECT|CT\b|optical|projection|coherence", re.I),
    # human imaging rows never take animal scanners, and preclinical rows never take clinical ones
    "mri-mrs-lt-7t": re.compile(r"rodent|small[- ]animal|preclinical|Biospec|PharmaScan|ICON|mouse|mice|\brats?\b", re.I),
    "mri-mrs-gte-7t": re.compile(r"rodent|small[- ]animal|preclinical|Biospec|PharmaScan|mouse|mice|\brats?\b", re.I),
    "pet": re.compile(r"rodent|small[- ]animal|preclinical|nanoScan|Inveon|Albira|β-CUBE", re.I),
    "pet-mri-1": re.compile(r"rodent|small[- ]animal|preclinical|nanoScan|insert", re.I),
    "pet-ct": re.compile(r"rodent|small[- ]animal|preclinical|nanoScan|Inveon|Albira|mMR|PET[- ]?MR", re.I),
    "micro-pet-ct": re.compile(r"mMR|PET[- ]?MR|Prisma|Achieva|clinical", re.I),
}
_CLINICAL_MRI = re.compile(r"(?<!pre)(?<!pre-)clinical|human|national|hospital|Prisma|Skyra|Terra|Achieva|Ingenia|Signa|Vida|Magnetom", re.I)
for _u in ("micro-mri-mrs-gte-7t", "micro-mri-mrs-lt-7t", "micro-mri-mrs-gte-7t-ex-vivo", "micro-mri-mrs-lt-7t-ex-vivo"):
    EXCLUDE.setdefault(_u, _CLINICAL_MRI)
# Hybrid systems named by their parts, e.g. "Albira CT/PET/SPECT" counts as PET/CT and SPECT/CT.
COMBO = {"micro-pet-ct": ["PET", "CT"], "micro-spect-ct": ["SPECT", "CT"], "micro-pet-mri": ["PET", "MRI?"],
         "pet-ct": ["PET", "CT"], "spect-ct": ["SPECT", "CT"]}


def _field_ok(uri: str, inst: str) -> bool:
    """MRI field strength must match the technology (below or at least 7 tesla)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:T|tesla)\b", inst)
    if not m or "mri" not in uri:
        return True
    field = float(m.group(1).replace(",", "."))
    if "lt-7t" in uri:
        return field < 7
    if "gte-7t" in uri:
        return field >= 7
    return True


_ABBR_SKIP = {"SP", "TC", "PM", "AM", "ST", "OI", "AT", "ET", "RS", "US", "MPI", "PCI"}


def _terms(uri: str, tech: dict) -> list[str]:
    terms = list(KEYWORDS.get(uri, []))
    abbr = (tech.get("abbreviation") or "").strip()
    for a in re.split(r"[/;,]", abbr):
        a = a.strip()
        if len(a) >= 3 and a.upper() not in _ABBR_SKIP and not a.startswith(("<", ">", "Field")):
            terms.append(a)
    return terms


def _hit(term: str, text: str) -> bool:
    if " " in term or "-" in term or "/" in term or not term.isalnum():
        return term.lower() in text.lower()
    if term.isupper() or any(ch.isdigit() for ch in term):  # abbreviations and model codes: exact case, whole word
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text) is not None
    return re.search(rf"\b{re.escape(term)}", text, re.I) is not None


def _split_top(text: str) -> list[str]:
    """Split on ';' and line breaks that are not inside brackets."""
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch in ";\n" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def facility_instruments(fac: dict, facts: list[dict]) -> list[str]:
    """Named instruments of one facility, from structured facts and its instruments field."""
    out = []
    for e in facts:
        if e["kind"] != "instrument_model":
            continue
        name = e["instrument"]
        maker_model = " ".join(x for x in (e["manufacturer"], e["model"]) if x)
        label = name if not maker_model or maker_model in name else f"{name} ({maker_model})"
        label = re.sub(r"^Documented instrument/platform family:\s*", "", label).strip().rstrip(".")
        label = re.sub(r"\s+at\s+[A-Z].*$", "", label)  # "SP8 at Advanced Light Microscopy (ALM)..." -> "SP8"
        if label and label not in out:
            out.append(label)
    raw = str(fac.get("instruments") or "")
    # "platform-level named (9.4T preclinical MRI; 1.5/3T clinical MRI)" -> the named items
    raw = re.sub(r"[^;]*?\bnamed\s*\(([^()]*)\)[^;]*", lambda m: m.group(1), raw)
    parts = []
    for part in _split_top(raw):
        parts += part.split(";") if "(" not in part else [part]
    parts = [p for part in parts for p in split_models(normalise_makers(part.strip()))]
    for part in parts:
        part = re.sub(r"\([^)]*named in news[^)]*\)", "", part).strip(" .")
        part = re.sub(r"\s*\([^()]*\bper\b[^()]*\)", "", part)  # "(at ALM, per KTH: ...)"
        part = re.sub(r"^(The facility|It)\s+(hosts|has|operates|runs)\s+(an?|the)\s+", "", part, flags=re.I)
        part = re.sub(r",\s*plus\b.*$", "", part).strip(" .,")
        part = re.sub(r"^(Per [^:]{3,60}|Provider-documented models/configurations|Named instruments?):\s*", "", part)
        part = re.sub(r"\s+and (additional|other)\b.*$", "", part).strip(" .,")
        if part.count("(") != part.count(")"):
            continue
        if 3 <= len(part) <= 140 and not re.search(
                r"otherwise|not enumerated|not listed|not itemi[sz]ed|platform-level|sub-?pages|as above|per registry",
                part, re.I):
            part = re.sub(r"^Provider-documented models/configurations:\s*", "", part)
            if part and part not in out:
                out.append(part)
    return out


MAKER_NAMES = [(r"\bThermo ?Fisher Scientific\b|\bThermoFisher\b|\bThermo Scientific\b|\bTFS\b", "Thermo Fisher"),
               (r"\bZEISS\b", "Zeiss"), (r"\bSCANCO\b", "Scanco"), (r"\bXRadia\b", "Xradia"), (r"\bMEDISO\b", "Mediso"),
               (r"\bSTELLARIS\b", "Stellaris"), (r"\bLEICA\b", "Leica"), (r"\bNIKON\b", "Nikon"),
               (r"\bSARTORIUS\b", "Sartorius"), (r"\bEVIDENT\b", "Evident"), (r"\bOLYMPUS\b", "Olympus"),
               (r"\bBRUKER\b", "Bruker"), (r"\bHITACHI\b", "Hitachi")]


def normalise_makers(t: str) -> str:
    """One spelling per maker, and "Micro-CT, SCANCO, µCT35" -> "Scanco µCT35"."""
    t = t.strip()
    # "Micro-CT — SCANCO — µCT35" (type, maker, model) -> "SCANCO µCT35"
    t = re.sub(r"^[^\u2014;]{2,60}?\s*\u2014\s*([^\u2014;]+?)\s*\u2014\s*([^\u2014;]+)$", r"\1 \2", t)
    t = re.sub(r"[\u2010\u2011\u2012\u2013\u2212]", "-", t)
    for pat, rep_ in MAKER_NAMES:
        t = re.sub(pat, rep_, t)
    return re.sub(r"(?:^|(?<=, ))(?i:micro-?CT|[a-z -]*microscope|[a-z -]*scanner),\s*"
                  r"(Zeiss|Scanco|Leica|Nikon|Olympus|Bruker|Thermo Fisher|Xradia),\s*", r"\1 ", t)


MODEL_WORDS = re.compile(r"\b(Bio[Ss]pec|Pharma[Ss]can|ICON|Avance|Albira|Inveon|nanoScan|NanoScan|Biograph|Vevo|"
                         r"Krios|Glacios|Talos|Tecnai|Morgagni|Aquilos|Lightsheet|Stellaris|Elyra|ELYRA|Airyscan)\b")
FIELD = re.compile(r"\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?\s*(?:T|Tesla)\b")


def _model_signal(t: str) -> bool:
    """Names a maker or model: a model number (not just a field strength), a maker, or a product name."""
    return bool(re.search(r"\d", FIELD.sub("", t)) or VENDORS.search(t) or MODEL_WORDS.search(t) or _named_model(t))


def split_models(t: str) -> list[str]:
    """"Talos L120c with EDX, Tecnai G2 Spirit Biotwin and JEM-1400 Flash" -> three instruments, so each
    is matched to its own technology. Commas inside brackets do not split."""
    pieces, depth, cur, i = [], 0, "", 0
    while i < len(t):
        ch = t[i]
        depth += ch in "(["
        depth -= ch in ")]" and depth > 0
        if depth == 0 and (t.startswith(", ", i) or t.startswith(" and ", i)):
            pieces.append(cur)
            cur = ""
            i += 2 if t.startswith(", ", i) else 5
            continue
        cur += ch
        i += 1
    pieces.append(cur)
    pieces = [re.sub(r"^(?:[a-z][\w-]*\s+)+(?=[A-Z0-9])", "", p.strip()) for p in pieces if p.strip()]
    # only split when every piece names a model; otherwise keep the text whole
    return pieces if len(pieces) > 1 and all(_model_signal(p) for p in pieces) else [t]


def instruments_by_technology(fac: dict, facts: list[dict], tech_uris: list[str], techs: dict) -> dict[str, list[str]]:
    """{technology_uri: [instrument, ...]} for one facility."""
    res: dict[str, list[str]] = {u: [] for u in tech_uris}
    # 1. direct links from the evidence
    for e in facts:
        u = e.get("technology_uri")
        if u in res and e["kind"] in ("technique_configuration", "instrument_configuration", "extended_method_capability"):
            t = re.sub(r"^Exact reviewed method:[^.]*\.\s*", "", e["text"]).strip().rstrip(".")
            t = re.sub(r";?\s*Imaging unit only$", "", t)
            for piece in split_models(normalise_makers(t)) if t and len(t) <= 90 else []:
                if piece not in res[u]:
                    res[u].append(piece)
    # 2. by name
    instruments = facility_instruments(fac, facts)
    for u in tech_uris:
        terms = _terms(u, techs.get(u, {}))
        for inst in instruments:
            ex = EXCLUDE.get(u)
            if ex and ex.search(inst):
                continue
            if not _field_ok(u, inst):
                continue
            combo = COMBO.get(u)
            hit = all(re.search(rf"(?<![A-Za-z]){c}(?![A-Za-z])", inst) for c in combo) if combo else False
            if (hit or any(_hit(t, inst) for t in terms)) and inst not in res[u]:
                res[u].append(inst)
    res = {u: _dedupe([c for c in (_clean(x) for x in v) if c]) for u, v in res.items()}
    return {u: v for u, v in res.items() if v}


VENDORS = re.compile(r"\b(Zeiss|Leica|Nikon|Olympus|Evident|Andor|Oxford|Abberior|Abbelight|Bruker|JPK|Asylum|"
                     r"Thermo|FEI|JEOL|Hitachi|Tescan|Gatan|Mediso|Siemens|Philips|GE|Bruker|PerkinElmer|Perkin|"
                     r"VisualSonics|Fujifilm|FujiFilm|Spectral|LaVision|Miltenyi|3i|Intelligent|Yokogawa|Visitron|"
                     r"Molecular Devices|Yokogawa|Hamamatsu|Becker|PicoQuant|Leica|Luxendo|Viventis|Bitplane|ONI|"
                     r"GE Healthcare|Sedecal|MILabs|Inviscan|Agilent|Varian|Canon|Toshiba|iThera|TomoWave|Revvity|"
                     r"Keyence|Cytiva|Applied Precision|Nanolive|Tomocube|Phasefocus|Witec|WITec|Horiba|Renishaw|"
                     r"Lumicks|Bio-Rad|Sartorius|Incucyte|Opera|Operetta|ImageXpress|CellInsight|Rigaku|Xradia|"
                     r"Scanco|SkyScan|Custom|custom|home-built|homebuilt|in-house|Cytek|Logos|MR Solutions|Femtonics|Rapp|"
                     r"Shimadzu|Spectral Instruments|Waters|Thorlabs|Photometrics|Abbelight|Evident|Delmic|"
                     r"Thermo Fisher|Xradia|Mediso|Bruker|prototype|Prototype)\b")
_VERB_TAIL = re.compile(r"\s+(supports|is|are|allows|enables|provides|offers|can|used for)\b.*$")


JUNK_PARENS = re.compile(r"\s*\(([^()]*\b(?:nm|mm|resolution|installed|named|compatible|as detailed|context)\b[^()]*)\)", re.I)


def _drop_junk_parens(t: str) -> str:
    """"(50-80 nm; live-compatible)" and "(installed 2022)" go; brackets that name a maker stay."""
    return JUNK_PARENS.sub(lambda m: m.group(0) if VENDORS.search(m.group(1)) else "", t)


def _clean(text: str) -> str:
    t = normalise_makers(text.strip())
    t = re.sub(r"^(Source-listed|Listed|Per [^:\u2014]{3,40}[:\u2014])\s*", "", t).strip(" .,:\u2014-")
    # "AMC-specific official Node inventory: Leica SP8" -> "Leica SP8"
    t = re.sub(r"^(?=[^:]*[a-z]{3})[A-Z][^:\d]{2,60}:\s+(?=\S)", "", t)
    t = re.sub(r"^(?:Named systems include|Systems include|Includes?)\s+(?:an?\s+)?", "", t)
    t = re.sub(r"\s+documented\b.*$|\s+configurations?$|\s+as detailed above$", "", t)
    if t.count("(") > t.count(")"):  # a text cut inside its brackets: "MaiTai laser (TCSPC"
        t = t[:t.rfind("(")].strip()
    t = re.sub(r"\s+for\s+(?=[A-Z0-9]).*$", "", t)  # "Nikon Eclipse Ti2-E for STORM"
    t = _drop_junk_parens(t).strip(" .,;")
    t = re.sub(r"\s+(?:super-resolution|(?:plate-based\s+)?high-content(?:\s+screening)?)$", "", t)
    # a bare field strength or a phrase about a site is not an instrument ("3.0T", "national 7T facility")
    if re.fullmatch(r"[\d.,/ ]+\s*(?:T|Tesla)", t) or re.match(r"(national|one|variable)\b", t, re.I):
        return ""
    t = _VERB_TAIL.sub("", t).strip(" .,")
    t = re.sub(r",\s*installed\b.*$|\s*\(plus [^)]*\)$|\s+and wider\b.*$", "", t).strip(" .,")
    if len(t) > 110 or re.match(r"As Row\b", t) or re.search(
            r"not all named|not named|as above|per registry|not itemi[sz]ed|categor(y|ies) confirmed|"
            r"modalities named|homepage|imagery|^project\b|project Neuro|"
            r"models? (are )?(on|listed on)|equipment (sub)?pages?|not applicable", t, re.I):
        return ""
    # "3T MRI, TEP-IRM (PET-MRI), MEG, EEG, PANAM, Stimulation" lists modalities, not instruments
    pieces = [x for x in re.split(r",\s*", t) if x.strip()]
    if len(pieces) >= 4 and sum(bool(re.search(r"\d", x)) for x in pieces) <= 1:
        return ""
    # keep only entries that name a model or a maker
    if not (re.search(r"\d", t) or VENDORS.search(t) or _named_model(t) or MODEL_WORDS.search(t)):
        return ""
    t = model_only(t)
    if t.count("(") > t.count(")"):  # a bracket left open by an earlier cut
        t = t[:t.rfind("(")].strip(" ,;")
    return t


TECHNIQUE_ABBR = {"STED", "FLIM", "FRET", "FRAP", "SMLM", "PALM", "STORM", "DSTORM", "PAINT", "CLEM", "TIRF", "SIM",
                  "MRI", "MRS", "PET", "SPECT", "CT", "OCT", "SEM", "TEM", "STEM", "FIB", "EDX", "EDS", "AFM", "SHG",
                  "THG", "CARS", "SRS", "OPT", "SPIM", "LSFM", "HCS", "HTM", "FCS", "FCCS", "BSL", "CLSM", "LSCM",
                  "SDCM", "MSI", "MALDI", "MINFLUX", "RESOLFT", "ISM", "EM", "LM", "GMO", "SPF", "IVM", "PAI", "US",
                  "HILO"}


def _named_model(t: str) -> bool:
    """A product name without digits or maker: ScanR, DeepSIM, NanoWizard, STEDYCON."""
    for w in re.findall(r"[A-Za-z][A-Za-z+]*", t):
        if w.upper() in TECHNIQUE_ABBR:
            continue
        if re.search(r"[a-z][A-Z]", w) or (w.isupper() and len(w) >= 5):
            return True
    return False


def model_only(t: str) -> str:
    """'Confocal microscope (Zeiss LSM 900)' -> 'Zeiss LSM 900'; cut a sentence that runs on."""
    t = re.split(r"\.\s+(?=[A-Z][a-z])", t)[0].strip(" .")
    t = re.sub(r"^(a|an|the)\s+", "", t)
    t = re.sub(r"\s*\((?:per|see|source|from)\b[^)]*\)", "", t, flags=re.I).strip(" .,")
    m = re.fullmatch(r"(.+?)\s*\(([^()]+)\)", t)
    if m:
        outer, inner = m.group(1), m.group(2)
        descriptive = (not re.search(r"\d", outer) and not VENDORS.search(outer) and not re.search(r"\b[A-Z]{2,}\d", outer)
                       and not _named_model(outer) and not MODEL_WORDS.search(outer))
        # "BioImaging spinning-disk/TIRF (Andor Dragonfly)": the maker is only in the brackets
        if (not VENDORS.search(outer) and not re.search(r"\d", outer) and VENDORS.search(inner)
                and VENDORS.sub("", inner).strip(" ,()")):  # not "NanoScan PET-CT (Mediso)"
            return inner.strip()
        if descriptive and (VENDORS.search(inner) or _named_model(inner) or MODEL_WORDS.search(inner)
                            or re.search(r"[A-Za-z]{2,}.*\d|\d.*[A-Za-z]{2,}", inner)):
            return inner.strip()
    return t


_GENERIC = {"mri", "scanner", "system", "source", "listed", "configuration", "microscope", "microscopy", "imaging",
            "scientific", "fisher", "thermo",
            "with", "and", "the", "for", "documented", "instrument", "platform", "family", "unit", "t"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower().replace(".0t", "t")) if w not in _GENERIC}


def _dedupe(items: list[str]) -> list[str]:
    """Drop entries whose distinctive words (80% or more) already appear in an entry kept."""
    out: list[str] = []
    for it in sorted(items, key=lambda v: (len(_tokens(v)), len(v)), reverse=True):
        tk = _tokens(it)
        if tk and any(len(tk & _tokens(o)) >= 0.8 * len(tk) for o in out):
            continue
        out.append(it)
    order = {v: i for i, v in enumerate(items)}
    return sorted(out, key=lambda v: order[v])
