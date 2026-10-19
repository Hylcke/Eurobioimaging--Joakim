"""Build one briefing file per Node for the n8n description workflow.

Usage:
    python build_node_files.py                 # all Nodes -> node_files/
    python build_node_files.py --node Flanders # one Node

Every file has the same structure, the one the EB-NODES writer and renderer
already expect:

  node, country, node_uri
  node_briefing   what the writer may use. No personal data, no addresses,
                  no coordinates.
  node_record     never sent to the writer: facility websites and URIs,
                  addresses, coordinates, Node and facility contacts, services.
  missing_info    what the master lacks for this Node (shown for review).

Sources:
  Knowledge Base Master (all facts, facility contacts, services, technologies)
  August master (Node contact only)
  link_status.json from check_links.py (a link appears only if it opened)

Structure and imaging domain are derived from the facility and technology
records, not taken from any earlier text. Facilities on membership hold are
left out of the page and listed in missing_info.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import OrderedDict, defaultdict
from datetime import date
from pathlib import Path

HERE_DIR = Path(__file__).resolve().parent

from reconcile import Catalogue, reconcile
from tech_instruments import instruments_by_technology
from kbdata import (EXTRA_NODE_WEBSITES, KB, LINK_OVERRIDES, LINK_REPLACEMENTS, LINK_STATUS, NODE_FILES, august_node_map, load_august, load_kb, norm, s,
                    urls_in)

# Technology categories of the master (portal categories), in page order.
CATEGORY_ORDER = [
    "Fluorescence Microscopy", "Fluorescence Nanoscopy", "Label-free Imaging", "Mesoscopic Imaging",
    "Functional Imaging and specialised methodologies", "Correlative Light Microscopy and Electron Microscopy",
    "Live-cell imaging and EM", "Cryo-EM", "Scanning Electron Microscopy (SEM)", "Ultrastructural analysis in 2D",
    "Ultrastructural analysis in 3D (volume EM)", "Ultrastructural localization of molecules", "X-ray and EM",
    "Sample characterisation", "Animal and plant Imaging", "ex-vivo and materials imaging using biomedical technologies",
    "Human Imaging", "Biological Image Data Services", "Medical Image Data services",
]
FAMILY = {  # category -> modality family, used to describe structure and domain
    "Fluorescence Microscopy": "light microscopy", "Fluorescence Nanoscopy": "light microscopy",
    "Label-free Imaging": "light microscopy", "Mesoscopic Imaging": "light microscopy",
    "Functional Imaging and specialised methodologies": "light microscopy",
    "Correlative Light Microscopy and Electron Microscopy": "correlative light and electron microscopy",
    "Live-cell imaging and EM": "correlative light and electron microscopy",
    "X-ray and EM": "correlative light and electron microscopy",
    "Cryo-EM": "electron microscopy", "Scanning Electron Microscopy (SEM)": "electron microscopy",
    "Ultrastructural analysis in 2D": "electron microscopy", "Ultrastructural analysis in 3D (volume EM)": "electron microscopy",
    "Ultrastructural localization of molecules": "electron microscopy",
    "Sample characterisation": "sample characterisation",
    "Animal and plant Imaging": "preclinical imaging",
    "ex-vivo and materials imaging using biomedical technologies": "preclinical imaging",
    "Human Imaging": "clinical and human imaging",
    "Biological Image Data Services": "image data services", "Medical Image Data services": "image data services",
}
BIOMEDICAL = {"preclinical imaging", "clinical and human imaging"}
SUPPORT_FAMILIES = {"image data services", "sample characterisation"}
FAMILY_ORDER = ["light microscopy", "electron microscopy", "correlative light and electron microscopy",
                "preclinical imaging", "clinical and human imaging", "sample characterisation", "image data services"]
PSEUDO_TECH = {"i-dont-know-which-technology"}
FULL_DETAIL_LIMIT = 10


def cap(text, limit):
    t = re.sub(r"\s+", " ", s(text))
    if len(t) <= limit:
        return t
    head = t[:limit]
    stop = max(head.rfind(". "), head.rfind("; "))
    return head[:stop + 1].strip() if stop > limit * 0.5 else re.sub(r"\s+\S*$", "", head).strip()


def short_name(name: str) -> str:
    name = s(name)
    for inner in re.findall(r"\(([^)]{2,12})\)", name):
        inner = inner.strip()
        if re.fullmatch(r"[A-Z0-9][A-Za-z0-9\-/+]*", inner) and len(re.findall(r"[A-Z]", inner)) >= 2:
            return inner
    # split at the first separator that is not inside brackets
    depth, cut = 0, len(name)
    for i, ch in enumerate(name):
        depth += ch == "("
        depth -= ch == ")" and depth > 0
        if depth == 0 and re.match(r",|\s/\s|\s*[\u2014\u2013]\s*|\s-\s", name[i:]) and i > 0:
            cut = i
            break
    trimmed = re.sub(r"\s*\([^)]*\)\s*$", "", name[:cut].strip()).strip()
    return trimmed or name


def strength_profile(by_cat: list[dict]) -> list[dict]:
    fam: dict[str, dict] = {}
    for g in by_cat:
        fm = FAMILY.get(g["category"], "other")
        d = fam.setdefault(fm, {"family": fm, "technologies": 0, "facilities": set()})
        for t in g["technologies"]:
            d["technologies"] += 1
            d["facilities"].update(t.get("provided_by") or [])
    out = [{"family": d["family"], "technologies": d["technologies"],
            "facility_count": len(d["facilities"]), "facilities": sorted(d["facilities"])} for d in fam.values()]
    return sorted(out, key=lambda d: (-d["facility_count"], -d["technologies"]))


GENERIC_TAIL = re.compile(r"^(EM|LM|light[- ]microscopy|electron[- ]microscopy|confocal|imaging|microscopy)?\s*(core\s*)?"
                          r"(facility|platform|unit)$", re.I)


def unique_short_names(facs: list[dict]) -> dict[str, str]:
    """Short name per facility; two facilities of one Node never share a short name.

    Names like "Montpellier / IPAM, Imagerie du Petit Animal" put a regional group first.
    When several facilities of a Node share that first part, it is a group, and the
    short name comes from the part after " / " (unless that part is generic, such as
    "EM facility")."""
    prefix = {}
    for f in facs:
        name = s(f.get("facility_name"))
        if " / " in name:
            prefix[name.split(" / ", 1)[0]] = prefix.get(name.split(" / ", 1)[0], 0) + 1
    sn = {}
    for f in facs:
        name = s(f.get("facility_name"))
        head, _, tail = name.partition(" / ")
        acr = re.compile(r"\b[A-Z][A-Z0-9'-]{2,}\b")
        tail_first = re.split(r",", tail)[0].strip()
        group_head = prefix.get(head, 0) > 1 or (acr.search(tail_first) and not acr.search(head))
        if tail and group_head and not GENERIC_TAIL.match(tail_first):
            sn[f["ebi_fac_id"]] = short_name(tail)
        else:
            sn[f["ebi_fac_id"]] = short_name(name)
    counts = {}
    for v in sn.values():
        counts[v] = counts.get(v, 0) + 1
    for f in facs:
        fid = f["ebi_fac_id"]
        if counts[sn[fid]] > 1:
            name = s(f.get("facility_name"))
            tail = name.split(" / ", 1)[1] if " / " in name else ""
            tail = re.split(r",|\s[\u2014\u2013]\s", tail)[0].strip()
            tail = re.sub(r"\s*\([^)]*\)\s*$", "", tail).strip()
            if tail and sn[fid] in tail:
                sn[fid] = tail  # "ImaChem - IBENS" rather than "ImaChem, ImaChem - IBENS"
            elif tail and tail != sn[fid] and re.search(r"[A-Z].*[A-Z]", tail):
                sn[fid] = tail  # two "(CRAN)" platforms: "OptiRAD platform" and "PhotoVivo platform"
            else:
                sn[fid] = f"{sn[fid]}, {tail}" if tail and tail != sn[fid] else f"{sn[fid]} ({fid})"
    for fid, v in sn.items():
        sn[fid] = re.sub(r"\s+within\s+.*$", "", v)
    for fid, v in sn.items():  # "FRIM platform" -> "FRIM"; the writer then never needs an article
        m = re.fullmatch(r"(\S*[A-Z]\S*[A-Z]\S*)\s+(platform|facility|unit)", v)
        if m and len(m.group(1)) >= 4:
            sn[fid] = m.group(1)
    seen = {}
    for f in facs:  # still the same: add the EBI-FAC ID
        seen.setdefault(sn[f["ebi_fac_id"]], []).append(f["ebi_fac_id"])
    for name, ids in seen.items():
        if len(ids) > 1:
            for fid in ids:
                sn[fid] = f"{name} ({fid})"
    return sn


def record_type(raw) -> str:
    t = s(raw).lower()
    if "core facility" in t:
        return "Core facility"
    if "data" in t:
        return "Data or analysis resource"
    if "platform" in t:
        return "Platform"
    if "service" in t:
        return "Service unit"
    if "sub-node" in t:
        return "Sub-node"
    return "Facility"


def undash(v):
    """No em dashes anywhere on the page: an em dash (or a spaced en dash used as
    one) becomes a comma. En dashes in number ranges stay."""
    if isinstance(v, str):
        v = re.sub(r"\s*\u2014\s*|\s+\u2013\s+", ", ", v)
        return re.sub(r"[\u2010\u2011\u2012\u2013\u2212]", "-", v)
    if isinstance(v, list):
        return [undash(x) for x in v]
    if isinstance(v, dict):
        return {k: undash(x) for k, x in v.items()}
    return v


INSTRUMENTS_PER_TECH = 5       # facilities per technology row
INSTRUMENTS_PER_FACILITY = 3   # instruments per facility in one row


def no_services(text) -> str:
    """Drop sentences that list services ("Services include training, ...", "Support includes ...").
    Services on the page come only from the signed SLA."""
    parts = re.split(r"(?<=[.;])\s+", s(text))
    keep = [p for p in parts if not re.match(r"(Services?|Support|User support|Offered services)\b[^.]{0,40}\b(include|includes|cover|covers|offered|are)\b", p, re.I)]
    return " ".join(keep).strip()


def clean_services(items: list[str]) -> list[str]:
    """The printed list of agreed services: no internal notes, no bare "Instruments", site notes in plain words,
    and fragments such as "no mouse/rodent facility access" joined to the item they belong to."""
    out: list[str] = []
    for x in items:
        x = re.sub(r"\s+", " ", x).strip()
        if re.search(r"INTERNAL|Not established|\bSQ\d+|^\[.*\]$|partial list", x, re.I):
            continue
        # Not a service a researcher can use, or a feasibility/booking/pricing promise (team, 16 Oct).
        if re.search(r"feasib|pilot stud|booking|pricing|\bprice|^collaborative research\b|^research and development\b"
                     r"|^infrastructure access$|^access to (the )?infrastructure$", x, re.I):
            continue
        site = ""
        m = re.search(r"\s*\[Site scope:\s*([^\]]+)\]\s*$", x)
        if m:
            x, site = x[:m.start()].strip(), m.group(1).strip()
            x = re.sub(r"^\((?:[A-Z][\w-]*)\)\s+", "", x)  # "(MAFIL) stimulation devices" with the site given anyway
            if site.lower() == x.lower():
                site = ""
        if re.fullmatch(r"instruments?", x, re.I):
            continue
        if not site and out and re.match(r"[a-z]", x) and not re.match(r"[a-z]+[A-Z]", x):
            out[-1] = f"{out[-1]}, {x}"
            continue
        if re.match(r"[a-z][a-z]", x):
            x = x[0].upper() + x[1:]
        if site:
            x = f"{x}, at {site}" if x.endswith(")") else f"{x} (at {site})"
        if x and x not in out:
            out.append(x)
    return out


def cap_list(items: list[str], n: int) -> list[str]:
    return items if len(items) <= n else items[:n] + [f"and {len(items) - n} more facilities"]


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def load_links() -> dict[str, dict]:
    status = json.loads(LINK_STATUS.read_text(encoding="utf-8")) if LINK_STATUS.exists() else {}
    if LINK_OVERRIDES.exists():
        with LINK_OVERRIDES.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if s(r.get("url")):
                    status[s(r["url"])] = {"ok": s(r.get("ok")).lower() in ("1", "yes", "true", "ok"),
                                           "status": "MANUAL", "checked_at": s(r.get("date"))}
    return status


def read_csv(path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--node", help="only Nodes whose name or URI contains this text")
    args = ap.parse_args()

    kb, aug = load_kb(), load_august()
    links = load_links()
    if not links:
        print("WARNING: no link_status.json. Run check_links.py first; until then every link is left off the pages.")

    replacements = {s(r["old_url"]): s(r["new_url"]) for r in read_csv(LINK_REPLACEMENTS) if s(r.get("old_url"))}
    extra_sites = {s(r["node_uri"]): s(r["url"]) for r in read_csv(EXTRA_NODE_WEBSITES) if s(r.get("node_uri"))}

    def good_link(url, missing, what):
        url = s(url)
        if url in replacements:  # the page moved; the new address was checked by hand
            url = replacements[url]
        if not url:
            missing.append(f"{what}: none recorded")
            return ""
        st = links.get(url)
        if st is None:
            missing.append(f"{what}: not checked yet ({url})")
            return ""
        if not st.get("ok"):
            missing.append(f"{what}: did not open ({st.get('status')}, {url})")
            return ""
        return url

    # A Node without a node_uri (SOM, at the moment) keeps its facilities through a name key.
    no_uri = [n for n in kb["Nodes"] if s(n.get("node_name")) and not s(n.get("node_uri"))]
    if len(no_uri) == 1:
        key = re.sub(r"[^a-z0-9]+", "-", s(no_uri[0]["node_name"]).lower()).strip("-")
        no_uri[0]["node_uri"], no_uri[0]["_no_uri"] = key, True
        for sheet in ("Facilities", "Node Services", "Official Services"):
            for r in kb.get(sheet, []):
                if not s(r.get("node_uri")) and any(v not in (None, "") for v in r.values()):
                    r["node_uri"] = key
    elif no_uri:
        print(f"WARNING: {len(no_uri)} Nodes have no node_uri and are skipped: " + "; ".join(s(n['node_name']) for n in no_uri))

    techs = {t["technology_uri"]: t for t in kb["Technologies"] if t.get("technology_uri")}
    catalogue = Catalogue(techs)
    node_techs = defaultdict(list)
    # NAVIGATOR GATES. Every relationship is used only when the master's navigator_route allows it
    # (Data Dictionary, Navigator rules). Anything else fails closed and is listed for review.
    for r in kb["Node Technologies"]:
        if (s(r.get("navigator_route")) == "REGISTERED_NODE_SCOPE"            # NOD-02
                and r.get("technology_uri") not in PSEUDO_TECH):
            node_techs[r["node_uri"]].append(r["technology_uri"])
    fac_techs = defaultdict(list)
    qualified_links = set()   # (ebi_fac_id, technology_uri) with a qualified allocation (LNK-01, kept)
    held_links = defaultdict(list)
    for r in kb["Facility Technologies"]:
        if r.get("technology_uri") in PSEUDO_TECH:
            continue
        route = s(r.get("navigator_route"))
        if route == "REGISTERED_PROVIDER_LINK":                               # LNK-01
            fac_techs[r["ebi_fac_id"]].append(r["technology_uri"])
            if s(r.get("round3_relation_status")) == "VALIDATED_FACILITY_ALLOCATION_QUALIFIED":
                qualified_links.add((r["ebi_fac_id"], r["technology_uri"]))
        elif route == "HELD_RELATIONSHIP":                                    # LNK-02
            held_links[r["ebi_fac_id"]].append((r["technology_uri"], s(r.get("round3_relation_status"))))
    fac_services = defaultdict(list)
    for r in kb["Services"]:
        if (r.get("ebi_fac_id") and s(r.get("navigator_route")) == "CURRENT_FACILITY_SERVICE"   # SVC-01
                and s(r.get("service_name"))):
            if s(r["service_name"]) not in fac_services[r["ebi_fac_id"]]:
                fac_services[r["ebi_fac_id"]].append(s(r["service_name"]))
    contacts = defaultdict(list)
    for c in kb["Contacts"]:
        if s(c.get("navigator_route")) != "PUBLIC_CONTACT":                   # CON-01 only
            continue
        role = s(c.get("role"))
        if re.search(r"earlier|context|historic|superseded", role, re.I):
            continue  # older contact records kept for history, not current contacts
        full = " ".join(x for x in (s(c.get("first_name")), s(c.get("last_name"))) if x)
        role = re.sub(r"\s*/\s*facility contact$", "", role, flags=re.I)
        if re.fullmatch(r"TECHNICAL[_ ]CONTACT", role, re.I):
            role = "Technical contact"
        elif re.search(r"contact|mailbox", role, re.I) and not re.search(r"head|director|manager|engineer|technical", role, re.I):
            role = ""  # "Facility/service contact", "Hubrecht Imaging Center contact" say nothing new
        if not full:
            role = "General enquiries"
        fid = c.get("ebi_fac_id")
        emails = {e.strip().lower() for e in re.split(r"[;,\s]+", s(c.get("email"))) if e.strip()}
        seen = {e.strip().lower() for x in contacts[fid] for e in re.split(r"[;,\s]+", x["email"]) if e.strip()}
        if not full and emails and emails <= seen:
            continue  # the same mailbox is already listed with a person
        contacts[fid].append({"full_name": full, "role": role, "email": s(c.get("email"))})
    open_q = defaultdict(int)
    for q in kb.get("Data Enrichment", []):
        if q.get("node_uri"):
            open_q[q["node_uri"]] += 1
    facs = defaultdict(list)
    for f in kb["Facilities"]:
        if f.get("ebi_fac_id"):
            facs[f.get("node_uri")].append(f)
    aug_nodes = august_node_map(kb, aug)

    # Scientific guidance per technology (what a technique does), for grounding section 2.
    guidance = {}
    for g in kb.get("Technology Guidance", []):
        if g.get("technology_uri"):
            guidance[g["technology_uri"]] = cap(". ".join(x.rstrip(". ") for x in (
                s(g.get("modality")), s(g.get("biological_scale")), s(g.get("strengths"))) if x) + ".", 260)
    # Structured capability facts per facility (instruments, workflows, sample types, biosafety).
    ev_by_fac = defaultdict(list)
    for e in kb.get("Evidence", []):
        fid = s(e.get("navigator_bound_facility")) or s(e.get("entity_id"))
        if not fid.startswith("EBI-FAC"):
            continue
        ev_by_fac[fid].append({
            "kind": s(e.get("field_or_relation")).replace("matching.", ""),
            "text": s(e.get("supported_value")),
            "instrument": s(e.get("instrument_or_workflow")), "manufacturer": s(e.get("manufacturer")),
            "model": s(e.get("instrument_model")), "technology_uri": s(e.get("technique_uri")),
            "sample_type": s(e.get("sample_type")), "organism": s(e.get("organism_species")),
            "sample_condition": s(e.get("sample_condition")), "biosafety": s(e.get("biosafety_condition")),
            "source_url": s(e.get("source_url")),
        })
    # Contracted services: only rows from a signed SLA (Annex 1.1). Facility-derived roll-ups and
    # services found on facility web pages are not part of the agreement. Nodes without SLA rows fall back to the Node service summary.
    sla_services = defaultdict(list)
    for r in kb.get("Node Services", []):
        if s(r.get("source_type")) != "SLA_ANNEX_1_1" or s(r.get("navigator_route")) != "NODE_CONTRACT_CONTEXT":  # SLA-01
            continue
        name_ = s(r.get("service_wording_sla")) or s(r.get("service_name_normalized"))
        site_ = s(r.get("named_site_wording")) if s(r.get("service_scope")) == "NAMED_SITE" else ""
        item = f"{name_} [Site scope: {site_}]" if site_ else name_
        if name_ and item not in sla_services[r.get("node_uri")]:
            sla_services[r.get("node_uri")].append(item)
    node_services = defaultdict(list)
    for r in kb.get("Node Services", []):
        name_ = s(r.get("service_name_normalized"))
        if name_ and name_ not in [x["service"] for x in node_services[r.get("node_uri")]]:
            node_services[r.get("node_uri")].append({"service": name_, "site": s(r.get("named_site_wording")),
                                                     "source": "signed SLA, Annex 1.1"})
    official = defaultdict(list)
    for r in kb.get("Official Services", []):
        official[r.get("node_uri")].append({"service": s(r.get("service_name_normalized")),
                                            "wording": s(r.get("source_wording")),
                                            "site": s(r.get("named_site_or_subnode")),
                                            "basis": "reported to the SAB; not contractual"})
    access = defaultdict(list)
    for r in kb.get("API Access Routes", []):
        if s(r.get("access_text")) and s(r["access_text"]) not in access[r.get("ebi_fac_id")]:
            access[r.get("ebi_fac_id")].append(s(r["access_text"]))
    q_by_fac = defaultdict(list)
    for q in kb.get("Data Enrichment", []):
        for fid in re.split(r"[;,\s]+", s(q.get("ebi_fac_ids"))):
            if fid:
                q_by_fac[fid].append(s(q.get("issue_id")))
    all_cities = set()
    for f in kb["Facilities"]:
        for part in re.split(r"[/;,()]", s(f.get("city"))):
            if len(part.strip()) >= 4:
                all_cities.add(part.strip())

    NODE_FILES.mkdir(exist_ok=True)
    index, review = [], []
    for node in sorted(kb["Nodes"], key=lambda n: s(n.get("node_name"))):
        uri, name = node.get("node_uri"), s(node.get("node_name"))
        if not uri:
            continue
        file_key = uri if re.fullmatch(r"[a-z0-9-]+", s(uri)) else re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if args.node and args.node.lower() not in (name + uri).lower():
            continue
        missing = []
        if node.get("_no_uri"):
            missing.append("Node has no node_uri in the master; the file is named after the Node name")
        all_f = sorted(facs.get(uri, []), key=lambda f: s(f.get("facility_name")))
        held = [f for f in all_f if s(f.get("navigator_route")) == "HELD_MEMBERSHIP"]
        pub = [f for f in all_f if f not in held]
        for f in held:
            missing.append(f"Facility on membership hold, left off the page: {s(f.get('facility_name'))} ({f['ebi_fac_id']})")
        SN = unique_short_names(pub)

        # Instruments per technology, from each providing facility's instrument records.
        # One entry per facility: "CCI: LSM 700, LSM 710, LSM 900".
        inst_by_tech = defaultdict(list)
        for f in pub:
            sn_ = SN[f['ebi_fac_id']]
            found = instruments_by_technology(f, ev_by_fac.get(f["ebi_fac_id"], []),
                                              fac_techs.get(f["ebi_fac_id"], []), techs)
            for u, insts in found.items():
                inst_by_tech[u].append(f"{sn_}: " + ", ".join(undash(x) for x in insts))
        provided_by = defaultdict(list)
        qualified_by = defaultdict(list)
        for f in pub:
            for u in fac_techs.get(f["ebi_fac_id"], []):
                sn_ = SN[f['ebi_fac_id']]
                if sn_ not in provided_by[u]:
                    provided_by[u].append(sn_)
                if (f["ebi_fac_id"], u) in qualified_links and sn_ not in qualified_by[u]:
                    qualified_by[u].append(sn_)
            for u, why in held_links.get(f["ebi_fac_id"], []):
                if u in techs:
                    missing.append(f"Held facility-technology link left out (LNK-02, {why}): "
                                   f"{SN[f['ebi_fac_id']]} - {s(techs[u]['technology_name']).replace('*', '').strip()}")
        # Technologies by category (the Node's registered portfolio).
        grouped = OrderedDict((c, []) for c in CATEGORY_ORDER)
        other = []
        registered = node_techs.get(uri, [])
        if not registered:  # no Node-level registration: fall back to what the facilities provide
            registered = sorted({u for f in pub for u in fac_techs.get(f["ebi_fac_id"], []) if u in techs})
            if registered:
                missing.append("No technologies registered to this Node; the table lists the facilities' technologies")
        for t_uri in registered:
            t = techs.get(t_uri)
            if not t:
                continue
            label = s(t.get("technology_name"))
            item = {"label": label.replace("*", "").strip(), "abbreviation": s(t.get("abbreviation")) or None,
                    "provisional": "*" in label, "technology_uri": t_uri,
                    "provided_by": provided_by.get(t_uri, []),
                    "provided_by_qualified": qualified_by.get(t_uri, []),
                    "instruments": inst_by_tech.get(t_uri, [])}
            cat = s(t.get("category_name")).strip()
            (grouped[cat] if cat in grouped else other).append(item)
        by_cat = [{"category": c, "technologies": sorted(v, key=lambda x: x["label"].lower())} for c, v in grouped.items() if v]
        if other:
            by_cat.append({"category": "Other", "technologies": other})
        families = [fm for fm in FAMILY_ORDER if any(FAMILY.get(g["category"]) == fm for g in by_cat)]
        provided = {u for f in pub for u in fac_techs.get(f["ebi_fac_id"], [])}
        unprovided = [techs[u]["technology_name"] for u in registered if u in techs and u not in provided]
        if unprovided:
            missing.append(f"Registered technologies with no facility named as provider ({len(unprovided)}): "
                           + "; ".join(sorted(s(x).replace('*', '') for x in unprovided)))
        if not by_cat:
            missing.append("No registered technologies")
        no_inst = sorted(it["label"] for g in by_cat for it in g["technologies"] if it["provided_by"] and not it["instruments"])
        if no_inst:
            missing.append(f"Technologies with no named instrument in the master ({len(no_inst)}): " + "; ".join(no_inst))

        # Geography and derived identity.
        cities = sorted({undash(s(f.get("city"))) for f in pub if s(f.get("city"))})
        insts = sorted({undash(s(f.get("institution"))) for f in pub if s(f.get("institution"))})
        countries = sorted({s(f.get("country_name")) for f in pub if s(f.get("country_name"))} or {s(node.get("country_name"))})
        n_pub = len(pub)
        core = [fm for fm in families if fm not in SUPPORT_FAMILIES]
        if n_pub == 0:
            shape = "No confirmed facilities on record"
            missing.append("No confirmed facilities: every facility of this Node is on membership hold")
        elif n_pub == 1 or (len(cities) <= 1 and len(insts) <= 1):
            shape = f"Single site: {plural(n_pub, 'facility', 'facilities')}" + (f" at {insts[0]}" if insts else "") + \
                    (f" in {cities[0]}" if cities else "")
        else:
            shape = (f"Distributed: {plural(n_pub, 'facility', 'facilities')} at {plural(len(insts), 'institution')} "
                     f"in {plural(len(cities), 'city', 'cities')}")
        if len(core) >= 2:
            shape += f"; multimodal ({', '.join(core)})"
        elif core:
            shape += f"; one modality family ({core[0]})"
        bio = [fm for fm in core if fm not in BIOMEDICAL]
        med = [fm for fm in core if fm in BIOMEDICAL]
        domain = ("Biological and biomedical imaging" if bio and med else
                  "Biomedical imaging" if med else "Biological imaging" if bio else "")
        if not domain:
            missing.append("Imaging domain could not be derived (no technologies)")

        # Node-level links and contacts.
        aug = aug_nodes.get(uri, {})
        site_urls = urls_in(aug.get("Node website")) or ([extra_sites[uri]] if uri in extra_sites else [])
        website = good_link(site_urls[0] if site_urls else "", missing, "Node website")
        portal_urls = urls_in(node.get("access_portal_url")) or urls_in(aug.get("Access Portal URL"))
        portal = good_link(portal_urls[0] if portal_urls else "", missing, "Access Portal page")
        def no_dash(v):
            return re.sub(r"\s*[\u2014\u2013]\s*", ", ", s(v))
        primary = no_dash(aug.get("Public contact"))
        additional = [no_dash(x) for x in s(aug.get("Additional public contacts")).split(";")
                      if x.strip() and not re.search(r"historic|earlier|superseded", x, re.I)]
        def drop_note(x):  # "Stoyno Stoynov (Node Contact), ..." -> "Stoyno Stoynov, ..."
            return re.sub(r"\s*\((?:[^()]*\s)?contact\)", "", x, flags=re.I).strip()
        primary, additional = drop_note(primary), [drop_note(x) for x in additional]
        if not primary:
            missing.append("Node contact: none in the August master")
        services_list = clean_services([p.strip() for x in sla_services.get(uri, []) for p in re.split(r";\s*", x)
                                        if p.strip()])
        services_contracted = bool(services_list)
        services_basis = "SLA" if services_contracted else ""
        if not services_contracted:
            # No signed SLA services: fall back to the Node's service summary in the database.
            # Valid, but below the SLA; the page marks the list with an asterisk for follow-up.
            services_list = clean_services([x.strip(" -\u2022\t") for x in re.split(r"\n|;", s(node.get("service_summary")))
                                            if x.strip(" -\u2022\t")])
            services_basis = "DATABASE" if services_list else ""
            missing.append("No services from a signed SLA: service list taken from the Node service summary "
                           "in the database, shown on the page as currently recorded, please confirm" if services_list else
                           "No services from a signed SLA and no service summary: Services section left off the page")

        # The August profile is older: check it against the master, which wins.
        fids = {f["ebi_fac_id"] for f in pub}
        inst_corpus = " ".join(
            [s(f.get(k)) for f in pub for k in ("instruments", "capabilities_applications", "public_description",
                                                  "expertise")] +
            [" ".join((e["instrument"], e["manufacturer"], e["model"], e["text"]))
             for fid in fids for e in ev_by_fac.get(fid, [])]).lower()
        serv_corpus = " ".join(
            [s(node.get("service_summary"))] + [x for fid in fids for x in fac_services.get(fid, [])] +
            [x["service"] for x in node_services.get(uri, [])] +
            [x["service"] + " " + x["wording"] for x in official.get(uri, [])] +
            [s(f.get(k)) for f in pub for k in ("public_description", "capabilities_applications")]).lower()
        checked, older_review = reconcile(aug, {
            "node_techs": set(registered) | provided, "families": families, "n_facilities": n_pub,
            "n_institutions": len(insts), "n_cities": len(cities), "cities": cities,
            "other_cities": all_cities, "instrument_corpus": inst_corpus, "service_corpus": serv_corpus}, catalogue)
        missing.extend(older_review)
        short_desc = undash(checked["short_description"])
        node_spec = undash(checked["node_specialties"])
        if primary and not any(s(c.get("email")) and s(c.get("email")).lower() in primary.lower()
                               for fid in fids for c in contacts.get(fid, [])):
            missing.append("Node contact comes from the older August master only; confirm it is current")
        node_cities = " ".join(cities).lower()
        not_to_name = sorted({c for c in all_cities
                              if re.search(rf"\b{re.escape(c)}\b", short_desc + " " + node_spec)
                              and c.lower() not in node_cities})
        if not short_desc:
            missing.append("Short description: none in the August master")
        detail = "full" if n_pub <= FULL_DETAIL_LIMIT else "condensed"
        desc_budget, aux_budget = (460, 260) if detail == "full" else (180, 0)
        b_facs, r_facs = [], []
        for f in pub:
            fid, fname = f["ebi_fac_id"], s(f.get("facility_name"))
            sn = SN[fid]
            tech_labels = sorted({s(techs[u]["technology_name"]).replace("*", "").strip()
                                  for u in fac_techs.get(fid, []) if u in techs})
            fm = []
            b_facs.append({
                "facility_id": fid, "name": fname, "short_name": sn, "institution": s(f.get("institution")),
                "city": s(f.get("city")), "record_type": record_type(f.get("record_type")),
                "description": cap(no_services(f.get("public_description") or f.get("capabilities_applications")), desc_budget),
                "technologies": cap("; ".join(tech_labels), desc_budget),
                "services": "",  # facility web-page services are not contracted; kept in the record only
                "application_areas": cap(f.get("application_areas"), aux_budget) if aux_budget else "",
                "capabilities": cap(no_services(f.get("capabilities_applications")), desc_budget),
                "workflows": cap("; ".join(e["text"] for e in ev_by_fac.get(fid, [])
                                           if e["kind"] in ("technique_configuration",
                                                            "instrument_configuration", "biosafety")), aux_budget or 160),
                "sample_types": sorted({x for e in ev_by_fac.get(fid, []) for x in (e["sample_type"], e["organism"]) if x}),
                "status": "confirmed",
            })
            fac_site = good_link((urls_in(f.get("website")) or [""])[0], fm, "website")
            addr = " ".join(x for x in (s(f.get("street_name")), s(f.get("street_number"))) if x)
            if not addr:
                fm.append("street address")
            if not s(f.get("latitude")) or not s(f.get("longitude")):
                fm.append("coordinates")
            if not contacts.get(fid):
                fm.append("facility contact")
            if not s(f.get("public_description")):
                fm.append("description")
            if not s(f.get("facility_uri")):
                fm.append("facility URI")
            if fm:
                missing.append(f"{sn} ({fid}): " + "; ".join(x if ":" in x else f"no {x}" for x in fm))
            r_facs.append({
                "facility_id": fid, "name": fname, "short_name": sn, "institution": s(f.get("institution")),
                "city": s(f.get("city")), "country": s(f.get("country_name")), "website": fac_site,
                "facility_uri": s(f.get("facility_uri")), "record_type": record_type(f.get("record_type")),
                "street_address": addr, "postal_code": s(f.get("postal_code")),
                "latitude": s(f.get("latitude")), "longitude": s(f.get("longitude")),
                "contacts": contacts.get(fid, []), "master_contact": None, "status": "confirmed",
                "access_routes": access.get(fid, []),
                # Complete profile, never cut: for review and for later use.
                "profile": {
                    "description": s(f.get("public_description")),
                    "capabilities_applications": s(f.get("capabilities_applications")),
                    "expertise": s(f.get("expertise")), "instruments": s(f.get("instruments")),
                    "application_areas": s(f.get("application_areas")),
                    "technologies": [{"label": s(techs[u]["technology_name"]).replace("*", "").strip(),
                                      "technology_uri": u} for u in fac_techs.get(fid, []) if u in techs],
                    "services": fac_services.get(fid, []),
                    "capability_facts": ev_by_fac.get(fid, []),
                    "data_enrichment_issue_ids": q_by_fac.get(fid, []),
                },
            })
        for f in held:
            r_facs.append({"facility_id": f["ebi_fac_id"], "name": s(f.get("facility_name")), "status": "unconfirmed"})

        inst_parts = []
        for f in pub:
            models = []
            for e in ev_by_fac.get(f["ebi_fac_id"], []):
                if e["kind"] == "instrument_model":
                    m = " ".join(x for x in (e["manufacturer"], e["model"]) if x)
                    m = f"{e['instrument']} ({m})" if m and e["instrument"] and m not in e["instrument"] else (m or e["instrument"])
                    if m and m not in models:
                        models.append(m)
            text = "; ".join(x for x in ("; ".join(models), s(f.get("instruments"))) if x)
            if text:
                inst_parts.append(f"{SN[f['ebi_fac_id']]}: {cap(text, 400)}")
        instruments = "; ".join(inst_parts)
        specialties = "; ".join(f"{SN[f['ebi_fac_id']]}: {cap(f.get('expertise'), 260)}"
                                for f in pub if s(f.get("expertise")))
        app_areas = "; ".join(f"{SN[f['ebi_fac_id']]}: {cap(f.get('application_areas'), 260)}"
                              for f in pub if s(f.get("application_areas")))
        with_desc = sum(1 for f in pub if len(s(f.get("public_description"))) > 40)
        quality = "good"
        if n_pub == 0 or with_desc == 0 or not by_cat:
            quality = "thin"
        if n_pub == 0 and not by_cat:
            quality = "empty"
        notes = []
        if with_desc < n_pub:
            notes.append(f"{n_pub - with_desc} of {n_pub} facilities have no usable description.")
        if open_q.get(uri):
            missing.append(f"{open_q[uri]} open issues for this Node in the Data Enrichment sheet")

        briefing = {
            "identity": {"name": name, "country": s(node.get("country_name")), "imaging_domain": domain,
                         "structure": shape, "short_description": short_desc,
                         "website": website, "access_portal_url": portal},
            "node_specialties": node_spec,
            # Earlier Node-level profile (August master): background for every section.
            # Checked against the master first; anything that contradicted it was left out.
            "august_node_profile": {k: undash(cap(v, 900)) for k, v in checked["profile"].items()
                                    if k != "services_support"},
            "technology_areas": families,
            # Where the Node's weight lies: per modality family, how many technologies and which facilities.
            "strength_profile": strength_profile(by_cat),
            "technologies_by_category": by_cat,
            "technology_notes": [],
            "technology_guidance": {item["label"]: guidance[item["technology_uri"]] for g in by_cat
                                    for item in g["technologies"] if item["technology_uri"] in guidance},
            "instrument_highlights": cap(instruments, 4000),
            "specialties": cap(specialties, 2500),
            "application_areas": cap(app_areas, 2500),
            # Services from the signed SLA; when there are none, the Node service summary in the database.
            # Only SLA services reach the writer; a database fallback list is printed by code with a
            # "currently recorded, please confirm" label and is never described in the text.
            "services_support": "; ".join(services_list) if services_basis == "SLA" else "",
            "services_contracted": services_contracted,
            "services_basis": services_basis,
            "geography": {"countries": countries, "cities": cities, "city_count": len(cities),
                          "cities_not_to_name": not_to_name, "institution_count": len(insts), "institutions": insts},
            "facility_counts": {"authoritative": n_pub},
            "size_profile": {"facility_count": n_pub, "facility_detail_level": detail},
            "facilities": b_facs,
            "source_quality_flag": quality,
            "source_notes": " ".join(notes),
            "truncated_source_fields": [],
        }
        record = {
            "node_name": name, "node_uri": uri, "submission_id": None, "has_questionnaire": False,
            "node_contact": {"primary": primary, "additional": additional, "respondent": None},
            "services_list": services_list,
            "services_basis": services_basis,
            "node_services": node_services.get(uri, []),
            "reported_services": official.get(uri, []),
            "facilities": r_facs,
        }
        doc = {"node": name, "country": s(node.get("country_name")), "node_uri": file_key, "kb_node_uri": uri, "has_questionnaire": False,
               "built": date.today().isoformat(), "source": KB.name,
               "node_briefing": briefing, "node_record": record, "missing_info": missing}
        doc = undash(doc)
        (NODE_FILES / f"{file_key}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        review.append((name, file_key, doc["missing_info"]))
        index.append({"node": name, "node_uri": file_key, "facilities": n_pub, "held": len(held),
                      "technologies": sum(len(g["technologies"]) for g in by_cat), "missing_items": len(missing),
                      "website": bool(website), "node_contact": bool(primary)})
    if not args.node:
        (NODE_FILES.parent / "node_files_index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        # Review list for Joakim: everything missing or left out, per Node (not printed on the pages).
        lines = [f"# Missing information for review ({date.today().isoformat()})", "",
                 "Not for publication. One section per Node, built from the Knowledge Base Master.", ""]
        for name_, key_, items in sorted(review):
            lines += [f"## {name_}", "", f"File: `{key_}.md`", ""] + [f"- {x}" for x in items] + [""]
        (HERE_DIR / "review").mkdir(exist_ok=True)
        (HERE_DIR / "review" / "missing_information.md").write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"Wrote {len(index)} Node files to {NODE_FILES}")
    print(f"  with a working Node website: {sum(i['website'] for i in index)}; with a Node contact: "
          f"{sum(i['node_contact'] for i in index)}; facilities on the pages: {sum(i['facilities'] for i in index)}")


if __name__ == "__main__":
    main()
