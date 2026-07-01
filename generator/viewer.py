import os
import json


def _build_class_detail(packages, module_name):
    detail = {}
    if not packages or module_name not in packages:
        return detail
    pkg = packages[module_name]
    for s in pkg.get("structs", []):
        attrs = []
        for t, n in s.attributes:
            vis = "-" if t == "const" else "+"
            attrs.append({"vis": vis, "name": n, "type": t})
        methods = []
        for m in s.methods:
            vis = "-" if m.is_static or m.file.endswith(".c") else "+"
            params = ", ".join(f"{n}: {t}" for t, n in m.parameters if t != "..." and n != "...")
            methods.append({"vis": vis, "name": m.name, "params": params, "ret": m.return_type})
        stype = "union" if s.stereotype == "union" else ("opaque" if s.stereotype == "opaque" else "struct")
        detail[s.name] = {"type": stype, "attrs": attrs, "methods": methods}
    for e in pkg.get("enums", []):
        detail[e.name] = {"type": "enum", "attrs": [{"vis": "+", "name": v, "type": ""} for v in e.values], "methods": []}
    for cb in pkg.get("callbacks", []):
        params = ", ".join(f"{n}: {t}" for t, n in cb.parameters if t != "...")
        detail[cb.name] = {"type": "callback", "attrs": [], "methods": [{"vis": "+", "name": "invoke", "params": params, "ret": cb.return_type}]}
    return detail


def generate_viewer_html(module_name, svg_path, module_names, packages=None, include_deps=None):
    try:
        with open(svg_path) as f:
            svg_expanded = f.read()
    except Exception:
        return None

    collapsed_path = svg_path.replace('.svg', '.collapsed.svg')
    try:
        with open(collapsed_path) as f:
            svg_collapsed = f.read()
    except Exception:
        svg_collapsed = svg_expanded

    include_deps = include_deps or []
    dep_list = [dst for src, dst in include_deps if src == module_name and dst != module_name]
    rev_deps = [src for src, dst in include_deps if dst == module_name and src != module_name]

    class_detail = _build_class_detail(packages, module_name)

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>c2uml — {module_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; overflow: hidden; display: flex; flex-direction: column; }}

.toolbar {{
  background: #1e293b; padding: 0.5em 1.2em; display: flex; align-items: center; gap: 1em;
  border-bottom: 1px solid #334155; z-index: 10; flex-shrink: 0;
}}
.toolbar a {{ color: #38bdf8; text-decoration: none; font-size: 0.9em; }}
.toolbar a:hover {{ color: #7dd3fc; }}
.breadcrumb {{ display: flex; align-items: center; gap: 0.4em; font-size: 0.9em; }}
.breadcrumb span {{ color: #64748b; }}
.module-title {{ color: #f1f5f9; font-weight: 600; font-size: 1.1em; }}
.toolbar-actions {{ margin-left: auto; display: flex; gap: 0.5em; }}
.toolbar-actions button {{
  background: #334155; color: #cbd5e1; border: 1px solid #475569; border-radius: 6px;
  padding: 0.35em 0.9em; cursor: pointer; font-size: 0.82em; transition: all 0.15s;
}}
.toolbar-actions button:hover {{ background: #475569; color: #f1f5f9; }}
.toolbar-actions button.active {{ background: #0ea5e9; border-color: #38bdf8; color: #fff; }}

.main {{ display: flex; flex: 1; overflow: hidden; }}

.sidebar {{
  width: 250px; background: #1e293b; border-right: 1px solid #334155;
  overflow-y: auto; flex-shrink: 0; display: flex; flex-direction: column;
}}
.sidebar.hidden {{ display: none; }}
.sidebar-section {{ padding: 0.7em 0.8em; border-bottom: 1px solid #334155; }}
.sidebar-section h3 {{ font-size: 0.7em; color: #64748b; text-transform: uppercase; margin-bottom: 0.5em; letter-spacing: 0.08em; }}
.sidebar-item {{
  padding: 0.3em 0.5em; border-radius: 5px; cursor: pointer; font-size: 0.82em;
  display: flex; align-items: center; gap: 0.5em; color: #94a3b8; transition: all 0.1s;
}}
.sidebar-item:hover {{ background: #334155; color: #f1f5f9; }}
.sidebar-item .badge {{
  font-size: 0.65em; padding: 0.15em 0.4em; border-radius: 3px; margin-left: auto; font-weight: 600;
}}
.badge-struct {{ background: #fef3c7; color: #92400e; }}
.badge-enum {{ background: #fecaca; color: #991b1b; }}
.badge-callback {{ background: #e9d5ff; color: #6b21a8; }}
.badge-union {{ background: #d1fae5; color: #065f46; }}
.badge-opaque {{ background: #dbeafe; color: #1e40af; }}
.dep-link {{ color: #38bdf8; text-decoration: none; display: block; padding: 0.25em 0.5em; border-radius: 5px; font-size: 0.82em; }}
.dep-link:hover {{ background: #334155; }}

.search-box {{ padding: 0.5em 0.8em; border-bottom: 1px solid #334155; }}
.search-box input {{
  width: 100%; padding: 0.4em 0.6em; background: #0f172a; border: 1px solid #334155;
  border-radius: 5px; color: #e2e8f0; font-size: 0.82em; outline: none;
}}
.search-box input:focus {{ border-color: #0ea5e9; }}

.viewer {{ flex: 1; overflow: auto; position: relative; background: #0f172a; }}
.viewer svg {{ display: block; }}
.viewer svg .highlighted {{ opacity: 1 !important; }}
.viewer svg .dimmed {{ opacity: 0.12 !important; }}

.popup {{
  position: fixed; background: #1e293b; border: 1px solid #334155; border-radius: 10px;
  padding: 0; font-size: 0.82em; z-index: 200; box-shadow: 0 8px 30px rgba(0,0,0,0.5);
  max-width: 420px; max-height: 70vh; display: none; overflow: hidden;
}}
.popup-header {{
  padding: 0.7em 1em; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 0.5em;
}}
.popup-header .popup-name {{ font-weight: 600; color: #38bdf8; font-size: 1.05em; }}
.popup-header .popup-type {{ color: #64748b; font-size: 0.85em; }}
.popup-header .popup-close {{
  margin-left: auto; cursor: pointer; color: #64748b; font-size: 1.2em; padding: 0 0.3em;
  border: none; background: none;
}}
.popup-header .popup-close:hover {{ color: #f1f5f9; }}

.legend-overlay {{
  position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 300;
  display: none; align-items: center; justify-content: center;
}}
.legend-overlay.visible {{ display: flex; }}
.legend-modal {{
  background: #1e293b; border: 1px solid #334155; border-radius: 12px;
  max-width: 520px; width: 90%; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
}}
.legend-header {{
  padding: 0.8em 1em; border-bottom: 1px solid #334155; display: flex;
  align-items: center; justify-content: space-between;
  font-weight: 600; color: #38bdf8; font-size: 1em;
}}
.legend-body {{ padding: 1em; }}
.legend-body table {{ width: 100%; border-collapse: collapse; margin-bottom: 0.8em; font-size: 0.82em; }}
.legend-body th {{ text-align: left; color: #64748b; font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.3em 0.5em; border-bottom: 1px solid #334155; }}
.legend-body td {{ padding: 0.3em 0.5em; color: #cbd5e1; }}
.lg-box {{ padding: 0.15em 0.5em; border-radius: 3px; color: #333; font-size: 0.85em; font-weight: 600; }}
.popup-body {{ padding: 0.5em 0; overflow-y: auto; max-height: calc(70vh - 3em); }}
.popup-group {{ padding: 0.3em 1em; }}
.popup-group-title {{ font-size: 0.7em; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3em; }}
.popup-row {{
  padding: 0.2em 0; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85em;
  color: #cbd5e1; display: flex; gap: 0.4em; line-height: 1.4;
}}
.popup-row .vis {{ color: #64748b; width: 1em; text-align: center; flex-shrink: 0; }}
.popup-row .vis.public {{ color: #22c55e; }}
.popup-row .vis.private {{ color: #ef4444; }}
.popup-row .mname {{ color: #e2e8f0; }}
.popup-row .mret {{ color: #64748b; }}
.popup-row .mparams {{ color: #94a3b8; }}
.popup-row.create .mname {{ color: #22c55e; }}
.popup-row.destroy .mname {{ color: #ef4444; }}
.popup-sep {{ border-top: 1px solid #334155; margin: 0.3em 1em; }}




</style>
</head><body>

<div class="toolbar">
  <div class="breadcrumb">
    <a href="index.html">index</a>
    <span>›</span>
    <span class="module-title">{module_name}</span>
  </div>
  <div class="toolbar-actions">
    <button onclick="toggleSidebar()" title="Toggle sidebar (S)">☰</button>
    <button onclick="toggleCollapse()" id="btnToggle" title="Toggle collapse">▬ Collapse</button>
    <button onclick="toggleLegend()" id="btnLegend" title="Legend">ℹ Legend</button>
    <button onclick="resetView()" title="Reset">⟲</button>
  </div>
</div>

<div class="main">
  <div class="sidebar" id="sidebar">
    <div class="search-box">
      <input type="text" id="classSearch" placeholder="Filter..." oninput="filterClasses()">
    </div>
    <div class="sidebar-section" id="classList">
      <h3>Classes</h3>
    </div>
    <div class="sidebar-section" id="depsList">
      <h3>Dependencies</h3>
    </div>
    <div class="sidebar-section" id="revDepsList">
      <h3>Used by</h3>
    </div>
  </div>

  <div class="viewer" id="viewer">
    <div id="svg-expanded">{svg_expanded}</div>
    <div id="svg-collapsed" style="display:none">{svg_collapsed}</div>
  </div>
</div>

<div class="popup" id="popup"></div>

<div class="legend-overlay" id="legendOverlay" onclick="toggleLegend()">
  <div class="legend-modal" onclick="event.stopPropagation()">
    <div class="legend-header">
      <span>c2uml — Legend</span>
      <button class="popup-close" onclick="toggleLegend()">✕</button>
    </div>
    <div class="legend-body">
      <table>
        <tr><th>Color</th><th>Element</th></tr>
        <tr><td><span class="lg-box" style="background:#FEF3C7">class</span></td><td>struct / typedef</td></tr>
        <tr><td><span class="lg-box" style="background:#EBF5FB">class</span></td><td>opaque pointer</td></tr>
        <tr><td><span class="lg-box" style="background:#D5F5E3">class</span></td><td>union</td></tr>
        <tr><td><span class="lg-box" style="background:#FADBD8">enum</span></td><td>enumeration</td></tr>
        <tr><td><span class="lg-box" style="background:#E8DAEF">iface</span></td><td>callback (fn ptr)</td></tr>
      </table>
      <table>
        <tr><th>Icon</th><th>Visibility</th></tr>
        <tr><td><span style="color:#22c55e">●</span> circle green</td><td>+ public attribute (.h)</td></tr>
        <tr><td><span style="color:#22c55e">○</span> circle green</td><td>+ public method (.h)</td></tr>
        <tr><td><span style="color:#ef4444">■</span> square red</td><td>- private attribute (.c)</td></tr>
        <tr><td><span style="color:#ef4444">□</span> square red</td><td>- private method (static/.c)</td></tr>
      </table>
      <table>
        <tr><th>Arrow</th><th>Relation</th></tr>
        <tr><td>*--</td><td>composition</td></tr>
        <tr><td>--></td><td>association (pointer)</td></tr>
        <tr><td>--|></td><td>inheritance (1st field)</td></tr>
        <tr><td>..></td><td>dependency / usage</td></tr>
      </table>
      <table>
        <tr><th>Style</th><th>Meaning</th></tr>
        <tr><td><span style="color:#22c55e">green text</span></td><td>&laquo;create&raquo; constructor</td></tr>
        <tr><td><span style="color:#ef4444">red text</span></td><td>&laquo;destroy&raquo; destructor</td></tr>
        <tr><td><span style="color:#3b82f6">blue text</span></td><td>macro function</td></tr>
        <tr><td><span style="color:#64748b;font-style:italic">gray italic</span></td><td>#define constant</td></tr>
      </table>
    </div>
  </div>
</div>




<script>
const MODULE = "{module_name}";
const ALL_MODULES = {json.dumps(sorted(module_names))};
const DEPS = {json.dumps(sorted(dep_list))};
const REV_DEPS = {json.dumps(sorted(rev_deps))};
const CLASS_DETAIL = {json.dumps(class_detail)};

let isCollapsed = false;

function init() {{
  setupSvgInteractions('svg-expanded');
  setupSvgInteractions('svg-collapsed');
  buildClassList();
  buildDepsList();
  document.addEventListener('click', (e) => {{
    if (!e.target.closest('.popup') && !e.target.closest('[id^="elem_"]'))
      closePopup();
  }});
}}

function setupSvgInteractions(containerId) {{
  const container = document.getElementById(containerId);
  const svg = container.querySelector('svg');
  if (!svg) return;

  svg.querySelectorAll('[id^="elem_"]').forEach(g => {{
    const name = g.id.replace('elem_', '');
    g.style.cursor = 'pointer';
    g.addEventListener('click', (e) => {{ e.stopPropagation(); if (isCollapsed) showPopup(e, name); }});
  }});

  svg.querySelectorAll('[id^="cluster_"]').forEach(g => {{
    const name = g.id.replace('cluster_', '');
    if (name !== MODULE && ALL_MODULES.includes(name)) {{
      g.style.cursor = 'pointer';
      g.addEventListener('click', () => {{ window.location.href = name + '.html'; }});
    }}
  }});

  svg.querySelectorAll('[id^="link_"]').forEach(g => {{
    g.style.cursor = 'pointer';
  }});
}}

function buildClassList() {{
  const container = document.getElementById('classList');
  const items = Object.keys(CLASS_DETAIL).sort();
  if (!items.length) {{ container.style.display = 'none'; return; }}
  items.forEach(name => {{
    const info = CLASS_DETAIL[name];
    const div = document.createElement('div');
    div.className = 'sidebar-item';
    div.dataset.name = name;
    div.innerHTML = `<span>${{name}}</span><span class="badge badge-${{info.type}}">${{info.type}}</span>`;
    div.addEventListener('click', () => scrollToClass(name));
    container.appendChild(div);
  }});
}}

function buildDepsList() {{
  const dc = document.getElementById('depsList');
  if (!DEPS.length) dc.style.display = 'none';
  else DEPS.forEach(d => {{ const a = document.createElement('a'); a.className = 'dep-link'; a.href = d+'.html'; a.textContent = '→ '+d; dc.appendChild(a); }});
  const rc = document.getElementById('revDepsList');
  if (!REV_DEPS.length) rc.style.display = 'none';
  else REV_DEPS.forEach(d => {{ const a = document.createElement('a'); a.className = 'dep-link'; a.href = d+'.html'; a.textContent = '← '+d; rc.appendChild(a); }});
}}

function showPopup(e, name) {{
  const info = CLASS_DETAIL[name];
  if (!info) return;

  let html = `<div class="popup-header">
    <span class="popup-name">${{name}}</span>
    <span class="popup-type">${{info.type}}</span>
    <button class="popup-close" onclick="closePopup()">✕</button>
  </div><div class="popup-body">`;

  if (info.attrs.length) {{
    html += `<div class="popup-group"><div class="popup-group-title">Attributes (${{info.attrs.length}})</div>`;
    info.attrs.forEach(a => {{
      const vc = a.vis === '+' ? 'public' : 'private';
      html += `<div class="popup-row"><span class="vis ${{vc}}">${{a.vis}}</span><span class="mname">${{a.name}}</span><span class="mret">${{a.type ? ': '+a.type : ''}}</span></div>`;
    }});
    html += `</div>`;
  }}

  if (info.attrs.length && info.methods.length) html += `<div class="popup-sep"></div>`;

  if (info.methods.length) {{
    html += `<div class="popup-group"><div class="popup-group-title">Methods (${{info.methods.length}})</div>`;
    info.methods.forEach(m => {{
      const vc = m.vis === '+' ? 'public' : 'private';
      let cls = 'popup-row';
      if (m.name.match(/_create|_new|_init|_open/)) cls += ' create';
      else if (m.name.match(/_destroy|_free|_close|_release/)) cls += ' destroy';
      html += `<div class="${{cls}}"><span class="vis ${{vc}}">${{m.vis}}</span><span class="mname">${{m.name}}</span><span class="mparams">(${{m.params}})</span><span class="mret">: ${{m.ret}}</span></div>`;
    }});
    html += `</div>`;
  }}

  if (!info.attrs.length && !info.methods.length) {{
    html += `<div class="popup-group" style="color:#64748b;padding:1em">No members</div>`;
  }}

  html += `</div>`;

  const popup = document.getElementById('popup');
  popup.innerHTML = html;
  popup.style.display = 'block';

  // Position near click
  const vw = window.innerWidth, vh = window.innerHeight;
  let left = e.clientX + 20, top = e.clientY - 40;
  popup.style.left = left + 'px';
  popup.style.top = top + 'px';

  // Adjust if overflows
  requestAnimationFrame(() => {{
    const r = popup.getBoundingClientRect();
    if (r.right > vw - 10) popup.style.left = (vw - r.width - 10) + 'px';
    if (r.bottom > vh - 10) popup.style.top = (vh - r.height - 10) + 'px';
    if (r.top < 10) popup.style.top = '10px';
  }});

  highlightClass(name);
}}

function closePopup() {{
  document.getElementById('popup').style.display = 'none';
  clearHighlight();
}}

function toggleLegend() {{
  document.getElementById('legendOverlay').classList.toggle('visible');
}}

function toggleCollapse() {{
  isCollapsed = !isCollapsed;
  document.getElementById('svg-expanded').style.display = isCollapsed ? 'none' : '';
  document.getElementById('svg-collapsed').style.display = isCollapsed ? '' : 'none';
  document.getElementById('btnToggle').innerHTML = isCollapsed ? '▤ Expand' : '▬ Collapse';
  document.getElementById('btnToggle').classList.toggle('active', isCollapsed);
  closePopup();
}}

function resetView() {{ if (isCollapsed) toggleCollapse(); closePopup(); }}

function scrollToClass(name) {{
  const cid = isCollapsed ? 'svg-collapsed' : 'svg-expanded';
  const g = document.querySelector('#' + cid + ' #elem_' + name);
  if (!g) return;
  const rect = g.querySelector('rect') || g.querySelector('path');
  if (!rect) return;
  const viewer = document.getElementById('viewer');
  const svg = document.querySelector('#' + cid + ' svg');
  const sr = svg.getBoundingClientRect();
  const vr = viewer.getBoundingClientRect();
  const x = parseFloat(rect.getAttribute('x') || 0);
  const y = parseFloat(rect.getAttribute('y') || 0);
  const sx = sr.width / svg.viewBox.baseVal.width;
  const sy = sr.height / svg.viewBox.baseVal.height;
  viewer.scrollTo({{ left: x*sx - vr.width/2 + 200, top: y*sy - vr.height/2 + 100, behavior: 'smooth' }});
  highlightClass(name);
  setTimeout(() => clearHighlight(), 2000);
}}

function highlightClass(name) {{
  const cid = isCollapsed ? 'svg-collapsed' : 'svg-expanded';
  const svg = document.querySelector('#' + cid + ' svg');
  if (!svg) return;
  const related = new Set(['elem_' + name]);
  svg.querySelectorAll('[id^="link_"]').forEach(g => {{
    if (g.id.includes(name)) {{
      related.add(g.id);
      const p = g.id.replace('link_', '').split('_to_');
      if (p.length === 2) {{ related.add('elem_'+p[0]); related.add('elem_'+p[1]); }}
    }}
  }});
  svg.querySelectorAll('g[id]').forEach(g => {{
    if (related.has(g.id)) {{ g.classList.add('highlighted'); g.classList.remove('dimmed'); }}
    else if (g.id.startsWith('elem_') || g.id.startsWith('link_')) {{ g.classList.add('dimmed'); g.classList.remove('highlighted'); }}
  }});
}}

function highlightRelation(linkG, cid) {{
  const svg = document.querySelector('#' + cid + ' svg');
  if (!svg) return;
  const related = new Set([linkG.id]);
  const p = linkG.id.replace('link_', '').split('_to_');
  if (p.length === 2) {{ related.add('elem_'+p[0]); related.add('elem_'+p[1]); }}
  svg.querySelectorAll('g[id]').forEach(g => {{
    if (related.has(g.id)) {{ g.classList.add('highlighted'); g.classList.remove('dimmed'); }}
    else if (g.id.startsWith('elem_') || g.id.startsWith('link_')) {{ g.classList.add('dimmed'); g.classList.remove('highlighted'); }}
  }});
}}

function clearHighlight(cid) {{
  const c = cid || (isCollapsed ? 'svg-collapsed' : 'svg-expanded');
  const svg = document.querySelector('#' + c + ' svg');
  if (svg) svg.querySelectorAll('.highlighted,.dimmed').forEach(g => g.classList.remove('highlighted','dimmed'));
}}


function toggleSidebar() {{ document.getElementById('sidebar').classList.toggle('hidden'); }}
function filterClasses() {{
  const q = document.getElementById('classSearch').value.toLowerCase();
  document.querySelectorAll('#classList .sidebar-item').forEach(el => {{
    el.style.display = el.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  }});
}}



init();
</script>
</body></html>"""

    return html
