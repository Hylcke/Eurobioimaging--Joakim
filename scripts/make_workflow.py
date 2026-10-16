"""Build the importable n8n workflow from the existing EB-NODES workflow.

Usage:
    python make_workflow.py

Reads  ../../data/reference/EB-NODES9.json (the current workflow export, not in git;
       set EB_WORKFLOW_TEMPLATE to use another path)
       node_writer_system_prompt_v14.md, clean_and_explode_sections.js, render_node_page.js
       (from ../n8n/ in the git repo, or from this folder)
Writes EB-NODES_KB_workflow.json, ready for n8n: Workflows > Import from file.

Kept as they are: Loop Over Nodes, AI Node Writer (new system prompt),
Anthropic Chat Model, Clean and explode sections, Save sections to sheet,
Create markdown file, Upload node page to Drive, Archive briefing.
Removed: the Google Sheets reads and "Build node briefing".
Added: List node files, Pick node files, Download node file, Read node file.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
# In the git repo the prompt, the code and the workflow live in ../n8n/.
N8N = HERE.parent / "n8n" if (HERE.parent / "n8n" / "render_node_page.js").exists() else HERE
SRC = Path(os.environ.get("EB_WORKFLOW_TEMPLATE") or HERE.parent.parent / "data" / "reference" / "EB-NODES9.json")
OUT = N8N / "EB-NODES_KB_workflow.json"

PICK = r"""// ============================================================
// PICK NODE FILES v2
// Keeps the Node files (*.json) from the Drive folder listing and, if
// NODE_FILTER is set, only the Nodes whose file name contains one of the
// comma-separated words. A file name that appears twice is used once.
// Examples: NODE_FILTER = "swedish"   or   "danish, flanders, embl"   or   "" for all Nodes.
// Language: JavaScript | Mode: Run Once for All Items
// ============================================================
const NODE_FILTER = "";

const words = NODE_FILTER.split(',').map(w => w.trim().toLowerCase()).filter(Boolean);
const seen = new Set();
const files = [];
for (const f of $input.all().map(i => i.json)) {
  const name = String(f.name || '');
  const low = name.toLowerCase();
  if (!low.endsWith('.json') || low === 'node_files_index.json') continue;
  if (words.length && !words.some(w => low.includes(w))) continue;
  if (seen.has(low)) continue;   // the same file uploaded twice
  seen.add(low);
  files.push({ id: f.id, name });
}
files.sort((a, b) => a.name.localeCompare(b.name));

if (!files.length) {
  throw new Error('No Node files found. Check the folder in "List node files" and NODE_FILTER (now: "' + NODE_FILTER + '").');
}
return files.map(f => ({ json: f }));
"""

READ = r"""// ============================================================
// READ NODE FILE v1
// Parses the downloaded Node file (built by build_node_files.py from the EB
// Knowledge Base Master) into node, country, node_briefing, node_record and
// missing_info, the shape "AI Node Writer" and "Render node page" expect.
// Language: JavaScript | Mode: Run Once for All Items
// ============================================================
const buffer = await this.helpers.getBinaryDataBuffer(0, 'data');
let doc;
try {
  doc = JSON.parse(buffer.toString('utf-8'));
} catch (e) {
  throw new Error('The Node file is not valid JSON: ' + e.message);
}
for (const key of ['node', 'node_briefing', 'node_record']) {
  if (!doc[key]) throw new Error(`The Node file has no "${key}".`);
}
return [{ json: doc }];
"""


def nid() -> str:
    return str(uuid.uuid4())


PROMPT_FILE = "node_writer_system_prompt_v14.md"


def main() -> None:
    wf = json.loads(SRC.read_text(encoding="utf-8"))
    nodes = {n["name"]: n for n in wf["nodes"]}
    drive_cred = nodes["Upload node page to Drive"]["credentials"]

    drop = {"Get Master Nodes", "Get Master Facilities", "Get Questionnaire Nodes", "Get Questionnaire Facilities",
            "Get Questionnaire Contacts", "Build node briefing"}
    keep = [n for n in wf["nodes"] if n["name"] not in drop and not (
        n["type"].endswith("stickyNote") and "Questionnaire" in n["parameters"].get("content", ""))]

    for n in keep:
        if n["name"] == "AI Node Writer":
            n["parameters"]["options"]["systemMessage"] = (N8N / PROMPT_FILE).read_text(encoding="utf-8")
            # Compact JSON halves the prompt size of the biggest Nodes.
            n["parameters"]["text"] = n["parameters"]["text"].replace(
                "JSON.stringify($json.node_briefing, null, 2)", "JSON.stringify($json.node_briefing)")
            assert "JSON.stringify($json.node_briefing)" in n["parameters"]["text"]
            # A busy or failed API call is retried before the run stops.
            n.update({"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000})
        if n["name"] == "Create markdown file":
            # A byte-order mark tells Windows and Drive the file is UTF-8, so Č, ě, ů show correctly.
            code = n["parameters"]["jsCode"]
            old = "Buffer.from(markdown, 'utf-8')"
            assert old in code
            code = code.replace(old, "Buffer.from('\\uFEFF' + markdown, 'utf-8')")
            code = code.replace("'text/markdown'", "'text/markdown; charset=utf-8'")
            n["parameters"]["jsCode"] = code
        if n["name"] == "Anthropic Chat Model":
            # Claude Opus 5.5: temperature, top K and top P must be left unset (400 error otherwise);
            # adaptive thinking is always on and shares max tokens with the answer.
            # 21000: large Nodes (PPBI) used all of 16000 on thinking and returned empty text.
            # Above about 21,300 the Anthropic SDK refuses non-streaming calls ("Streaming is required").
            n["parameters"]["model"] = {"__rl": True, "value": "claude-opus-5-5", "mode": "id"}
            n["parameters"]["options"] = {"maxTokensToSample": 21000}
        if n["name"] in ("Archive briefing", "Save sections to sheet"):
            # Output is the Markdown file only; the Sheets copies are switched off (data passes through).
            n["disabled"] = True
        if n["name"] in ("Upload node page to Drive", "Archive briefing", "Save sections to sheet"):
            n.update({"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 3000})
        if n["name"] == "Render node page":
            n["parameters"]["jsCode"] = (N8N / "render_node_page.js").read_text(encoding="utf-8")
        if n["name"] == "Clean and explode sections":
            code = n["parameters"]["jsCode"]
            code = code.replace("const loopItem = $('Loop Over Nodes').first().json;",
                                "const loopItem = $('Read node file').first().json;")
            code = code.replace("Could not read from \"Loop Over Nodes\". That node must exist between \"Build node briefing\" and \"AI Node Writer\".",
                                "Could not read from \"Read node file\".")
            code = code.replace('Check that "Loop Over Nodes" sits between "Build node briefing" and "AI Node Writer" with a batch size of 1.',
                                'Check that "Loop Over Nodes" has a batch size of 1.')
            # Identity check: the written text must be about the Node being processed.
            old_ret = "\nreturn results;"
            assert code.rstrip().endswith("return results;")
            guard = r"""
// ------------------------------------------------------------
// IDENTITY CHECK. The text must be about the Node of this loop round: it has to
// name the Node or at least one of its facilities. Otherwise the run stops,
// so a page can never be filled with another Node's text.
// ------------------------------------------------------------
{
  const doc = $('Read node file').first().json;
  const b = doc.node_briefing || {};
  const names = new Set();
  const add = v => { const t = String(v || '').trim(); if (t.length >= 3) names.add(t.toLowerCase()); };
  add(doc.node);
  (String(doc.node).match(/\(([^)]+)\)/g) || []).forEach(m => add(m.slice(1, -1)));
  (b.facilities || []).forEach(f => { add(f.short_name); add(f.name); });
  const allText = results.map(r => r.json.section_text).join(' ').toLowerCase();
  const hit = [...names].some(n => allText.includes(n));
  if (!hit) {
    throw new Error(`The written text does not mention "${doc.node}" or any of its facilities. ` +
      'It may belong to another Node. Check that "AI Node Writer" has no pinned data and turn off prompt caching, then rerun this Node.');
  }
}
"""
            code = code.rstrip()[: -len("return results;")] + guard + "\nreturn results;\n"
            # Robust parsing: accept {sections:[...]}, a bare array, or loose section objects.
            old_parse = """const raw = inputItems[0].json.output;
const parsed = extractFirstJSONObject(typeof raw === 'string' ? raw : JSON.stringify(raw));
"""
            assert old_parse in code, "parse block not found in Clean step"
            new_parse = r"""const raw = inputItems[0].json.output;
// The writer is asked for {"sections": [...]}, but sometimes returns a bare list
// of sections, or the sections one after another. All three are accepted.
function allTopLevelObjects(text) {
  const out = [];
  let pos = 0;
  while (pos < text.length) {
    const start = text.indexOf('{', pos);
    if (start === -1) break;
    let depth = 0, inString = false, escaped = false, end = -1;
    for (let i = start; i < text.length; i++) {
      const ch = text[i];
      if (escaped) { escaped = false; continue; }
      if (ch === '\\') { escaped = true; continue; }
      if (ch === '"') { inString = !inString; continue; }
      if (inString) continue;
      if (ch === '{') depth++;
      else if (ch === '}') { depth--; if (depth === 0) { end = i; break; } }
    }
    if (end === -1) break;
    try { out.push(JSON.parse(text.slice(start, end + 1))); } catch (e) {}
    pos = end + 1;
  }
  return out;
}
function parseWriterOutput(value) {
  if (value && typeof value === 'object') return value;
  const text = String(value || '').replace(/^\s*```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '').trim();
  try { return JSON.parse(text); } catch (e) {}
  const objs = allTopLevelObjects(text);
  const wrapped = objs.find(o => o && Array.isArray(o.sections));
  if (wrapped) return wrapped;
  const loose = objs.filter(o => o && o.section_title);
  if (loose.length) return { sections: loose };
  return objs[0] || null;
}
let parsed = parseWriterOutput(raw);
if (parsed && !Array.isArray(parsed) && !Array.isArray(parsed.sections) && parsed.section_title) {
  parsed = { sections: [parsed] };  // a single section; the missing-section check below reports the rest
}
"""
            code = code.replace(old_parse, new_parse)
            old_order = '"Facilities",\n  "Services and user support"\n];'
            assert old_order in code, "section order not found in Clean step"
            code = code.replace(old_order, '"Services and user support",\n  "Facilities"\n];')
            n["parameters"]["jsCode"] = code
        if n["name"] == "Archive briefing":
            txt = json.dumps(n["parameters"])
            n["parameters"] = json.loads(txt.replace("$('Loop Over Nodes')", "$('Read node file')"))
            # A Google Sheets cell holds at most 50,000 characters; the full files stay on Drive.
            cols = n["parameters"]["columns"]["value"]
            for k in ("briefing", "record"):
                if k in cols:
                    cols[k] = cols[k].replace("node_" + k + ") }}", "node_" + k + ").slice(0, 49000) }}")
                    assert ".slice(0, 49000)" in cols[k], k
        if n["name"] == "Loop Over Nodes":
            n["position"] = [560, -64]
        if n["type"].endswith("stickyNote") and "Writer" in n["parameters"].get("content", ""):
            n["parameters"]["content"] = ("## Writer and loop checker\nOne Node file per loop: download, read, write five "
                                          "sections, check them, render the page with the facility table, technology "
                                          "list, services, contacts, locations and missing information, then upload "
                                          "the Markdown file.")

    # From v3 the Clean step is kept as a whole file (clean_and_explode_sections.js), not as patches.
    for n in keep:
        if n["name"] == "Clean and explode sections":
            n["parameters"]["jsCode"] = (N8N / "clean_and_explode_sections.js").read_text(encoding="utf-8")

    trigger = next(n for n in keep if n["type"].endswith("manualTrigger"))
    trigger["position"] = [-400, -64]
    new = [
        {"parameters": {"content": "## Node files\nThe files come from **build_node_files.py** "
                        "(EuroBioImaging_Master_Data/n8n), one JSON per Node built from the EB Knowledge Base Master. "
                        "Upload the node_files folder to Google Drive and pick that folder in **List node files**. "
                        "To run one Node, set NODE_FILTER in **Pick node files**.",
                        "height": 260, "width": 520, "color": 5},
         "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [-460, -360], "id": nid(), "name": "Sticky Note KB"},
        {"parameters": {"resource": "fileFolder", "returnAll": True,
                        "filter": {"folderId": {"__rl": True, "value": "", "mode": "list", "cachedResultName": ""},
                                   "whatToSearch": "files"},
                        "options": {"fields": ["id", "name", "mimeType"]}},
         "type": "n8n-nodes-base.googleDrive", "typeVersion": 3, "position": [-176, -64], "id": nid(),
         "name": "List node files", "credentials": drive_cred},
        {"parameters": {"jsCode": PICK}, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [176, -64],
         "id": nid(), "name": "Pick node files"},
        {"parameters": {"operation": "download",
                        "fileId": {"__rl": True, "value": "={{ $json.id }}", "mode": "id"}, "options": {}},
         "type": "n8n-nodes-base.googleDrive", "typeVersion": 3, "position": [912, 48], "id": nid(),
         "name": "Download node file", "credentials": drive_cred},
        {"parameters": {"jsCode": READ}, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [1264, 48],
         "id": nid(), "name": "Read node file"},
    ]
    conns = {k: v for k, v in wf["connections"].items() if k not in drop}
    conns[trigger["name"]] = {"main": [[{"node": "List node files", "type": "main", "index": 0}]]}
    conns["List node files"] = {"main": [[{"node": "Pick node files", "type": "main", "index": 0}]]}
    conns["Pick node files"] = {"main": [[{"node": "Loop Over Nodes", "type": "main", "index": 0}]]}
    conns["Loop Over Nodes"] = {"main": [[], [{"node": "Download node file", "type": "main", "index": 0}]]}
    conns["Download node file"] = {"main": [[{"node": "Read node file", "type": "main", "index": 0}]]}
    conns["Read node file"] = {"main": [[{"node": "AI Node Writer", "type": "main", "index": 0}]]}

    out = {"name": "EB-NODES KB descriptions", "nodes": keep + new, "connections": conns,
           "settings": {"executionOrder": "v1", "binaryMode": "separate"}, "pinData": {}}
    names = {n["name"] for n in out["nodes"]}
    for src, c in conns.items():
        assert src in names, src
        for branch in c.get("main", []) + c.get("ai_languageModel", []):
            for edge in branch:
                assert edge["node"] in names, edge["node"]
    for n in out["nodes"]:
        assert "Build node briefing" not in json.dumps(n.get("parameters", {})) or n["type"].endswith("stickyNote") \
            or n["name"] == "Clean and explode sections", n["name"]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(out['nodes'])} nodes")


if __name__ == "__main__":
    main()
