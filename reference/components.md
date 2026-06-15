# Interactive component library

Copy-adaptable patterns for the page. This is a **parts bin, not a checklist**:
use them as starting points, restyle to the chosen palette (use CSS variables),
rename, combine, or invent new ones. You are not limited to this list, and you
should **not** use all of it on one page. Pick the few that fit your source, and
make the mix differ from your last note. Never copy another note's built HTML to
reproduce its layout. (The snippets below all use one running example, a
procrastination talk, only to stay concrete; that topic is not a template.)
Rules that always hold:

- **Real content only.** Charts plot numbers the source actually gave. Quotes
  are verbatim from the source (transcript or article). Never fabricate data to
  fill a component.
- **Persist user input.** Anything the user types or checks must survive reload.
  Go through the page's `store` (see §0) and offer an export — don't scatter raw
  `localStorage` calls through your components.
- **Accessible + reduced-motion.** Keyboard-usable, real contrast, honor
  `prefers-reduced-motion`.
- **Self-contained.** Everything is inline: CSS, JS, and the `store` itself. The
  only externals are optional CDN libs (Chart.js, Mermaid), and only when used.

---

## 0. Foundation: persistence + export (self-contained)

Each page carries its own tiny `store` so user input survives reload. It's plain
`localStorage`, keyed by the page's slug, with the synchronous `get/set` API the
components below use. Paste this once, before your other page JS:

```html
<meta name="robots" content="noindex, nofollow" />   <!-- optional: keep the page out of search -->
...
<script>
const SLUG = 'NOTE-SLUG';   // any stable id unique to this page (e.g. the folder name)

function createStore(slug) {
  const KEY = 'idn:' + slug;
  let data = {};
  try { data = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch {}
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(data)); } catch {} };
  return {
    get: (k, d) => (k in data ? data[k] : d),   // sync read
    set: (k, v) => { data[k] = v; save(); },     // sync write, persists immediately
    keys: () => Object.keys(data),
    clear: () => { data = {}; localStorage.removeItem(KEY); return Promise.resolve(); },
  };
}

// auto-save + restore every [data-save] field (text, textarea, checkbox, range)
function wireSaves(store) {
  document.querySelectorAll('[data-save]').forEach(el => {
    const k = el.dataset.save, isCheck = el.type === 'checkbox';
    const saved = store.get(k);
    if (saved !== undefined) { if (isCheck) el.checked = saved; else el.value = saved; }
    const push = () => store.set(k, isCheck ? el.checked : el.value);
    el.addEventListener('input', push);
    el.addEventListener('change', push);
  });
}

// download every [data-export] field as a markdown file
function exportNotes(title, filename = 'my-notes.md') {
  const lines = ['# ' + title, ''];
  document.querySelectorAll('[data-export]').forEach(el => {
    const val = el.type === 'checkbox' ? (el.checked ? 'yes' : 'no') : el.value;
    if (val) lines.push('- **' + el.dataset.export + '**: ' + val);
  });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/markdown' }));
  a.download = filename; a.click(); URL.revokeObjectURL(a.href);
}

const store = createStore(SLUG);
document.addEventListener('DOMContentLoaded', () => {
  wireSaves(store);
  // ...then wire your decks / quizzes / habits / nav / video modal with the
  // snippets below. They all read and write through `store`.
});
</script>
```

The store API the rest of this file relies on:

```js
store.get(key, default)   // sync read
store.set(key, value)     // sync write (persists immediately)
store.keys()              // string[]
store.clear()             // wipe this page's saved data (returns a Promise)
```

`data-save="uniqueKey"` auto-saves a field; `data-export="Label"` includes it in
the export. Offer an Export and a Reset button:

```html
<button onclick="exportNotes('Page title', 'my-plan.md')">⤓ Export my answers</button>
<button onclick="if(confirm('Clear all your saved answers?')){store.clear().then(()=>location.reload());}">Reset</button>
```

If you hand-roll a component instead of using `wireSaves`, just read/write
through `store` (every snippet below does).

> **Optional: cross-device sync + login (companion site).** If you publish these
> pages into a backend-backed site, you can swap the inline `store` for a shared
> one without touching a single component. The reference site this skill grew out
> of ships an `/app.js` exposing `window.VN`: `VN.createStore(slug)` keeps the
> same sync `get/set` API but persists to a server (Upstash Redis) partitioned by
> the logged-in user, with `localStorage` as an offline cache.
> `VN.initPage({ slug, videoId })` does auth bar + hydrate + the generic wirings
> and returns the store; `VN.wireSaves`/`wireDecks`/`wireQuizzes`/`exportNotes`
> mirror the inline helpers. With a server store, hydrate before wiring:
> `await store.hydrate()`. One gotcha if you use `VN.mountAuthBar()`: it pins a
> fixed pill in the top-right corner, so keep any sticky top bar's controls clear
> of that corner (give the bar `padding-right`, e.g. `8.5rem` on mobile).

---

## 1. Orientation

### Chapter rail + scroll-spy + reading progress

```html
<div class="progress"><span id="bar"></span></div>
<nav class="rail"><ol id="toc"></ol></nav>
```
```js
const sections = [...document.querySelectorAll('main section[id]')];
const toc = document.getElementById('toc');
sections.forEach(s => {
  const li = document.createElement('li');
  li.innerHTML = `<a href="#${s.id}">${s.dataset.nav || s.querySelector('h2')?.textContent}</a>`;
  toc.appendChild(li);
});
const links = [...toc.querySelectorAll('a')];
const bar = document.getElementById('bar');
addEventListener('scroll', () => {
  const h = document.documentElement;
  bar.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight) * 100) + '%';
  const i = sections.findLastIndex(s => s.getBoundingClientRect().top < innerHeight * 0.3);
  links.forEach((a, j) => a.classList.toggle('active', j === i));
}, { passive: true });
```

### Mobile jump bar (when the rail is hidden)

On phones the rail is hidden, so give a sticky top bar with a "Jump to"
`<select>` (`#mnav`). Populate it from the same `sections` list as the rail:

```css
.mnav { position: sticky; top: 0; z-index: 80; display: flex; gap: 10px; align-items: center;
  padding: 9px 16px; background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); }
.mnav #mnav { flex: 1; /* the select grows to fill the space */ }
@media (min-width: 1040px) { .mnav { display: none; } }   /* hidden once the rail shows */
@media (max-width: 640px)  { .mnav { padding-right: 8.5rem; } }  /* leave room for any top-right control */
```
```html
<div class="mnav"><label for="mnav">Jump to</label><select id="mnav" aria-label="Jump to section"></select></div>
```
```js
const mnav = document.getElementById('mnav');
sections.forEach(s => {
  const opt = document.createElement('option');
  opt.value = s.id; opt.textContent = s.dataset.nav || s.querySelector('h2')?.textContent;
  mnav.appendChild(opt);
});
mnav.addEventListener('change', () => { location.hash = mnav.value; });
```

### Video modal + timestamp seeking (videos; preferred over an embed at the top)

For **video** notes only. Don't pin a big iframe at the top of the page and don't
make timestamps open a new YouTube tab. Instead: a compact **"Watch video"**
button, and a **modal** that plays the video. Timestamp buttons open that same
modal seeked to the moment.

Put the button in the rail under the TOC for desktop **and** add a second
`floating` copy for mobile. The rail is hidden on phones, so the rail button
alone leaves mobile with **no watch button at all** — the floating one is what
phone users tap. Float it **bottom-right** (not the top bar). Only one
`#watchBtn` listener is wired, so the floating copy just forwards its click to it.

```html
<!-- desktop trigger: place under the TOC inside the rail -->
<button class="watch-btn" id="watchBtn" type="button">▶ Watch video</button>

<!-- mobile trigger: place once, just before </body>; forwards to #watchBtn -->
<button class="watch-btn floating" type="button"
        onclick="document.getElementById('watchBtn').click()">▶ Watch</button>

<!-- modal: place once, just before </body> -->
<div class="vmodal" id="vmodal" hidden>
  <div class="vmodal-backdrop" data-close></div>
  <div class="vmodal-box" role="dialog" aria-modal="true" aria-label="Video player">
    <button class="vmodal-close" data-close type="button" aria-label="Close video">×</button>
    <div class="vmodal-frame" id="vmodalFrame"></div>
  </div>
</div>
```
```css
.watch-btn { cursor: pointer; }
/* show the floating copy only where the rail is hidden (use YOUR mobile breakpoint) */
.watch-btn.floating { display: none; }
@media (max-width: 1039px) {
  .watch-btn.floating { display: inline-flex; position: fixed; right: 1.1rem; bottom: 1.1rem;
    z-index: 90; border-radius: 999px; box-shadow: 0 6px 24px rgba(0,0,0,.25); }
}
.vmodal[hidden] { display: none; }
.vmodal { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 1rem; }
.vmodal-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,.72); }
.vmodal-box { position: relative; width: min(92vw, 980px); aspect-ratio: 16 / 9; background: #000; border-radius: 12px; overflow: hidden; }
.vmodal-frame, .vmodal-frame iframe { width: 100%; height: 100%; border: 0; }
.vmodal-close { position: absolute; top: -2.6rem; right: 0; font-size: 1.6rem; line-height: 1; background: none; border: 0; color: #fff; cursor: pointer; }
```
```js
const VIDEO_ID = 'VIDEO_ID'; // from meta.json
const vmodal = document.getElementById('vmodal');
const vframe = document.getElementById('vmodalFrame');
const hmsToSeconds = hms => { const p = hms.split(':').map(Number); return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1]; };

function openVideoAt(seconds = 0) {
  vframe.innerHTML = `<iframe src="https://www.youtube.com/embed/${VIDEO_ID}?start=${Math.floor(seconds)}&autoplay=1&rel=0" title="Video" allow="autoplay; encrypted-media; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>`;
  vmodal.hidden = false; document.body.style.overflow = 'hidden';
}
function closeVideo() { vmodal.hidden = true; vframe.innerHTML = ''; document.body.style.overflow = ''; } // clearing the iframe stops playback

document.getElementById('watchBtn')?.addEventListener('click', () => openVideoAt(0));
vmodal.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', closeVideo));
addEventListener('keydown', e => { if (e.key === 'Escape' && !vmodal.hidden) closeVideo(); });

// Timestamp buttons: <button class="ts" data-ts="00:04:12">04:12</button>
document.querySelectorAll('.ts[data-ts]').forEach(b =>
  b.addEventListener('click', () => openVideoAt(hmsToSeconds(b.dataset.ts))));
```

Each click rebuilds the iframe at the new `start=`, which is simple and works
offline-free of any API. For seamless seeking without a reload, load the YouTube
IFrame Player API once and call `player.seekTo(seconds, true)` instead.

**Keep `referrerpolicy="strict-origin-when-cross-origin"` on the iframe.** YouTube
now requires a referrer to validate the embed; without it (e.g. the page is served
with a `Referrer-Policy: no-referrer` header) the player fails with **Error 153
"Video player configuration error"**. The element-level attribute sends just the
origin to YouTube and overrides a stricter document/header policy for that one
request.

### Read original (articles)

For **article** notes there is no modal and no timestamps. Give a compact button
that links to the source URL (from meta.json) in a new tab, placed in the rail
under the TOC the same way the "Watch video" button is — and, like the watch
button, add a `floating` copy for mobile so phone users (who don't see the rail)
can still reach it. Use plain in-page anchors (section `id`s) for "jump to" links
instead of timestamps.

```html
<a class="read-btn" href="ARTICLE_URL" target="_blank" rel="noopener">Read original article ↗</a>
<!-- mobile copy, just before </body> -->
<a class="read-btn floating" href="ARTICLE_URL" target="_blank" rel="noopener">Read ↗</a>
```
```css
.read-btn { display: inline-block; text-decoration: none; cursor: pointer; }
.read-btn.floating { display: none; }
@media (max-width: 1039px) {
  .read-btn.floating { display: inline-block; position: fixed; right: 1.1rem; bottom: 1.1rem;
    z-index: 90; border-radius: 999px; box-shadow: 0 6px 24px rgba(0,0,0,.25); }
}
```

---

## 2. Understanding

### Concept card

```html
<article class="concept">
  <h3>Instant-gratification monkey</h3>
  <p class="what">The impulse that hijacks attention toward easy, fun, now.</p>
  <p class="why">Matters because it explains *why* willpower alone fails.</p>
</article>
```

### Reframe flip-card (belief → truer belief)

```html
<button class="flip" aria-pressed="false">
  <span class="front">"I work best under pressure."</span>
  <span class="back">You produce *something* under pressure. The cost is the work you never start.</span>
</button>
```
```js
document.querySelectorAll('.flip').forEach(b =>
  b.addEventListener('click', () => b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') !== 'true')));
```
```css
.flip .back { display: none; } .flip[aria-pressed="true"] .front { display: none; } .flip[aria-pressed="true"] .back { display: inline; }
```

### Go-deeper accordion (progressive disclosure)

```html
<details><summary>Why two all-nighters is the wrong lesson</summary><p>…</p></details>
```

### Annotated pull-quote (timestamp button for videos)

```html
<figure class="quote">
  <blockquote>"The Panic Monster is dormant most of the time."</blockquote>
  <figcaption>The only thing the monkey fears. <button class="ts" data-ts="00:06:40" type="button">06:40</button></figcaption>
</figure>
```

For an **article**, drop the timestamp button and cite the section/heading
instead (e.g. `<figcaption>From "The cost of waiting".</figcaption>`).

### Comparison table

```html
<table class="cmp"><thead><tr><th></th><th>Deadline tasks</th><th>No-deadline tasks</th></tr></thead>
<tbody><tr><th>Panic Monster</th><td>Wakes up</td><td>Never wakes</td></tr></tbody></table>
```

---

## 3. Data & diagrams

### Charts (Chart.js via CDN) — real numbers only

```html
<canvas id="chart1" height="160"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script>
new Chart(document.getElementById('chart1'), {
  type: 'bar',
  data: { labels: ['Planned', 'Actual'], datasets: [{ data: [12, 3], backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--accent') }] },
  options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
});
</script>
```
Only build a chart if the video gives real figures. Otherwise use a diagram or
table. Pull colors from your CSS variables so charts match the palette.

### Diagrams / flowcharts / mind-maps (Mermaid via CDN)

```html
<pre class="mermaid">
flowchart LR
  A[Deadline approaches] --> B{Panic Monster wakes?}
  B -- yes --> C[Work happens]
  B -- no --> D[Nothing happens]
</pre>
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
mermaid.initialize({ startOnLoad: true, theme: 'base',
  themeVariables: { primaryColor: '#…', lineColor: '#…', fontFamily: 'inherit' } });
</script>
```

### Timeline (hand-rolled, no lib)

```html
<ol class="timeline">
  <li><span class="t">Week 1</span><p>Plenty of time, monkey in charge.</p></li>
  <li><span class="t">3 days out</span><p>Panic Monster wakes.</p></li>
</ol>
```

### Cycle / loop diagram (keep the labels upright)

For self-reinforcing loops (e.g. potential → action → results → belief → back to
potential). **The trap: never rotate the label text to follow the ring.** The
nodes at the bottom come out upside-down and unreadable. Position the nodes
around the circle and leave every label horizontal. If you animate the ring
spinning, counter-rotate each node's content by the negative angle so the words
stay upright.

```html
<div class="cycle" aria-label="The certainty cycle">
  <div class="cycle-center"><b>Certainty</b><span>this will work</span></div>
  <ul class="cycle-ring">
    <li><b>Potential</b><span>you tap more</span></li>
    <li><b>Action</b><span>massive, all in</span></li>
    <li><b>Results</b><span>great outcomes</span></li>
    <li><b>Belief</b><span>this works</span></li>
  </ul>
</div>
```
```css
.cycle { position: relative; width: 320px; height: 320px; margin: 2rem auto; }
.cycle-center { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; }
.cycle-ring { list-style: none; margin: 0; padding: 0; }
.cycle-ring > li { position: absolute; transform: translate(-50%, -50%); width: 104px; height: 104px;
  border-radius: 50%; display: grid; place-content: center; text-align: center; /* upright, never rotated */
  background: var(--surface); border: 2px solid var(--accent); padding: .4rem; }
```
```js
document.querySelectorAll('.cycle').forEach(c => {
  const items = [...c.querySelectorAll('.cycle-ring > li')], R = 120;
  items.forEach((li, i) => {
    const a = (i / items.length) * 2 * Math.PI - Math.PI / 2; // first node at top, clockwise
    li.style.left = `calc(50% + ${Math.cos(a) * R}px)`;
    li.style.top = `calc(50% + ${Math.sin(a) * R}px)`;
  });
});
```
Want the flow arrows? Draw a faint SVG ring with arrowheads behind the nodes.
Put the arrowheads on the curve, never the words.

---

## 4. Active recall (testing)

### Flashcard deck (Anki-style, with mastery + persistence)

```html
<section class="deck" data-deck='[
  {"q":"What wakes the Panic Monster?","a":"A real, near deadline or scary consequence."},
  {"q":"Why does willpower alone fail the procrastinator?","a":"The instant-gratification monkey hijacks attention toward easy/fun/now."}
]'>
  <div class="card"><div class="face q"></div><div class="face a"></div></div>
  <div class="deck-ctrls">
    <button data-act="again">Review again</button>
    <button data-act="flip">Show answer</button>
    <button data-act="got">Got it</button>
  </div>
  <p class="deck-meta"><span class="pos"></span> · <b class="mastered">0</b>/<span class="total"></span> mastered
    <button data-act="reset" class="mini">reset</button></p>
</section>
```
```js
document.querySelectorAll('.deck').forEach((deck, di) => {
  const cards = JSON.parse(deck.dataset.deck), key = 'deck' + di;
  const q = deck.querySelector('.face.q'), a = deck.querySelector('.face.a'), cardEl = deck.querySelector('.card');
  const posEl = deck.querySelector('.pos'), mEl = deck.querySelector('.mastered');
  deck.querySelector('.total').textContent = cards.length;
  let mastered = new Set(store.get(key, [])), queue = [], pos = 0;
  const rebuild = () => { queue = cards.map((_, i) => i).filter(i => !mastered.has(i)); pos = 0; };
  const render = () => {
    mEl.textContent = mastered.size; cardEl.classList.remove('flipped');
    if (!queue.length) { q.textContent = 'Deck complete. All mastered.'; a.textContent = ''; posEl.textContent = ''; return; }
    if (pos >= queue.length) pos = 0;
    const i = queue[pos]; q.textContent = cards[i].q; a.textContent = cards[i].a;
    posEl.textContent = `card ${pos + 1} of ${queue.length}`;
  };
  const flip = () => cardEl.classList.toggle('flipped');
  cardEl.onclick = flip;
  deck.querySelector('[data-act=flip]').onclick = flip;
  deck.querySelector('[data-act=again]').onclick = () => { pos++; render(); };
  deck.querySelector('[data-act=got]').onclick = () => { if (queue.length) { mastered.add(queue[pos]); store.set(key, [...mastered]); rebuild(); render(); } };
  deck.querySelector('[data-act=reset]').onclick = () => { mastered = new Set(); store.set(key, []); rebuild(); render(); };
  rebuild(); render();
});
```
```css
.card .face.a { display: none; } .card.flipped .face.q { display: none; } .card.flipped .face.a { display: block; }
```

### Multiple-choice quiz (instant feedback + explanation + score)

```html
<form class="quiz" data-quiz='[
  {"q":"What finally makes the procrastinator act?","options":["Better planning","The Panic Monster waking up","More willpower"],"answer":1,"why":"The deadline wakes the Panic Monster, the monkey''s only fear."}
]'></form>
<p class="quiz-score" hidden></p>
```
(Note: inside the JSON attribute, write an apostrophe as `''` or avoid it.)
```js
document.querySelectorAll('.quiz').forEach((form, qi) => {
  const items = JSON.parse(form.dataset.quiz), saved = store.get('quiz' + qi, {});
  const score = () => {
    const got = items.filter((it, i) => saved[i] === it.answer).length;
    const el = form.nextElementSibling;
    if (el && el.classList.contains('quiz-score')) { el.hidden = false; el.textContent = `Score: ${got} / ${items.length}`; }
  };
  items.forEach((it, i) => {
    const fs = document.createElement('fieldset');
    fs.innerHTML = `<legend>${i + 1}. ${it.q}</legend>` +
      it.options.map((o, j) => `<label><input type="radio" name="q${qi}_${i}" value="${j}"><span>${o}</span></label>`).join('');
    const why = document.createElement('p'); why.className = 'why'; why.hidden = true; why.textContent = it.why; fs.appendChild(why);
    form.appendChild(fs);
    fs.querySelectorAll('input').forEach(inp => inp.addEventListener('change', () => {
      const chosen = +inp.value;
      fs.querySelectorAll('label').forEach((l, j) => { l.classList.toggle('correct', j === it.answer); l.classList.toggle('wrong', j === chosen && chosen !== it.answer); });
      why.hidden = false; saved[i] = chosen; store.set('quiz' + qi, saved); score();
    }));
    if (saved[i] != null) { const inp = fs.querySelector(`input[value="${saved[i]}"]`); if (inp) { inp.checked = true; inp.dispatchEvent(new Event('change')); } }
  });
  score();
});
```

### Cloze (fill-the-blank, click to reveal)

```html
<p class="cloze">The monkey chases <span class="blank" data-a="instant gratification"></span>; its only fear is the <span class="blank" data-a="Panic Monster"></span>.</p>
```
```js
document.querySelectorAll('.cloze .blank').forEach(b => {
  b.textContent = '\u2002\u2002\u2002\u2002\u2002';
  b.onclick = () => { b.classList.add('revealed'); b.textContent = b.dataset.a; };
});
```

---

## 5. Application (the point)

All inputs below auto-save and export via the section 0 helpers.

### Action checklist

```html
<ul class="actions">
  <li><label><input type="checkbox" data-save="act-timer" data-export="Action: 10-minute timer">
    When I feel avoidance, start a 10-minute timer and commit only to those 10 minutes.</label></li>
</ul>
```

### If-then implementation intentions (highest-leverage)

```html
<p class="ifthen">If <input data-save="if1" data-export="If" placeholder="I open a new tab to avoid the task">
  then I will <input data-save="then1" data-export="Then" placeholder="close it and write one sentence">.</p>
```

### Reflection journal / "apply to your situation"

```html
<label class="reflect">Where does the instant-gratification monkey run your day?
  <textarea data-save="reflect-monkey" data-export="Reflection: monkey" rows="4"></textarea></label>
```

### Habit tracker (7-day)

```html
<div class="habit" data-habit="Start before I feel ready"></div>
```
```js
document.querySelectorAll('.habit').forEach((h, hi) => {
  const key = 'habit' + hi; let days = store.get(key, Array(7).fill(false));
  h.innerHTML = `<p>${h.dataset.habit}</p><div class="days"></div>`;
  const row = h.querySelector('.days');
  ['M', 'T', 'W', 'T', 'F', 'S', 'S'].forEach((d, i) => {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = d; b.className = days[i] ? 'on' : '';
    b.onclick = () => { days[i] = !days[i]; b.classList.toggle('on', days[i]); store.set(key, days); };
    row.appendChild(b);
  });
});
```

### Scenario / decision practice

```html
<div class="scenario">
  <p class="prompt">It's 9pm, the report is due tomorrow, and you "work best under pressure." What does the framework predict, and what's the better move?</p>
  <textarea data-save="scn1" data-export="Scenario answer" rows="3" placeholder="Your call..."></textarea>
  <details><summary>How the framework reads this</summary><p>The Panic Monster will get it done, badly. The fix is a smaller, earlier deadline you actually fear.</p></details>
</div>
```

---

## 6. More elements to reach for (build per content)

The catalog above is not the whole world. When a source calls for something
else, build it. A couple that fill common gaps, then a list to spark your own.

### "Where do you land?" slider (positioning / opinion)

For debates, opinion essays, or any "rate your own situation" moment. Persists
via `data-save`; run the small sync below after `wireSaves(store)` so the readout
matches the restored value.

```html
<div class="scale">
  <p class="prompt">After hearing both sides, where do you land?</p>
  <div class="scale-row">
    <span>Caution</span>
    <input type="range" min="0" max="10" value="5"
           data-save="land" data-export="Where I land (0 caution to 10 bold)">
    <output>5</output>
    <span>Bold</span>
  </div>
  <textarea data-save="land-why" data-export="Why" rows="2" placeholder="Because..."></textarea>
</div>
```
```js
document.querySelectorAll('.scale input[type=range]').forEach(r => {
  const out = r.parentElement.querySelector('output');
  const sync = () => { if (out) out.textContent = r.value; };
  r.addEventListener('input', sync); sync();
});
```

### Self-assessment scorecard (diagnostic)

Rate yourself against the source's criteria and get a total. Hand-rolled, saves
through `store`. Give each scorecard a unique `id`.

```html
<form class="scorecard" id="readiness" data-items='[
  "I have a specific, written goal",
  "I review progress every week",
  "Someone holds me accountable"
]'><p class="scorecard-total"></p></form>
```
```js
document.querySelectorAll('.scorecard').forEach(form => {
  const items = JSON.parse(form.dataset.items), key = 'score:' + (form.id || 0);
  const saved = store.get(key, {}), totalEl = form.querySelector('.scorecard-total');
  const render = () => { const sum = items.reduce((s, _, i) => s + (saved[i] || 0), 0);
    totalEl.textContent = 'Score: ' + sum + ' / ' + items.length * 5; };
  items.forEach((label, i) => {
    const row = document.createElement('label'); row.className = 'score-row';
    row.innerHTML = '<span>' + label + '</span>';
    const dots = document.createElement('div'); dots.className = 'score-dots';
    for (let n = 1; n <= 5; n++) {
      const b = document.createElement('button'); b.type = 'button'; b.textContent = n;
      if ((saved[i] || 0) >= n) b.classList.add('on');
      b.onclick = () => { saved[i] = n; store.set(key, saved);
        dots.querySelectorAll('button').forEach((x, j) => x.classList.toggle('on', j < n)); render(); };
      dots.appendChild(b);
    }
    row.appendChild(dots); form.insertBefore(row, totalEl);
  });
  render();
});
```

### Build-your-own (no snippet; shape them to the content)

- **Ranking / ordering** — tap-sort items into priority order (up/down buttons
  are touch-friendly); save the order array through `store`.
- **Matching pairs** — connect term to definition; good for vocabulary-heavy talks.
- **Myth vs fact toggle** — a claim flips to reveal "myth" or "fact" plus the
  why; great for explainers and debunking.
- **Interactive step-runner** — for tutorials: reveal one step at a time with a
  "next" button and a checkbox per step.
- **Branching decision tree** — for "if this, do that" methods: each choice leads
  to the next node and ends on a recommendation.

Persist anything the user produces through `store` (or `data-save`), keep it
keyboard-usable, and style it to the page's palette.

---

## 7. Motion & print

### Reveal on scroll (respects reduced motion)

```js
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const els = document.querySelectorAll('[data-reveal]');
if (reduce) { els.forEach(el => el.classList.add('in')); }
else {
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: 0.15 });
  els.forEach(el => io.observe(el));
}
```
```css
[data-reveal] { opacity: 0; transform: translateY(12px); transition: opacity .6s, transform .6s; }
[data-reveal].in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
```

### Print stylesheet (so the page also prints cleanly)

```css
@media print {
  .rail, .progress, .deck-ctrls, .quiz, button { display: none !important; }
  body { color: #111; background: #fff; }
  a[href^="http"]::after { content: " (" attr(href) ")"; font-size: .75em; color: #555; }
  section { break-inside: avoid; }
}
```

---

## CDN libraries (only when they earn it)

- **Chart.js** `https://cdn.jsdelivr.net/npm/chart.js@4` — bar/line/radar/doughnut.
- **Mermaid** `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs` — flow/mind maps.

Prefer hand-rolled SVG/CSS for simple visuals. Don't pull a library for one box.
If offline use matters to the user, inline a tiny SVG chart instead of Chart.js.

