"""ASO intelligence dashboard — clear, focused presentation."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ASO Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f7f5f1;
      --paper: #fffdf9;
      --ink: #1c1917;
      --muted: #78716c;
      --line: #e7e5e4;
      --accent: #0f766e;
      --accent-bg: #ecfdf8;
      --warn-bg: #fff7ed;
      --warn: #c2410c;
      --good: #166534;
      --danger: #b91c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Source Sans 3", system-ui, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.5;
    }
    h1, h2, h3 {
      font-family: Fraunces, Georgia, serif;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.2;
      margin: 0;
    }
    .wrap {
      max-width: 880px;
      margin: 0 auto;
      padding: 28px 20px 64px;
    }
    .top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 28px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }
    .top p {
      margin: 8px 0 0;
      color: var(--muted);
      max-width: 42ch;
    }
    .actions { display: flex; gap: 8px; flex-shrink: 0; }
    button {
      border: 0;
      border-radius: 8px;
      padding: 10px 14px;
      font: 600 14px "Source Sans 3", sans-serif;
      cursor: pointer;
      background: var(--accent);
      color: #fff;
    }
    button.ghost {
      background: transparent;
      color: var(--ink);
      border: 1px solid var(--line);
    }
    button:disabled { opacity: 0.55; cursor: wait; }
    .status {
      min-height: 1.4em;
      margin: 0 0 18px;
      font-size: 14px;
      color: var(--muted);
    }
    .status.ok { color: var(--good); }
    .status.err { color: var(--danger); }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 22px;
    }
    .stat {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
    }
    .stat label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .stat b {
      font-family: Fraunces, Georgia, serif;
      font-size: 24px;
    }
    nav.views {
      display: flex;
      gap: 6px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }
    nav.views button {
      background: transparent;
      color: var(--muted);
      border: 1px solid transparent;
      padding: 8px 12px;
    }
    nav.views button.on {
      background: var(--paper);
      color: var(--ink);
      border-color: var(--line);
    }
    .view { display: none; }
    .view.on { display: block; }
    .section-title {
      font-size: 22px;
      margin-bottom: 6px;
    }
    .section-help {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 15px;
    }
    .list { display: grid; gap: 12px; }
    .item {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px 18px;
    }
    .item h3 {
      font-size: 18px;
      margin-bottom: 8px;
    }
    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 10px;
    }
    .tag {
      font-size: 12px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 999px;
      background: var(--accent-bg);
      color: var(--accent);
    }
    .tag.soft {
      background: #f5f5f4;
      color: var(--muted);
    }
    .tag.warm {
      background: var(--warn-bg);
      color: var(--warn);
    }
    .item p {
      margin: 0 0 8px;
      font-size: 15px;
    }
    .item p:last-child { margin-bottom: 0; }
    .item.clickable {
      cursor: pointer;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .item.clickable:hover {
      border-color: #99f6e4;
      box-shadow: 0 4px 14px rgba(15, 118, 110, 0.08);
    }
    .item .teaser {
      color: var(--muted);
      font-size: 15px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .item .open-link {
      margin-top: 10px;
      font-size: 13px;
      font-weight: 600;
      color: var(--accent);
    }
    .detail-panel {
      margin-top: 18px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 20px 22px;
    }
    .detail-panel .detail-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }
    .detail-panel .detail-head h3 {
      font-size: 24px;
      margin-bottom: 8px;
    }
    .detail-section {
      margin-bottom: 18px;
    }
    .detail-section:last-child { margin-bottom: 0; }
    .detail-section h4 {
      margin: 0 0 6px;
      font-family: Fraunces, Georgia, serif;
      font-size: 17px;
    }
    .detail-section p {
      margin: 0;
      font-size: 15px;
      white-space: pre-wrap;
      line-height: 1.6;
    }
    .detail-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      font-size: 13px;
      color: var(--muted);
    }
    .label {
      display: block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 2px;
    }
    .field { margin-bottom: 10px; }
    .field:last-child { margin-bottom: 0; }
    .quiet { color: var(--muted); font-size: 14px; }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 12px;
      padding: 28px;
      text-align: center;
      color: var(--muted);
      background: var(--paper);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }
    th, td {
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      background: #fafaf9;
    }
    tr:last-child td { border-bottom: 0; }
    .report-body {
      margin-top: 14px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
    }
    .report-body h3 {
      font-size: 16px;
      margin: 16px 0 8px;
    }
    .report-body h3:first-child { margin-top: 0; }
    .report-body p, .report-body li {
      font-size: 14px;
      color: var(--ink);
    }
    .report-body ul { padding-left: 18px; margin: 0 0 10px; }
    .banner {
      background: var(--accent-bg);
      border: 1px solid #99f6e4;
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 16px;
      font-size: 14px;
    }
    @media (max-width: 720px) {
      .top { flex-direction: column; align-items: stretch; }
      .stats { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>ASO Intelligence</h1>
        <p>Clear daily view of product ideas, market opportunities, and reports.
           Generate pulls keywords and competitors from your trending apps first.</p>
      </div>
      <div class="actions">
        <button id="runBtn" onclick="runDaily()">Generate today’s report</button>
        <button class="ghost" onclick="loadData()">Refresh</button>
      </div>
    </div>

    <p id="status" class="status">Loading…</p>
    <div id="banner"></div>

    <div class="stats" id="stats"></div>

    <nav class="views">
      <button class="on" data-view="ideas" onclick="showView('ideas')">Ideas</button>
      <button data-view="opportunities" onclick="showView('opportunities')">Opportunities</button>
      <button data-view="trends" onclick="showView('trends')">Trends</button>
      <button data-view="reports" onclick="showView('reports')">Reports</button>
    </nav>

    <section class="view on" id="view-ideas">
      <h2 class="section-title">Product ideas</h2>
      <p class="section-help">What to build next — click an idea for a plain-English product brief.</p>
      <div class="list" id="ideas"></div>
      <div id="ideaDetail"></div>
    </section>

    <section class="view" id="view-opportunities">
      <h2 class="section-title">Market opportunities</h2>
      <p class="section-help">Where demand and gaps look strongest right now.</p>
      <div class="list" id="opportunities"></div>
    </section>

    <section class="view" id="view-trends">
      <h2 class="section-title">Trending apps</h2>
      <p class="section-help">Recent chart movers from App Store and Google Play.</p>
      <div id="trends"></div>
      <h2 class="section-title" style="margin-top:28px">Keywords</h2>
      <p class="section-help">High-opportunity search terms.</p>
      <div id="keywords"></div>
    </section>

    <section class="view" id="view-reports">
      <h2 class="section-title">Reports</h2>
      <p class="section-help">Saved daily and weekly intelligence reports.</p>
      <div class="list" id="reports"></div>
      <div id="reportDetail"></div>
    </section>
  </div>

  <script>
    function $(id) { return document.getElementById(id); }
    function esc(v) {
      return String(v ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }
    function nice(v) {
      return String(v || "").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
    }
    function num(v) {
      if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
      return Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 });
    }
    function when(v) {
      if (!v) return "—";
      const d = new Date(v);
      return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString();
    }
    function setStatus(text, kind="") {
      const el = $("status");
      el.textContent = text;
      el.className = "status" + (kind ? " " + kind : "");
    }
    function showView(name) {
      document.querySelectorAll("nav.views button").forEach(b => b.classList.toggle("on", b.dataset.view === name));
      document.querySelectorAll(".view").forEach(v => v.classList.toggle("on", v.id === "view-" + name));
    }
    function empty(msg) {
      return `<div class="empty">${esc(msg)}</div>`;
    }
    function shortProblem(text) {
      if (!text) return "Market gap identified from store signals.";
      // Drop noisy score dumps like "(30 trend signals, 0 fast-growing)..."
      return String(text)
        .replace(/\([^)]*trend signals[^)]*\)/gi, "")
        .replace(/\s+/g, " ")
        .trim();
    }

    function renderStats(counts) {
      const items = [
        ["Ideas", counts.ideas],
        ["Opportunities", counts.opportunities],
        ["Trending apps", counts.trends],
        ["Reports", counts.reports],
      ];
      $("stats").innerHTML = items.map(([label, value]) => `
        <div class="stat"><label>${esc(label)}</label><b>${num(value)}</b></div>
      `).join("");
    }

    function renderIdeas(items) {
      if (!items?.length) {
        $("ideas").innerHTML = empty("No ideas yet. Click “Generate today’s report”.");
        $("ideaDetail").innerHTML = "";
        return;
      }
      $("ideas").innerHTML = items.map(item => `
        <article class="item clickable" onclick="openIdea(${item.id})" role="button" tabindex="0"
          onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openIdea(${item.id})}">
          <h3>${esc(item.title)}</h3>
          <div class="tags">
            <span class="tag">${esc(nice(item.idea_type))}</span>
            <span class="tag soft">Confidence ${num(item.confidence_score)}</span>
          </div>
          <p class="teaser">${esc(item.proposed_solution || shortProblem(item.problem_statement))}</p>
          <div class="open-link">View full idea details →</div>
        </article>
      `).join("");
    }

    function renderIdeaDetail(data) {
      const idea = data.idea || {};
      const sections = data.detail_sections || [];
      $("ideaDetail").innerHTML = `
        <div class="detail-panel">
          <div class="detail-head">
            <div>
              <h3>${esc(idea.title)}</h3>
              <div class="tags">
                <span class="tag">${esc(nice(idea.idea_type))}</span>
                <span class="tag soft">Confidence ${num(idea.confidence_score)}</span>
                ${idea.source_opportunity_id ? `<span class="tag warm">Opportunity #${esc(idea.source_opportunity_id)}</span>` : ""}
              </div>
            </div>
            <button class="ghost" onclick="closeIdeaDetail()">Close</button>
          </div>
          ${sections.map(section => `
            <div class="detail-section">
              <h4>${esc(section.title)}</h4>
              <p>${esc(section.body)}</p>
            </div>
          `).join("")}
          <div class="detail-meta">
            <span>Generated ${when(idea.generated_at)}</span>
            <span>Idea ID #${esc(idea.id)}</span>
          </div>
        </div>
      `;
      $("ideaDetail").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function closeIdeaDetail() {
      $("ideaDetail").innerHTML = "";
    }

    async function openIdea(id) {
      setStatus("Loading idea details…");
      try {
        const res = await fetch(`/api/dashboard/ideas/${id}`);
        const data = await res.json();
        if (!res.ok || data.error) throw new Error(data.error || "Could not load idea");
        renderIdeaDetail(data);
        showView("ideas");
        setStatus("Idea details ready.", "ok");
      } catch (err) {
        setStatus(String(err.message || err), "err");
      }
    }

    function renderOpportunities(items) {
      if (!items?.length) {
        $("opportunities").innerHTML = empty("No opportunities yet.");
        return;
      }
      $("opportunities").innerHTML = items.map(item => `
        <article class="item">
          <h3>${esc(item.title)}</h3>
          <div class="tags">
            <span class="tag">${esc(item.category || "General")}</span>
            <span class="tag warm">Score ${num(item.opportunity_score)}</span>
          </div>
          <p>${esc(shortProblem(item.description))}</p>
        </article>
      `).join("");
    }

    function renderTrends(data) {
      const trends = data.trends || [];
      $("trends").innerHTML = trends.length ? `
        <table>
          <thead><tr><th>App</th><th>Store</th><th>Chart</th><th>Rank</th></tr></thead>
          <tbody>
            ${trends.map(row => `
              <tr>
                <td>
                  <strong>${esc(row.name)}</strong>
                  <div class="quiet">${esc(row.category || "—")}</div>
                </td>
                <td>${esc(nice(row.platform))}</td>
                <td>${esc(nice(row.chart_type))}</td>
                <td>${num(row.rank)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : empty("No trending apps yet.");

      const keywords = data.keywords || [];
      $("keywords").innerHTML = keywords.length ? `
        <table>
          <thead><tr><th>Keyword</th><th>Store</th><th>Opportunity</th></tr></thead>
          <tbody>
            ${keywords.map(row => `
              <tr>
                <td><strong>${esc(row.term)}</strong></td>
                <td>${esc(nice(row.platform))}</td>
                <td>${num(row.opportunity_score)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : empty("No keywords yet.");
    }

    function markdownToHtml(md) {
      if (!md) return "<p class='quiet'>No report content.</p>";
      const lines = String(md).split(/\r?\n/);
      let html = "";
      let inList = false;
      const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };
      for (const raw of lines) {
        const line = raw.trimEnd();
        if (!line.trim()) { closeList(); continue; }
        if (line.startsWith("### ")) { closeList(); html += `<h3>${esc(line.slice(4))}</h3>`; continue; }
        if (line.startsWith("## ")) { closeList(); html += `<h3>${esc(line.slice(3))}</h3>`; continue; }
        if (line.startsWith("# ")) { closeList(); html += `<h3>${esc(line.slice(2))}</h3>`; continue; }
        if (line.startsWith("- ")) {
          if (!inList) { html += "<ul>"; inList = true; }
          html += `<li>${esc(line.slice(2).replace(/\*\*(.*?)\*\*/g, "$1"))}</li>`;
          continue;
        }
        closeList();
        html += `<p>${esc(line.replace(/\*\*(.*?)\*\*/g, "$1"))}</p>`;
      }
      closeList();
      return html;
    }

    function renderReports(items) {
      if (!items?.length) {
        $("reports").innerHTML = empty("No reports yet.");
        return;
      }
      $("reports").innerHTML = items.map(item => `
        <article class="item">
          <h3>${esc(item.title)}</h3>
          <div class="tags">
            <span class="tag">${esc(nice(item.report_type))}</span>
            <span class="tag soft">${esc(nice(item.report_format))}</span>
          </div>
          <p class="quiet">${esc((item.summary || "").split(".")[0] + ".")}</p>
          <p class="quiet">${when(item.generated_at)}</p>
          <button class="ghost" onclick="openReport(${item.id})">Read report</button>
        </article>
      `).join("");
    }

    async function openReport(id) {
      setStatus("Opening report…");
      try {
        const res = await fetch(`/api/dashboard/reports/${id}`);
        const data = await res.json();
        if (!res.ok || data.error) throw new Error(data.error || "Could not open report");
        $("reportDetail").innerHTML = `
          <div class="report-body">
            <h3>${esc(data.report.title)}</h3>
            ${markdownToHtml(data.content || data.report.summary || "")}
          </div>
        `;
        showView("reports");
        setStatus("Report ready.", "ok");
      } catch (err) {
        setStatus(String(err.message || err), "err");
      }
    }

    function renderAll(data) {
      renderStats(data.counts || {});
      renderIdeas(data.ideas || []);
      renderOpportunities(data.opportunities || []);
      renderTrends(data);
      renderReports(data.reports || []);
    }

    async function loadData() {
      setStatus("Refreshing…");
      try {
        const res = await fetch("/api/dashboard/overview");
        if (!res.ok) throw new Error("Failed to load dashboard data");
        const data = await res.json();
        renderAll(data);
        setStatus(`Ready · ${num(data.counts?.ideas || 0)} ideas · ${num(data.counts?.reports || 0)} reports`, "ok");
      } catch (err) {
        setStatus(String(err.message || err), "err");
      }
    }

    async function runDaily() {
      const btn = $("runBtn");
      btn.disabled = true;
      setStatus("Generating ideas and today’s report…");
      try {
        const res = await fetch("/api/dashboard/run-daily?opportunity_limit=8&ideas_per_opportunity=1&report_format=markdown", {
          method: "POST",
        });
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Run failed");
        $("banner").innerHTML = `
          <div class="banner">
            Done. Created <strong>${num(data.total_ideas_generated)}</strong> ideas
            and saved report <strong>#${num(data.report_id)}</strong>.
            ${Array.isArray(data.keyword_seeds) && data.keyword_seeds.length
              ? `<div class="quiet" style="margin-top:6px">Keyword seeds from trends: ${esc(data.keyword_seeds.slice(0,8).join(", "))}</div>`
              : ""}
            ${data.competitor_targets ? `<div class="quiet">Competitors analyzed from trends: ${num(data.competitor_targets)}</div>` : ""}
          </div>
        `;
        await loadData();
        showView("ideas");
        if (data.report_id) await openReport(data.report_id);
        setStatus("Today’s report is ready.", "ok");
      } catch (err) {
        setStatus(String(err.message || err), "err");
      } finally {
        btn.disabled = false;
      }
    }

    loadData();
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_dashboard() -> str:
    return DASHBOARD_HTML


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    return DASHBOARD_HTML
