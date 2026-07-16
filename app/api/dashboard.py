"""ASO intelligence dashboard — trends, opportunities, ideas, and reports."""

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
  <title>ASO Intelligence — AI ASO Platform</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f3f6f4;
      --surface: #ffffff;
      --ink: #14201b;
      --muted: #5b6b63;
      --line: #d7e0db;
      --accent: #0f766e;
      --accent-soft: #d8f3ef;
      --warn: #b45309;
      --danger: #b91c1c;
      --good: #15803d;
      --shadow: 0 10px 30px rgba(20, 32, 27, 0.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", system-ui, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 0% 0%, #dff5ef 0, transparent 28%),
        radial-gradient(circle at 100% 0%, #e8efe9 0, transparent 24%),
        var(--bg);
      min-height: 100vh;
    }
    h1, h2, h3, .brand {
      font-family: Sora, "IBM Plex Sans", sans-serif;
      letter-spacing: -0.02em;
    }
    a { color: var(--accent); }
    .shell { max-width: 1200px; margin: 0 auto; padding: 24px 20px 48px; }
    header {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    .brand { font-size: 28px; margin: 0 0 6px; }
    .subtitle { margin: 0; color: var(--muted); max-width: 52ch; line-height: 1.5; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; }
    button, .btn {
      border: 0;
      border-radius: 10px;
      padding: 11px 16px;
      font: 600 14px "IBM Plex Sans", sans-serif;
      cursor: pointer;
      background: var(--accent);
      color: #fff;
    }
    button.secondary, .btn.secondary {
      background: var(--surface);
      color: var(--ink);
      border: 1px solid var(--line);
    }
    button:disabled { opacity: 0.6; cursor: wait; }
    .status {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 13px;
      min-height: 1.2em;
    }
    .status.error { color: var(--danger); }
    .status.ok { color: var(--good); }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .metric {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px 16px;
      box-shadow: var(--shadow);
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }
    .metric strong { font-family: Sora, sans-serif; font-size: 26px; }
    .tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    .tab {
      background: transparent;
      color: var(--muted);
      border: 1px solid transparent;
      padding: 8px 12px;
    }
    .tab.active {
      background: var(--accent-soft);
      color: var(--accent);
      border-color: #b7e4dc;
    }
    .panel {
      display: none;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      box-shadow: var(--shadow);
    }
    .panel.active { display: block; }
    .panel h2 { margin: 0 0 6px; font-size: 20px; }
    .panel .lead { margin: 0 0 16px; color: var(--muted); }
    .grid-2 {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 16px;
    }
    .card-list { display: grid; gap: 12px; }
    .card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      background: #fbfcfb;
    }
    .card h3 { margin: 0 0 8px; font-size: 16px; }
    .meta { color: var(--muted); font-size: 12px; margin: 0; }
    .badges { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 12px;
      background: var(--accent-soft);
      color: var(--accent);
    }
    .badge.neutral { background: #eef2f0; color: var(--muted); }
    .badge.warn { background: #fff7ed; color: var(--warn); }
    table { width: 100%; border-collapse: collapse; }
    th, td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 14px;
    }
    th { color: var(--muted); font-size: 12px; font-weight: 600; }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 12px;
      padding: 24px;
      text-align: center;
      color: var(--muted);
    }
    .report-box {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12.5px;
      line-height: 1.5;
      background: #0f1c18;
      color: #d7efe7;
      border-radius: 12px;
      padding: 16px;
      max-height: 520px;
      overflow: auto;
    }
    .run-summary {
      background: var(--accent-soft);
      border: 1px solid #b7e4dc;
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 16px;
    }
    @media (max-width: 900px) {
      header { flex-direction: column; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid-2 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1 class="brand">ASO Intelligence</h1>
        <p class="subtitle">
          Your AI ASO employee — trending apps, market opportunities, product ideas,
          and daily intelligence reports in one place.
        </p>
      </div>
      <div class="actions">
        <button id="runDailyBtn" onclick="runDailyPipeline()">Generate Daily Ideas Report</button>
        <button class="secondary" onclick="refreshDashboard()">Refresh</button>
      </div>
    </header>

    <p id="status" class="status">Loading intelligence…</p>
    <div id="runBanner"></div>

    <div class="metrics" id="metrics"></div>

    <div class="tabs">
      <button class="tab active" data-tab="overview" onclick="showTab('overview')">Overview</button>
      <button class="tab" data-tab="trends" onclick="showTab('trends')">Trends</button>
      <button class="tab" data-tab="opportunities" onclick="showTab('opportunities')">Opportunities</button>
      <button class="tab" data-tab="ideas" onclick="showTab('ideas')">Product Ideas</button>
      <button class="tab" data-tab="reports" onclick="showTab('reports')">Reports</button>
    </div>

    <section class="panel active" id="panel-overview">
      <h2>Today’s intelligence</h2>
      <p class="lead">Highest-signal opportunities and product ideas ready for review.</p>
      <div class="grid-2">
        <div>
          <h3>Top product ideas</h3>
          <div class="card-list" id="overviewIdeas"></div>
        </div>
        <div>
          <h3>Latest report</h3>
          <div id="overviewReport"></div>
        </div>
      </div>
    </section>

    <section class="panel" id="panel-trends">
      <h2>Trending apps</h2>
      <p class="lead">Recent Apple App Store and Google Play chart signals.</p>
      <div id="trendsTable"></div>
      <h3 style="margin-top:20px">Top keyword opportunities</h3>
      <div id="keywordsTable"></div>
    </section>

    <section class="panel" id="panel-opportunities">
      <h2>Market opportunities</h2>
      <p class="lead">Category gaps synthesized from trends, keywords, competitors, and reviews.</p>
      <div class="card-list" id="opportunitiesList"></div>
    </section>

    <section class="panel" id="panel-ideas">
      <h2>Product ideas</h2>
      <p class="lead">AI-generated mobile app, SaaS, and AI product concepts.</p>
      <div class="card-list" id="ideasList"></div>
    </section>

    <section class="panel" id="panel-reports">
      <h2>Daily & weekly reports</h2>
      <p class="lead">Saved intelligence reports with actionable recommendations.</p>
      <div class="card-list" id="reportsList"></div>
      <div id="reportDetail" style="margin-top:16px"></div>
    </section>
  </div>

  <script>
    let state = null;

    function setStatus(text, kind = "") {
      const el = document.getElementById("status");
      el.textContent = text;
      el.className = "status" + (kind ? " " + kind : "");
    }

    function showTab(name) {
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + name));
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function titleCase(value) {
      return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function formatNumber(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
      return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
    }

    function formatDate(value) {
      if (!value) return "—";
      const d = new Date(value);
      return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
    }

    function empty(msg) {
      return `<div class="empty">${escapeHtml(msg)}</div>`;
    }

    function renderMetrics(counts) {
      const items = [
        ["Trending apps", counts.trends],
        ["Opportunities", counts.opportunities],
        ["Product ideas", counts.ideas],
        ["Reports", counts.reports],
        ["Keywords", counts.keywords],
        ["Competitors", counts.competitors],
        ["Reviews", counts.reviews],
        ["Memory", counts.memory],
      ];
      document.getElementById("metrics").innerHTML = items.map(([label, value]) => `
        <div class="metric"><span>${escapeHtml(label)}</span><strong>${formatNumber(value)}</strong></div>
      `).join("");
    }

    function renderIdeaCards(items, limit = 6) {
      if (!items || !items.length) return empty("No product ideas yet. Click Generate Daily Ideas Report.");
      return items.slice(0, limit).map((item) => `
        <div class="card">
          <h3>${escapeHtml(item.title)}</h3>
          <div class="badges">
            <span class="badge">${escapeHtml(titleCase(item.idea_type))}</span>
            <span class="badge neutral">Confidence ${formatNumber(item.confidence_score)}</span>
          </div>
          <p><strong>Problem:</strong> ${escapeHtml(item.problem_statement || "Not available")}</p>
          <p><strong>Solution:</strong> ${escapeHtml(item.proposed_solution || "Not available")}</p>
          <p class="meta">Audience: ${escapeHtml(item.target_audience || "—")} · Monetization: ${escapeHtml(item.monetization_strategy || "—")}</p>
        </div>
      `).join("");
    }

    function renderOverview(data) {
      document.getElementById("overviewIdeas").innerHTML = renderIdeaCards(data.ideas, 4);
      const report = data.latest_report;
      if (!report) {
        document.getElementById("overviewReport").innerHTML = empty("No report yet. Generate a daily ideas report to create one.");
        return;
      }
      document.getElementById("overviewReport").innerHTML = `
        <div class="card">
          <h3>${escapeHtml(report.title)}</h3>
          <div class="badges">
            <span class="badge">${escapeHtml(titleCase(report.report_type))}</span>
            <span class="badge neutral">${escapeHtml(titleCase(report.report_format))}</span>
          </div>
          <p>${escapeHtml(report.summary || "")}</p>
          <p class="meta">${formatDate(report.generated_at)}${report.file_path ? " · " + escapeHtml(report.file_path) : ""}</p>
        </div>
        ${data.latest_report_preview ? `<div class="report-box">${escapeHtml(data.latest_report_preview)}</div>` : ""}
      `;
    }

    function renderTrends(data) {
      const trends = data.trends || [];
      document.getElementById("trendsTable").innerHTML = trends.length ? `
        <table>
          <thead><tr><th>App</th><th>Platform</th><th>Chart</th><th>Rank</th><th>Rating</th></tr></thead>
          <tbody>
            ${trends.map((row) => `
              <tr>
                <td><strong>${escapeHtml(row.name)}</strong><br><span class="meta">${escapeHtml(row.category || "—")}</span></td>
                <td>${escapeHtml(titleCase(row.platform))}</td>
                <td>${escapeHtml(titleCase(row.chart_type))}</td>
                <td>${formatNumber(row.rank)}</td>
                <td>${formatNumber(row.rating)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : empty("No trending apps saved yet. Run App Store / Google Play research first.");

      const keywords = data.keywords || [];
      document.getElementById("keywordsTable").innerHTML = keywords.length ? `
        <table>
          <thead><tr><th>Keyword</th><th>Platform</th><th>Opportunity</th><th>Volume</th><th>Difficulty</th></tr></thead>
          <tbody>
            ${keywords.map((row) => `
              <tr>
                <td><strong>${escapeHtml(row.term)}</strong></td>
                <td>${escapeHtml(titleCase(row.platform))}</td>
                <td>${formatNumber(row.opportunity_score)}</td>
                <td>${formatNumber(row.search_volume)}</td>
                <td>${formatNumber(row.difficulty_score)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : empty("No keywords saved yet.");
    }

    function renderOpportunities(data) {
      const items = data.opportunities || [];
      document.getElementById("opportunitiesList").innerHTML = items.length ? items.map((item) => `
        <div class="card">
          <h3>${escapeHtml(item.title)}</h3>
          <div class="badges">
            <span class="badge">${escapeHtml(item.category || "General")}</span>
            <span class="badge warn">Score ${formatNumber(item.opportunity_score)}</span>
          </div>
          <p>${escapeHtml(item.description || "")}</p>
          <p class="meta">ID ${formatNumber(item.id)} · ${formatDate(item.identified_at)}</p>
        </div>
      `).join("") : empty("No opportunities yet. Generate a daily report to synthesize them.");
    }

    function renderIdeas(data) {
      document.getElementById("ideasList").innerHTML = renderIdeaCards(data.ideas, 20);
    }

    function renderReports(data) {
      const items = data.reports || [];
      document.getElementById("reportsList").innerHTML = items.length ? items.map((item) => `
        <div class="card">
          <h3>${escapeHtml(item.title)}</h3>
          <div class="badges">
            <span class="badge">${escapeHtml(titleCase(item.report_type))}</span>
            <span class="badge neutral">${escapeHtml(titleCase(item.report_format))}</span>
          </div>
          <p>${escapeHtml(item.summary || "")}</p>
          <p class="meta">${formatDate(item.generated_at)}${item.file_path ? " · " + escapeHtml(item.file_path) : ""}</p>
          <button class="secondary" onclick="openReport(${item.id})">Open report</button>
        </div>
      `).join("") : empty("No reports yet.");
    }

    async function openReport(id) {
      setStatus("Loading report…");
      try {
        const res = await fetch(`/api/dashboard/reports/${id}`);
        const data = await res.json();
        if (!res.ok || data.error) throw new Error(data.error || "Failed to load report");
        document.getElementById("reportDetail").innerHTML = `
          <h3>${escapeHtml(data.report.title)}</h3>
          <div class="report-box">${escapeHtml(data.content || data.report.summary || "No file content available.")}</div>
        `;
        showTab("reports");
        setStatus("Report loaded.", "ok");
      } catch (err) {
        setStatus(String(err.message || err), "error");
      }
    }

    function renderAll(data) {
      state = data;
      renderMetrics(data.counts || {});
      renderOverview(data);
      renderTrends(data);
      renderOpportunities(data);
      renderIdeas(data);
      renderReports(data);
    }

    async function refreshDashboard() {
      setStatus("Refreshing dashboard…");
      try {
        const res = await fetch("/api/dashboard/overview");
        if (!res.ok) throw new Error("Failed to load overview");
        const data = await res.json();
        renderAll(data);
        setStatus(`Updated · ${formatNumber(data.counts?.ideas || 0)} ideas · ${formatNumber(data.counts?.reports || 0)} reports`, "ok");
      } catch (err) {
        setStatus(String(err.message || err), "error");
      }
    }

    async function runDailyPipeline() {
      const btn = document.getElementById("runDailyBtn");
      btn.disabled = true;
      setStatus("Running daily intelligence pipeline (opportunities → ideas → report → memory)…");
      try {
        const res = await fetch("/api/dashboard/run-daily?opportunity_limit=10&ideas_per_opportunity=1&report_format=markdown", {
          method: "POST",
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail ? JSON.stringify(data.detail) : "Pipeline failed");

        document.getElementById("runBanner").innerHTML = `
          <div class="run-summary">
            <strong>Daily pipeline complete.</strong>
            Generated ${formatNumber(data.total_ideas_generated)} ideas ·
            ${formatNumber(data.ideas_in_report)} in report ·
            Report ID ${formatNumber(data.report_id)}
            ${data.file_path ? " · File: " + escapeHtml(data.file_path) : ""}
          </div>
        `;
        await refreshDashboard();
        showTab("overview");
        setStatus("Daily ideas report ready.", "ok");
        if (data.report_id) openReport(data.report_id);
      } catch (err) {
        setStatus(String(err.message || err), "error");
      } finally {
        btn.disabled = false;
      }
    }

    refreshDashboard();
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
