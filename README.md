# Euro-BioImaging Node pages

This repo holds the pipeline that writes the public description page of each
Euro-BioImaging Node (40 Nodes). An n8n workflow reads one JSON file per Node,
built from the EB Knowledge Base, has Claude write five sections of text, adds
tables and contacts in code, and saves one Markdown page per Node to Google Drive.

Owner and curator: Joakim Edman. Current version: prompt v14, October 2026.

## Where the content comes from

- **Methods, instruments, people and services** come only from the Knowledge Base.
- **Services** come from the Node's signed SLA (Annex 1.1) first. A Node with no
  SLA services falls back to the services recorded in the database, and the page
  marks that list with `*` ("Services offered*"). A Node with neither gets no
  Services section.
- **Facility websites and descriptions** are used only for specialty and research
  focus context. They never add a method, instrument or service.
- Counts, cities and institutions are derived from the facility records, so the
  text cannot disagree with the tables.
- A link is printed only if it opened in `check_links.py`.
- Tables, service lists and contacts are printed by code exactly as recorded.
  The AI only writes prose.

## Folders

| Folder | What is in it |
| --- | --- |
| `n8n/` | The workflow to import (`EB-NODES_KB_workflow.json`), the writer prompt (`node_writer_system_prompt_v14.md`) and the code of the boxes "Clean and explode sections" and "Render node page" |
| `scripts/` | Python that builds the Node files from the Knowledge Base (`build_node_files.py`, `kbdata.py`, `reconcile.py`, `tech_instruments.py`, `check_links.py`), rebuilds the workflow (`make_workflow.py`), the link CSVs, and `tools/` (`check_pages.py` to check finished pages, `rerender.js` to rebuild pages and keep the AI text) |
| `docs/` | `HOW_TO_RUN.md` (step by step), `NODE_FILES.md` (fields of a Node file, page layout, rules), `OPTIMISATION_2026-10-15.md` (review of the first batch and the fixes after it) |
| `AI Prompts/` | Prompts from the 2025 approach (rewriting website text with local models). Kept for reference |
| `rrexp-files/` | Node texts from that 2025 approach (RREXP 4.0). Kept for reference |

Not in the repo: the Knowledge Base xlsx files, the generated `node_files/`,
finished pages, backups and review outputs. The workflow JSON has no account,
Drive folder or spreadsheet IDs; you pick those in n8n after importing.

## Pipeline

1. `check_links.py` opens every Node, portal and facility link and writes `link_status.json`.
2. `build_node_files.py` reads the Knowledge Base Master (and the older August
   master, checked by `reconcile.py`) and writes `node_files/<node_uri>.json`.
   Each file has a `node_briefing` (what the writer may use), a `node_record`
   (what code prints) and `missing_info` (gaps, for review only).
3. The `node_files` folder is uploaded to Google Drive.
4. The n8n workflow "EB-NODES KB descriptions" runs:
   1. **List node files** and **Pick node files** (`NODE_FILTER` picks Nodes; empty means all)
   2. **Loop Over Nodes**, one Node at a time
   3. **Download node file** and **Read node file**
   4. **AI Node Writer** (Claude, `claude-opus-5-5`, prompt v14) writes Overview,
      Imaging technologies offered, Specialties and research focus, Services and
      user support, and Facilities, about 1,000 words
   5. **Clean and explode sections** checks the five sections, checks the text is
      about this Node, tidies it and writes review flags
   6. **Render node page** adds the technology table, service list, facility table
      and the access and contact block
   7. **Create markdown file** and **Upload node page to Drive** save `<node_uri>.md`
      in the Drive folder EB-Nodes
5. `tools/check_pages.py` checks the finished pages against the Node files.

## How to run

Click-by-click steps are in `docs/HOW_TO_RUN.md`. In short:

```
pip install openpyxl requests
set EB_KB_MASTER=path\to\EB_Knowledge_Base_Master.xlsx
set EB_AUGUST_MASTER=path\to\EuBI_Master_Nodes_and_Facilities_v1.xlsx
python scripts/check_links.py
python scripts/build_node_files.py
```

Without the two variables the scripts look for the xlsx files in the folder
layout used on Joakim's laptop. Then:

1. Upload `scripts/node_files` to Google Drive.
2. In n8n, import `n8n/EB-NODES_KB_workflow.json`, pick the Google Drive,
   Google Sheets and Anthropic accounts, the `node_files` folder in
   **List node files** and the output folder in **Upload node page to Drive**.
3. Set `NODE_FILTER` in **Pick node files** (one Node to test, then batches of 10)
   and click **Execute workflow**.

After changing the prompt or the code, `python scripts/make_workflow.py` rebuilds
the workflow JSON (it needs the original n8n export, see `EB_WORKFLOW_TEMPLATE` in
the script), or paste the prompt and the `.js` files into the boxes by hand.

## Changelog

### Writer prompt (`node_writer_system_prompt`)

- **v14** (16 Oct 2026): services are "the services recorded in the Euro-BioImaging
  database": SLA services first, database services as fallback. An empty list
  means no Services text.
- **v13** (16 Oct): services may only come from `services_support`, which now holds
  the signed SLA services only. No Services text when the Node has no SLA services.
- **v12** (16 Oct, team feedback): methods, services, instruments and which
  facility offers them come only from the structured fields; descriptions only
  give expertise and research focus. A method offered by one or two facilities is
  never presented as a Node-wide strength, and counts come from `provided_by`.
  Nothing on feasibility, sample acceptance, availability, booking, prices or how
  to get access.
- **v11** (15 Oct): a method is named only if it is in `technologies_by_category`,
  and only for the facilities in its `provided_by` list. The last Overview
  paragraph is a guide that points research communities to at most three
  facilities, and the Facilities section does not repeat it. Hyphens in compound
  words are fine, dashes as punctuation are not. On four test Nodes the review
  flags went from 12 (v10) to 1.
- **v10** (14 Oct): every facility in a list gets its city, or none does. "List"
  is not used as a verb for facilities. Fixed an example that began "Most users".
- **v9**: no claims about what most users do. Connecting two facts is fine only if
  both are in the briefing.
- **v8**: at most three techniques, instruments or places in one sentence.
  Biosafety facts stay with their facility. Specialties no longer repeats staff
  expertise from the Overview.
- **v7**: longer Overview (230 to 290 words, two or three paragraphs) with a
  paragraph on staff expertise. Facility counts only from
  `facility_counts.authoritative`, places only from `geography`. Facilities are
  named by short name, with the city at first mention. Word targets per section,
  three invented examples of the target style, and a final read-through (at most
  one semicolon and one colon per section).
- **v6**: plain writing rules: the voice of a core facility manager, sentences of
  about 12 to 25 words, known information first and new information last, no
  inflated words such as "state-of-the-art" or "comprehensive".
- **v5**: before writing, the model works out the Node's main strength from
  `strength_profile` and its two or three distinctive strengths, and writes every
  section around that.
- **v4**: rewritten around the reader, a researcher deciding whether the Node
  can help, with one question per section. About half the length of v3.
- **v3**: uses the checked August Node profile, the older short description and
  specialties, and technology guidance as background only. New Services section,
  placed before Facilities. The technology table and service list are rendered
  under the text.
- **v2**: Overview uses the imaging domain and structure derived from the records
  instead of the Node type. Per-facility fields start with the short name.
- **v1** (14 Oct): first prompt for Knowledge Base Node files. Five sections in
  one JSON object, every fact must come from the briefing, tables and contacts
  are left to code.

### Read node file

- **v1** (14 Oct): new box. Parses the downloaded Node file and stops if `node`,
  `node_briefing` or `node_record` is missing. It replaced the Google Sheets reads
  and "Build node briefing" of the earlier workflow, together with the new boxes
  List node files, Pick node files (v2: `NODE_FILTER`, each file once, index file
  skipped) and Download node file. No changes since.

### Clean and explode sections

- **16 Oct, latest**: an empty answer from the writer now stops the run with its
  own message (out of tokens) instead of "no parseable JSON".
- **16 Oct**: when the Node has no services, any Services text is dropped and
  flagged. "Elemental analysis/EDX" is flagged when the Node does not register it.
- **v3** (15 Oct): every section is tidied before it reaches the page: dashes,
  headings, bold, bullet marks, "Access:" lines and email addresses. Each section
  gets `review_flags` (word count, more than one semicolon or colon, banned words
  such as "unique", "comprehensive", "most users", "listed as", emails, methods
  the Node does not register). Flags never stop the run.
- **v2** (14 Oct): batch safety (the Node name comes from the current loop round,
  so 40 Nodes are never saved under one name). Reads from Read node file. Accepts
  the writer's JSON in several shapes after a run failed with "no sections array".
  Stops and lists what came back when a section is missing. Identity check: stops
  if the text names neither the Node nor any of its facilities (added after one
  page came back with another Node's text). Removes em dashes.
- **v1**: takes the first complete JSON object from the answer (balanced-brace
  scan from the EB-TECH workflow) and emits one item per section.

### Render node page

- **16 Oct, latest**: the "(provisional)" mark is gone from the technology table
  (the flag stays in the Node file). The service list heading is "Services
  offered*" when the list comes from the database, and the Services section is
  left out when the Node has no services.
- **v12** (16 Oct): no links in the AI text. Technology names in the table carry
  the technology URI (`TECH_URL` can turn them into links once the Access Portal
  has technology pages). Facility names in the facility table and locations carry
  the facility URI. A facility's general mailbox is listed before people. Empty
  instrument cells stay empty (`NO_INSTRUMENT` is off).
- **v11** (15 Oct): a facility whose only link is the Access Portal page gets no
  link. "+ network" is dropped from facility names, an address with several towns
  uses the first, bare "Instruments" and internal notes are dropped from the
  service list. A final pass removes dashes used as punctuation and any "Access:"
  line. Review flags from Clean are collected on the output.
- **v10**: coordinates are no longer printed. Contacts without a person show as
  "General enquiries".
- **v9**: the missing-information list is no longer printed on the page.
- **v8**: facility table with three columns (Facility linked to its website,
  Institution, City). Paragraph breaks from the writer are kept.
- **v7**: technology table with two columns, Technology and Instrument highlights
  (every named model, grouped by facility short name).
- **v6**: the technology table lists every registered technology with the
  instruments the providing facilities document for it.
- **v5**: section order Overview, Imaging technologies, Specialties, Services,
  Facilities. The facility table opens the Facilities section. Access routes are
  shown with the contacts.
- **v4** (14 Oct): reads the Node file from Read node file. Facility names link to
  their checked websites, the Services section is followed by the service list,
  and each facility shows its address.
- **v3**: batch safety. **v2**: short-name column.

### Create markdown file

- **14 Oct**: the file starts with a UTF-8 byte-order mark and is saved as
  `text/markdown; charset=utf-8`, so letters such as Č, ě and ů show correctly in
  Windows and Google Drive.
- **v1**: turns the page into a binary file named `<node_uri>.md` for the Drive
  upload, and stops if the page or file name is missing.

### Workflow settings

- **16 Oct**: max tokens raised from 16,000 to 21,000 after PPBI (20 facilities)
  came back empty because thinking used the whole budget. 21,000 is close to the
  most n8n allows without streaming.

- Model `claude-opus-5-5` by ID, 21,000 max tokens, temperature, top K and top P
  unset (they give an error 400), prompt caching off.
- The briefing is sent as compact JSON, which halves the prompt for the largest Nodes.
- AI Node Writer and Upload node page to Drive retry up to 3 times.
- Save sections to sheet and Archive briefing are switched off; the output is the
  Markdown file only.
