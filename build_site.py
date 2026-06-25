"""
Build site/index.html from the data CSVs.
Embeds all data as JSON in the page so it runs from file:// with no server.
Run make_brackets.py first so the bracket SVGs exist.
"""
import csv
import json
import os
from collections import defaultdict

YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
FORMATS = ["10-team double bye", "8-team no byes", "10-team 6 single byes"]

def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build_data():
    trank = read_csv("data/trank_mvc.csv")
    champs = read_csv("data/arch_madness_champions.csv")
    summary = read_csv("data/simulation_summary.csv")
    analysis = read_csv("data/analysis_by_year.csv")

    record = {(int(r["year"]), r["team"]): r["record"] for r in trank}

    teams = {}
    seen = defaultdict(set)
    for r in summary:
        y = int(r["year"])
        if r["format"] != FORMATS[0]:
            continue
        if r["team"] in seen[y]:
            continue
        seen[y].add(r["team"])
        teams.setdefault(y, []).append({
            "seed": int(r["seed"]),
            "team": r["team"],
            "trank": int(float(r["trank"])),
            "adj_em": float(r["adj_em"]),
            "adj_t": float(r["adj_t"]),
            "record": record.get((y, r["team"]), ""),
        })
    for y in teams:
        teams[y].sort(key=lambda t: t["seed"])

    champions = {}
    for r in champs:
        champions[int(r["year"])] = {
            "champion": r["champion"],
            "champion_seed": r["champion_seed"],
            "runner_up": r["runner_up"],
            "runner_up_seed": r["runner_up_seed"],
            "champion_score": r["champion_score"],
            "runner_up_score": r["runner_up_score"],
            "notes": r["notes"],
        }

    summ = defaultdict(lambda: defaultdict(list))
    for r in summary:
        y = int(r["year"])
        summ[y][r["format"]].append({
            "team": r["team"],
            "seed": int(r["seed"]),
            "win_pct": float(r["win_pct"]),
            "actual_champion": int(r["actual_champion"]),
        })
    for y in summ:
        for fmt in summ[y]:
            summ[y][fmt].sort(key=lambda t: -t["win_pct"])

    ana = defaultdict(dict)
    for r in analysis:
        y = int(r["year"])
        ana[y][r["format"]] = {
            "model_pick_team": r["model_pick_team"],
            "model_pick_seed": r["model_pick_seed"],
            "model_pick_win_pct": float(r["model_pick_win_pct"]),
            "actual_champion": r["actual_champion"],
            "actual_sim_win_pct": float(r["actual_sim_win_pct"]) if r["actual_sim_win_pct"] else None,
            "model_correct": r["model_correct"],
        }

    seed_pct = {fmt: defaultdict(float) for fmt in FORMATS}
    seed_years = {fmt: defaultdict(int) for fmt in FORMATS}
    for r in summary:
        fmt = r["format"]
        seed = int(r["seed"])
        seed_pct[fmt][seed] += float(r["win_pct"])
        seed_years[fmt][seed] += 1
    overall_sim = {}
    for fmt in FORMATS:
        overall_sim[fmt] = {s: round(seed_pct[fmt][s] / max(1, seed_years[fmt][s]), 2)
                            for s in sorted(seed_pct[fmt])}

    actual_seed = defaultdict(int)
    n_years = 0
    for r in champs:
        n_years += 1
        if r["champion_seed"]:
            actual_seed[int(r["champion_seed"])] += 1
    overall_actual = {s: round(100 * actual_seed[s] / n_years, 1) for s in sorted(actual_seed)}

    accuracy = {}
    for fmt in FORMATS:
        correct = sum(1 for r in analysis if r["format"] == fmt and r["model_correct"] == "1")
        total = sum(1 for r in analysis if r["format"] == fmt)
        accuracy[fmt] = {"correct": correct, "total": total}

    return {
        "years": YEARS,
        "formats": FORMATS,
        "teams": teams,
        "champions": champions,
        "summary": summ,
        "analysis": ana,
        "overall_sim": overall_sim,
        "overall_actual": overall_actual,
        "seed_champ_counts": dict(actual_seed),
        "accuracy": accuracy,
        "n_years": n_years,
        "bracket_imgs": BRACKET_IMGS,
    }

BRACKET_IMGS = {
    "10-team double bye": "brackets/double_bye.svg",
    "8-team no byes": "brackets/no_byes.svg",
    "10-team 6 single byes": "brackets/six_byes.svg",
}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arch Madness Bracket Models</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#127936;</text></svg>">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {
    --nav: #0f172a; --accent: #2563eb; --good: #16a34a; --bad: #dc2626;
    --bg: #f1f5f9; --card: #ffffff; --line: #e2e8f0; --text: #1e293b; --muted: #64748b;
    --hl: #fef3c7;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, Arial, sans-serif;
         background: var(--bg); color: var(--text); }

  /* Nav */
  nav { background: var(--nav); color: #fff; display: flex; align-items: center;
        gap: 4px; padding: 0 16px; position: sticky; top: 0; z-index: 10; min-height: 52px; }
  .brand { font-weight: 700; font-size: 16px; white-space: nowrap; padding-right: 12px; }
  nav a.tab { color: #cbd5e1; padding: 14px 12px; cursor: pointer; font-size: 14px;
        text-decoration: none; border-bottom: 3px solid transparent; white-space: nowrap; }
  nav a.tab:hover { color: #fff; }
  nav a.tab.active { color: #fff; border-bottom-color: var(--accent); font-weight: 600; }
  .year-sel { background: #1e293b; border: 1px solid #334155; color: #cbd5e1;
        padding: 5px 10px; border-radius: 6px; font-size: 14px; cursor: pointer; margin: 0 4px;
        -webkit-appearance: none; appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2394a3b8'/%3E%3C/svg%3E");
        background-repeat: no-repeat; background-position: right 10px center; padding-right: 28px; }
  .year-sel:focus { outline: 2px solid var(--accent); }
  .spacer { flex: 1; }

  /* Layout */
  main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h2 { font-size: 18px; margin: 28px 0 12px; }
  p.sub { color: var(--muted); font-size: 14px; margin: 0 0 16px; }

  /* Cards */
  .cards { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
  .card h3 { margin: 0 0 10px; font-size: 15px; }

  /* Tables */
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }
  tr.champ { background: #fef9c3; font-weight: 600; }

  /* Badges */
  .badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px;
        font-weight: 700; color: #fff; }
  .badge.y { background: var(--good); } .badge.n { background: var(--bad); }
  .pick { font-size: 17px; font-weight: 700; margin: 2px 0 4px; }
  .pick .pct { color: var(--accent); }
  .toplist { list-style: none; padding: 0; margin: 10px 0 0; font-size: 13px; }
  .toplist li { display: flex; justify-content: space-between; padding: 3px 0;
        border-bottom: 1px dashed var(--line); }

  /* Home hero */
  .hero { padding: 36px 0 20px; }
  .hero h1 { font-size: clamp(2rem, 5vw, 2.8rem); line-height: 1.1; margin-bottom: 10px; }
  .hero .subtitle { font-size: clamp(1rem, 2.5vw, 1.2rem); color: var(--muted); }
  .hero .subtitle em { color: var(--accent); font-style: normal; font-weight: 700; }

  .tog { padding: 5px 14px; border: 1px solid var(--line); border-radius: 999px;
        background: var(--bg); color: var(--muted); cursor: pointer; font-size: 12px; }
  .tog.active { background: var(--accent); color: #fff; border-color: var(--accent); }

  /* Format sections (home) */
  .fmt-sec { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        padding: 20px 24px; margin-bottom: 20px; }
  .fmt-sec-hdr { display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 8px; margin-bottom: 6px; }
  .fmt-sec-hdr h2 { margin: 0; font-size: 19px; display: flex; align-items: center; gap: 10px; }
  .fmt-tog { display: flex; gap: 6px; align-items: center; }
  .badge-new { background: #7c3aed; color: #fff; font-size: 11px; font-weight: 700;
        padding: 2px 8px; border-radius: 999px; letter-spacing: .04em; }
  .seed-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
  .seed-stat { background: var(--bg); border-radius: 8px; padding: 10px 16px; }
  .seed-stat .sv { font-size: 1.4rem; font-weight: 700; color: var(--accent); }
  .seed-stat .sk { font-size: 12px; color: var(--muted); }

  /* Accordion */
  details.accordion { border: 1px solid var(--line); border-radius: 8px;
        margin-bottom: 14px; overflow: hidden; }
  details.accordion summary { padding: 10px 14px; cursor: pointer; font-size: 14px;
        font-weight: 600; list-style: none; display: flex; justify-content: space-between; }
  details.accordion summary::-webkit-details-marker { display: none; }
  details.accordion summary::after { content: '\\25BE'; color: var(--muted); }
  details.accordion[open] summary::after { content: '\\25B4'; }
  details.accordion img { max-width: 100%; display: block;
        border-top: 1px solid var(--line); padding: 12px; }

  /* Year page quick-nav */
  .quick-nav { display: flex; gap: 8px; flex-wrap: wrap; padding: 10px 0 16px;
        border-bottom: 1px solid var(--line); margin-bottom: 4px; }
  .qbtn { padding: 7px 16px; border: 1px solid var(--line); border-radius: 999px;
        background: var(--card); cursor: pointer; font-size: 13px; font-weight: 500; }
  .qbtn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

  /* Section flash */
  .sec { scroll-margin-top: 68px; border-radius: 10px; }
  @keyframes flash { 0%,100%{background:transparent} 30%,70%{background:var(--hl)} }
  .sec.flash { animation: flash 1.4s ease; }

  /* Result cards */
  .result-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 12px; }
  @media (max-width: 540px) { .result-cards { grid-template-columns: 1fr; } }
  .rc { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
  .rc.win { border-left: 4px solid var(--good); }
  .rc.lose { border-left: 4px solid var(--muted); }
  .rc .rc-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--muted);
        letter-spacing: .06em; margin-bottom: 4px; }
  .rc .rc-name { font-size: 1.15rem; font-weight: 700; }
  .rc .rc-seed { font-size: 0.85rem; color: var(--muted); font-weight: 400; }
  .rc .rc-score { font-size: 0.9rem; color: var(--muted); margin-bottom: 10px; }
  .rc .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; }
  .stat-box { background: var(--bg); border-radius: 6px; padding: 8px; text-align: center; }
  .stat-box .bv { font-weight: 700; font-size: 1rem; color: var(--accent); }
  .stat-box .bk { font-size: 11px; color: var(--muted); }

  /* Chalk */
  .chalk-sec { background: var(--card); border: 1px solid var(--line); border-radius: 10px;
        padding: 20px 24px; margin-top: 24px; }
  .chalk-sec h2 { margin: 0 0 4px; }
  .chalk-opts { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 16px; }
  .copt { padding: 6px 16px; border: 1px solid var(--line); border-radius: 999px;
        background: var(--bg); cursor: pointer; font-size: 13px; }
  .copt.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .chalk-rounds { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
  .chalk-round { background: var(--bg); border-radius: 8px; padding: 12px 16px; min-width: 155px; }
  .chalk-round h4 { margin: 0 0 8px; font-size: 11px; text-transform: uppercase;
        color: var(--muted); letter-spacing: .06em; }
  .cg { margin-bottom: 8px; }
  .cg .cg-mu { font-size: 11px; color: var(--muted); line-height: 1.4; }
  .cg .cg-w { font-weight: 700; font-size: 13px; }
  .chalk-champ { margin-top: 14px; background: #f0fdf4; border: 1px solid #86efac;
        border-radius: 8px; padding: 12px 16px; }
  .chalk-champ .cc-lbl { font-size: 11px; font-weight: 700; color: var(--good);
        text-transform: uppercase; letter-spacing: .06em; }
  .chalk-champ .cc-name { font-size: 1.15rem; font-weight: 700; margin-top: 4px; }
  .chalk-champ .cc-stats { font-size: 13px; color: var(--muted); margin-top: 4px; }

  /* About */
  .about code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
  .about pre { background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 8px;
        overflow-x: auto; font-size: 13px; line-height: 1.5; }
  .about img { max-width: 100%; border: 1px solid var(--line); border-radius: 8px;
        display: block; margin: 8px 0 20px; }

  canvas { max-height: 240px; }
</style>
</head>
<body>
<nav id="nav"></nav>
<main id="main"></main>
<script>
const DATA = __DATA__;
let charts = [];
let viewMode = 'bar';
let chalkFormat = DATA.formats[0];
let currentYear = null;

const FMT_LABEL = {
  '10-team double bye':    'If it was a 10-team with a double bye',
  '8-team no byes':        'If it was an 8-team bracket',
  '10-team 6 single byes': 'If it was a 10-team with 6 byes'
};
const FMT_SHORT = {
  '10-team double bye':    'Double Bye',
  '8-team no byes':        '8-Team',
  '10-team 6 single byes': '6 Byes'
};
const BLUE = '#2563eb';
const AMBER = '#f59e0b';

function destroyCharts() { charts.forEach(c => c.destroy()); charts = []; }

/* ── Nav ── */
function buildNav() {
  const opts = DATA.years.map(y => `<option value="${y}">${y}</option>`).join('');
  document.getElementById('nav').innerHTML =
    `<span class="brand">Arch Madness</span>
     <a class="tab" id="tab-home" href="#" onclick="show('home');return false">Home</a>
     <select class="year-sel" id="yr-sel" onchange="if(this.value)show('year',+this.value)">
       <option value="">Year</option>${opts}
     </select>
     <a class="tab" id="tab-about" href="#" onclick="show('about');return false">About</a>`;
}

function setNav(view) {
  document.getElementById('tab-home').classList.toggle('active', view === 'home');
  document.getElementById('tab-about').classList.toggle('active', view === 'about');
  document.getElementById('yr-sel').value = view === 'year' ? String(currentYear) : '';
}

function show(view, year) {
  destroyCharts();
  if (view === 'home')  { renderHome();       setNav('home');  location.hash = 'home'; }
  if (view === 'about') { renderAbout();      setNav('about'); location.hash = 'about'; }
  if (view === 'year')  { currentYear = year; renderYear(year); setNav('year'); location.hash = 'year/' + year; }
  window.scrollTo(0, 0);
}

/* ── Home ── */
function renderHome() {
  const n  = DATA.n_years;
  const c1 = DATA.seed_champ_counts[1] || 0;
  const c2 = DATA.seed_champ_counts[2] || 0;

  let html = `
    <div class="card" style="margin-bottom:20px;padding:24px 28px">
      <h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.1;margin:0 0 10px">Over the Last ${n} Years</h1>
      <p style="font-size:clamp(1rem,2.5vw,1.15rem);color:var(--muted);margin:0">
        The #1 seed won <strong style="color:var(--accent)">${c1} of ${n}</strong> championships
        &nbsp;&middot;&nbsp;
        The #2 seed won <strong style="color:var(--accent)">${c2} of ${n}</strong>
      </p>
    </div>`;

  DATA.formats.forEach((fmt, i) => {
    const sim = DATA.overall_sim[fmt];
    const s1  = (sim[1] || 0).toFixed(1);
    const s2  = (sim[2] || 0).toFixed(1);
    const isNew = fmt === '10-team double bye';
    html += `
    <div class="fmt-sec">
      <div class="fmt-sec-hdr">
        <h2>${FMT_LABEL[fmt]}${isNew ? ' <span class="badge-new">NEW 2027</span>' : ''}</h2>
        <div class="fmt-tog">
          <button class="tog ${viewMode==='bar'?'active':''}"   data-m="bar"   onclick="setViewMode('bar')">Bar Chart</button>
          <button class="tog ${viewMode==='table'?'active':''}" data-m="table" onclick="setViewMode('table')">Table</button>
        </div>
      </div>
      <div class="seed-row">
        <div class="seed-stat"><div class="sv">${s1}%</div><div class="sk">#1 Seed avg win %</div></div>
        <div class="seed-stat"><div class="sv">${s2}%</div><div class="sk">#2 Seed avg win %</div></div>
      </div>
      <details class="accordion">
        <summary>About this format</summary>
        <img src="${DATA.bracket_imgs[fmt]}" alt="${fmt} bracket">
      </details>
      <div id="fc${i}"></div>
    </div>`;
  });

  document.getElementById('main').innerHTML = html;
  DATA.formats.forEach((fmt, i) => drawFmtChart(i, fmt));
}

function setViewMode(mode) {
  viewMode = mode;
  document.querySelectorAll('.tog').forEach(b => b.classList.toggle('active', b.dataset.m === mode));
  DATA.formats.forEach((fmt, i) => { if (document.getElementById('fc'+i)) drawFmtChart(i, fmt); });
}

function drawFmtChart(idx, fmt) {
  const el = document.getElementById('fc' + idx);
  if (!el) return;
  charts = charts.filter(c => { if (c.canvas && c.canvas.parentElement === el) { c.destroy(); return false; } return true; });

  const sim   = DATA.overall_sim[fmt];
  const seeds = Object.keys(sim).map(Number).sort((a,b) => a-b);

  if (viewMode === 'table') {
    let t = '<table><thead><tr><th>Seed</th><th>Avg Sim Win %</th><th>Actual Win %</th></tr></thead><tbody>';
    seeds.forEach(s => {
      const actPct = ((DATA.seed_champ_counts[s]||0)/DATA.n_years*100).toFixed(1);
      t += `<tr><td>#${s}</td><td>${sim[s].toFixed(1)}%</td><td>${actPct}%</td></tr>`;
    });
    el.innerHTML = t + '</tbody></table>';
  } else {
    el.innerHTML = `<canvas id="fc-cv${idx}"></canvas>`;
    charts.push(new Chart(document.getElementById('fc-cv'+idx), {
      type: 'bar',
      data: {
        labels: seeds.map(s => '#' + s),
        datasets: [
          { label: 'Simulated %', data: seeds.map(s => sim[s]), backgroundColor: BLUE }
        ]
      },
      options: { responsive: true,
        plugins: { legend: { labels: { boxWidth: 12 } } },
        scales:  { x: { ticks: { font: { size: 11 } } },
                   y: { beginAtZero: true, ticks: { callback: v => v + '%' } } }
      }
    }));
  }
}

/* ── About ── */
function renderAbout() {
  let brackets = '';
  DATA.formats.forEach(fmt => {
    brackets += `<h3>${FMT_LABEL[fmt]}</h3><img src="${DATA.bracket_imgs[fmt]}" alt="${fmt}">`;
  });
  document.getElementById('main').innerHTML = `
    <div class="about">
      <h1>How This Works</h1>
      <h2>Data Source</h2>
      <p>Team efficiency ratings come from <strong>T-Rank</strong> (barttorvik.com): adjusted
         offensive efficiency (AdjOE), defensive efficiency (AdjDE), and tempo (AdjT) for every
         MVC team, 2015&ndash;2025 (2020 skipped &mdash; tournament cancelled).</p>
      <h2>Win Probability</h2>
      <p>Each game is decided by the two teams' efficiency margins on a neutral court:</p>
      <pre>expected_margin = AdjEM_A - AdjEM_B      (AdjEM = AdjOE - AdjDE)
sigma           = 11.9 &times; sqrt(avg_pace / 67.5)
p_win           = normal_cdf(expected_margin / sigma)</pre>
      <ul>
        <li><code>sigma = 11.9</code> is the KenPom empirical standard deviation for college basketball.</li>
        <li>Tempo scaling: faster games have more scoring variance.</li>
        <li>No home-court adjustment &mdash; all MVC games at Enterprise Center, St. Louis.</li>
      </ul>
      <h2>Simulation</h2>
      <p>Each year &times; format is played <strong>10,000 times</strong>. A team's championship %
         is how many of those runs it won. Seeds are actual MVC seeds (set by conference record),
         not by efficiency.</p>
      <h2>The Three Bracket Formats</h2>
      ${brackets}
      <h2>A Proposal: Split Format for the Combined Event</h2>
      <p>Starting in 2027 both the men&rsquo;s and women&rsquo;s MVC tournaments join in St. Louis
         as Arch Madness. Both brackets have 10 teams. What if the two brackets used
         <em>different</em> formats optimized around a shared schedule?</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0">
        <div style="background:var(--bg);border-radius:10px;padding:14px 18px">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin-bottom:6px">Women</div>
          <div style="font-weight:700;font-size:15px;margin-bottom:4px">10-team double bye</div>
          <div style="font-size:13px;color:var(--muted)">Seeds 1&amp;2 rest until the <strong>semifinals</strong>.</div>
          <div style="margin-top:8px;font-size:1.1rem;font-weight:700;color:var(--accent)">${(DATA.overall_sim['10-team double bye'][1]||0).toFixed(1)}%</div>
          <div style="font-size:11px;color:var(--muted)">#1 seed avg simulated win rate</div>
        </div>
        <div style="background:var(--bg);border-radius:10px;padding:14px 18px">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin-bottom:6px">Men</div>
          <div style="font-weight:700;font-size:15px;margin-bottom:4px">10-team with 6 byes</div>
          <div style="font-size:13px;color:var(--muted)">Seeds 1&ndash;6 rest until the <strong>quarterfinals</strong>.</div>
          <div style="margin-top:8px;font-size:1.1rem;font-weight:700;color:var(--accent)">${(DATA.overall_sim['10-team 6 single byes'][1]||0).toFixed(1)}%</div>
          <div style="font-size:11px;color:var(--muted)">#1 seed avg simulated win rate</div>
        </div>
      </div>
      <table>
        <thead><tr><th>Day</th><th>Women</th><th>Men</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Wed</strong></td>
            <td>First round: 3v10, 4v9, 5v8, 6v7 &nbsp;<span style="color:var(--muted);font-size:12px">(4 games)</span></td>
            <td style="color:var(--muted)">&mdash;</td>
          </tr>
          <tr>
            <td><strong>Thu</strong></td>
            <td>Quarterfinals: R1 winners play each other &mdash; seeds 1&amp;2 still out &nbsp;<span style="color:var(--muted);font-size:12px">(2 games)</span></td>
            <td>Opening round: 7v10, 8v9 &nbsp;<span style="color:var(--muted);font-size:12px">(2 games)</span></td>
          </tr>
          <tr style="background:var(--hl)">
            <td><strong>Fri</strong></td>
            <td style="color:var(--muted)">&mdash;</td>
            <td><strong>Quarterfinals</strong>: seeds 1&ndash;6 join in &nbsp;<span style="color:var(--muted);font-size:12px">(4 games)</span></td>
          </tr>
          <tr>
            <td><strong>Sat</strong></td>
            <td>Semifinals: seeds 1&amp;2 join in &nbsp;<span style="color:var(--muted);font-size:12px">(2 games)</span></td>
            <td>Semifinals &nbsp;<span style="color:var(--muted);font-size:12px">(2 games)</span></td>
          </tr>
          <tr>
            <td><strong>Sun</strong></td>
            <td>Championship Final</td>
            <td>Championship Final</td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top:14px;color:var(--muted)">Friday delivers 4 men&rsquo;s games in a single
         session &mdash; the best day of the tournament. Women&rsquo;s seeds 1 and 2 are protected
         until the final four. Men&rsquo;s seeds 1&ndash;6 get a meaningful rest advantage without
         sitting out as long as the double-bye format would require.</p>
    </div>`;
}

/* ── Year ── */
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}

function renderYear(year) {
  const m      = document.getElementById('main');
  const teams  = DATA.teams[year] || [];
  const champ  = DATA.champions[year];
  const cName  = champ ? champ.champion : '';

  // Quick-nav
  let html = `<h1>${year} Arch Madness</h1>
    <div class="quick-nav">
      <button class="qbtn" onclick="scrollToSection('sec-sims')">Simulations</button>
      <button class="qbtn" onclick="scrollToSection('sec-field')">Teams</button>
      <button class="qbtn" onclick="scrollToSection('sec-actual')">Actual Results</button>
      <button class="qbtn" onclick="scrollToSection('sec-chalk')">Chalk Bracket</button>
    </div>`;

  // Simulations
  html += `<div id="sec-sims" class="sec"><h2>Title Odds by Format</h2><div class="cards">`;

  // Actual winner card
  if (champ) {
    const cSt = teams.find(t => t.team === champ.champion);
    const em  = cSt ? (cSt.adj_em >= 0 ? '+' : '') + cSt.adj_em.toFixed(1) : '';
    const sc  = champ.champion_score && champ.runner_up_score
                ? `${champ.champion_score}–${champ.runner_up_score}` : '';
    html += `<div class="card" style="border-left:4px solid var(--good)">
      <h3 style="color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Actual Winner</h3>
      <div class="pick" style="font-size:1.2rem">${champ.champion}</div>
      <div style="color:var(--muted);font-size:13px;margin-bottom:12px">
        Seed #${champ.champion_seed || '?'}${sc ? ' &middot; ' + sc : ''}
      </div>
      ${cSt ? `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        <div class="stat-box"><div class="bv">${em}</div><div class="bk">AdjEM</div></div>
        <div class="stat-box"><div class="bv">${cSt.adj_t.toFixed(1)}</div><div class="bk">AdjT</div></div>
        <div class="stat-box"><div class="bv">#${cSt.trank}</div><div class="bk">T-Rank</div></div>
      </div>` : ''}
      ${champ.notes ? `<p class="sub" style="margin-top:10px;font-size:12px">${champ.notes}</p>` : ''}
    </div>`;
  }

  DATA.formats.forEach((f, i) => {
    const ana     = DATA.analysis[year][f];
    const correct = ana.model_correct === '1';
    html += `<div class="card">
      <h3>${FMT_LABEL[f]}</h3>
      <div class="pick">${ana.model_pick_team} <span class="pct">${ana.model_pick_win_pct.toFixed(1)}%</span></div>
      <div>Model pick &middot; <span class="badge ${correct?'y':'n'}">${correct?'CORRECT':'MISS'}</span></div>
      <canvas id="yrc${i}"></canvas>
      <ul class="toplist">`;
    DATA.summary[year][f].slice(0, 5).forEach(t => {
      html += `<li><span>${t.seed}. ${t.team}</span><span>${t.win_pct.toFixed(1)}%</span></li>`;
    });
    html += `</ul></div>`;
  });
  html += `</div></div>`;

  // Field
  html += `<div id="sec-field" class="sec"><h2>Teams</h2>
    <table><thead><tr><th>Seed</th><th>Team</th><th>T-Rank</th><th>AdjEM</th><th>AdjT</th><th>Record</th></tr></thead><tbody>`;
  teams.forEach(t => {
    const cls = t.team === cName ? ' class="champ"' : '';
    const em  = (t.adj_em >= 0 ? '+' : '') + t.adj_em.toFixed(1);
    html += `<tr${cls}><td>${t.seed}</td><td>${t.team}</td><td>${t.trank}</td><td>${em}</td><td>${t.adj_t.toFixed(1)}</td><td>${t.record}</td></tr>`;
  });
  html += `</tbody></table></div>`;

  // Actual results
  html += `<div id="sec-actual" class="sec"><h2>Actual Result</h2>`;
  if (champ) {
    const cSt = teams.find(t => t.team === champ.champion);
    const rSt = teams.find(t => t.team === champ.runner_up);
    const sc  = champ.champion_score && champ.runner_up_score
                ? `${champ.champion_score}–${champ.runner_up_score}` : '';
    html += `<div class="result-cards">`;
    html += rcCard('win',  'Champion',  champ.champion,  champ.champion_seed,  sc, cSt);
    html += rcCard('lose', 'Runner-Up', champ.runner_up, champ.runner_up_seed, sc, rSt);
    html += `</div>`;
    if (champ.notes) html += `<p class="sub" style="margin-top:10px">${champ.notes}</p>`;
  }
  html += `</div>`;

  // Chalk
  html += `<div id="sec-chalk" class="chalk-sec sec">
    <h2>Chalk Bracket</h2>
    <p class="sub">If the higher-efficiency team wins every game.</p>
    <div class="chalk-opts" id="chalk-opts"></div>
    <div id="chalk-out"></div>
  </div>`;

  m.innerHTML = html;

  // Chalk option buttons
  const optsEl = document.getElementById('chalk-opts');
  DATA.formats.forEach(fmt => {
    const b = document.createElement('button');
    b.className = 'copt' + (fmt === chalkFormat ? ' active' : '');
    b.textContent = FMT_SHORT[fmt];
    b.dataset.fmt = fmt;
    b.onclick = () => setChalkFmt(fmt);
    optsEl.appendChild(b);
  });
  renderChalk(year);

  // Year charts
  DATA.formats.forEach((f, i) => {
    const rows = DATA.summary[year][f].slice().sort((a,b) => a.seed - b.seed);
    charts.push(new Chart(document.getElementById('yrc' + i), {
      type: 'bar',
      data: {
        labels: rows.map(r => '#' + r.seed),
        datasets: [{ label: 'Win %', data: rows.map(r => r.win_pct),
          backgroundColor: rows.map(r => r.actual_champion ? AMBER : BLUE) }]
      },
      options: { responsive: true, plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { callback: v => v + '%' } } } }
    }));
  });
}

function rcCard(cls, label, name, seed, score, stats) {
  let h = `<div class="rc ${cls}">
    <div class="rc-lbl">${label}</div>
    <div class="rc-name">${name} <span class="rc-seed">${seed ? '#' + seed : ''}</span></div>
    ${score ? '<div class="rc-score">' + score + '</div>' : ''}`;
  if (stats) {
    const em = (stats.adj_em >= 0 ? '+' : '') + stats.adj_em.toFixed(1);
    h += `<div class="stats-grid">
      <div class="stat-box"><div class="bv">${em}</div><div class="bk">AdjEM</div></div>
      <div class="stat-box"><div class="bv">${stats.adj_t.toFixed(1)}</div><div class="bk">AdjT</div></div>
      <div class="stat-box"><div class="bv">#${stats.trank}</div><div class="bk">T-Rank</div></div>
    </div>`;
  }
  return h + '</div>';
}

/* ── Chalk ── */
function setChalkFmt(fmt) {
  chalkFormat = fmt;
  document.querySelectorAll('.copt').forEach(b => b.classList.toggle('active', b.dataset.fmt === fmt));
  renderChalk(currentYear);
}

function chalkBracket(fmt, teams) {
  const s = {};
  teams.forEach(t => s[t.seed] = t);
  const w = (a, b) => !a ? b : !b ? a : (a.adj_em >= b.adj_em ? a : b);
  const mu = (a, b) => `#${a ? a.seed : '?'} ${a ? a.team : '?'} vs #${b ? b.seed : '?'} ${b ? b.team : '?'}`;
  const rounds = [];

  if (fmt === '10-team double bye') {
    const r1 = [w(s[3],s[10]), w(s[4],s[9]), w(s[5],s[8]), w(s[6],s[7])];
    rounds.push({ name: 'First Round', games: [
      { mu: mu(s[3],s[10]), winner: r1[0] }, { mu: mu(s[4],s[9]), winner: r1[1] },
      { mu: mu(s[5],s[8]), winner: r1[2] }, { mu: mu(s[6],s[7]), winner: r1[3] },
    ]});
    const qf = [w(r1[0],r1[1]), w(r1[2],r1[3])];
    rounds.push({ name: 'Quarterfinals', games: [
      { mu: `${r1[0]?r1[0].team:'?'} vs ${r1[1]?r1[1].team:'?'}`, winner: qf[0] },
      { mu: `${r1[2]?r1[2].team:'?'} vs ${r1[3]?r1[3].team:'?'}`, winner: qf[1] },
    ]});
    const sf = [w(s[1],qf[0]), w(s[2],qf[1])];
    rounds.push({ name: 'Semifinals', games: [
      { mu: `#1 ${s[1]?s[1].team:'?'} vs ${qf[0]?qf[0].team:'?'}`, winner: sf[0] },
      { mu: `#2 ${s[2]?s[2].team:'?'} vs ${qf[1]?qf[1].team:'?'}`, winner: sf[1] },
    ]});
    const champ = w(sf[0],sf[1]);
    rounds.push({ name: 'Championship', games: [{ mu: `${sf[0]?sf[0].team:'?'} vs ${sf[1]?sf[1].team:'?'}`, winner: champ }]});
    return { rounds, champion: champ };
  }

  if (fmt === '10-team 6 single byes') {
    const r1 = [w(s[7],s[10]), w(s[8],s[9])];
    rounds.push({ name: 'First Round', games: [
      { mu: mu(s[7],s[10]), winner: r1[0] }, { mu: mu(s[8],s[9]), winner: r1[1] },
    ]});
    const qf = [w(s[1],r1[1]), w(s[2],r1[0]), w(s[3],s[6]), w(s[4],s[5])];
    rounds.push({ name: 'Quarterfinals', games: [
      { mu: `#1 ${s[1]?s[1].team:'?'} vs ${r1[1]?r1[1].team:'?'}`, winner: qf[0] },
      { mu: `#2 ${s[2]?s[2].team:'?'} vs ${r1[0]?r1[0].team:'?'}`, winner: qf[1] },
      { mu: mu(s[3],s[6]), winner: qf[2] }, { mu: mu(s[4],s[5]), winner: qf[3] },
    ]});
    const sf = [w(qf[0],qf[3]), w(qf[1],qf[2])];
    rounds.push({ name: 'Semifinals', games: [
      { mu: `${qf[0]?qf[0].team:'?'} vs ${qf[3]?qf[3].team:'?'}`, winner: sf[0] },
      { mu: `${qf[1]?qf[1].team:'?'} vs ${qf[2]?qf[2].team:'?'}`, winner: sf[1] },
    ]});
    const champ = w(sf[0],sf[1]);
    rounds.push({ name: 'Championship', games: [{ mu: `${sf[0]?sf[0].team:'?'} vs ${sf[1]?sf[1].team:'?'}`, winner: champ }]});
    return { rounds, champion: champ };
  }

  // 8-team no byes
  const r1 = [w(s[1],s[8]), w(s[2],s[7]), w(s[3],s[6]), w(s[4],s[5])];
  rounds.push({ name: 'First Round', games: [
    { mu: mu(s[1],s[8]), winner: r1[0] }, { mu: mu(s[2],s[7]), winner: r1[1] },
    { mu: mu(s[3],s[6]), winner: r1[2] }, { mu: mu(s[4],s[5]), winner: r1[3] },
  ]});
  const sf = [w(r1[0],r1[3]), w(r1[1],r1[2])];
  rounds.push({ name: 'Semifinals', games: [
    { mu: `${r1[0]?r1[0].team:'?'} vs ${r1[3]?r1[3].team:'?'}`, winner: sf[0] },
    { mu: `${r1[1]?r1[1].team:'?'} vs ${r1[2]?r1[2].team:'?'}`, winner: sf[1] },
  ]});
  const champ = w(sf[0],sf[1]);
  rounds.push({ name: 'Championship', games: [{ mu: `${sf[0]?sf[0].team:'?'} vs ${sf[1]?sf[1].team:'?'}`, winner: champ }]});
  return { rounds, champion: champ };
}

function renderChalk(year) {
  const out = document.getElementById('chalk-out');
  if (!out) return;
  const teams = DATA.teams[year];
  if (!teams) { out.innerHTML = '<p class="sub">No team data for this year.</p>'; return; }
  const { rounds, champion } = chalkBracket(chalkFormat, teams);
  let html = '<div class="chalk-rounds">';
  rounds.forEach(r => {
    html += `<div class="chalk-round"><h4>${r.name}</h4>`;
    r.games.forEach(g => {
      html += `<div class="cg"><div class="cg-mu">${g.mu}</div><div class="cg-w">&rarr; ${g.winner ? g.winner.team : '?'}</div></div>`;
    });
    html += '</div>';
  });
  html += '</div>';
  if (champion) {
    const em = (champion.adj_em >= 0 ? '+' : '') + champion.adj_em.toFixed(1);
    html += `<div class="chalk-champ">
      <div class="cc-lbl">Chalk Champion</div>
      <div class="cc-name">#${champion.seed} ${champion.team}</div>
      <div class="cc-stats">AdjEM ${em} &middot; AdjT ${champion.adj_t.toFixed(1)} &middot; T-Rank #${champion.trank}</div>
    </div>`;
  }
  out.innerHTML = html;
}

buildNav();
(function() {
  const h = location.hash.replace('#', '');
  if (h.startsWith('year/')) { const y = parseInt(h.split('/')[1]); if (DATA.years.includes(y)) { show('year', y); return; } }
  if (h === 'about') { show('about'); return; }
  show('home');
})();
</script>
</body>
</html>
"""

def main():
    data = build_data()
    html = HTML.replace("__DATA__", json.dumps(data))
    os.makedirs("docs", exist_ok=True)
    out = os.path.join("docs", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
