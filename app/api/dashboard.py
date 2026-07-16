"""Browser UI for manually testing implemented modules."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI ASO Platform Test UI</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f172a;
      --panel: #111827;
      --muted: #94a3b8;
      --text: #e5e7eb;
      --border: #263244;
      --accent: #38bdf8;
      --accent-2: #22c55e;
      --danger: #fb7185;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #193154 0, var(--bg) 34rem);
      color: var(--text);
    }
    header {
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--border);
      background: rgba(15, 23, 42, 0.78);
      position: sticky;
      top: 0;
      z-index: 2;
      backdrop-filter: blur(12px);
    }
    h1 { margin: 0 0 8px; font-size: 28px; }
    h2 { margin: 0 0 12px; font-size: 18px; }
    p { color: var(--muted); margin: 0; line-height: 1.5; }
    main {
      display: grid;
      grid-template-columns: minmax(320px, 520px) minmax(360px, 1fr);
      gap: 20px;
      padding: 24px 32px 32px;
    }
    section, aside {
      background: rgba(17, 24, 39, 0.9);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
    }
    section { padding: 18px; margin-bottom: 16px; }
    aside {
      position: sticky;
      top: 118px;
      height: calc(100vh - 150px);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .result-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 18px;
      border-bottom: 1px solid var(--border);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    label {
      display: block;
      margin: 10px 0 6px;
      color: var(--muted);
      font-size: 13px;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: #0b1220;
      color: var(--text);
      padding: 10px 11px;
      outline: none;
    }
    textarea {
      min-height: 92px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    button {
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: #03111c;
      cursor: pointer;
      font-weight: 700;
      padding: 10px 12px;
      margin: 10px 8px 0 0;
    }
    button.secondary { background: #334155; color: var(--text); }
    button.success { background: var(--accent-2); color: #052e16; }
    button.danger { background: var(--danger); color: #3f0713; }
    code {
      color: #bae6fd;
      background: #0b1220;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1px 5px;
    }
    .hint { font-size: 13px; color: var(--muted); margin-top: 10px; }
    .status {
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .output {
      margin: 0;
      padding: 18px;
      overflow: auto;
      flex: 1;
      background: #050b14;
      color: var(--text);
      font-size: 14px;
      line-height: 1.45;
    }
    .empty {
      color: var(--muted);
      border: 1px dashed var(--border);
      border-radius: 12px;
      padding: 18px;
      text-align: center;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin: 0 0 16px;
    }
    .metric, .item-card {
      background: #0b1220;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
    }
    .metric strong {
      display: block;
      font-size: 24px;
      margin-top: 4px;
    }
    .metric span, .meta {
      color: var(--muted);
      font-size: 12px;
    }
    .item-card {
      margin-bottom: 12px;
    }
    .item-card h3 {
      margin: 0 0 8px;
      font-size: 16px;
    }
    .badges {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 8px;
      background: #1e293b;
      color: #cbd5e1;
      font-size: 12px;
    }
    .badge.good { background: rgba(34, 197, 94, 0.18); color: #86efac; }
    .badge.bad { background: rgba(251, 113, 133, 0.18); color: #fda4af; }
    .badge.info { background: rgba(56, 189, 248, 0.18); color: #7dd3fc; }
    .thumb {
      width: 72px;
      height: 72px;
      object-fit: cover;
      border-radius: 12px;
      border: 1px solid var(--border);
      float: right;
      margin-left: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #0b1220;
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
    }
    th, td {
      text-align: left;
      border-bottom: 1px solid var(--border);
      padding: 10px;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    tr:last-child td { border-bottom: 0; }
    @media (max-width: 980px) {
      main { grid-template-columns: 1fr; padding: 18px; }
      aside { position: static; height: 60vh; }
      header { padding: 22px 18px 14px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>AI ASO Platform Test UI</h1>
    <p>Manual browser controls for Modules 1-6. These buttons call the same FastAPI endpoints you test from PowerShell.</p>
  </header>
  <main>
    <div>
      <section>
        <h2>Module 1: Foundation</h2>
        <button onclick="requestJson('/health')">Health</button>
        <button class="secondary" onclick="requestJson('/health/runtime')">Runtime Health</button>
        <p class="hint">Confirms FastAPI, settings, DB startup, and runtime abstraction wiring.</p>
      </section>

      <section>
        <h2>Module 2: App Store Research</h2>
        <div class="grid">
          <div>
            <label for="appStoreLimit">Limit</label>
            <input id="appStoreLimit" type="number" value="25" min="1" max="200">
          </div>
          <div>
            <label for="appStoreChart">Chart filter</label>
            <select id="appStoreChart">
              <option value="">All</option>
              <option value="top_free">Top Free</option>
              <option value="top_paid">Top Paid</option>
              <option value="fast_growing">Fast Growing</option>
            </select>
          </div>
        </div>
        <button onclick="runAppStoreResearch()">Run Research</button>
        <button class="secondary" onclick="listAppStoreTrending()">List Trending</button>
      </section>

      <section>
        <h2>Module 3: Google Play Research</h2>
        <div class="grid">
          <div>
            <label for="googlePlayLimit">Limit</label>
            <input id="googlePlayLimit" type="number" value="25" min="1" max="200">
          </div>
          <div>
            <label for="googlePlayChart">Chart filter</label>
            <select id="googlePlayChart">
              <option value="">All</option>
              <option value="top_free">Top Free</option>
              <option value="top_paid">Top Paid</option>
              <option value="top_grossing">Top Grossing</option>
              <option value="fast_growing">Fast Growing</option>
            </select>
          </div>
        </div>
        <label><input id="googleFetchDetails" type="checkbox" style="width:auto"> Fetch rating counts (slower)</label>
        <button onclick="runGooglePlayResearch()">Run Research</button>
        <button class="secondary" onclick="listGooglePlayTrending()">List Trending</button>
      </section>

      <section>
        <h2>Module 4: Keyword Research</h2>
        <label for="keywordSeeds">Seed terms, comma separated</label>
        <input id="keywordSeeds" value="fitness, habit tracker">
        <div class="grid">
          <div>
            <label for="keywordPlatforms">Platforms</label>
            <select id="keywordPlatforms">
              <option value="">Both</option>
              <option value="app_store">App Store</option>
              <option value="google_play">Google Play</option>
            </select>
          </div>
          <div>
            <label for="keywordLimit">Suggestions per seed</label>
            <input id="keywordLimit" type="number" value="5" min="1" max="50">
          </div>
        </div>
        <button onclick="runKeywordResearch()">Run Keyword Research</button>
        <button class="secondary" onclick="listKeywords()">List Keywords</button>
      </section>

      <section>
        <h2>Module 5: Competitor Analysis</h2>
        <div class="grid">
          <div>
            <label for="competitorPlatform">Platform</label>
            <select id="competitorPlatform">
              <option value="app_store">App Store</option>
              <option value="google_play">Google Play</option>
            </select>
          </div>
          <div>
            <label for="competitorReviews">Reviews per app</label>
            <input id="competitorReviews" type="number" value="5" min="0" max="100">
          </div>
        </div>
        <label for="competitorAppId">Store app ID</label>
        <input id="competitorAppId" value="284882215">
        <button onclick="runCompetitorAnalysis()">Analyze Competitor</button>
        <button class="secondary" onclick="listCompetitors()">List Competitors</button>
        <label for="competitorReviewId">Competitor DB ID for reviews</label>
        <input id="competitorReviewId" type="number" value="1" min="1">
        <button class="secondary" onclick="listCompetitorReviews()">List Competitor Reviews</button>
      </section>

      <section>
        <h2>Module 6: Reviews Intelligence</h2>
        <div class="grid">
          <div>
            <label for="reviewCompetitorIds">Competitor DB IDs</label>
            <input id="reviewCompetitorIds" value="1">
          </div>
          <div>
            <label for="reviewLimit">Reviews per competitor</label>
            <input id="reviewLimit" type="number" value="10" min="0" max="200">
          </div>
        </div>
        <button onclick="runReviewsIntelligence()">Analyze Reviews</button>
        <button class="secondary" onclick="listReviews()">List Reviews</button>
        <button class="secondary" onclick="listBugReviews()">Bug Reviews</button>
        <button class="secondary" onclick="listNegativeReviews()">Negative Reviews</button>
      </section>

      <section>
        <h2>Module 7: Market Opportunities</h2>
        <div class="grid">
          <div>
            <label for="oppMinScore">Min score (synthesize)</label>
            <input id="oppMinScore" type="number" value="45" min="0" max="100">
          </div>
          <div>
            <label for="oppMinKeywordOpp">Min keyword opportunity</label>
            <input id="oppMinKeywordOpp" type="number" value="55" min="0" max="100">
          </div>
        </div>
        <label for="oppPerSourceLimit">Per-source limit</label>
        <input id="oppPerSourceLimit" type="number" value="300" min="10" max="2000">
        <button onclick="runOpportunitySynthesis()">Synthesize Opportunities</button>

        <h3 style="margin-top:18px; font-size:16px;">View Saved Opportunities</h3>
        <div class="grid">
          <div>
            <label for="oppListCategory">Category (optional)</label>
            <input id="oppListCategory" placeholder="e.g. Finance">
          </div>
          <div>
            <label for="oppListLimit">Limit</label>
            <input id="oppListLimit" type="number" value="50" min="1" max="500">
          </div>
        </div>
        <div class="grid">
          <div>
            <label for="oppListMinScore">Min opportunity score (list)</label>
            <input id="oppListMinScore" type="number" value="0" min="0" max="100">
          </div>
        </div>
        <button class="secondary" onclick="listOpportunities()">List Opportunities</button>
      </section>

    </div>

    <aside>
      <div class="result-header">
        <strong>Response</strong>
        <span id="status" class="status">Ready</span>
      </div>
      <div id="output" class="output">
        <div class="empty">Open http://127.0.0.1:8000/dashboard and click a module action.</div>
      </div>
    </aside>
  </main>

  <script>
    const output = document.getElementById("output");
    const statusEl = document.getElementById("status");

    function value(id) {
      return document.getElementById(id).value.trim();
    }

    function numberValue(id) {
      return Number(value(id));
    }

    function csv(id) {
      return value(id).split(",").map(item => item.trim()).filter(Boolean);
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function showHtml(html) {
      output.innerHTML = html;
    }

    function formatNumber(value) {
      if (value === null || value === undefined || value === "") return "Not available";
      if (typeof value === "number") return value.toLocaleString();
      return escapeHtml(value);
    }

    function formatDate(value) {
      if (!value) return "Not available";
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? escapeHtml(value) : date.toLocaleString();
    }

    function platformName(value) {
      if (value === "app_store") return "App Store";
      if (value === "google_play") return "Google Play";
      return escapeHtml(value || "Unknown");
    }

    function titleCase(value) {
      return String(value || "Not available")
        .replaceAll("_", " ")
        .replace(/\\b\\w/g, char => char.toUpperCase());
    }

    function metric(label, value) {
      return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${formatNumber(value)}</strong></div>`;
    }

    function emptyState(message) {
      return `<div class="empty">${escapeHtml(message)}</div>`;
    }

    function skippedBlock(skipped) {
      const entries = Object.entries(skipped || {});
      if (!entries.length) return "";
      return `
        <div class="item-card">
          <h3>Skipped items</h3>
          <p class="meta">These were skipped safely, so the rest of the request still completed.</p>
          ${entries.map(([key, reason]) => `
            <div class="badges"><span class="badge bad">${escapeHtml(key)}</span></div>
            <p>${escapeHtml(reason)}</p>
          `).join("")}
        </div>
      `;
    }

    function renderHealth(data) {
      return `
        <div class="summary-grid">
          ${metric("Status", data.status || (data.healthy ? "Healthy" : "Not healthy"))}
          ${metric("Environment", data.app_env || "Current")}
          ${metric("Agent runtime", data.agent_runtime || "Unknown")}
        </div>
      `;
    }

    function renderRunSummary(data, title) {
      if (data.total_keywords !== undefined) {
        return `
          <h2>${title}</h2>
          <div class="summary-grid">
            ${metric("Keywords saved", data.total_keywords)}
            ${metric("Seeds processed", Object.keys(data.seeds || {}).length)}
            ${metric("Skipped", Object.keys(data.skipped || {}).length)}
          </div>
          ${renderSimpleCounts("Seed results", data.seeds)}
          ${skippedBlock(data.skipped)}
        `;
      }

      if (data.total_competitors !== undefined && data.total_reviews !== undefined && data.sentiment) {
        return `
          <h2>${title}</h2>
          <div class="summary-grid">
            ${metric("Competitors analyzed", data.total_competitors)}
            ${metric("Reviews analyzed", data.total_reviews)}
            ${metric("Bug mentions", data.bugs)}
            ${metric("Feature requests", data.feature_requests)}
          </div>
          <div class="summary-grid">
            ${metric("Positive reviews", data.sentiment.positive)}
            ${metric("Neutral reviews", data.sentiment.neutral)}
            ${metric("Negative reviews", data.sentiment.negative)}
          </div>
          ${renderCompetitorRunCards(data.competitors)}
          ${skippedBlock(data.skipped)}
        `;
      }

      if (data.total_competitors !== undefined) {
        return `
          <h2>${title}</h2>
          <div class="summary-grid">
            ${metric("Competitors saved", data.total_competitors)}
            ${metric("Reviews saved", data.total_reviews)}
            ${metric("Skipped", Object.keys(data.skipped || {}).length)}
          </div>
          ${renderCompetitorRunCards(data.competitors)}
          ${skippedBlock(data.skipped)}
        `;
      }

      if (data.charts !== undefined) {
        return `
          <h2>${title}</h2>
          <div class="summary-grid">
            ${metric("Chart rows saved", Object.values(data.charts || {}).reduce((sum, count) => sum + count, 0))}
            ${metric("Fast growing apps", data.fast_growing)}
            ${metric("Skipped charts", Object.keys(data.skipped_charts || {}).length)}
          </div>
          ${renderSimpleCounts("Chart results", data.charts)}
          ${skippedBlock(data.skipped_charts)}
        `;
      }

      return renderObjectSummary(data);
    }

    function renderSimpleCounts(title, counts) {
      const entries = Object.entries(counts || {});
      if (!entries.length) return emptyState(`No ${title.toLowerCase()} yet.`);
      return `
        <div class="item-card">
          <h3>${escapeHtml(title)}</h3>
          <table>
            <thead><tr><th>Name</th><th>Saved</th></tr></thead>
            <tbody>
              ${entries.map(([name, count]) => `
                <tr><td>${escapeHtml(titleCase(name))}</td><td>${formatNumber(count)}</td></tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    function renderCompetitorRunCards(competitors) {
      const entries = Object.entries(competitors || {});
      if (!entries.length) return "";
      return entries.map(([key, value]) => `
        <div class="item-card">
          <h3>${escapeHtml(key)}</h3>
          <div class="badges">
            <span class="badge info">Competitor ID ${formatNumber(value.competitor_id)}</span>
            <span class="badge">Reviews ${formatNumber(value.reviews)}</span>
            ${value.bugs !== undefined ? `<span class="badge bad">Bugs ${formatNumber(value.bugs)}</span>` : ""}
            ${value.feature_requests !== undefined ? `<span class="badge good">Requests ${formatNumber(value.feature_requests)}</span>` : ""}
          </div>
        </div>
      `).join("");
    }

    function renderTrendingApps(items) {
      if (!items.length) return emptyState("No trending apps saved yet. Run research first.");
      return `
        <h2>Trending Apps</h2>
        <table>
          <thead><tr><th>Rank</th><th>App</th><th>Category</th><th>Rating</th></tr></thead>
          <tbody>
            ${items.map(app => `
              <tr>
                <td>${formatNumber(app.rank)}</td>
                <td><strong>${escapeHtml(app.name)}</strong><br><span class="meta">${escapeHtml(app.developer || "")}</span></td>
                <td>${escapeHtml(app.category || "Not available")}</td>
                <td>${formatNumber(app.rating)}<br><span class="meta">${formatNumber(app.rating_count)} ratings</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderKeywords(items) {
      if (!items.length) return emptyState("No keywords saved yet. Run keyword research first.");
      return `
        <h2>Keyword Opportunities</h2>
        <table>
          <thead><tr><th>Keyword</th><th>Platform</th><th>Volume</th><th>Difficulty</th><th>Opportunity</th></tr></thead>
          <tbody>
            ${items.map(keyword => `
              <tr>
                <td><strong>${escapeHtml(keyword.term)}</strong></td>
                <td>${platformName(keyword.platform)}</td>
                <td>${formatNumber(keyword.search_volume)}</td>
                <td>${formatNumber(keyword.difficulty_score)}</td>
                <td><span class="badge good">${formatNumber(keyword.opportunity_score)}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderCompetitors(items) {
      if (!items.length) return emptyState("No competitors saved yet. Analyze a competitor first.");
      return `
        <h2>Tracked Competitors</h2>
        ${items.map(app => `
          <div class="item-card">
            ${Array.isArray(app.screenshots) && app.screenshots[0] ? `<img class="thumb" src="${escapeHtml(app.screenshots[0])}" alt="">` : ""}
            <h3>${escapeHtml(app.name)}</h3>
            <div class="badges">
              <span class="badge info">ID ${formatNumber(app.id)}</span>
              <span class="badge">${platformName(app.platform)}</span>
              <span class="badge">${escapeHtml(app.pricing_model || "Unknown pricing")}</span>
            </div>
            <p>${escapeHtml(app.developer || "Unknown developer")} - ${escapeHtml(app.category || "Unknown category")}</p>
            <p class="meta">Rating: ${formatNumber(app.rating)} from ${formatNumber(app.rating_count)} ratings. Last analyzed: ${formatDate(app.last_analyzed_at)}</p>
            ${Array.isArray(app.features) && app.features.length ? `<p><strong>Features:</strong> ${escapeHtml(app.features.slice(0, 4).join(", "))}</p>` : ""}
          </div>
        `).join("")}
      `;
    }

    function renderReviews(items) {
      if (!items.length) return emptyState("No reviews found for this filter.");
      return `
        <h2>Review Intelligence</h2>
        ${items.map(review => `
          <div class="item-card">
            <h3>${escapeHtml(review.author || "Anonymous reviewer")}</h3>
            <div class="badges">
              <span class="badge ${review.sentiment === "positive" ? "good" : review.sentiment === "negative" ? "bad" : "info"}">${titleCase(review.sentiment)}</span>
              <span class="badge">Rating ${formatNumber(review.rating)}</span>
              ${review.mentions_bug ? `<span class="badge bad">Bug mentioned</span>` : ""}
              ${review.mentions_feature_request ? `<span class="badge good">Feature request</span>` : ""}
            </div>
            <p>${escapeHtml(review.review_text || "No review text")}</p>
            <p class="meta">Competitor ID ${formatNumber(review.competitor_id)} - ${platformName(review.platform)} - Posted ${formatDate(review.posted_at)}</p>
          </div>
        `).join("")}
      `;
    }

    function renderObjectSummary(data) {
      const rows = Object.entries(data || {});
      if (!rows.length) return emptyState("No data returned.");
      return `
        <table>
          <tbody>
            ${rows.map(([key, val]) => `<tr><th>${escapeHtml(titleCase(key))}</th><td>${escapeHtml(typeof val === "object" ? JSON.stringify(val) : val)}</td></tr>`).join("")}
          </tbody>
        </table>
      `;
    }

    function renderOpportunitySynthesisSummary(data) {
      const skippedCount = Object.keys(data.skipped || {}).length;
      const signals = data.signals || {};
      return `
        <h2>Opportunity Synthesis</h2>
        <div class="summary-grid">
          ${metric("Opportunities saved", data.opportunities)}
          ${metric("Skipped sources", skippedCount)}
        </div>
        ${renderSimpleCounts("Signal sources", signals)}
        ${skippedBlock(data.skipped)}
      `;
    }

    function renderOpportunities(items) {
      if (!items.length) return emptyState("No opportunities saved yet. Click 'Synthesize Opportunities' first.");
      return `
        <h2>Market Opportunities</h2>
        <table>
          <thead>
            <tr>
              <th>Opportunity</th>
              <th>Category</th>
              <th>Score</th>
              <th>What we found</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(item => `
              <tr>
                <td><strong>${escapeHtml(item.title)}</strong><br><span class="meta">ID ${formatNumber(item.id)}</span></td>
                <td>${escapeHtml(item.category || "Not available")}</td>
                <td><span class="badge good">${formatNumber(item.opportunity_score)}</span><br><span class="meta">${formatDate(item.identified_at)}</span></td>
                <td>${escapeHtml(item.description || "")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderReadable(path, data) {
      if (path.startsWith("/health")) return renderHealth(data || {});
      if (path.includes("/api/opportunities/synthesize")) return renderOpportunitySynthesisSummary(data || {});
      if (path.includes("/research") || path.includes("/analyze")) return renderRunSummary(data || {}, "Run Complete");
      if (Array.isArray(data)) {
        if (path.includes("/trending")) return renderTrendingApps(data);
        if (path.includes("/keywords")) return renderKeywords(data);
        if (path.includes("/opportunities")) return renderOpportunities(data);
        if (path.includes("/competitors") && path.includes("/reviews")) return renderReviews(data);
        if (path.includes("/competitors")) return renderCompetitors(data);
        if (path.includes("/reviews")) return renderReviews(data);
        return data.length ? renderObjectSummary({ items: `${data.length} rows returned` }) : emptyState("No rows returned.");
      }
      return renderObjectSummary(data || {});
    }

    function setStatus(text, ok = true) {
      statusEl.textContent = text;
      statusEl.style.color = ok ? "var(--muted)" : "var(--danger)";
    }

    async function requestJson(path, options = {}) {
      const started = performance.now();
      setStatus(`Loading ${path}`);
      try {
        const response = await fetch(path, {
          headers: { "Content-Type": "application/json", ...(options.headers || {}) },
          ...options
        });
        const text = await response.text();
        let data = text;
        try { data = text ? JSON.parse(text) : null; } catch (_) {}
        const elapsed = Math.round(performance.now() - started);
        setStatus(`${response.status} ${response.statusText} - ${elapsed}ms`, response.ok);
        showHtml(renderReadable(path, data));
      } catch (error) {
        setStatus("Request failed", false);
        showHtml(`<div class="empty">Request failed: ${escapeHtml(error)}</div>`);
      }
    }

    function query(params) {
      const search = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== "" && val !== null && val !== undefined) search.set(key, val);
      });
      const text = search.toString();
      return text ? `?${text}` : "";
    }

    function runAppStoreResearch() {
      requestJson(`/api/app-store/research${query({ limit: numberValue("appStoreLimit") })}`, { method: "POST" });
    }

    function listAppStoreTrending() {
      requestJson(`/api/app-store/trending${query({
        limit: numberValue("appStoreLimit"),
        chart_type: value("appStoreChart")
      })}`);
    }

    function runGooglePlayResearch() {
      requestJson(`/api/google-play/research${query({
        limit: numberValue("googlePlayLimit"),
        fetch_details: document.getElementById("googleFetchDetails").checked
      })}`, { method: "POST" });
    }

    function listGooglePlayTrending() {
      requestJson(`/api/google-play/trending${query({
        limit: numberValue("googlePlayLimit"),
        chart_type: value("googlePlayChart")
      })}`);
    }

    function runKeywordResearch() {
      const platform = value("keywordPlatforms");
      const body = {
        seed_terms: csv("keywordSeeds"),
        platforms: platform ? [platform] : null,
        suggestions_per_seed: numberValue("keywordLimit")
      };
      requestJson("/api/keywords/research", { method: "POST", body: JSON.stringify(body) });
    }

    function listKeywords() {
      const platform = value("keywordPlatforms");
      requestJson(`/api/keywords${query({ platform })}`);
    }

    function runCompetitorAnalysis() {
      const body = {
        targets: [{ platform: value("competitorPlatform"), store_app_id: value("competitorAppId") }],
        reviews_per_app: numberValue("competitorReviews")
      };
      requestJson("/api/competitors/analyze", { method: "POST", body: JSON.stringify(body) });
    }

    function listCompetitors() {
      requestJson("/api/competitors");
    }

    function listCompetitorReviews() {
      requestJson(`/api/competitors/${numberValue("competitorReviewId")}/reviews`);
    }

    function runReviewsIntelligence() {
      const ids = csv("reviewCompetitorIds").map(Number).filter(Boolean);
      const body = {
        competitor_ids: ids.length ? ids : null,
        reviews_per_competitor: numberValue("reviewLimit")
      };
      requestJson("/api/reviews/analyze", { method: "POST", body: JSON.stringify(body) });
    }

    function listReviews() {
      requestJson("/api/reviews");
    }

    function listBugReviews() {
      requestJson("/api/reviews?mentions_bug=true");
    }

    function listNegativeReviews() {
      requestJson("/api/reviews?sentiment=negative");
    }

    function runOpportunitySynthesis() {
      const body = {
        min_score: numberValue("oppMinScore"),
        min_keyword_opportunity: numberValue("oppMinKeywordOpp"),
        per_source_limit: numberValue("oppPerSourceLimit"),
      };
      requestJson("/api/opportunities/synthesize", { method: "POST", body: JSON.stringify(body) });
    }

    function listOpportunities() {
      requestJson(`/api/opportunities${query({
        category: value("oppListCategory"),
        min_opportunity_score: numberValue("oppListMinScore"),
        limit: numberValue("oppListLimit"),
      })}`);
    }

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
