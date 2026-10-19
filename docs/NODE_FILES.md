# Node description files and page layout

This folder turns the EB Knowledge Base Master into one JSON file per Node. The
n8n workflow `EB-NODES KB descriptions` reads each file, has an AI writer draft
five prose sections, and uploads a finished Markdown page per Node to Google
Drive.

Owner and curator: Joakim Edman. Only Joakim decides what is published.

## Pipeline

```
EB_Knowledge_Base_Master.xlsx   (current facts; always wins)
EuBI_Master_Nodes_and_Facilities_v1.xlsx   (older August Node profile; checked first)
link_status.json + link_overrides.csv      (which links open)
        |
        v
build_node_files.py  ->  node_files/<node_uri>.json  (40 files) + node_files_index.json
        |
        v   upload node_files/ to Google Drive
n8n: List node files > Pick node files > Loop > Download > Read node file
     > AI Node Writer (prompt v15) > Clean and explode sections (tidy, checks, identity guard) > [Save sections to sheet, off]
     > Render node page (render_node_page.js) > Create markdown file > Upload to Drive
```

## Commands

Run on Joakim's Windows Python (the facility websites are blocked from the
sandboxes):

```
python scripts/check_links.py            # checks every Node, portal and facility link; writes link_status.json
python scripts/build_node_files.py       # all Nodes
python scripts/build_node_files.py --node swedish   # one Node (does not touch the index)
python scripts/make_workflow.py          # rebuilds EB-NODES_KB_workflow.json after a prompt or render change
```

Then upload `node_files/` to Drive, pick that folder in **List node files**, and
set `NODE_FILTER` in **Pick node files** to test one Node.

## Files

| File | What it does |
| --- | --- |
| `kbdata.py` | Paths and loading. Reads the master sheets listed in `SHEETS`; Evidence is filtered to structured capability facts. |
| `check_links.py` | Opens every link (GET, browser user agent, 25 s). 2xx is OK; 401/403/429 is BOT_BLOCKED. `link_overrides.csv` lets a person mark a link as checked by hand. |
| `link_overrides.csv` | Links that block automated checks or gave certificate/timeout errors, treated as working, plus hand-checked replacement links: `url,ok,checked_by,date,note` |
| `link_replacements.csv` | Dead links whose page moved: `old_url,new_url,checked_by,date,note`. The build prints the new address instead. |
| `extra_node_websites.csv` | Node websites missing from the August master: `node_uri,url,checked_by,date` (SOM) |
| `node_files_index.json` | One line per Node: facility count, missing items, website and contact present |
| `build_node_files.py` | Builds the Node files. All selection and checking rules live here. |
| `reconcile.py` | Checks the older August Node profile against the master and leaves out what contradicts it. |
| `tech_instruments.py` | Finds the instruments behind each facility technology (for the technology table). |
| `node_writer_system_prompt_v15.md` | System prompt of the AI writer (current). Methods, instruments, services and which facility offers them come only from the structured Knowledge Base fields; descriptions only give expertise and specialty context. About 1,000 words in five sections. See the changelog in the top-level README for v1 to v15. |
| `render_node_page.js` | Code of the n8n node "Render node page". Builds everything on the page that is not prose. |
| `make_workflow.py` | Builds the importable workflow from the n8n export `data/reference/EB-NODES9.json` (not in git; set `EB_WORKFLOW_TEMPLATE`), injecting prompt v15, the Render code and the Clean code. |
| `clean_and_explode_sections.js` | Code of the n8n node "Clean and explode sections". Stops the run if the text names neither the Node nor any of its facilities (guards against pinned or cached output from another Node). |
| `EB-NODES_KB_workflow.json` | The workflow to import into n8n. |

## The finished page

| # | Section | Written by |
| --- | --- | --- |
| 1 | Overview | AI writer |
| 2 | Imaging technologies offered | AI writer, then a table of every technology registered to the Node with two columns: Technology (the name carries the technology URI), and Instrument highlights (every named model, grouped by facility short name, e.g. `CFIB: LSM 880, LSM 900; DaMBIC: SP8`; empty when no model is recorded). |
| 3 | Specialties and research focus | AI writer |
| 4 | Services and user support | AI writer, then the Node's service list: from the signed SLA, or from the database when the Node has no SLA services (heading marked `*`). No section when the Node has no services at all |
| 5 | Facilities | Facility table (facility linked to its website, with the facility URI as link title; institution, city), then AI writer |
| 6 | Access and contact | Render code: Node contact, Node website, Access Portal page, then per facility its address, contacts and access routes (coordinates stay in the JSON) |
| (review) | Missing information | Not on the page. Written by the build to `review/missing_information.md`, one section per Node |

The prose target is about 1,000 words in total (Overview 230 to 290, Technologies
180 to 240, Specialties 150 to 200, Services 140 to 190, Facilities 180 to 240).
Do not shorten it.

## What is in a Node file

Top level: `node`, `country`, `node_uri`, `built`, `source`, then three blocks.

### `node_briefing` (what the AI writer reads)

| Field | Content | Source |
| --- | --- | --- |
| `identity.name`, `country` | Node name and country | Master, Nodes |
| `identity.imaging_domain` | Biological, biomedical, or both | Derived from the Node's technology families |
| `identity.structure` | Single site or distributed, with facility, institution and city counts and modality families | Derived from the master's facilities |
| `identity.short_description` | Older description, with contradicting sentences removed | August master, checked by `reconcile.py` |
| `identity.website`, `access_portal_url` | Only if the link opened in `check_links.py` | August master / master Nodes |
| `node_specialties` | Older specialties text, checked | August master, checked |
| `august_node_profile` | Main technology areas, featured technologies, services and support, instrument highlights; contradictions removed | August master, checked |
| `strength_profile` | Per modality family: number of technologies and the facilities offering it, heaviest first. Tells the writer where the Node's weight lies | Derived |
| `technology_areas` | Modality families present (light, electron, correlative, preclinical, clinical, sample characterisation, image data) | Derived |
| `technologies_by_category` | Every technology registered to the Node, by portal category. Each item: label, abbreviation, provisional flag, technology URI, facilities that provide it, instruments per facility | Master: Node Technologies, Facility Technologies, Technologies; instruments from `tech_instruments.py` |
| `technology_guidance` | One line per technology: modality, scale, strengths. Background only, never printed | Master, Technology Guidance |
| `instrument_highlights` | Per facility: named instruments and models | Master: Facilities.instruments and Evidence instrument facts |
| `specialties`, `application_areas` | Per facility, short name first | Master, Facilities |
| `services_support`, `services_basis`, `services_contracted` | The only services the writer may mention. `SLA`: Node Services rows with source_type SLA_ANNEX_1_1. `DATABASE`: the Node has no SLA rows, so Nodes.service_summary is used. Empty: no services | Master: Node Services, Nodes |
| `geography` | Countries, cities, institutions and any city the text must not name | Derived from the master's facilities |
| `facility_counts`, `size_profile` | Facility count; full or condensed facility detail (over 10 facilities is condensed) | Derived |
| `facilities[]` | Per facility: ID, name, short name, institution, city, type, description, technologies, services, application areas, capabilities, workflows, sample types | Master: Facilities, Facility Technologies, Services, Evidence |
| `source_quality_flag`, `source_notes` | good, thin or empty, with the reason | Derived |

### `node_record` (what the render code prints; never rewritten by the AI)

| Field | Content | Source |
| --- | --- | --- |
| `node_contact` | Primary and additional public contacts | August master (the master has no Node contact) |
| `services_list`, `services_basis`, `node_services`, `reported_services` | The printed service list and its basis (SLA or DATABASE); the other two are kept for review | Master |
| `facilities[]` | Name, short name, institution, address, postal code, city, country, latitude, longitude, checked website, facility URI, type, contacts, access routes, and a full `profile`: description, capabilities, expertise, instruments, application areas, technologies with URIs, services, all capability facts, and Data Enrichment issue IDs | Master: Facilities, Contacts, API Access Routes, Evidence, Data Enrichment |

Facilities on membership hold are listed as `unconfirmed` and left off the page.

### `missing_info` (not on the page; written to `review/missing_information.md`)

Holds and unconfirmed facilities; registered technologies no facility provides;
technologies with no named instrument; links that are missing, unchecked or
did not open; facilities without an address, coordinates, contact, description
or URI; the Node contact needing confirmation; every part of the older August
text that was left out and why; the number of open Data Enrichment issues.

## Rules

1. **The master wins.** The Knowledge Base Master is the current source. The
   August master is older and is only used where the master has nothing
   (Node description text, Node contact, Node website), after `reconcile.py`
   has removed anything that contradicts the master: wrong facility,
   institution or city counts, cities where the Node has no facility,
   technologies the Node does not offer, and instruments whose model is not in
   the master's facility records. Services never come from the August master or
   from facility web pages (see rule 8).
2. **Every printed link must open.** Links come from `link_status.json`; an
   unchecked or failing link is left off and listed in `missing_info`.
3. **Data Enrichment issues are not used in descriptions.** Their IDs are kept
   for review only.
4. **The master's Navigator gates decide what is used.** Only rows on a positive
   `navigator_route` reach a Node file: NOD-02 (Node technologies), FAC-01 (facilities),
   LNK-01 (facility providers), SVC-01 (facility services), CON-01 (contacts), SLA-01
   (signed SLA services). Held and unknown routes fail closed and are listed in
   `review/missing_information.md`.
5. **No em dashes** anywhere in the files (`undash()`), and plain, neutral
   language in the prompt and the page.
6. **The writer never sees anything it may not print**, and the render code
   prints structured facts exactly as recorded.
7. **Prague**: earlier pilot findings for the Prague Node were wrong and were
   discarded; only the master's own Prague records are used.

8. **Content sources.** Methods, instruments, people and services come only
   from the Knowledge Base. Services come from the signed SLA first and from the
   database when there is no SLA (marked `*`). Facility websites and descriptions
   are used only for specialty and expertise context.

## Decisions (14 Oct 2026)

- Everything in the Knowledge Base Master counts as true. The Data Enrichment sheet is never used for the text.
- Structure and imaging domain are derived from the facility and technology records. Node type is not used.
- The August short description, specialties and Node profile are starting material, checked against the master first. Counts, cities, technologies and instruments always follow the master.
- Node contact: August master. Facility contacts: Knowledge Base Master.
- The technology section ends with a table of every registered technology, with instrument highlights per facility.
- A link appears on a page only if `check_links.py` opened it (or it is in `link_overrides.csv`).
- Facilities on membership hold stay off the page and are listed under missing information.
- Missing information is not printed on the page. It goes to `review/missing_information.md`.
- Short names: a name like "FRIM platform" becomes "FRIM", and two facilities sharing a bracketed acronym get their own names ("OptiRAD", "PhotoVivo" rather than "CRAN, ...").

## Making a similar set of files

For another page type (facility pages, technology pages, a newsletter), keep
the same split:

1. **One file per entity, same structure for every entity.** Put what the
   writer may use in a `briefing` block, what is printed as-is in a `record`
   block, and gaps in `missing_info`.
2. **Load once, join on stable keys.** Use URIs and EBI-FAC IDs, never
   database UUIDs. Reuse `kbdata.py`.
3. **Derive, do not copy, summary facts** (counts, structure, domain) from the
   records, so the text cannot disagree with the tables.
4. **Check older or secondary sources against the master** before use, the way
   `reconcile.py` does, and list everything left out.
5. **Check links before they reach a page.**
6. **Keep tables and contact blocks out of the AI's hands.** Render them in
   code; let the AI write prose only, with word targets per section.
7. **Write a test render** of every file before uploading (a small Node script
   that runs the render code with placeholder sections is enough), and look at
   two or three files by hand.
8. **Document the new file in this README**: fields, sources, rules.
