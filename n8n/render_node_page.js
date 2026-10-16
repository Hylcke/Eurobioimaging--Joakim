// ============================================================
// RENDER NODE PAGE v12 (Knowledge Base edition)
// v12: technology names in the table carry their technology URI (a link to their page
// once TECH_URL is set, the Access Portal has no technology pages yet); facility names
// in the facility table and locations carry their facility URI; no links in the text; NO_INSTRUMENT can fill empty instrument cells
// (off); a facility's general mailbox is listed before people.
// v11: a facility whose only link is the Node's Access Portal page gets no link;
// "+ network" is dropped from facility names; an address uses the first city of
// "Linz / Hagenberg / Wels / Steyr"; the service list drops bare "Instruments" and
// internal notes; a final pass removes dashes used as punctuation, unifies the
// other dash characters to a plain hyphen and drops any "Access:" line.
// v10: coordinates are no longer printed; contacts without a person show as
// "General enquiries".
// v9: the missing-information list is no longer printed on the page.
// v8: the facility table has three columns, Facility (linked), Institution and
// City; short names, types and URIs stay in the JSON. Paragraph breaks written
// by the AI are kept.
// v7: the technology table has two columns, Technology and Instrument
// highlights (every named model, grouped by facility short name).
// v6: the technology table lists every registered technology with the
// instruments that the providing facilities document for it.
// v5: section order Overview, Imaging technologies, Specialties, Services,
// Facilities; the technology list is a table with technology URIs and the
// facilities that provide each technology; the facility table opens the
// Facilities section; facility access routes are shown with the contacts.
// v4: reads the Node file from "Read node file" (one JSON per Node built from
// the EB Knowledge Base Master). Facility names link to their checked websites,
// the table carries the facility URI, the Services section is followed by the
// service list, each facility shows its address and coordinates, and a
// "Missing information" block lists what the master lacks for this Node.
// v3: batch safety, v2: short-name column (unchanged).
// Language: JavaScript | Mode: Run Once for All Items
// ============================================================
//
// Parts of the page that never touch the language model: the facility table,
// the technology list, the service list, the access and contact block and the
// missing-information block. They must appear exactly as recorded.
// ============================================================

let fileItem;
try {
  fileItem = $('Read node file').first().json;
} catch (e) {
  throw new Error('Could not read from "Read node file". That node must sit between the Drive download and "AI Node Writer".');
}

const briefing = fileItem.node_briefing;
const record = fileItem.node_record;
if (!briefing || !record) {
  throw new Error('The current Node file carries no node_briefing or node_record.');
}

const written = $('Clean and explode sections').all().map(i => i.json);
const foreign = written.filter(w => w.node && w.node !== fileItem.node);
if (foreign.length) {
  throw new Error(`Received ${foreign.length} section(s) belonging to a different node ` +
    `(expected "${fileItem.node}", saw "${foreign[0].node}"). The loop is not scoping correctly.`);
}
if (!written.length) {
  throw new Error('No written sections received from "Clean and explode sections".');
}

const SECTION_ORDER = [
  "Overview",
  "Imaging technologies offered",
  "Specialties and research focus",
  "Services and user support",
  "Facilities"
];

function s(v) {
  return (v === undefined || v === null) ? '' : String(v).trim();
}
function cell(v) {
  return s(v).replace(/\|/g, '\\|').replace(/\s*\n\s*/g, ' ');
}
function link(text, url, title) {
  if (!s(url)) return s(text);
  const t = s(title) ? ` "${s(title).replace(/"/g, '')}"` : '';
  return `[${s(text).replace(/[\[\]]/g, '')}](${s(url)}${t})`;
}
const PORTAL = s(briefing.identity && briefing.identity.access_portal_url);
// Technology pages. Leave empty until the Access Portal publishes one page per technology;
// then set it, for example 'https://www.eurobioimaging-access.eu/technology/{uri}', and every
// technology name in the table links to its page. The URI is always kept in the Node file.
const TECH_URL = '';
// Text for a technology row with no instrument on record. Left empty on the team's advice (16 Oct),
// so the page shows instruments only where we have them.
const NO_INSTRUMENT = '';
// A facility link that only leads to the Node's Access Portal page is not the facility's website.
function facilityLink(f) {
  const url = s(f.website);
  const usable = url && url !== PORTAL && !/eurobioimaging-access\.eu\/nodes\//i.test(url);
  // The facility URI rides along as the link title, so it is embedded but not printed.
  const uri = s(f.facility_uri);
  return link(facilityName(f), usable ? url : (uri ? `#${uri}` : ''), uri);
}
function facilityName(f) {
  return s(f.name).replace(/\s*\+\s*network$/i, '');
}

const sectionText = {};
for (const w of written) {
  if (w.section) sectionText[w.section] = s(w.section_text);
}

// ------------------------------------------------------------
// FACILITY LINKS IN THE TEXT: the first time a facility is named on the page (by its
// short name or full name), the name links to the facility's checked website.
// ------------------------------------------------------------
function linkFacilitiesInText(order) {
  const facs = (record.facilities || []).filter(f => f.status !== 'unconfirmed');
  const shortById = {};
  for (const bf of (briefing.facilities || [])) shortById[bf.facility_id] = s(bf.short_name);
  const targets = [];
  for (const f of facs) {
    const url = s(f.website);
    if (!url || url === PORTAL || /eurobioimaging-access\.eu\/nodes\//i.test(url)) continue;
    const names = [...new Set([s(f.name), shortById[f.facility_id] || s(f.short_name)].filter(n => n.length >= 3))];
    targets.push({ url, names: names.sort((a, b) => b.length - a.length), done: false });
  }
  const esc = t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  for (const title of order) {
    let text = sectionText[title];
    if (!text) continue;
    // longest names first, so "LM facility" never links inside a longer name
    const all = targets.flatMap(t => t.names.map(n => ({ t, n }))).sort((a, b) => b.n.length - a.n.length);
    for (const { t, n } of all) {
      if (t.done) continue;
      const re = new RegExp(`(^|[^\\w\\[/-])(${esc(n)})(?![\\w-]|\\]\\()`);
      const m = text.match(re);
      if (!m) continue;
      const before = text.slice(0, m.index + m[1].length);
      if ((before.match(/\[/g) || []).length > (before.match(/\]/g) || []).length) continue;  // inside a link already
      text = before + `[${m[2]}](${t.url})` + text.slice(m.index + m[0].length);
      t.done = true;
    }
    sectionText[title] = text;
  }
}

const tableFacilities = (record.facilities || []).filter(f => f.status !== 'unconfirmed');

// ------------------------------------------------------------
// FACILITY TABLE: facility (linked to its website), institution, city
// ------------------------------------------------------------
function buildFacilityTable() {
  if (!tableFacilities.length) return '';
  let md = '| Facility | Institution | City |\n| --- | --- | --- |\n';
  for (const f of tableFacilities) {
    md += `| ${cell(facilityLink(f))} | ${cell(f.institution)} | ${cell(f.city)} |\n`;
  }
  return md + '\n';
}

// ------------------------------------------------------------
// TECHNOLOGY TABLE: every registered technology, its instruments and providers
// ------------------------------------------------------------
function buildTechnologyList() {
  const groups = briefing.technologies_by_category || [];
  if (!groups.length) return '';
  let md = '| Technology | Instrument highlights |\n| --- | --- |\n';
  for (const g of groups) {
    for (const t of g.technologies) {
      // Every technology name carries its URI: as a link to its page once TECH_URL is set,
      // until then as an in-page link "#<uri>" with the URI as its title.
      const uri = s(t.technology_uri);
      const name = !uri ? t.label
        : link(t.label, TECH_URL ? TECH_URL.replace('{uri}', uri) : `#${uri}`, uri);
      const label = name;  // the provisional flag stays in the Node file, not on the page (16 Oct)
      const inst = (t.instruments || []).join('; ') || NO_INSTRUMENT;
      md += `| ${cell(label)} | ${cell(inst)} |\n`;
    }
  }
  return md + '\n';
}

// ------------------------------------------------------------
// SERVICE LIST from the Node's service summary
// ------------------------------------------------------------
function buildServiceList() {
  const list = (record.services_list || []).map(s)
    .filter(x => x && !/^instruments?$/i.test(x) && !/^\[.*\]$/.test(x) && !/INTERNAL/.test(x) && !/partial list/i.test(x));
  if (!list.length) return '';
  return list.map(x => `- ${x}`).join('\n') + '\n\n';
}

// ------------------------------------------------------------
// CONTACTS AND LOCATIONS
// ------------------------------------------------------------
function renderFacilityContact(f) {
  // A general mailbox (no person named) comes first, people after it.
  const qc = [...(f.contacts || [])].sort((a, b) => (s(a.full_name) ? 1 : 0) - (s(b.full_name) ? 1 : 0));
  return qc.map(c => {
    const name = s(c.full_name);
    const email = s(c.email);
    if (!name) return email ? `${s(c.role) || 'General enquiries'}: ${email}` : '';
    const role = s(c.role) ? ` (${s(c.role)})` : '';
    return `${name}${role}${email ? ', ' + email : ''}`;
  }).filter(Boolean).join('; ');
}

function buildContactBlock() {
  let md = '';
  const nodeContact = s(record.node_contact && record.node_contact.primary);
  if (nodeContact) md += `**Node contact:** ${nodeContact}\n\n`;
  const additional = (record.node_contact && record.node_contact.additional) || [];
  if (additional.length) md += `**Additional contacts:** ${additional.join('; ')}\n\n`;
  const site = s(briefing.identity.website);
  if (site) md += `**Node website:** ${link(site, site)}\n\n`;
  const portal = s(briefing.identity.access_portal_url);
  if (portal) md += `**Euro-BioImaging Access Portal:** ${link(portal, portal)}\n\n`;

  if (tableFacilities.length) {
    md += '### Facility locations and contacts\n\n';
    for (const f of tableFacilities) {
      md += `**${facilityLink(f)}**  \n`;
      const city = s(f.city).split(/\s+\/\s+/)[0];  // "Linz / Hagenberg / Wels / Steyr": the address is in Linz
      const addr = [s(f.street_address), [s(f.postal_code), city].filter(Boolean).join(' '), s(f.country)].filter(Boolean);
      if (addr.length) md += `${addr.join(', ')}  \n`;
      // Coordinates stay in the Node file (latitude, longitude) but are not printed.
      const contact = renderFacilityContact(f);
      if (contact) md += `Contact: ${contact}  \n`;
      // Access routes stay in the Node file but are not printed (the Access Portal link covers access).
      md += '\n';
    }
  }
  return md;
}

// ------------------------------------------------------------
// ASSEMBLE
// ------------------------------------------------------------
// Facility links stay out of the written text (Joakim, 16 Oct): they appear only in the
// facility table and the facility locations. linkFacilitiesInText() is kept but not called.

const nodeName = s(briefing.identity.name);
let markdown = `# ${nodeName}\n\n`;
const missingSections = [];

for (const title of SECTION_ORDER) {
  const text = sectionText[title];
  if (!text) { missingSections.push(title); continue; }
  if (title === 'Facilities') {
    // The facility table opens the section; the written text follows it.
    const table = buildFacilityTable();
    markdown += `## ${title}\n\n` + (table ? `${table}` : '') + `${text}\n\n`;
    continue;
  }
  markdown += `## ${title}\n\n${text}\n\n`;
  if (title === 'Imaging technologies offered') {
    const techList = buildTechnologyList();
    if (techList) markdown += `### Technologies and instruments\n\n${techList}`;
  }
  if (title === 'Services and user support') {
    const services = buildServiceList();
    // * = not from a signed SLA (Node service summary in the database); to be confirmed later.
    const star = record.services_basis === 'DATABASE' ? '*' : '';
    if (services) markdown += `### Services offered${star}\n\n${services}`;
  }
}

markdown += `## Access and contact\n\n${buildContactBlock()}`;

// Final pass over the whole page. A dash used as punctuation becomes a comma, any other
// dash-like character becomes a plain hyphen (so "CSIC–UPV" and "CSIC-UPV" read the same),
// and no "Access:" line is printed, because access always goes through Euro-BioImaging.
markdown = markdown
  .replace(/(\d)\s*[\u2013\u2014]\s*(\d)/g, '$1-$2')
  .replace(/[ \t]*\u2014[ \t]*/g, ', ')
  .replace(/ \u2013 /g, ', ')
  .replace(/[\u2010\u2011\u2012\u2013\u2212]/g, '-')
  .split('\n').filter(line => !/^\s*Access:/.test(line)).join('\n');

// The missing-information list is for review only. It stays in the Node file
// (missing_info) and in review/missing_information.md; it is not printed on the page.
const missingInfo = fileItem.missing_info || [];

const fileName = (fileItem.node_uri || nodeName.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_|_$/g, '')) + '.md';

return [{
  json: {
    node: nodeName,
    fileName: fileName,
    markdown: markdown,
    word_count_total: markdown.split(/\s+/).filter(Boolean).length,
    sections_included: SECTION_ORDER.filter(t => sectionText[t]),
    sections_missing: missingSections,
    facilities_in_table: tableFacilities.length,
    facilities_excluded: (record.facilities || []).filter(f => f.status === 'unconfirmed').length,
    technology_categories: (briefing.technologies_by_category || []).length,
    missing_info_items: missingInfo.length,
    // Style and fact checks from "Clean and explode sections", per section. For review only.
    review_flags: written.filter(w => (w.review_flags || []).length).map(w => `${w.section}: ${w.review_flags.join('; ')}`)
  }
}];
