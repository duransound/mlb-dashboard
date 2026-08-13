"""
Shared HTML/CSS/JS template for the NWSL analytics dashboard: a single
self-contained, tabbed, interactive page combining every chart built so far.
No CDN dependencies (learned the hard way -- see README) -- pure vanilla
SVG + JS, so it also works fully offline once generated.

This is the natural stepping stone toward a real webapp: it's already a
client-side single-page app. The jump from here to "deployed webapp" is
mostly: (1) swap the embedded JSON for a live fetch, (2) host the file
somewhere. See the README's "From dashboard to webapp" section.
"""

import json

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Karla:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Cg transform='translate(100,100)'%3E%3Cg transform='rotate(0)'%3E%3Cpath fill='%23C98A2E' stroke='%231F1B16' stroke-width='4' d='M0,0 C-22,-11 -37,-33 -33,-55 C-29,-75 29,-75 33,-55 C37,-33 22,-11 0,0 Z'/%3E%3C/g%3E%3Cg transform='rotate(90)'%3E%3Cpath fill='%23C98A2E' stroke='%231F1B16' stroke-width='4' d='M0,0 C-22,-11 -37,-33 -33,-55 C-29,-75 29,-75 33,-55 C37,-33 22,-11 0,0 Z'/%3E%3C/g%3E%3Cg transform='rotate(180)'%3E%3Cpath fill='%23C98A2E' stroke='%231F1B16' stroke-width='4' d='M0,0 C-22,-11 -37,-33 -33,-55 C-29,-75 29,-75 33,-55 C37,-33 22,-11 0,0 Z'/%3E%3C/g%3E%3Cg transform='rotate(270)'%3E%3Cpath fill='%23C98A2E' stroke='%231F1B16' stroke-width='4' d='M0,0 C-22,-11 -37,-33 -33,-55 C-29,-75 29,-75 33,-55 C37,-33 22,-11 0,0 Z'/%3E%3C/g%3E%3Ccircle r='10' fill='%231F1B16'/%3E%3C/g%3E%3C/svg%3E">
<style>
  :root {{
    color-scheme: light;
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --grid: #e1e0d9;
    --baseline: #c3c2b7;
    --series-1: #C98A2E;
    --series-1-dark: #8A5A1E;
    --series-1-ink: #1F1B16;
    --surface-2: #eceff1;
    --red: #e34948;
    --font-body: 'Karla', system-ui, -apple-system, "Segoe UI", sans-serif;
    --font-head: 'Fraunces', Georgia, serif;
    --font-brand: 'Fraunces', Georgia, serif;
    --brand-amber: #C98A2E;
    --brand-ink: #1F1B16;
    --brand-clay: #B5573F;
    --brand-warmgray: #8C8377;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: var(--font-body); background: var(--page); color: var(--text-primary); }}
  .app {{ max-width: 960px; margin: 0 auto; padding: 28px 24px 48px; text-align: left; }}
  .masthead {{ display: flex; align-items: center; gap: 10px; margin-bottom: 22px; }}
  .masthead-mark {{ width: 36px; height: 36px; flex: none; }}
  .masthead-word {{ font-family: var(--font-brand); font-weight: 600; font-size: 16px; color: var(--brand-ink); letter-spacing: -0.01em; }}
  .app-header {{ border-top: 1px solid var(--grid); padding-top: 18px; }}
  .app-header h1 {{ font-family: var(--font-head); font-weight: 600; letter-spacing: -0.01em; font-size: 22px; margin: 0 0 4px; }}
  .app-header p {{ font-size: 13px; color: var(--text-secondary); margin: 0 0 20px; max-width: 660px; }}
  .tabs {{ display: flex; gap: 6px; flex-wrap: wrap; border-bottom: 1px solid var(--grid); margin-bottom: 20px; }}
  .tab-btn {{
    appearance: none; border: none; background: none; padding: 9px 14px; font-family: var(--font-body); font-size: 13px;
    font-weight: 700; color: var(--text-muted); cursor: pointer; border-radius: 8px 8px 0 0;
    position: relative; top: 1px;
  }}
  .tab-btn:hover {{ color: var(--text-primary); }}
  .tab-btn.active {{ color: var(--series-1); border-bottom: 2px solid var(--series-1); }}
  .panel {{ display: none; background: var(--surface-1); border-radius: 12px; padding: 20px 24px 24px; text-align: left; }}
  .panel.active {{ display: block; }}
  .kicker {{ font-family: var(--font-body); font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-muted); margin: 0 0 6px; }}
  .panel h2 {{ font-family: var(--font-head); font-weight: 600; letter-spacing: -0.01em; font-size: 18px; margin: 0 0 6px; line-height: 1.35; max-width: 640px; }}
  .panel .blurb {{ font-size: 12.5px; color: var(--text-secondary); margin: 0 0 16px; max-width: 640px; }}
  .story {{ margin: 0 0 22px; padding: 16px 20px; background: var(--surface-1); border-radius: 12px; border-left: 3px solid var(--series-1); }}
  .story .kicker {{ margin: 0 0 6px; }}
  .story-lede {{ font-family: var(--font-body); font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.5; margin: 0; max-width: 680px; }}
  .panel select {{
    font-family: var(--font-body); font-size: 13px; font-weight: 500; color: var(--text-primary);
    background: var(--surface-1); border: 1px solid var(--baseline); border-radius: 6px;
    padding: 7px 10px; cursor: pointer;
  }}
  .picker-label {{ font-size: 11.5px; color: var(--text-muted); margin: 0 0 4px; }}
  .picker-row {{ display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-end; margin-bottom: 4px; }}
  .picker-group {{ display: flex; flex-direction: column; }}
  .compare-caption {{ font-size: 12.5px; color: var(--text-primary); font-weight: 500; margin-top: 14px; }}
  /* The longer, paragraph-style team blurb (build_team_blurbs) reads as
     supporting detail, not a headline stat -- lighter weight/color than the
     punchier one-line stat-leader caption that follows it, and pulled in
     closer so the two read as one connected block. */
  .compare-caption.team-blurb {{ font-weight: 400; color: var(--text-secondary); margin-bottom: 2px; }}
  .compare-caption.team-blurb + .compare-caption {{ margin-top: 6px; }}
  .axis line {{ stroke: var(--baseline); }}
  .axis text {{ fill: var(--text-muted); font-size: 11px; }}
  .gridline {{ stroke: var(--grid); stroke-width: 1px; }}
  .axis-label {{ fill: var(--text-secondary); font-size: 12px; }}
  .bar {{ fill: var(--series-1); }}
  .bar.negative {{ fill: var(--red); }}
  .bar.muted {{ fill: var(--baseline); }}
  .bar:hover {{ opacity: 0.85; cursor: pointer; }}
  .bar-label {{ fill: var(--text-primary); font-size: 11px; }}
  .bar-label.muted {{ fill: var(--text-muted); }}
  .bar-value {{ fill: var(--text-secondary); font-size: 10.5px; }}
  .annotation {{
    fill: var(--text-primary); font-size: 11.5px; font-weight: 600;
    /* Halo behind the text (a stroke drawn under the fill via paint-order)
       so the one annotated point's label stays legible even when it lands
       over a busy background -- e.g. a dense unlabeled scatter cluster,
       see drawScatter's DENSE_THRESHOLD. */
    paint-order: stroke; stroke: var(--surface-1); stroke-width: 4px; stroke-linejoin: round;
  }}
  .bubble {{ fill: var(--series-1); stroke: var(--surface-1); stroke-width: 2px; cursor: pointer; }}
  .bubble.muted {{ fill: var(--baseline); }}
  .bubble:hover, .bubble.hover {{ fill: var(--series-1-dark); }}
  /* Dense mode (hundreds of unlabeled points): a lighter stroke and some
     fill transparency so overlapping dots read as visible density rather
     than a solid mass -- see drawScatter's DENSE_THRESHOLD. */
  .bubble.dense {{ stroke-width: 1px; fill-opacity: 0.8; }}
  .bubble.dense.muted {{ fill-opacity: 0.55; }}
  .badge-text {{ fill: var(--series-1-ink); font-size: 9.5px; font-weight: 600; text-anchor: middle; pointer-events: none; }}
  .badge-text.muted {{ fill: var(--text-secondary); }}
  .refline {{ stroke: var(--baseline); stroke-width: 1px; stroke-dasharray: 4 3; }}
  /* Solid (not dashed), so it reads as a fixed reference point (0 WAR =
     replacement level) rather than a sample-dependent statistic like the
     dashed median lines. */
  .zero-line {{ stroke: var(--text-muted); stroke-width: 1px; }}
  .tooltip {{
    position: absolute; pointer-events: none; background: var(--text-primary); color: #fff;
    padding: 8px 10px; border-radius: 6px; font-size: 12px; line-height: 1.5; opacity: 0;
    transition: opacity 0.1s ease; box-shadow: 0 4px 14px rgba(0,0,0,0.18); max-width: 230px; z-index: 10;
  }}
  .tooltip .name {{ font-weight: 600; margin-bottom: 2px; }}
  .tooltip .row {{ color: #d8d8d4; }}
  .footnote {{ font-size: 11px; color: var(--text-muted); margin-top: 14px; }}
  .legend {{ display: flex; gap: 16px; font-size: 11.5px; color: var(--text-secondary); margin-bottom: 10px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .legend-swatch {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  .line-path {{ fill: none; stroke: var(--series-1); stroke-width: 2.5px; }}
  .line-dot {{ fill: var(--series-1); stroke: var(--surface-1); stroke-width: 2px; cursor: pointer; }}
  .line-dot:hover {{ fill: var(--series-1-dark); }}
  .pitch-outline {{ fill: none; stroke: var(--baseline); stroke-width: 1.5px; }}
  .pitch-line {{ fill: none; stroke: var(--baseline); stroke-width: 1px; }}
  .shot-dot {{ stroke: var(--series-1); stroke-width: 1.5px; cursor: pointer; }}
  .shot-dot.goal {{ fill: var(--series-1); }}
  .shot-dot.no-goal {{ fill: var(--surface-1); }}
  .shot-dot.muted {{ stroke: var(--baseline); }}
  .shot-dot.muted.no-goal {{ fill: var(--surface-1); }}
</style>
</head>
<body>
<div class="app">
  <div class="masthead">
    <svg class="masthead-mark" viewBox="0 0 240 240" aria-hidden="true">
      <g stroke="#B5573F" fill="none" stroke-linecap="round" opacity="0.6">
        <path d="M6,74 L234,74" stroke-width="2"/>
        <path d="M6,74 C34,46 52,20 68,20 C92,20 96,54 120,58 C144,54 148,20 172,20 C188,20 206,46 234,74" stroke-width="2"/>
        <line x1="63" y1="72" x2="63" y2="20" stroke-width="3"/>
        <line x1="73" y1="72" x2="73" y2="20" stroke-width="3"/>
        <line x1="63" y1="34" x2="73" y2="34" stroke-width="2"/>
        <line x1="63" y1="52" x2="73" y2="52" stroke-width="2"/>
        <line x1="167" y1="72" x2="167" y2="20" stroke-width="3"/>
        <line x1="177" y1="72" x2="177" y2="20" stroke-width="3"/>
        <line x1="167" y1="34" x2="177" y2="34" stroke-width="2"/>
        <line x1="167" y1="52" x2="177" y2="52" stroke-width="2"/>
      </g>
      <path fill="none" stroke="#8C8377" stroke-width="1.5" opacity="0.25" stroke-linecap="round" d="M-10,80 C40,72 80,88 120,80 C160,72 200,88 250,80"/>
      <path fill="none" stroke="#8C8377" stroke-width="1.5" opacity="0.35" stroke-linecap="round" d="M-10,195 C40,183 80,207 120,195 C160,183 200,207 250,195"/>
      <path fill="none" stroke="#8C8377" stroke-width="2" opacity="0.55" stroke-linecap="round" d="M-10,210 C40,196 90,224 130,210 C170,196 210,224 250,210"/>
      <path fill="none" stroke="#8C8377" stroke-width="2.5" opacity="0.8" stroke-linecap="round" d="M-10,226 C40,210 90,240 130,226 C170,210 220,240 250,226"/>
      <g transform="translate(120,150)">
        <g transform="rotate(0)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <g transform="rotate(90)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <g transform="rotate(180)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <g transform="rotate(270)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <circle r="8" fill="#1F1B16"/>
      </g>
    </svg>
    <span class="masthead-word">Poppies in the Fog</span>
  </div>
  <div class="app-header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>
{story_block}  <div class="tabs" id="tabs"></div>
  <div id="panels"></div>
</div>
<div class="tooltip" id="tooltip"></div>
<script>
const CHARTS = {charts_json};

// ---------- tiny chart-drawing library (no dependencies) ----------
const svgNS = "http://www.w3.org/2000/svg";
function el(tag, attrs) {{
  const e = document.createElementNS(svgNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}}
function niceStep(maxVal, targetTicks) {{
  const raw = maxVal / targetTicks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const norm = raw / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
  return step;
}}
function ticksFor(minVal, maxVal, targetTicks) {{
  const step = niceStep(maxVal - minVal, targetTicks);
  const out = [];
  const start = Math.ceil(minVal / step) * step;
  for (let t = start; t <= maxVal + 1e-6; t += step) out.push(Math.round(t * 1000) / 1000);
  return out;
}}

// 1-2-5-per-decade ticks (1, 2, 5, 10, 20, 50, 100, ...) -- the standard
// spacing for a log axis, used when a value's real range spans multiple
// orders of magnitude (e.g. MLB salary: a ~$400K league-minimum player and
// a $70M+ star on the same axis). A linear axis in that case spends nearly
// all its pixels on the handful of high earners and crushes everyone else
// into the first few percent of the width -- confirmed against a live
// 676-player run, where that crushing (not point count on its own) was the
// real source of the "still cluttered" complaint after per-point labels
// were already removed for dense charts.
function logTicksFor(minVal, maxVal) {{
  const startExp = Math.floor(Math.log10(minVal));
  const endExp = Math.ceil(Math.log10(maxVal));
  const out = [];
  for (let exp = startExp; exp <= endExp; exp++) {{
    for (const m of [1, 2, 5]) {{
      const v = m * Math.pow(10, exp);
      if (v >= minVal * 0.999 && v <= maxVal * 1.001) out.push(Math.round(v * 1000) / 1000);
    }}
  }}
  return out;
}}
const tooltip = document.getElementById("tooltip");

function showTooltip(html, event) {{
  tooltip.innerHTML = html;
  tooltip.style.opacity = 1;
  moveTooltip(event);
}}
function moveTooltip(event) {{
  tooltip.style.left = (event.pageX + 14) + "px";
  tooltip.style.top = (event.pageY - 10) + "px";
}}
function hideTooltip() {{ tooltip.style.opacity = 0; }}

function drawDivergingBar(container, cfg) {{
  // Stable per-point id so a click can be traced back to the same bar
  // across re-renders, independent of the value-sort order below.
  cfg.data.forEach((d, i) => {{ if (d.__cid === undefined) d.__cid = i; }});
  let activeCid = null; // null = show the curated default highlight

  function renderOnce() {{
    container.innerHTML = "";
    // Reader-driven highlight swap: clicking a bar makes IT the sole
    // highlighted/annotated bar and mutes every other bar, exactly like the
    // curated default -- just reader-picked instead of author-picked. This
    // keeps the Design Guidelines' "exactly one emphasized point" rule true
    // at all times; it never adds a second color, it only reassigns the one
    // that already exists.
    const effective = activeCid === null ? cfg.data
      : cfg.data.map(d => ({{...d, highlight: d.__cid === activeCid}}));
    // Descending -- row 0 (top of the chart) is the highest value. Every
    // caller of this chart (Surplus Value, MVP Tracker, Compare Teammates)
    // treats "first row" as "top-ranked," so the chart itself needs to
    // render that way rather than each caller working around an ascending
    // sort with y-axis flips or reversed data.
    const data = [...effective].sort((a, b) => b.value - a.value);
    const longestLabel = Math.max(...data.map(d => d.label.length));
    const margin = {{top: 8, right: 30, bottom: 34, left: Math.max(90, longestLabel * 6.5 + 12)}};
    const width = 820 - margin.left - margin.right;
    const rowH = 26;
    const height = data.length * rowH;
    const svg = el("svg", {{width: width + margin.left + margin.right, height: height + margin.top + margin.bottom}});
    const g = el("g", {{transform: `translate(${{margin.left}},${{margin.top}})`}});
    svg.appendChild(g);
    container.appendChild(svg);

    // oneSided: for data that's never negative (e.g. goals scored), skip the
    // diverging -max..max axis -- showing unused negative ticks for a value
    // that literally can't go negative is exactly the chartjunk the Design
    // Guidelines doc calls out. Scale 0..max and start bars at the left edge
    // instead of a center zero line.
    const oneSided = cfg.oneSided && data.every(d => d.value >= 0);
    const maxAbs = Math.max(...data.map(d => Math.abs(d.value))) * 1.15 || 1;
    const x = oneSided ? (v => (v / maxAbs) * width) : (v => (v / maxAbs) * (width / 2) + width / 2);
    const zeroX = x(0);

    ticksFor(oneSided ? 0 : -maxAbs, maxAbs, oneSided ? 5 : 6).forEach(t => {{
      g.appendChild(el("line", {{class: "gridline", x1: x(t), x2: x(t), y1: -4, y2: height + 4}}));
      const label = el("text", {{class: "axis-label", x: x(t), y: height + 20, "text-anchor": "middle"}});
      label.textContent = t;
      g.appendChild(label);
    }});
    if (!oneSided) {{
      g.appendChild(el("line", {{x1: zeroX, x2: zeroX, y1: -4, y2: height + 4, stroke: "var(--baseline)", "stroke-width": 1}}));
    }}

    const hasHighlight = data.some(d => d.highlight);

    data.forEach((d, i) => {{
      const y = i * rowH + 4;
      const barW = Math.abs(x(d.value) - zeroX);
      const barX = d.value < 0 ? x(d.value) : zeroX;
      const isMuted = hasHighlight && !d.highlight;
      const rect = el("rect", {{
        class: "bar" + (isMuted ? " muted" : (d.value < 0 ? " negative" : "")),
        x: barX, y: y, width: Math.max(barW, 1), height: rowH - 8, rx: 3,
      }});
      rect.addEventListener("mouseenter", (event) => showTooltip(
        `<div class="name">${{d.label}}</div><div class="row">${{cfg.valueLabel}}: ${{d.value.toFixed(2)}}</div>${{d.extra ? `<div class="row">${{d.extra}}</div>` : ""}}`, event));
      rect.addEventListener("mousemove", moveTooltip);
      rect.addEventListener("mouseleave", hideTooltip);
      rect.addEventListener("click", () => {{
        activeCid = (activeCid === d.__cid) ? null : d.__cid;
        renderOnce();
      }});
      g.appendChild(rect);

      const label = el("text", {{class: "bar-label" + (isMuted ? " muted" : ""), x: -8, y: y + (rowH - 8) / 2 + 4, "text-anchor": "end"}});
      label.textContent = d.label;
      g.appendChild(label);

      if (d.highlight) {{
        const sign = (!oneSided && d.value >= 0) ? "+" : "";
        const annoX = x(d.value) + (d.value < 0 ? -8 : 8);
        const anno = el("text", {{
          class: "annotation", x: annoX, y: y + (rowH - 8) / 2 + 4,
          "text-anchor": d.value < 0 ? "end" : "start",
        }});
        anno.textContent = sign + d.value.toFixed(1) + (cfg.annotationSuffix || "");
        g.appendChild(anno);
      }}
    }});

    const xLabel = el("text", {{class: "axis-label", x: width / 2, y: height + 34, "text-anchor": "middle"}});
    xLabel.textContent = cfg.xAxisLabel || "";
    g.appendChild(xLabel);

    // Clicking anywhere on the chart that isn't a bar (empty axis/gridline
    // area) reverts to the curated default highlight.
    svg.addEventListener("click", (event) => {{
      if (event.target === svg && activeCid !== null) {{ activeCid = null; renderOnce(); }}
    }});
  }}

  renderOnce();
}}

function resolveCollisions(points, r, padding) {{
  const minDist = r * 2 + padding;
  for (let iter = 0; iter < 300; iter++) {{
    let moved = false;
    for (let i = 0; i < points.length; i++) {{
      for (let j = i + 1; j < points.length; j++) {{
        const a = points[i], b = points[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 0.01) {{ dx = (Math.random() - 0.5); dy = (Math.random() - 0.5); dist = 0.01; }}
        if (dist < minDist) {{
          const push = (minDist - dist) / 2;
          const ux = dx / dist, uy = dy / dist;
          a.x -= ux * push; a.y -= uy * push;
          b.x += ux * push; b.y += uy * push;
          moved = true;
        }}
      }}
    }}
    if (!moved) break;
  }}
  return points;
}}

function drawScatter(container, cfg) {{
  // Stable per-point id so a click can be traced back to the same bubble
  // across re-renders (collision-avoidance nudges positions slightly
  // differently once highlight/mute states change, so identity has to
  // travel via an id, not screen position).
  cfg.data.forEach((d, i) => {{ if (d.__cid === undefined) d.__cid = i; }});
  let activeCid = null; // null = show the curated default highlight
  let selectedTeam = "ALL";

  // Team picker -- only for charts whose points carry a `team` (i.e. a
  // player-level scatter like League Picture, not a team-level one like
  // Team Spending vs. Production, where each point already IS one team).
  // Picking a team highlights every one of that team's players against the
  // full-league backdrop, same highlight/mute convention used everywhere
  // else, rather than filtering the rest out entirely -- the point of this
  // chart is seeing a team's roster *relative to the whole league*, which a
  // filtered-down view would throw away.
  const hasTeams = cfg.data.some(d => d.team);
  let chartMount = container;
  if (hasTeams) {{
    const pickerRow = document.createElement("div");
    pickerRow.className = "picker-row";
    const teamGroup = document.createElement("div");
    teamGroup.className = "picker-group";
    const teamLabel = document.createElement("div");
    teamLabel.className = "picker-label";
    teamLabel.textContent = "Team";
    const teamSelect = document.createElement("select");
    const allOpt = el2("option", {{value: "ALL"}});
    allOpt.textContent = "All teams";
    teamSelect.appendChild(allOpt);
    [...new Set(cfg.data.map(d => d.team))].sort((a, b) => {{
      const nameA = (cfg.teamNames && cfg.teamNames[a]) || a;
      const nameB = (cfg.teamNames && cfg.teamNames[b]) || b;
      return nameA.localeCompare(nameB);
    }}).forEach(abbr => {{
      const opt = el2("option", {{value: abbr}});
      opt.textContent = (cfg.teamNames && cfg.teamNames[abbr]) ? cfg.teamNames[abbr] : abbr;
      teamSelect.appendChild(opt);
    }});
    teamGroup.appendChild(teamLabel);
    teamGroup.appendChild(teamSelect);
    pickerRow.appendChild(teamGroup);
    container.appendChild(pickerRow);

    chartMount = document.createElement("div");
    container.appendChild(chartMount);

    const caption = document.createElement("p");
    caption.className = "compare-caption team-blurb";
    container.appendChild(caption);

    teamSelect.addEventListener("change", () => {{
      selectedTeam = teamSelect.value;
      activeCid = null; // a team pick supersedes a single clicked point
      renderOnce();
      if (selectedTeam === "ALL") {{
        caption.textContent = "";
      }} else if (cfg.teamBlurbs && cfg.teamBlurbs[selectedTeam]) {{
        // Pre-computed on the Python side (build_team_blurbs) -- combined
        // WAR/salary/surplus for the team's tracked players, not re-derived
        // here, so this stays consistent with every other insight sentence
        // in the dashboard.
        caption.textContent = cfg.teamBlurbs[selectedTeam];
      }} else {{
        const n = cfg.data.filter(d => d.team === selectedTeam).length;
        const teamFull = (cfg.teamNames && cfg.teamNames[selectedTeam]) || selectedTeam;
        const possessive = teamFull.endsWith("s") ? teamFull + "'" : teamFull + "'s";
        caption.textContent = `Highlighting ${{possessive}} ${{n}} tracked player${{n === 1 ? "" : "s"}} against the full sample.`;
      }}
    }});
  }}

  function renderOnce() {{
    chartMount.innerHTML = "";
    // Reader-driven highlight swap -- see drawDivergingBar for the same
    // pattern. Clicking a bubble makes it the sole highlighted bubble;
    // every other bubble mutes to gray, same as the curated default. If the
    // clicked point isn't the curated story point it simply has no
    // `annotation` text to show (that guard already exists below) -- the
    // color swap plus the existing hover tooltip is enough detail, and it
    // avoids inventing a new sentence for an arbitrary point. A team pick
    // from the dropdown above (if any) takes precedence over both.
    let data;
    if (selectedTeam !== "ALL") {{
      data = cfg.data.map(d => ({{...d, highlight: d.team === selectedTeam}}));
    }} else if (activeCid === null) {{
      data = cfg.data;
    }} else {{
      data = cfg.data.map(d => ({{...d, highlight: d.__cid === activeCid}}));
    }}

    const margin = {{top: 12, right: 24, bottom: 46, left: 58}};
    const width = 780 - margin.left - margin.right;
    const height = (cfg.height || 520) - margin.top - margin.bottom;
    const R = cfg.radius || 16;

    const svg = el("svg", {{width: width + margin.left + margin.right, height: height + margin.top + margin.bottom}});
    const g = el("g", {{transform: `translate(${{margin.left}},${{margin.top}})`}});
    svg.appendChild(g);
    chartMount.appendChild(svg);

    const xMax = Math.max(...data.map(d => d.x)) * 1.15;
    // yMin stays 0 unless the data actually goes negative (e.g. below-
    // replacement WAR) -- then it extends down with the same 1.15 buffer
    // used everywhere else, so those points get a real position on the
    // chart instead of landing below the plotted area. Below-zero WAR is
    // real (see build_dashboard.py -- it's no longer filtered out by
    // default) and is exactly the data the Surplus Value tab's "biggest
    // overpay" side depends on, so this chart needs to be able to show it.
    const yMinRaw = Math.min(0, ...data.map(d => d.y));
    const yMin = yMinRaw < 0 ? yMinRaw * 1.15 : 0;
    const yMax = Math.max(...data.map(d => d.y)) * 1.15;
    const yRange = yMax - yMin;

    // Log x-axis (cfg.xScaleType === "log"): for a value like MLB salary
    // that spans ~2 orders of magnitude (a ~$0.4M league-minimum player to
    // a $70M+ star), a linear axis spends nearly all its width on the
    // handful of high earners and crushes the rest into the first few
    // percent of the chart -- confirmed against a live 676-player run,
    // where that (not raw point count, already handled by DENSE_THRESHOLD
    // below) was the real source of remaining clutter. Only opt a chart
    // into this when its x-value is guaranteed positive across its whole
    // range -- log(0) and negative values have no position on this scale.
    const xLog = cfg.xScaleType === "log";
    let xScale, xTicks;
    if (xLog) {{
      const xMinData = Math.max(0.01, Math.min(...data.map(d => d.x)));
      const logMin = Math.log10(xMinData), logMax = Math.log10(xMax);
      xScale = v => ((Math.log10(Math.max(v, xMinData)) - logMin) / (logMax - logMin)) * width;
      xTicks = logTicksFor(xMinData, xMax);
    }} else {{
      xScale = v => (v / xMax) * width;
      xTicks = ticksFor(0, xMax, 8);
    }}
    // invertY: plot higher values lower on screen (useful when "lower is better",
    // e.g. xG Against, so "up" reads as "good" on both axes at once)
    const yScale = cfg.invertY
      ? (v => ((v - yMin) / yRange) * height)
      : (v => height - ((v - yMin) / yRange) * height);

    xTicks.forEach(t => g.appendChild(el("line", {{class: "gridline", x1: xScale(t), x2: xScale(t), y1: 0, y2: height}})));
    ticksFor(yMin, yMax, 8).forEach(t => g.appendChild(el("line", {{class: "gridline", x1: 0, x2: width, y1: yScale(t), y2: yScale(t)}})));

    const xAxis = el("g", {{class: "axis", transform: `translate(0,${{height}})`}});
    xTicks.forEach(t => {{
      const txt = el("text", {{x: xScale(t), y: 18, "text-anchor": "middle"}}); txt.textContent = t; xAxis.appendChild(txt);
    }});
    xAxis.appendChild(el("line", {{x1: 0, x2: width, y1: 0, y2: 0}}));
    g.appendChild(xAxis);

    const yAxis = el("g", {{class: "axis"}});
    ticksFor(yMin, yMax, 8).forEach(t => {{
      const txt = el("text", {{x: -10, y: yScale(t) + 4, "text-anchor": "end"}}); txt.textContent = t; yAxis.appendChild(txt);
    }});
    yAxis.appendChild(el("line", {{x1: 0, x2: 0, y1: 0, y2: height}}));
    g.appendChild(yAxis);

    const xLabel = el("text", {{class: "axis-label", x: width / 2, y: height + 38, "text-anchor": "middle"}}); xLabel.textContent = cfg.xAxisLabel; g.appendChild(xLabel);
    const yLabel = el("text", {{class: "axis-label", transform: "rotate(-90)", x: -height / 2, y: -40, "text-anchor": "middle"}}); yLabel.textContent = cfg.yAxisLabel; g.appendChild(yLabel);

    if (cfg.refLine) {{
      const lim = Math.min(xMax, yMax);
      g.appendChild(el("line", {{class: "refline", x1: xScale(0), y1: yScale(0), x2: xScale(lim), y2: yScale(lim)}}));
    }}
    if (yMin < 0) {{
      // A solid zero-WAR baseline, distinct from the dashed median lines --
      // "replacement level" is a meaningful reference point in its own
      // right (a below-replacement player is a specific, named bad
      // outcome), not just wherever the sample's middle happens to fall.
      g.appendChild(el("line", {{class: "zero-line", x1: 0, x2: width, y1: yScale(0), y2: yScale(0)}}));
    }}
    if (cfg.medianLines) {{
      const medX = data.map(d => d.x).sort((a,b) => a-b)[Math.floor(data.length / 2)];
      const medY = data.map(d => d.y).sort((a,b) => a-b)[Math.floor(data.length / 2)];
      g.appendChild(el("line", {{class: "refline", x1: xScale(medX), x2: xScale(medX), y1: 0, y2: height}}));
      g.appendChild(el("line", {{class: "refline", x1: 0, x2: width, y1: yScale(medY), y2: yScale(medY)}}));
    }}

    // true data positions, then (for a small-enough point count) nudge apart
    // only enough to stop overlap. Past a point, per-point text labels can't
    // work no matter how good the nudging is -- a few hundred 3-letter
    // badges each need ~20px of clear horizontal room, which a ~700px-wide
    // chart simply doesn't have, and forcing it just pushes labels into the
    // margins and past the axes (confirmed against a live 676-player run:
    // the result read as "points falling off the chart", when what had
    // actually happened was label text spilling outside the plot area).
    // Past DENSE_THRESHOLD points, skip per-point badges/collision-nudging
    // entirely -- small muted dots at their true positions (design
    // guidelines: "label selectively, never a number on every point"),
    // identity carried by the tooltip instead of a label.
    const DENSE_THRESHOLD = 60;
    const denseMode = data.length > DENSE_THRESHOLD;
    const points = data.map(d => ({{x: xScale(d.x), y: yScale(d.y), d}}));
    if (!denseMode) resolveCollisions(points, R, 3);

    const hasHighlight = data.some(d => d.highlight);

    // Draw order: muted points first, highlighted last -- so in a dense
    // cluster the one highlighted point never ends up buried under later-
    // drawn muted dots sharing roughly the same position (this is a stable
    // sort, so it only reorders relative to highlight status, nothing else).
    const drawOrder = [...points].sort((a, b) => (a.d.highlight ? 1 : 0) - (b.d.highlight ? 1 : 0));

    drawOrder.forEach(p => {{
      const d = p.d;
      const isMuted = hasHighlight && !d.highlight;
      const dx = p.x - xScale(d.x), dy = p.y - yScale(d.y);
      const displaced = Math.sqrt(dx * dx + dy * dy) > 3;
      const node = el("g", {{class: "player-node", transform: `translate(${{p.x}},${{p.y}})`}});
      if (displaced) {{
        // faint leader line back to the true data position when nudged for legibility
        node.appendChild(el("line", {{
          x1: 0, y1: 0, x2: xScale(d.x) - p.x, y2: yScale(d.y) - p.y,
          stroke: "var(--baseline)", "stroke-width": 1, "stroke-dasharray": "2 2",
        }}));
      }}
      // In dense mode the highlighted point gets a slightly bigger radius
      // too -- on top of drawing last (see drawOrder above), size is a
      // second, independent way for it to read as "the one point that
      // matters" against a few hundred same-sized muted dots.
      const denseHighlightBump = denseMode && d.highlight ? 3 : 0;
      const circle = el("circle", {{
        class: "bubble" + (isMuted ? " muted" : "") + (denseMode ? " dense" : ""),
        r: (denseMode ? Math.max(R, 4) : R) + denseHighlightBump,
      }});
      node.appendChild(circle);
      if (!denseMode) {{
        const label = el("text", {{class: "badge-text" + (isMuted ? " muted" : ""), dy: "0.32em", "text-anchor": "middle"}});
        label.textContent = d.badge;
        node.appendChild(label);
      }}

      if (d.highlight && d.annotation) {{
        // Prefer placing the annotation beside the bubble (right, or left if
        // there's no room to the right before the chart edge) -- but in a
        // dense cluster, that text can run straight through a neighboring
        // bubble. Check for that along the annotation's actual horizontal
        // band and fall back to stacking the text above the bubble instead,
        // which is reliably clear of horizontal neighbors.
        const estTextWidth = d.annotation.length * 6.4;
        const anchorRight = (p.x + R + 8 + estTextWidth) < width;
        const sideX = anchorRight ? p.x + R + 8 : p.x - R - 8;
        const sideEndX = anchorRight ? sideX + estTextWidth : sideX - estTextWidth;
        const bandLo = Math.min(sideX, sideEndX) - R, bandHi = Math.max(sideX, sideEndX) + R;
        const collides = points.some(other => other.d !== d
          && Math.abs(other.y - p.y) < R * 2
          && other.x > bandLo && other.x < bandHi);

        let annoX = anchorRight ? R + 8 : -(R + 8);
        let annoY = 4;
        let annoAnchor = anchorRight ? "start" : "end";
        if (collides) {{
          // Stack above the bubble instead -- but centering on the bubble can
          // run the text off the left/right edge of the chart when the bubble
          // itself sits near an edge, so clamp to the visible plot area.
          annoY = -(R + 10);
          const halfW = estTextWidth / 2;
          if (p.x - halfW < 4) {{ annoAnchor = "start"; annoX = 4 - p.x; }}
          else if (p.x + halfW > width - 4) {{ annoAnchor = "end"; annoX = (width - 4) - p.x; }}
          else {{ annoAnchor = "middle"; annoX = 0; }}
        }}
        const anno = el("text", {{class: "annotation", x: annoX, y: annoY, "text-anchor": annoAnchor}});
        anno.textContent = d.annotation;
        node.appendChild(anno);
      }}

      g.appendChild(node);

      node.addEventListener("mouseenter", (event) => {{
        circle.classList.add("hover");
        showTooltip(d.tooltip, event);
      }});
      node.addEventListener("mousemove", moveTooltip);
      node.addEventListener("mouseleave", () => {{ circle.classList.remove("hover"); hideTooltip(); }});
      node.addEventListener("click", () => {{
        if (selectedTeam !== "ALL") return; // the team dropdown owns highlighting while a team is picked
        activeCid = (activeCid === d.__cid) ? null : d.__cid;
        renderOnce();
      }});
    }});

    // Clicking empty chart area (not a bubble) reverts to the curated default.
    svg.addEventListener("click", (event) => {{
      if (selectedTeam !== "ALL") return;
      if (event.target === svg && activeCid !== null) {{ activeCid = null; renderOnce(); }}
    }});
  }}

  renderOnce();
}}

function drawTeamCompare(container, cfg) {{
  const pickerRow = document.createElement("div");
  pickerRow.className = "picker-row";

  const teamGroup = document.createElement("div");
  teamGroup.className = "picker-group";
  const teamLabel = document.createElement("div");
  teamLabel.className = "picker-label";
  teamLabel.textContent = "Team";
  const teamSelect = document.createElement("select");
  Object.keys(cfg.rosters).sort((a, b) => {{
    const nameA = (cfg.teamNames && cfg.teamNames[a]) || a;
    const nameB = (cfg.teamNames && cfg.teamNames[b]) || b;
    return nameA.localeCompare(nameB);
  }}).forEach(abbr => {{
    const opt = el2("option", {{value: abbr}});
    opt.textContent = (cfg.teamNames && cfg.teamNames[abbr]) ? cfg.teamNames[abbr] : abbr;
    teamSelect.appendChild(opt);
  }});
  teamGroup.appendChild(teamLabel);
  teamGroup.appendChild(teamSelect);

  const statGroup = document.createElement("div");
  statGroup.className = "picker-group";
  const statLabel = document.createElement("div");
  statLabel.className = "picker-label";
  statLabel.textContent = "Metric";
  const statSelect = document.createElement("select");
  cfg.stats.forEach(s => {{
    const opt = el2("option", {{value: s.key}});
    opt.textContent = s.label;
    statSelect.appendChild(opt);
  }});
  statGroup.appendChild(statLabel);
  statGroup.appendChild(statSelect);

  pickerRow.appendChild(teamGroup);
  pickerRow.appendChild(statGroup);
  container.appendChild(pickerRow);

  const chartMount = document.createElement("div");
  container.appendChild(chartMount);

  // Team blurb (pre-computed Python-side, build_team_blurbs) sits above the
  // stat-specific leader line -- one is "what does the data say about this
  // team overall" (fixed per team), the other is "who's on top of the
  // metric you just picked" (changes with the Metric dropdown too).
  const teamBlurbEl = document.createElement("p");
  teamBlurbEl.className = "compare-caption team-blurb";
  container.appendChild(teamBlurbEl);

  const caption = document.createElement("p");
  caption.className = "compare-caption";
  container.appendChild(caption);

  function render() {{
    chartMount.innerHTML = "";
    const teamAbbr = teamSelect.value;
    const statKey = statSelect.value;
    const statCfg = cfg.stats.find(s => s.key === statKey);
    const players = cfg.rosters[teamAbbr] || [];
    teamBlurbEl.textContent = (cfg.teamBlurbs && cfg.teamBlurbs[teamAbbr]) || "";
    if (players.length === 0) {{ caption.textContent = "No roster data for this team."; return; }}
    const sorted = [...players].sort((a, b) => b[statKey] - a[statKey]);
    const top = sorted[0];

    const barData = sorted.map(p => ({{
      label: p.name,
      value: p[statKey],
      highlight: p.name === top.name,
    }}));

    drawDivergingBar(chartMount, {{
      data: barData,
      valueLabel: statCfg.label,
      xAxisLabel: statCfg.label,
      annotationSuffix: statCfg.suffix || "",
    }});

    const teamFull = (cfg.teamNames && cfg.teamNames[teamAbbr]) ? cfg.teamNames[teamAbbr] : teamAbbr;
    caption.textContent = `${{teamFull}}: ${{top.name}} leads the roster in ${{statCfg.label}} (${{top[statKey].toFixed(2)}}${{statCfg.suffix || ""}}).`;
  }}

  teamSelect.addEventListener("change", render);
  statSelect.addEventListener("change", render);
  render();
}}
function el2(tag, attrs) {{
  const e = document.createElement(tag);
  for (const k in (attrs || {{}})) e.setAttribute(k, attrs[k]);
  return e;
}}

function drawMvpTracker(container, cfg) {{
  // Same picker-row + drawDivergingBar pattern as drawTeamCompare above,
  // just switching on league (AL/NL) instead of team -- one leaderboard
  // visible at a time rather than both leagues squeezed side by side,
  // which would force either tiny bar labels or a much taller page.
  const pickerRow = document.createElement("div");
  pickerRow.className = "picker-row";
  const leagueGroup = document.createElement("div");
  leagueGroup.className = "picker-group";
  const leagueLabel = document.createElement("div");
  leagueLabel.className = "picker-label";
  leagueLabel.textContent = "League";
  const leagueSelect = document.createElement("select");
  [["AL", "American League"], ["NL", "National League"]].forEach(([value, text]) => {{
    const opt = el2("option", {{value}});
    opt.textContent = text;
    leagueSelect.appendChild(opt);
  }});
  leagueSelect.value = cfg.defaultLeague || "AL";
  leagueGroup.appendChild(leagueLabel);
  leagueGroup.appendChild(leagueSelect);
  pickerRow.appendChild(leagueGroup);
  container.appendChild(pickerRow);

  const chartMount = document.createElement("div");
  container.appendChild(chartMount);

  const caption = document.createElement("p");
  caption.className = "compare-caption";
  container.appendChild(caption);

  function render() {{
    chartMount.innerHTML = "";
    const league = leagueSelect.value;
    const players = (cfg.leagues && cfg.leagues[league]) || [];
    if (players.length === 0) {{ caption.textContent = "No tracked players in this league."; return; }}
    const leader = players[0]; // Python side already sorts each league's list by WAR, descending

    const barData = players.map(p => {{
      const surplusSign = p.surplus_m >= 0 ? "+" : "";
      return {{
        label: `${{p.name}} (${{p.team}})`,
        value: p.war,
        highlight: p === leader,
        extra: `${{p.role}} &middot; Salary $${{p.salary_m.toFixed(1)}}M &middot; Surplus vs. market: ${{surplusSign}}${{p.surplus_m.toFixed(1)}}M`,
      }};
    }});

    drawDivergingBar(chartMount, {{
      data: barData, oneSided: true,
      valueLabel: "WAR", xAxisLabel: "WAR",
    }});

    const leagueFull = league === "AL" ? "American League" : "National League";
    caption.textContent = `${{leader.name}} (${{leader.team}}) leads the ${{leagueFull}} at ${{leader.war.toFixed(1)}} WAR.`;
  }}

  leagueSelect.addEventListener("change", render);
  render();
}}

function drawLine(container, cfg) {{
  // Single-series line chart -- e.g. a league-wide total plotted one point
  // per season. One highlighted point (per the highlight/mute convention
  // used everywhere else in this dashboard) gets a static annotation; every
  // other point is a plain series-color dot with no callout.
  const margin = {{top: 16, right: 28, bottom: 40, left: 50}};
  const width = 780 - margin.left - margin.right;
  const height = (cfg.height || 340) - margin.top - margin.bottom;

  const svg = el("svg", {{width: width + margin.left + margin.right, height: height + margin.top + margin.bottom}});
  const g = el("g", {{transform: `translate(${{margin.left}},${{margin.top}})`}});
  svg.appendChild(g);
  container.appendChild(svg);

  const xs = cfg.data.map(d => d.x);
  const ys = cfg.data.map(d => d.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMax = Math.max(...ys) * 1.15 || 1;
  const xScale = v => ((v - xMin) / (xMax - xMin || 1)) * width;
  const yScale = v => height - (v / yMax) * height;

  ticksFor(0, yMax, 5).forEach(t => {{
    g.appendChild(el("line", {{class: "gridline", x1: 0, x2: width, y1: yScale(t), y2: yScale(t)}}));
    const label = el("text", {{class: "axis-label", x: -10, y: yScale(t) + 4, "text-anchor": "end"}});
    label.textContent = t;
    g.appendChild(label);
  }});

  const xAxis = el("g", {{class: "axis", transform: `translate(0,${{height}})`}});
  cfg.data.forEach(d => {{
    const txt = el("text", {{x: xScale(d.x), y: 18, "text-anchor": "middle"}});
    txt.textContent = d.xLabel !== undefined ? d.xLabel : d.x;
    xAxis.appendChild(txt);
  }});
  xAxis.appendChild(el("line", {{x1: 0, x2: width, y1: 0, y2: 0}}));
  g.appendChild(xAxis);

  const pathD = cfg.data.map((d, i) => `${{i === 0 ? "M" : "L"}}${{xScale(d.x)}},${{yScale(d.y)}}`).join(" ");
  g.appendChild(el("path", {{class: "line-path", d: pathD}}));

  cfg.data.forEach(d => {{
    const cx = xScale(d.x), cy = yScale(d.y);
    const dot = el("circle", {{class: "line-dot", cx: cx, cy: cy, r: d.highlight ? 6 : 4.5}});
    dot.addEventListener("mouseenter", (event) => showTooltip(d.tooltip || `<div class="row">${{d.y}}</div>`, event));
    dot.addEventListener("mousemove", moveTooltip);
    dot.addEventListener("mouseleave", hideTooltip);
    g.appendChild(dot);

    if (d.highlight && d.annotation) {{
      const above = cy > 24;
      const anno = el("text", {{
        class: "annotation", x: cx, y: above ? cy - 14 : cy + 22, "text-anchor": "middle",
      }});
      anno.textContent = d.annotation;
      g.appendChild(anno);
    }}
  }});

  const xLabel = el("text", {{class: "axis-label", x: width / 2, y: height + 34, "text-anchor": "middle"}});
  xLabel.textContent = cfg.xAxisLabel || "";
  g.appendChild(xLabel);
  const yLabel = el("text", {{class: "axis-label", transform: "rotate(-90)", x: -height / 2, y: -34, "text-anchor": "middle"}});
  yLabel.textContent = cfg.yAxisLabel || "";
  g.appendChild(yLabel);
}}

function drawSeasonCompare(container, cfg) {{
  // Same dropdown-driven pattern as drawTeamCompare, but the picker
  // selects a SEASON instead of a team, and the bar chart shows every
  // team's value for that season.
  const pickerRow = document.createElement("div");
  pickerRow.className = "picker-row";

  const seasonGroup = document.createElement("div");
  seasonGroup.className = "picker-group";
  const seasonLabel = document.createElement("div");
  seasonLabel.className = "picker-label";
  seasonLabel.textContent = "Season";
  const seasonSelect = document.createElement("select");
  cfg.seasons.forEach(s => {{
    const opt = el2("option", {{value: s}});
    opt.textContent = s;
    seasonSelect.appendChild(opt);
  }});
  seasonSelect.value = cfg.seasons[cfg.seasons.length - 1];
  seasonGroup.appendChild(seasonLabel);
  seasonGroup.appendChild(seasonSelect);
  pickerRow.appendChild(seasonGroup);
  container.appendChild(pickerRow);

  const chartMount = document.createElement("div");
  container.appendChild(chartMount);
  const caption = document.createElement("p");
  caption.className = "compare-caption";
  container.appendChild(caption);

  function render() {{
    chartMount.innerHTML = "";
    const season = seasonSelect.value;
    const rows = cfg.bySeason[season] || [];
    if (rows.length === 0) {{ caption.textContent = "No data for this season."; return; }}
    const sorted = [...rows].sort((a, b) => b.value - a.value);
    const top = sorted[0];
    drawDivergingBar(chartMount, {{
      data: rows.map(r => ({{label: r.label, value: r.value, highlight: r.label === top.label}})),
      valueLabel: cfg.valueLabel, xAxisLabel: cfg.valueLabel, oneSided: true,
    }});
    caption.textContent = `${{season}}: ${{top.label}} led the league with ${{top.value}} ${{cfg.valueLabel.toLowerCase()}}.`;
  }}

  seasonSelect.addEventListener("change", render);
  render();
}}

function drawShotMap(container, cfg) {{
  // Pitch diagram in StatsBomb's coordinate system (0-120 long, 0-80
  // wide), shots normalized to attack rightward so they cluster near the
  // right-hand goal regardless of which literal end they were taken at.
  // Filled dot = goal, hollow dot = anything else; dot radius scales with
  // xG, so a glance at size alone tells you how "clean" a chance was.
  const margin = {{top: 10, right: 16, bottom: 16, left: 16}};
  const width = 720;
  const height = width * (80 / 120);
  const svg = el("svg", {{width: width + margin.left + margin.right, height: height + margin.top + margin.bottom}});
  const g = el("g", {{transform: `translate(${{margin.left}},${{margin.top}})`}});
  svg.appendChild(g);
  container.appendChild(svg);

  const xScale = v => (v / 120) * width;
  const yScale = v => (v / 80) * height;

  // pitch outline + key markings (attacking half is what matters here, but
  // draw the full pitch for context/orientation)
  g.appendChild(el("rect", {{class: "pitch-outline", x: 0, y: 0, width: width, height: height, rx: 2}}));
  g.appendChild(el("line", {{class: "pitch-line", x1: xScale(60), x2: xScale(60), y1: 0, y2: height}}));
  g.appendChild(el("circle", {{class: "pitch-line", cx: xScale(60), cy: yScale(40), r: xScale(10) - xScale(0)}}));
  // 18-yard box + 6-yard box + goal, right-hand (attacking) end only
  g.appendChild(el("rect", {{class: "pitch-line", x: xScale(102), y: yScale(18), width: xScale(18) - xScale(0), height: yScale(62) - yScale(18)}}));
  g.appendChild(el("rect", {{class: "pitch-line", x: xScale(114), y: yScale(30), width: xScale(6) - xScale(0), height: yScale(50) - yScale(30)}}));
  g.appendChild(el("line", {{class: "pitch-outline", x1: width, x2: width, y1: yScale(36), y2: yScale(44), stroke: "var(--series-1)", "stroke-width": 3}}));

  const hasHighlight = cfg.data.some(d => d.highlight);
  const maxXg = Math.max(...cfg.data.map(d => d.xg)) || 0.1;

  cfg.data.forEach(d => {{
    // normalize direction: shots taken in the defensive half are mirrored
    // so every shot renders as if attacking the same (right-hand) goal
    const flip = d.x < 60;
    const px = flip ? 120 - d.x : d.x;
    const py = flip ? 80 - d.y : d.y;
    const isMuted = hasHighlight && !d.highlight;
    const r = 4 + Math.sqrt(d.xg / maxXg) * 11;
    const dot = el("circle", {{
      class: "shot-dot " + (d.outcome === "Goal" ? "goal" : "no-goal") + (isMuted ? " muted" : ""),
      cx: xScale(px), cy: yScale(py), r: r,
    }});
    dot.addEventListener("mouseenter", (event) => showTooltip(d.tooltip, event));
    dot.addEventListener("mousemove", moveTooltip);
    dot.addEventListener("mouseleave", hideTooltip);
    g.appendChild(dot);

    if (d.highlight && d.annotation) {{
      const anchorRight = xScale(px) < width - 160;
      const anno = el("text", {{
        class: "annotation", x: xScale(px) + (anchorRight ? r + 8 : -(r + 8)), y: yScale(py) + 4,
        "text-anchor": anchorRight ? "start" : "end",
      }});
      anno.textContent = d.annotation;
      g.appendChild(anno);
    }}
  }});

  const legend = document.createElement("div");
  legend.className = "legend";
  legend.innerHTML = `
    <div class="legend-item"><span class="legend-swatch" style="background:var(--series-1);"></span>Goal</div>
    <div class="legend-item"><span class="legend-swatch" style="background:var(--surface-1); border:1.5px solid var(--series-1);"></span>No goal</div>
    <div class="legend-item">Dot size = xG</div>
  `;
  container.insertBefore(legend, svg);
}}

// ---------- build tabs + panels ----------
const tabsEl = document.getElementById("tabs");
const panelsEl = document.getElementById("panels");

CHARTS.forEach((chart, i) => {{
  const btn = document.createElement("button");
  btn.className = "tab-btn" + (i === 0 ? " active" : "");
  btn.textContent = chart.tabLabel;
  btn.addEventListener("click", () => {{
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-" + i).classList.add("active");
  }});
  tabsEl.appendChild(btn);

  const panel = document.createElement("div");
  panel.className = "panel" + (i === 0 ? " active" : "");
  panel.id = "panel-" + i;
  panel.innerHTML = `<p class="kicker">${{chart.metricLabel || chart.tabLabel}}</p><h2>${{chart.title}}</h2><p class="blurb">${{chart.blurb}}</p><div class="chart-mount"></div><p class="footnote">${{chart.footnote || ""}}</p>`;
  panelsEl.appendChild(panel);

  const mount = panel.querySelector(".chart-mount");
  if (chart.type === "diverging-bar") drawDivergingBar(mount, chart);
  if (chart.type === "scatter") drawScatter(mount, chart);
  if (chart.type === "team-compare") drawTeamCompare(mount, chart);
  if (chart.type === "mvp-tracker") drawMvpTracker(mount, chart);
  if (chart.type === "line") drawLine(mount, chart);
  if (chart.type === "season-compare") drawSeasonCompare(mount, chart);
  if (chart.type === "shot-map") drawShotMap(mount, chart);
}});
</script>
</body>
</html>
"""


def render_dashboard(title, subtitle, charts, story=None, story_kicker="This week's value picture"):
    """charts: list of dicts matching the JS CHARTS shape. tooltip fields
    must be pre-rendered HTML strings per point (see build helpers below).
    story: optional short dashboard-level narrative (see
    chart_builders.build_story_lede) rendered as a highlighted block between
    the header and the tab bar -- the same insight-led storytelling
    convention used on every chart, just applied once for the whole page.
    Omitted entirely (no empty block left behind) if None/empty."""
    if story:
        story_block = (
            '  <div class="story">\n'
            f'    <p class="kicker">{story_kicker}</p>\n'
            f'    <p class="story-lede">{story}</p>\n'
            '  </div>\n'
        )
    else:
        story_block = ""
    return PAGE_TEMPLATE.format(
        title=title, subtitle=subtitle, charts_json=json.dumps(charts), story_block=story_block,
    )
