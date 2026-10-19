// ============================================================
// CLEAN AND EXPLODE SECTIONS v3.1
// v3.1 (19 Oct): review flags also catch evaluating or recommending phrases (strongest, suits,
// will find, natural place, within one Node). An empty writer answer stops the run with its own message.
// v3: every section is tidied before it reaches the page (dashes, stray markdown,
// "Access:" lines, people's email addresses), and style and fact checks are
// written to review_flags on each item. Flags never stop the run.
// EB-NODES pipeline. Place after "AI Node Writer".
// Language: JavaScript | Mode: Run Once for All Items
// ============================================================
//
// The agent returns all five sections in one JSON object. This node validates
// that object and emits one item per section, so each becomes its own row in
// Node_Body_Output and stays independently reviewable.
//
// BATCH SAFETY. Every item this node emits carries the name of the node it
// belongs to, taken from the current loop iteration rather than from the
// briefing node's full output. In batch mode the briefing node emits one item
// per Euro-BioImaging node, so $('Build node briefing').first() resolves to the
// FIRST node on every iteration, and all forty nodes' sections would be written
// to the sheet under one name. Downstream nodes read $json.node from here
// instead of reaching back.
//
// JSON extraction uses the balanced-brace scanner carried over from EB-TECH
// rather than a greedy regex. A greedy /\{[\s\S]*\}/ spans from the first "{"
// to the LAST "}", so if the model emits the object twice, or appends a fenced
// copy, both objects plus everything between them are swallowed into one invalid
// blob and a corrupted string reaches the sheet. The scanner returns the first
// span that actually parses and ignores anything after it.
// ============================================================

const EXPECTED_SECTIONS = [
  "Overview",
  "Imaging technologies offered",
  "Specialties and research focus",
  "Services and user support",
  "Facilities"
];

// ------------------------------------------------------------
// Extract the first complete, valid JSON object from a string.
// Walks the string tracking brace depth, respecting strings and escapes.
// ------------------------------------------------------------
function extractFirstJSONObject(text) {
  if (typeof text !== 'string') return null;

  for (let start = text.indexOf('{'); start !== -1; start = text.indexOf('{', start + 1)) {
    let depth = 0;
    let inString = false;
    let escaped = false;

    for (let i = start; i < text.length; i++) {
      const ch = text[i];
      if (escaped) { escaped = false; continue; }
      if (ch === '\\') { escaped = true; continue; }
      if (ch === '"') { inString = !inString; continue; }
      if (inString) continue;

      if (ch === '{') depth++;
      else if (ch === '}') {
        depth--;
        if (depth === 0) {
          try { return JSON.parse(text.slice(start, i + 1)); }
          catch (e) { break; }
        }
      }
    }
  }
  return null;
}

// ------------------------------------------------------------
// Normalise section titles for matching. The agent is told to return exact
// strings, but casing and stray whitespace should not cause a section to be
// dropped when the text itself is fine.
// ------------------------------------------------------------
function normTitle(v) {
  return String(v === undefined || v === null ? '' : v)
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

// ------------------------------------------------------------
// One agent response per iteration. More than one means the loop is missing or
// misconfigured, which in batch mode would silently process only the first node.
// Fail loudly instead.
// ------------------------------------------------------------
const inputItems = $input.all();
if (inputItems.length !== 1) {
  throw new Error(`Expected exactly one agent response, received ${inputItems.length}. ` +
    'Check that "Loop Over Nodes" has a batch size of 1.');
}

// Identity of the node being processed on THIS iteration.
let currentNode = '';
let currentSubmissionId = null;
try {
  const loopItem = $('Read node file').first().json;
  currentNode = loopItem.node || '';
  currentSubmissionId = (loopItem.node_record && loopItem.node_record.submission_id) || null;
} catch (e) {
  throw new Error('Could not read from "Read node file".');
}
if (!currentNode) {
  throw new Error('The current loop item carries no node name.');
}

const raw = inputItems[0].json.output;
if (typeof raw === 'string' && !raw.trim()) {
  throw new Error('AI Node Writer returned an empty answer, most likely because thinking used all the tokens. ' +
    'Raise Maximum Number of Tokens in "Anthropic Chat Model" (21000 at most without streaming) and rerun this Node.');
}
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

if (!parsed) {
  throw new Error('AI Node Writer returned no parseable JSON object. Check the raw output field of that node.');
}

// ------------------------------------------------------------
// Accept either the documented shape {sections:[...]} or a bare array, since a
// model occasionally drops the wrapper. Anything else is a real failure.
// ------------------------------------------------------------
let sections = null;
if (Array.isArray(parsed.sections)) sections = parsed.sections;
else if (Array.isArray(parsed)) sections = parsed;

if (!sections) {
  throw new Error('Parsed JSON has no "sections" array. Got keys: ' + Object.keys(parsed).join(', '));
}

// ------------------------------------------------------------
// Match returned sections to the expected five, in the expected order.
// Missing sections throw rather than passing silently, because a page assembled
// from four sections looks finished and is not.
// ------------------------------------------------------------
const byTitle = {};
for (const s of sections) {
  if (!s || !s.section_title) continue;
  byTitle[normTitle(s.section_title)] = s;
}

const missing = EXPECTED_SECTIONS.filter(t => !byTitle[normTitle(t)]);
if (missing.length) {
  throw new Error('Agent output is missing section(s): ' + missing.join(' | ') +
    '. Returned: ' + sections.map(s => s && s.section_title).join(' | '));
}

// ------------------------------------------------------------
// TIDY. Dashes used as punctuation become commas; every other dash-like character
// becomes a plain hyphen, so "CSIC–UPV" and "CSIC-UPV" are the same text. Headings,
// bold markers, bullet marks and "Access:" lines do not belong in running text.
// ------------------------------------------------------------
function tidy(text) {
  return String(text)
    .replace(/\r\n?/g, '\n')
    .replace(/(\d)\s*[\u2013\u2014]\s*(\d)/g, '$1-$2')  // "3 – 4 days" is a range
    .replace(/[ \t]*\u2014[ \t]*/g, ', ')
    .replace(/ \u2013 /g, ', ')
    .replace(/[\u2010\u2011\u2012\u2013\u2212]/g, '-')
    .replace(/\*\*|__/g, '')
    .split('\n')
    .filter(line => !/^\s*#{1,6}\s/.test(line) && !/^\s*Access:/i.test(line))
    .map(line => line.replace(/^\s*[-*\u2022]\s+/, '').replace(/[ \t]+$/g, ''))
    .join('\n')
    .replace(/[^\S\n]{2,}/g, ' ')
    .replace(/ ,/g, ',')
    .replace(/,,+/g, ',')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// ------------------------------------------------------------
// REVIEW FLAGS. Cheap checks for what Joakim looks for in review. They are stored
// on each item (and summed in "Render node page") but never stop the run.
// ------------------------------------------------------------
const WORD_RANGE = {
  "Overview": [230, 290], "Imaging technologies offered": [180, 240],
  "Specialties and research focus": [150, 200], "Services and user support": [140, 190], "Facilities": [180, 240]
};
const BANNED = /\b(state-of-the-art|cutting-edge|world-class|unique|comprehensive|diverse|robust|seamless(ly)?|wide range|notably|importantly|it is worth noting|most users|listed as|is listed|are listed|strongest|best suited|well suited|suits|natural place|will find|most support|within one node|in one place)\b/gi;
// Method names the writer could take from a facility description although the
// Node does not register them. Each is checked against the Node's technology labels.
const METHOD_CHECKS = [
  [/\bSTED\b/, /STED/], [/\b(STORM|dSTORM|PALM|single[- ]molecule locali[sz]ation|SMLM)\b/i, /SMLM|Single Molecule localization/i],
  [/\bMINFLUX\b/, /MINFLUX/], [/light[- ]sheet/i, /light[- ]?sheet|SPIM/i], [/two[- ]photon|multiphoton/i, /Two-photon|2P/i],
  [/\bFLIM\b|lifetime imaging/i, /FLIM|Lifetime/i], [/\bFRET\b/, /FRET/], [/\bFRAP\b/, /FRAP/],
  [/\bFCS\b|correlation spectroscopy/i, /FCS/], [/\bTIRF\b|total internal reflection/i, /TIRF/],
  [/spinning[- ]dis[ck]/i, /Spinning/i], [/structured illumination|\bSIM\b/, /\bSIM\b|Structured/i],
  [/expansion microscopy/i, /Expansion/i], [/\bRaman\b/i, /Raman/i], [/harmonic generation|\bSHG\b/i, /Harmonic/i],
  [/cryo[- ]electron tomography|\bcryo-ET\b/i, /Cryo Electron Tomography|Cryo-ET/i], [/\bFIB-SEM\b/i, /FIB/i],
  [/serial block[- ]face/i, /Serial Blockface|SBF/i], [/array tomography/i, /Array tomography/i],
  [/\bCLEM\b|correlative light and electron/i, /CLEM|Correlative/i], [/atomic force/i, /Atomic Force/i],
  [/intravital/i, /ntravital/i], [/\bSPECT\b/, /SPECT/], [/\bPET\b/, /PET/], [/\bMEG\b|magnetoencephalograph/i, /MEG/],
  [/optical coherence tomography|\bOCT\b/, /OCT/], [/photoacoustic/i, /hotoacoustic|PAI/i],
  [/mass spectrometry imaging|\bMALDI\b/i, /Mass spectrometry/i], [/micro-?CT\b/i, /CT/],
  [/high[- ]content screening/i, /high content|HTM/i], [/\bMRI\b|magnetic resonance/i, /MRI|MRS/i],
  [/\bultrasound\b/i, /\bUS\b|ultrasound/i], [/elemental analysis|\bEDX\b|\bEDS\b/i, /EDX|Elemental/i]
];
function reviewFlags(title, text, registeredLabels) {
  const flags = [];
  const words = text.split(/\s+/).filter(Boolean).length;
  let [lo, hi] = WORD_RANGE[title] || [0, 1e9];
  if (title === 'Facilities' && facilityCount === 1) [lo, hi] = [80, 160];  // one facility: four or five sentences
  if (words < lo * 0.9 || words > hi * 1.1) flags.push(`${words} words (aim ${lo} to ${hi})`);
  const semis = (text.match(/;/g) || []).length;
  const colons = (text.match(/:/g) || []).length;
  if (semis > 1) flags.push(`${semis} semicolons`);
  if (colons > 1) flags.push(`${colons} colons`);
  const banned = [...new Set((text.match(BANNED) || []).map(x => x.toLowerCase()))];
  if (banned.length) flags.push('wording: ' + banned.join(', '));
  if (/[\w.+-]+@[\w-]+(\.[\w-]+)+/.test(text)) flags.push('email address in text');
  const missing = METHOD_CHECKS.filter(([inText, inLabels]) => inText.test(text) && !registeredLabels.some(l => inLabels.test(l)))
    .map(([inText]) => (text.match(inText) || [''])[0]);
  if (missing.length) flags.push('methods not registered for this Node: ' + [...new Set(missing)].join(', '));
  return flags;
}
let registeredLabels = [];
let facilityCount = 0;
let hasServices = true;
try {
  const b = $('Read node file').first().json.node_briefing || {};
  hasServices = String(b.services_support || '').trim() !== '';
  facilityCount = (b.facilities || []).length;
  registeredLabels = (b.technologies_by_category || []).flatMap(g => (g.technologies || []).map(t => String(t.label || '')));
} catch (e) { /* the identity check below reports a missing node file */ }

const results = [];
for (const title of EXPECTED_SECTIONS) {
  const s = byTitle[normTitle(title)];
  const text = String(s.section_text || '').trim();

  // A Node with no services on record (no SLA and no service summary) gets no Services section.
  if (title === 'Services and user support' && !hasServices) {
    results.push({ json: { node: currentNode, submission_id: currentSubmissionId, section: title,
      section_text: '', word_count: 0, claimed_word_count: null, contained_em_dash: false, tidied: !!text,
      review_flags: text ? ['Services text dropped: no services on record'] : [],
      output: JSON.stringify({ section_title: title, section_text: '', word_count: 0 }) } });
    continue;
  }
  if (!text) {
    throw new Error(`Section "${title}" returned empty section_text.`);
  }

  // Recount rather than trusting the model's own word_count.
  const actualWords = text.split(/\s+/).filter(Boolean).length;

  // Dashes, stray markdown and "Access:" lines are removed here rather than by a rerun.
  const cleanText = tidy(text).replace(/\s*[\w.+-]+@[\w-]+(\.[\w-]+)+/g, '');
  const flags = reviewFlags(title, tidy(text), registeredLabels);

  results.push({
    json: {
      node: currentNode,
      submission_id: currentSubmissionId,
      section: title,
      section_text: cleanText,
      word_count: actualWords,
      claimed_word_count: s.word_count === undefined ? null : s.word_count,
      contained_em_dash: /\u2014/.test(text),
      tidied: cleanText !== text,
      review_flags: flags,
      // Stored to the sheet as the canonical record of this section.
      output: JSON.stringify({
        section_title: title,
        section_text: cleanText,
        word_count: actualWords
      })
    }
  });
}


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

return results;
