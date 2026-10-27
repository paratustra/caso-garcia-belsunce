// usage: playwriter -s <session> -e "$(cat scripts/acquisition/grab.js)" — reads jobs [{url, out}] from JOBS_FILE,
// saves each page's main text as Markdown at `out` and writes a <out>.links.txt sidecar.
// It runs inside Playwriter and cannot see its own path: JOBS_FILE is the GRAB_JOBS env var if set, else
// .jobs.json relative to the process cwd (run from the repo root, or use absolute paths).
// The "Fuente:"/"Descargado:" headers stay in Spanish: tools/ingest.py parses them.
const fs = require('fs');
const JOBS_FILE = (typeof process !== 'undefined' && process.env.GRAB_JOBS) || '.jobs.json';
const jobs = JSON.parse(fs.readFileSync(JOBS_FILE, 'utf8'));
const page = state.page || (state.page = await context.newPage());
for (const { url, out } of jobs) {
  if (fs.existsSync(out)) { console.log('SKIP', out); continue; }
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    const d = await page.evaluate(() => {
      const el = document.querySelector('#mw-content-text, article, main, [role=main]') || document.body;
      return { title: document.title, url: location.href, text: el.innerText,
        links: [...el.querySelectorAll('a[href^="http"]')].map(a => a.href) };
    });
    fs.mkdirSync(require('path').dirname(out), { recursive: true });
    fs.writeFileSync(out, `# ${d.title}\n\nFuente: ${d.url}\nDescargado: ${new Date().toISOString()}\n\n${d.text}\n`);
    fs.writeFileSync(out.replace(/\.md$/, '.links.txt'), [...new Set(d.links)].join('\n'));
    console.log('OK', out, d.text.length);
  } catch (e) { console.log('FAIL', url, e.message.split('\n')[0]); }
}
