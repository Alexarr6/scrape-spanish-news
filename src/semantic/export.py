from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go

from src.semantic.contracts import EmbeddingArtifact, PointArtifact, SemanticMetrics

PLOT_DIV_ID = "semantic-map"
INSPECTOR_PANEL_ID = "semantic-inspector"
FILTER_FORM_ID = "semantic-filters"
SEARCH_INPUT_ID = "semantic-search"
SOURCE_FILTER_ID = "semantic-source-filter"
SECTION_FILTER_ID = "semantic-section-filter"
DATE_FROM_ID = "semantic-date-from"
DATE_TO_ID = "semantic-date-to"
COUNT_LABEL_ID = "semantic-count-label"
NEIGHBOR_LIST_ID = "semantic-neighbor-list"


def write_embeddings_jsonl(records: list[EmbeddingArtifact], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")


def write_points_json(records: list[PointArtifact], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.model_dump() for record in records]
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_metrics(metrics: SemanticMetrics, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics.model_dump(), handle, ensure_ascii=False, indent=2)


def write_semantic_map_html(records: list[PointArtifact], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig = go.Figure()
    for source in sorted({record.source for record in records}):
        group = [record for record in records if record.source == source]
        fig.add_trace(
            go.Scatter(
                x=[record.x for record in group],
                y=[record.y for record in group],
                mode="markers",
                name=source,
                customdata=[_point_payload(record) for record in group],
                text=[record.title for record in group],
                hovertemplate=(
                    "<b>%{customdata[2]}</b><br>"
                    "source=%{customdata[1]}<br>"
                    "date=%{customdata[5]}<br>"
                    "section=%{customdata[6]}<br>"
                    "article_id=%{customdata[0]}<br>"
                    "%{customdata[7]}<extra></extra>"
                ),
                marker={"size": 9, "opacity": 0.82},
            )
        )
    fig.update_layout(title="Semantic article map", template="plotly_white")

    payload_json = json.dumps([record.model_dump() for record in records], ensure_ascii=False)
    fig.write_html(
        out_path,
        include_plotlyjs=True,
        full_html=True,
        div_id=PLOT_DIV_ID,
        post_script=_post_script(payload_json),
    )


def _point_payload(record: PointArtifact) -> list[object]:
    return [
        record.article_id,
        record.source,
        record.title,
        record.url,
        record.published_at,
        record.display_date or record.published_date or record.published_at[:10],
        record.section,
        record.summary_snippet,
        record.text_length,
        record.embedding_model,
        [neighbor.model_dump() for neighbor in record.neighbors],
    ]


def _post_script(payload_json: str) -> str:
    return f"""
const explorerRecords = {payload_json};
const plot = document.getElementById('{PLOT_DIV_ID}');
const plotContainer = plot.parentElement;
const state = {{
  selectedId: null,
  records: explorerRecords,
  byId: new Map(explorerRecords.map((record) => [record.article_id, record])),
  indexById: new Map(),
  visibleSources: new Set(),
  visibleSections: new Set(),
}};

function escapeHtml(value) {{
  return String(value ?? '').replace(/[&<>\"]/g, (char) => ({{
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
  }})[char]);
}}

function snippetLabel(snippet) {{
  if (!snippet) return 'No summary snippet available.';
  return snippet;
}}

function buildChrome() {{
  const shell = document.createElement('div');
  shell.id = 'semantic-explorer-shell';
  shell.innerHTML = `
    <style>
      #semantic-explorer-shell {{ display:grid; grid-template-columns:minmax(0, 1fr) 360px; gap:16px; align-items:start; margin-top:16px; }}
      #semantic-explorer-sidebar {{ border:1px solid #d7dce5; border-radius:12px; padding:14px; background:#fff; box-shadow:0 1px 4px rgba(0,0,0,0.05); }}
      #{FILTER_FORM_ID} {{ display:grid; gap:10px; margin-bottom:14px; }}
      #{FILTER_FORM_ID} label {{ display:grid; gap:4px; font:600 12px/1.4 sans-serif; color:#334155; }}
      #{FILTER_FORM_ID} input, #{FILTER_FORM_ID} select, #{FILTER_FORM_ID} button {{ font:500 13px/1.3 sans-serif; padding:8px 10px; border:1px solid #cbd5e1; border-radius:8px; }}
      #{COUNT_LABEL_ID} {{ font:600 12px/1.4 sans-serif; color:#475569; }}
      #{INSPECTOR_PANEL_ID} h2 {{ margin:0 0 8px; font:700 18px/1.25 sans-serif; }}
      .semantic-meta {{ margin:0 0 10px; color:#475569; font:500 12px/1.5 sans-serif; }}
      .semantic-snippet {{ font:400 13px/1.55 sans-serif; color:#0f172a; margin:0 0 12px; }}
      .semantic-actions {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }}
      .semantic-actions button, .semantic-actions a {{ border:1px solid #cbd5e1; border-radius:8px; padding:8px 10px; background:#f8fafc; color:#0f172a; text-decoration:none; font:600 12px/1.2 sans-serif; }}
      .semantic-neighbors {{ border-top:1px solid #e2e8f0; padding-top:12px; }}
      .semantic-neighbors h3 {{ margin:0 0 8px; font:700 14px/1.3 sans-serif; }}
      .semantic-neighbors ul {{ list-style:none; padding:0; margin:0; display:grid; gap:8px; }}
      .semantic-neighbors li {{ border:1px solid #e2e8f0; border-radius:10px; padding:10px; background:#f8fafc; }}
      .semantic-neighbors button {{ all:unset; cursor:pointer; color:#0f172a; display:block; width:100%; }}
      .semantic-empty {{ color:#64748b; font:500 13px/1.5 sans-serif; }}
      @media (max-width: 980px) {{ #semantic-explorer-shell {{ grid-template-columns:1fr; }} }}
    </style>
    <div id="semantic-explorer-main"></div>
    <aside id="semantic-explorer-sidebar">
      <form id="{FILTER_FORM_ID}">
        <div id="{COUNT_LABEL_ID}"></div>
        <label>Search title or snippet
          <input id="{SEARCH_INPUT_ID}" type="search" placeholder="Search semantic map" />
        </label>
        <label>Source
          <select id="{SOURCE_FILTER_ID}">
            <option value="">All sources</option>
          </select>
        </label>
        <label>Section
          <select id="{SECTION_FILTER_ID}">
            <option value="">All sections</option>
          </select>
        </label>
        <label>Published from
          <input id="{DATE_FROM_ID}" type="date" />
        </label>
        <label>Published to
          <input id="{DATE_TO_ID}" type="date" />
        </label>
        <button type="button" id="semantic-reset-filters">Reset filters</button>
      </form>
      <section id="{INSPECTOR_PANEL_ID}">
        <p class="semantic-empty">Click a point to inspect the article, then jump through its semantic neighbors without getting kicked into a new tab like it's 2009.</p>
      </section>
    </aside>`;
  plotContainer.parentElement.insertBefore(shell, plotContainer);
  shell.querySelector('#semantic-explorer-main').appendChild(plotContainer);
}}

function populateFilters() {{
  const sources = [...new Set(state.records.map((record) => record.source).filter(Boolean))].sort();
  const sections = [...new Set(state.records.map((record) => record.section).filter(Boolean))].sort();
  const sourceSelect = document.getElementById('{SOURCE_FILTER_ID}');
  const sectionSelect = document.getElementById('{SECTION_FILTER_ID}');
  sources.forEach((value) => sourceSelect.appendChild(new Option(value, value)));
  sections.forEach((value) => sectionSelect.appendChild(new Option(value, value)));
}}

function filteredRecords() {{
  const search = document.getElementById('{SEARCH_INPUT_ID}').value.trim().toLowerCase();
  const source = document.getElementById('{SOURCE_FILTER_ID}').value;
  const section = document.getElementById('{SECTION_FILTER_ID}').value;
  const dateFrom = document.getElementById('{DATE_FROM_ID}').value;
  const dateTo = document.getElementById('{DATE_TO_ID}').value;
  return state.records.filter((record) => {{
    const haystack = `${{record.title}} ${{record.summary_snippet}}`.toLowerCase();
    if (search && !haystack.includes(search)) return false;
    if (source && record.source !== source) return false;
    if (section && record.section !== section) return false;
    if (dateFrom && record.published_date && record.published_date < dateFrom) return false;
    if (dateTo && record.published_date && record.published_date > dateTo) return false;
    return true;
  }});
}}

function updateCountLabel(matches) {{
  document.getElementById('{COUNT_LABEL_ID}').textContent = `Showing ${{matches.length}} / ${{state.records.length}} articles`;
}}

function applyFilters() {{
  const matches = filteredRecords();
  const matchIds = new Set(matches.map((record) => record.article_id));
  plot.data.forEach((trace) => {{
    const xs = [];
    const ys = [];
    const text = [];
    const customdata = [];
    explorerRecords.forEach((record) => {{
      if (record.source !== trace.name || !matchIds.has(record.article_id)) return;
      xs.push(record.x);
      ys.push(record.y);
      text.push(record.title);
      customdata.push([record.article_id, record.source, record.title, record.url, record.published_at, record.display_date, record.section, record.summary_snippet, record.text_length, record.embedding_model, record.neighbors]);
    }});
    Plotly.restyle(plot, {{ x: [xs], y: [ys], text: [text], customdata: [customdata] }}, [trace.uid ? plot.data.findIndex((item) => item.uid === trace.uid) : plot.data.indexOf(trace)]);
  }});
  updateCountLabel(matches);
  if (state.selectedId && !matchIds.has(state.selectedId)) {{
    state.selectedId = null;
    renderInspector(null);
  }}
}}

function renderInspector(record) {{
  const inspector = document.getElementById('{INSPECTOR_PANEL_ID}');
  if (!record) {{
    inspector.innerHTML = `<p class="semantic-empty">No article selected. Click a point, use search, or filter the cloud until the chaos becomes useful.</p>`;
    return;
  }}
  const neighbors = (record.neighbors || []).map((neighbor, idx) => `
    <li>
      <button type="button" data-neighbor-id="${{neighbor.article_id}}">
        <strong>${{idx + 1}}. ${{escapeHtml(neighbor.title || '(untitled)')}}</strong><br>
        <span class="semantic-meta">similarity=${{Number(neighbor.similarity).toFixed(4)}} · ${{escapeHtml(neighbor.source)}} · ${{escapeHtml(neighbor.display_date || neighbor.published_date || '')}} · ${{escapeHtml(neighbor.section || 'sectionless')}}</span><br>
        <span class="semantic-snippet">${{escapeHtml(snippetLabel(neighbor.summary_snippet))}}</span>
      </button>
    </li>`).join('');
  inspector.innerHTML = `
    <h2>${{escapeHtml(record.title)}}</h2>
    <p class="semantic-meta">article_id=${{record.article_id}} · ${{escapeHtml(record.source)}} · ${{escapeHtml(record.display_date || record.published_date || '')}} · ${{escapeHtml(record.section || 'sectionless')}} · chars=${{record.text_length}}</p>
    <p class="semantic-snippet">${{escapeHtml(snippetLabel(record.summary_snippet))}}</p>
    <div class="semantic-actions">
      <a href="${{escapeHtml(record.url)}}" target="_blank" rel="noopener">Open original article</a>
      <button type="button" id="semantic-highlight-neighbors">Highlight neighbors</button>
      <button type="button" id="semantic-clear-selection">Clear selection</button>
    </div>
    <div class="semantic-neighbors">
      <h3>Nearest semantic neighbors</h3>
      <ul id="{NEIGHBOR_LIST_ID}">${{neighbors || '<li class="semantic-empty">No exported neighbors for this point.</li>'}}</ul>
    </div>`;

  inspector.querySelector('#semantic-clear-selection')?.addEventListener('click', () => {{
    state.selectedId = null;
    renderInspector(null);
  }});
  inspector.querySelector('#semantic-highlight-neighbors')?.addEventListener('click', () => highlightNeighbors(record));
  inspector.querySelectorAll('[data-neighbor-id]').forEach((button) => {{
    button.addEventListener('click', () => selectArticle(Number(button.dataset.neighborId)));
  }});
}}

function highlightNeighbors(record) {{
  const ids = new Set([record.article_id, ...(record.neighbors || []).map((neighbor) => neighbor.article_id)]);
  plot.data.forEach((trace, traceIndex) => {{
    const sizes = (trace.customdata || []).map((entry) => ids.has(entry[0]) ? 14 : 8);
    const opacities = (trace.customdata || []).map((entry) => ids.has(entry[0]) ? 1 : 0.2);
    Plotly.restyle(plot, {{ 'marker.size': [sizes], 'marker.opacity': [opacities] }}, [traceIndex]);
  }});
}}

function selectArticle(articleId) {{
  const record = state.byId.get(articleId);
  if (!record) return;
  state.selectedId = articleId;
  renderInspector(record);
  highlightNeighbors(record);
}}

function wireEvents() {{
  plot.on('plotly_click', (event) => {{
    const articleId = event.points?.[0]?.customdata?.[0];
    if (articleId != null) selectArticle(Number(articleId));
  }});
  ['{SEARCH_INPUT_ID}', '{SOURCE_FILTER_ID}', '{SECTION_FILTER_ID}', '{DATE_FROM_ID}', '{DATE_TO_ID}'].forEach((id) => {{
    document.getElementById(id).addEventListener('input', applyFilters);
    document.getElementById(id).addEventListener('change', applyFilters);
  }});
  document.getElementById('semantic-reset-filters').addEventListener('click', () => {{
    document.getElementById('{FILTER_FORM_ID}').reset();
    applyFilters();
  }});
}}

buildChrome();
populateFilters();
wireEvents();
applyFilters();
"""
