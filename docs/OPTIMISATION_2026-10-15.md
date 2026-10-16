# Node pages: review of batch 1 and optimisation (15 October 2026)

Reviewed: the 10 pages of batch 1 (Prague, Italy, Poland, NL, Austria, BLivIN, B-Min, SLN@BCN, Bilbao, BIN).
Checked against: `node_files/<node>.json` with the new checker `tools/check_pages.py`.

## 1. Verdict

The AI text is good. Every page is about the right Node, counts and cities match the master, and the
closing paragraph of the Overview works as a guide for researchers. Most problems sat in the parts
built by code (tables, service lists, contacts), and those are now fixed. One real content problem
remained in the AI text: methods that the Node does not register.

| Check | Batch 1 as delivered | Batch 1 rebuilt with new code (same AI text) |
| --- | --- | --- |
| All flags | 52 | 22 |
| Problems in tables, lists, contacts | 30 | 0 |
| Methods not registered, or attached to a facility that does not provide them | 22 | 22 (needs prompt v11, see 3) |

## 2. What was wrong and where it is fixed

| Problem seen | Example | Fixed in |
| --- | --- | --- |
| Junk words in instrument cells | "AMC-specific official Node inventory:", "LSM 980 documented FRAP", "IX83 TIRF configuration", "(50-80 nm; live-compatible)", "Imaging flow cytometry (Cytek ImageStream MKII)" | `tech_instruments.py` |
| Grouped model lists put in the wrong row | NL: Tecnai and JEM TEMs in the EDX and SEM rows; B-Min: Raman system in the confocal row; Austria: Krios and Glacios in the chemically fixed TEM row | `tech_instruments.py` (lists split per model, then matched one by one) |
| Maker spelt three ways, duplicates | "Thermo Scientific Glacios" and "Thermo Fisher Glacios"; "Micro-CT, SCANCO, µCT35" | `tech_instruments.py` |
| Bare "Instruments" in every service list | all pages | `build_node_files.py`, `render_node_page.js` |
| Internal notes in service lists | "[Partial list: incomplete logistics wording remains open.]", "Not established, see SQ09 in Services Questions - INTERNAL." (Valencia), "[Site scope: ...]" (France and others) | `build_node_files.py` (notes removed, site notes become "(at NeurImag)") |
| Broken service fragments | "no mouse/rodent facility access" as its own bullet | `build_node_files.py` (joined to the item before) |
| Raw contact roles | "(TECHNICAL_CONTACT)", "(senior/formal or historical contact)", "(Node Contact)", "Facility/service contact" | `build_node_files.py` (historical contacts dropped, roles in plain words) |
| Long short name | "Jagiellonian University site within Advanced Light Microscopy Node Poland" | `build_node_files.py` (now "Jagiellonian University site") |
| Same institution counted twice because of a dash | "Biofisika Institute (CSIC–UPV/EHU)" and "(CSIC-UPV/EHU)" | `build_node_files.py` (all dash characters become "-" before counting; Bilbao now 2 institutions) |
| Facility linked to the Access Portal page | Padua, LLTM, ICNAS | `render_node_page.js` (no link instead) |
| "+ network" in a facility name | ICNAS | `render_node_page.js` |
| Address with four towns | "4020 Linz / Hagenberg / Wels / Steyr" | `render_node_page.js` (first town only) |
| Access lines | "Access: Open access via Euro-BioImaging (...)" | `render_node_page.js` and `clean_and_explode_sections.js` |
| Dashes | em dash, spaced en dash, non-breaking hyphens | `clean_and_explode_sections.js` and a final pass in `render_node_page.js`: a dash used as punctuation becomes a comma, every other dash character becomes "-", "3 – 4" becomes "3-4" |

Changes to the 40 Node files: 97 of 1,092 instrument cells changed, and only one cell became
empty (LBIC "national 7T facility", which is not an instrument).

## 3. The AI text: methods the Node does not register

The writer sometimes takes a method from a facility description even though the Node does not
register it. Examples: STED and STORM on B-Min (SLN offers them, but under SLN@BCN), light-sheet on
SLN@BCN, MINFLUX on Poland, EEG and retinal OCT on BIN, intravital at ALMU. A researcher could ask
for something that cannot be requested through that Node.

Prompt v11 adds one rule (name a method only if it is in technologies_by_category, and attach it only
to facilities in its provided_by list) and a matching line in the final check.

## 4. Prompt v11 and the simulated runs

Each prompt was run on four Nodes chosen to test the weak points: B-Min (unregistered methods), BLivIN
(STED instrument name, ALMU intravital), BIN (single facility) and Austria (19 facilities). The runs
used the same model and the exact message n8n sends.

| Prompt | Flags on 4 Nodes | Notes |
| --- | --- | --- |
| v10 (current) | 12 | STED, STORM, EEG, OCT, lifetime imaging and CLEM named without registration |
| v11 first draft | 2 | Unregistered methods gone. Side effect: hyphens dropped ("carbon 11", "live cell", "short lived") |
| v11 final | 1 | Hyphens back ("carbon-11", "live-cell"), no dashes as punctuation. Only flag: BIN Facilities is short, which is expected for a one-facility Node |

Other changes in v11:

1. **The closing Overview paragraph is now an explicit guide**, because that is the part you liked.
   It points each research community to the facility that serves it, with at most three facilities.
   Example from the Austria run: "Structural biologists will find the most specialised help at the
   Electron Microscopy Facility in Klosterneuburg. Cell biologists who need confocal, super-resolution
   or live-cell imaging can turn to MedUni Vienna Core Facility Imaging."
2. **The Facilities section no longer repeats that guide.** It covers the facilities the guide did not
   name and how the sites work together.
3. **Hyphen rule clarified.** "No dashes" now means no dash used as punctuation. Hyphens in compound
   words stay, which reads more naturally.

## 5. New checks in the workflow (they never stop a run)

`Clean and explode sections` v3 now:

- tidies every section: dashes, headings, bold, bullet marks, "Access:" lines and email addresses
- writes `review_flags` per section: word count, more than one semicolon or colon, banned words
  ("unique", "comprehensive", "most users", "listed as" and others), email addresses and methods
  not registered for the Node

`Render node page` collects them in `review_flags`, so you can see them in the n8n output of each run.

## 6. New tools

- `tools/check_pages.py <folder>` checks finished pages (or writer JSON) against the Node files, as in
  this review.
- `tools/rerender.js` rebuilds finished pages with the current code and Node files and keeps the AI text.
  The batch 1 pages rebuilt this way are in `review/batch1_rerendered`.
- `tools/tidytest.js` tests the tidying in Clean.

All earlier tests still pass: `tools/sim.js` (40 of 40) and `tools/cleantest.js` (7 OK, 2 expected errors).

## 7. Data issues for the Data Enrichment sheet (not changed by code)

- ALEMBIC (Italy): facility contact is the Naples Node contact, with another email.
- LLTM (Poland): no registered technologies, although its record lists spinning disk, confocal, ELYRA PALM and laser microdissection systems.
- Naples (Italy): institution recorded as "IEOMI-CNR, second unit".
- One SLN@BCN contact: three different emails across pages.
- BRALM (Bilbao): contact is the BREM technical director, with the BRALM mailbox.
- SLN: different website on the B-Min and SLN@BCN pages.
- NMR Laboratory (FLI), LiiFE (FLI) and Swedish NMI contacts: see the 14 October handover.

## 8. Backups

The code and Node files from before these changes are in `backup_20261015/`.

## 9. Update 16 October (team feedback from Ali and Aman)

- Prompt v12: methods, services, instruments and which facility offers them come only from the structured Knowledge Base fields; descriptions are used only for expertise and research focus. A method offered by one or two facilities is never presented as a Node-wide strength, and facility counts come from provided_by. Nothing on feasibility, sample acceptance, availability, booking, prices or how to get access.
- Render v12: the first mention of each facility in the text links to its checked website. Technology names can link to a technology page through `TECH_URL`, which is empty for now because the Access Portal has no technology pages yet ("Coming Soon") and the old eurobioimaging.eu/service pages return 404. General mailboxes are listed before people. Empty instrument cells stay empty (team preference); `NO_INSTRUMENT` can fill them later.
- Tables stay, as agreed with the team.
- Simulated v12 on Austria and BLivIN: the Austria SMLM count is now right; one known BLivIN item remains (ALMU described with intravital imaging, which its own description states but its registration does not).

## 10. Services from signed SLAs only (16 Oct, prompt v13)

- Services now come only from Node Services rows with source_type SLA_ANNEX_1_1 (signed SLA, Annex 1.1). Facility web-page services, workflow support and "Services include ..." sentences are no longer in the AI briefing.
- New briefing key services_contracted. 11 Nodes have no SLA services: no service list, empty Services section, no services described anywhere.
- Prompt v13: only services_support may be mentioned; final check against it. Clean: empty Services text allowed when not contracted.
- Sim check: BLivIN Services text uses only the SLA list (courses, cell-line maintenance, immunocytochemistry, macros gone); SLN@BCN Services empty, no services elsewhere.

## 11. Fallback for Nodes without SLA services (16 Oct, prompt v14)

- SLA services stay the first source. A Node with no SLA rows now falls back to its service summary in the Nodes sheet (the list the pages had before). services_basis = SLA / DATABASE in briefing and record.
- Render: "### Services offered*" when the list comes from the database, so these can be checked later. 10 Nodes carry the asterisk; Medical and Preclinical Imaging Hungary has no services at all and gets no Services section.
- Prompt v14: services_support is "the services recorded in the Euro-BioImaging database"; empty list = no Services text. Clean drops Services text only when services_support is empty.

## 12. Final production check (16 Oct, prompt v14)

- Workflow JSON: prompt == v14, Clean and Render code == files, model claude-opus-5-5, 16000 tokens, retry on, sheet boxes off, loop wired on the "loop" output, NODE_FILTER "". The JSON's "List node files" folder is blank, so pick the folder if importing instead of pasting.
- Code test (tools/sim.js): 40 of 40 Nodes; cleantest as expected.
- Real writer test, 5 Nodes through Clean, Render and Create markdown (tools/runreal.js, pages in review/final_check/pages): BLivIN (SLA), France Life Imaging and Sofia (database, starred), Medical and Preclinical Imaging Hungary (no services, no Services section, no services in the text), Austria. No errors, no dashes, no Access lines. check_pages: 5 minor flags (Austria CIUS "correlative light and electron" inferred; Sofia Facilities 179 words; Sofia instrument "Lifetime/PIE configuration"; LabTAU ultrasound research is specialty context; Hungary Services missing is expected).
