# How to run the Node description workflow

From the files on your laptop to 40 finished Node pages in Google Drive.

In this repo the files are split over `n8n/` (workflow, prompt, code), `scripts/`
(Python build and tools) and `docs/`. On Joakim's laptop they all sit in one folder,
`EuroBioImaging_Master_Data\n8n`, which is what the steps below call "the n8n folder".
The Knowledge Base xlsx files and the generated `node_files/` are not in the repo.

Status on 14 Oct 2026: the links are checked and the 40 Node files are built.
Start at **Part 2**. Come back to Part 1 only when the master changes.

---

## Part 1. Rebuild the Node files (only when the master changes)

1. Open File Explorer at the n8n folder (in the repo: `scripts/`).
2. Click the address bar, type `powershell`, press Enter.
3. First time only: `python -m pip install openpyxl requests`
   (if `python` is not recognised, use `py` instead in every command).
4. `python check_links.py` (5 to 10 minutes; checks every website link).
5. `python build_node_files.py` (1 minute). The last lines must say
   `Wrote 40 Node files`.

Link files you can edit in Notepad (the build reads them every time):

| File | Use |
| --- | --- |
| `link_overrides.csv` | A site that blocks the check but works: `url,true,Joakim,date,note` |
| `link_replacements.csv` | A page that moved: `old_url,new_url,Joakim,date,note` (also add the new url to `link_overrides.csv`) |
| `extra_node_websites.csv` | A Node website the August master lacks: `node_uri,url,Joakim,date` |

---

## Part 2. Upload the Node files to Google Drive

Use the Google account that n8n uses ("Google Drive account").

1. Go to https://drive.google.com.
2. If an older `node_files` folder is there: right-click it, **Move to bin**.
3. Click **+ New** (top left), then **Folder upload**.
4. Pick the `node_files` folder that `build_node_files.py` wrote,
   click **Upload**, confirm.
5. Wait for "40 uploads complete" (bottom right).

The finished pages will go to your existing Drive folder **EB-Nodes**. If it
holds pages from earlier test runs, move them out first so you do not mix old
and new versions (a re-run adds files with the same name, it does not replace).

---

## Part 3. Import and connect the workflow in n8n

### 3.1 Import

1. Open https://joakimedman.app.n8n.cloud, go to the project **EB_Nodes**.
2. **Create workflow**.
3. Top right **...** menu, **Import from file...**, pick
   `EB-NODES_KB_workflow.json` (in the repo: `n8n/EB-NODES_KB_workflow.json`).
4. You see 17 boxes and 3 coloured notes. Click **Save**.

If you imported an earlier version today, delete that one (Overview, the
workflow's **...**, **Delete**) so you do not run the old copy by mistake.

### 3.2 Accounts

Double-click each box and look at **Credential to connect with** at the top.
If it is empty or red, pick the account from the list. Close the box.

| Box | Account |
| --- | --- |
| List node files | Google Drive account |
| Download node file | Google Drive account |
| Upload node page to Drive | Google Drive account |
| Save sections to sheet | Google Sheets OAuth2 API |
| Archive briefing | Google Sheets OAuth2 API |
| Anthropic Chat Model | Anthropic account |

### 3.3 Point "List node files" at the uploaded folder

1. Double-click **List node files**.
2. In **Filter**, at **Folder**, choose **From list** and click the
   `node_files` folder from Part 2.
3. Close the box, **Save**.

Do this again every time you re-upload `node_files` (the new folder has a new ID).

### 3.4 Quick look

The copy of the workflow in this repo has no account IDs, Drive folder ID or
spreadsheet ID. After importing it, pick the accounts (3.2), the `node_files`
folder (3.3), the **EB-Nodes** folder in **Upload node page to Drive** and, only if
you switch the sheet boxes on, the spreadsheet in the two sheet boxes.

- **Upload node page to Drive**: Folder = **EB-Nodes**.
- **Save sections to sheet**: EB-NODES_pipeline_sheets_v1, sheet **Node_Body_Output**.
- **Archive briefing**: same spreadsheet, sheet **Node_Briefings**.
- **Anthropic Chat Model**: model `claude-opus-5-5` (By ID), Maximum Number of Tokens 16000, Prompt Caching off. Leave temperature, top K, top P and thinking unset (adaptive thinking is always on; setting them gives an error 400).
- **Save sections to sheet** and **Archive briefing** are switched off. Leave them off.

---

## Part 4. Test one Node

1. Double-click **Pick node files**.
2. In the code, change `const NODE_FILTER = "";` to

   ```
   const NODE_FILTER = "swedish";
   ```

3. Close, **Save**, then click **Execute workflow** (bottom of the canvas).
4. Boxes turn green in turn. "AI Node Writer" takes 1 to 2 minutes.
5. Open **EB-Nodes** in Drive. Download
   `swedish-national-microscopy-infrastructure-nmi.md` and open it in
   Notepad (or any Markdown viewer). Check:
   - five written sections, about 1,000 words together, no invented facts;
   - the technology table (Technology, Instrument highlights);
   - the facility table (Facility linked to its website, Institution, City);
   - addresses and contacts under "Access and contact", no coordinates.

If the text needs changes, tell me what is wrong; the prompt is
`node_writer_system_prompt_v14.md` and a new workflow file is one command.

---

## Part 4b. Test set of three representative Nodes

After any change to the prompt or the page layout, run these three first. They
cover a single-facility preclinical Node, a medium microscopy Node and the
largest biomedical Node:

```
const NODE_FILTER = "center-for-advanced-preclinical-imaging-capi, swedish-national-microscopy-infrastructure-nmi, france-life-imaging-node";
```

Download the three `.md` files from the output folder into
a `test_pages` folder
and ask Claude to review them; it can read that folder directly.

## Part 4c. Trial run of the 15 October changes (prompt v11, Clean v3, Render v11)

Five Nodes that exercise every fix (unregistered methods, single facility, very
large Node, service list, instrument tables, contacts):

```
const NODE_FILTER = "barcelona-mesoscopic-imaging-node, barcelona-live-and-intravital-node, brain-imaging-network-bin, austrian-bioimaging-node-cmi, advanced-nl-microscopy";
```

Put the five pages in `test_pages` and check them with:

```
python tools/check_pages.py test_pages
```

## Part 4d. Rebuild finished pages without a new AI run

When only the tables, lists or contacts change, the AI text can be kept:

```
node tools/rerender.js EB-NODES_KB_workflow.json node_files <folder with pages> <new folder>
```

## Part 5. Run all 40 Nodes in four batches

One batch of 10 takes about 15 to 20 minutes. Batches keep each run short (n8n
Cloud may stop very long runs) and, if something fails, you only redo that
batch. For each batch: open **Pick node files**, replace the `NODE_FILTER`
line with the line below, **Save**, **Execute workflow**, wait until it stops.

Batch 1:
```
const NODE_FILTER = "advanced-light-and-electron-microscopy-node-prague-cz, advanced-light-microscopy-italian-node, advanced-light-microscopy-node-poland, advanced-nl-microscopy, austrian-bioimaging-node-cmi, barcelona-live-and-intravital-node, barcelona-mesoscopic-imaging-node, barcelona-super-resolution-light-and-nanoscopy-node, bilbao-node, brain-imaging-network-bin";
```

Batch 2:
```
const NODE_FILTER = "cellular-imaging-hungary, center-for-advanced-preclinical-imaging-capi, challenges-framework-flagship-node, danish-bioimaging, digital-imaging-multimodal-platform-neuromed-dimp-neuromed, dutch-high-field-imaging-hub, euro-bioimaging-embl-node, facility-of-excellence-in-imaging-ammi-maastricht, finnish-advanced-microscopy-node, finnish-biomedical-imaging-node";
```

Batch 3:
```
const NODE_FILTER = "flanders-bioimaging-imaging-node, france-life-imaging-node, french-bioimaging-node, israel-bioimaging, madrid-advanced-microscopy-center-madmic, medical-and-preclinical-imaging-hungary, molecular-imaging-italian-node, multimodal-imaging-node-brno-cz, normic-oslo-advanced-light-microscopy-node-oslo, normolim-norwegian-molecular-imaging-infrastructure";
```

Batch 4:
```
const NODE_FILTER = "phase-contrast-imaging-flagship-node-trieste, population-imaging-flagship-node-rotterdam, portuguese-platform-of-bioimaging-ppbi, preclinical-imaging-centre-prime-molecular-imaging-dutch-node, radiology-and-medical-imaging-valencia, simbion-node, smart-optical-microscopy-som-node, sofia-bioimaging-node-advanced-light-microscopy-node-sofia-bulgaria, swedish-national-microscopy-infrastructure-nmi, the-uk-node";
```

To redo single Nodes, list just those: `const NODE_FILTER = "danish, flanders";`.

When all four are done, **EB-Nodes** has 40 `.md` files.

---

## Part 6. If a box turns red

Click the red box; the error is in the panel on the right. The run stops at
that Node; pages already uploaded stay in Drive. Fix the cause, then rerun only
the Nodes that are missing (Part 5, last tip).

| Red box | Message (roughly) | Fix |
| --- | --- | --- |
| List node files | folder missing / no access | Part 3.3: pick the folder again |
| Pick node files | "No Node files found" | Typo in NODE_FILTER, or the folder is empty |
| Download node file, Upload node page to Drive | 401 / invalid credentials | Part 3.2: reconnect Google Drive account |
| Save sections to sheet, Archive briefing | 401, or sheet not found | Part 3.2 and 3.4 |
| Anthropic Chat Model, AI Node Writer | 401 / invalid API key | Part 3.2: check the Anthropic account |
| Anthropic Chat Model, AI Node Writer | 429 / overloaded / rate limit | Wait a few minutes, rerun that Node (it already retried 3 times) |
| Clean and explode sections | "missing section(s)" or "no parseable JSON" | The writer answered in the wrong format once; rerun that Node. If it repeats, send me the message |
| Clean and explode sections | "does not mention ... or any of its facilities" | The writer returned another Node's text. Unpin data on AI Node Writer, check Prompt Caching is off, rerun that Node |
| Render node page | "different node" | Rerun that Node alone |

Nothing happens at all after **Execute workflow**: the Drive folder is empty,
or "List node files" points at the wrong folder (Part 3.3).

---

## What the workflow does (for reference)

1. **List node files** lists the JSON files in your Drive folder.
2. **Pick node files** keeps the Nodes in NODE_FILTER (all if empty), each once.
3. **Loop Over Nodes** takes one Node at a time.
4. **Download node file** and **Read node file** load that Node's file.
5. **AI Node Writer** (Claude Opus 5.5, prompt v14) writes five sections.
6. **Clean and explode sections** checks all five are there, checks the text belongs to this Node, and removes em dashes.
7. **Save sections to sheet** (off) would store them in Node_Body_Output.
8. **Render node page** adds the technology table, service list, facility
   table and contacts.
9. **Create markdown file** and **Upload node page to Drive** save
   `<node_uri>.md` in EB-Nodes.
10. **Archive briefing** (off), then the loop takes the next Node.
