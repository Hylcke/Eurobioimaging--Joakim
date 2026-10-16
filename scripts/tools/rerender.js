// Rebuilds finished pages with the current code and Node files, keeping the AI text.
//   node tools/rerender.js EB-NODES_KB_workflow.json node_files <pages folder> <output folder>
// The written sections are taken from each page, passed through "Clean and explode
// sections" and "Render node page" exactly as in n8n, and saved as a new page. Tables,
// lists and contacts come out as the current code builds them, so a fix to those parts
// never needs a new AI run. Review flags are printed for every page.
const fs = require('fs'), path = require('path');
const [wfPath, nodeDir, pageDir, outDir] = process.argv.slice(2);
const wf = JSON.parse(fs.readFileSync(wfPath, 'utf8'));
const code = n => wf.nodes.find(x => x.name === n).parameters.jsCode;
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
const run = (name, ctx) => new AsyncFunction('$input', '$', 'Buffer', code(name)).call({ helpers: ctx.helpers }, ctx.$input, ctx.$, Buffer);
const TITLES = ["Overview", "Imaging technologies offered", "Specialties and research focus", "Services and user support", "Facilities"];
const esc = t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function sections(md) {
  return TITLES.map(t => {
    const m = md.match(new RegExp(`^## ${esc(t)}\\n([\\s\\S]*?)(?=^## |$(?![\\s\\S]))`, 'm'));
    let body = m ? m[1] : '';
    body = body.split(/^### /m)[0].split('\n').filter(l => !l.startsWith('|')).join('\n').trim();
    return { section_title: t, section_text: body, word_count: body.split(/\s+/).filter(Boolean).length };
  });
}
(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  for (const f of fs.readdirSync(pageDir).filter(x => x.endsWith('.md'))) {
    const key = f.replace(/\.md$/, '').replace(/^[0-9a-f]{8}-/, '').replace(/\d+$/, '');
    const nodeFile = path.join(nodeDir, key + '.json');
    if (!fs.existsSync(nodeFile)) { console.log('SKIP', f, '(no Node file', key + ')'); continue; }
    const raw = fs.readFileSync(nodeFile);
    const outs = {};
    const $ = n => ({ first: () => outs[n][0], all: () => outs[n] });
    const helpers = { getBinaryDataBuffer: async () => raw,
      prepareBinaryData: async (buf, fileName, mime) => ({ data: buf.toString('base64'), fileName, mimeType: mime }) };
    try {
      outs['Read node file'] = await run('Read node file', { $input: { all: () => [{ json: {} }] }, $, helpers });
      const md0 = fs.readFileSync(path.join(pageDir, f), 'utf8').replace(/^﻿/, '');
      const agent = [{ json: { output: JSON.stringify({ sections: sections(md0) }) } }];
      outs['Clean and explode sections'] = await run('Clean and explode sections', { $input: { all: () => agent }, $, helpers });
      const saved = outs['Clean and explode sections'];
      outs['Render node page'] = await run('Render node page', { $input: { all: () => saved, first: () => saved[0] }, $, helpers });
      const r = outs['Render node page'][0].json;
      fs.writeFileSync(path.join(outDir, r.fileName), '﻿' + r.markdown, 'utf8');
      console.log('OK  ', r.fileName, r.review_flags.length ? '\n      ' + r.review_flags.join('\n      ') : '');
    } catch (e) { console.log('FAIL', f, e.message); }
  }
})();
